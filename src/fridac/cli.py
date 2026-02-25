from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence, Tuple

from ._embedded_shim import SHIM_JS


@dataclass
class WatchedScript:
    original_path: Path
    shimmed_path: Path
    mtime_ns: int


def _write_shimmed_content(shim_text: str, original_path: Path, shimmed_path: Path) -> None:
    original_bytes = original_path.read_bytes()
    marker = f"\n// ---- SHIM END. SOURCE: {original_path} ----\n".encode("utf-8", errors="replace")

    with shimmed_path.open("wb") as temp_file:
        temp_file.write(shim_text.encode("utf-8"))
        temp_file.write(marker)
        temp_file.write(original_bytes)
        temp_file.flush()
        os.fsync(temp_file.fileno())


def _create_shimmed_script(shim_text: str, script_path: str) -> WatchedScript:
    original_path = Path(script_path).expanduser()
    if not original_path.exists() or not original_path.is_file():
        raise FileNotFoundError(f"Script file not found: {script_path}")

    fd, shimmed_path_str = tempfile.mkstemp(prefix="fridac_", suffix=".js")
    os.close(fd)

    shimmed_path = Path(shimmed_path_str)
    _write_shimmed_content(shim_text, original_path, shimmed_path)

    return WatchedScript(
        original_path=original_path.resolve(),
        shimmed_path=shimmed_path.resolve(),
        mtime_ns=original_path.stat().st_mtime_ns,
    )


def _rewrite_arguments(args: Sequence[str], shim_text: str) -> Tuple[List[str], List[WatchedScript]]:
    rewritten: List[str] = []
    watched: List[WatchedScript] = []

    i = 0
    while i < len(args):
        arg = args[i]

        if arg in ("-l", "--load"):
            if i + 1 >= len(args):
                raise ValueError(f"Missing script path after {arg}")

            loaded_script = args[i + 1]
            watched_script = _create_shimmed_script(shim_text, loaded_script)
            watched.append(watched_script)

            rewritten.append(arg)
            rewritten.append(str(watched_script.shimmed_path))
            i += 2
            continue

        if arg.startswith("--load="):
            loaded_script = arg.split("=", 1)[1]
            watched_script = _create_shimmed_script(shim_text, loaded_script)
            watched.append(watched_script)

            rewritten.append(f"--load={watched_script.shimmed_path}")
            i += 1
            continue

        rewritten.append(arg)
        i += 1

    return rewritten, watched


def _watch_loop(stop_event: threading.Event, watched: Sequence[WatchedScript], shim_text: str) -> None:
    while not stop_event.wait(0.5):
        for script in watched:
            try:
                current_mtime_ns = script.original_path.stat().st_mtime_ns
            except OSError:
                continue

            if current_mtime_ns != script.mtime_ns:
                try:
                    _write_shimmed_content(shim_text, script.original_path, script.shimmed_path)
                    script.mtime_ns = current_mtime_ns
                except OSError as exc:
                    print(
                        f"Failed to refresh shimmed script for {script.original_path}: {exc}",
                        file=sys.stderr,
                    )


def _cleanup_temp_scripts(watched: Sequence[WatchedScript]) -> None:
    for script in watched:
        try:
            script.shimmed_path.unlink(missing_ok=True)
        except OSError:
            pass


def _find_frida_binary() -> str | None:
    from_path = shutil.which("frida")
    if from_path is not None:
        return from_path

    candidate_names = ("frida", "frida.exe", "frida.cmd", "frida.bat")
    candidate_dirs = []

    try:
        candidate_dirs.append(Path(sys.executable).resolve().parent)
    except Exception:
        pass

    try:
        candidate_dirs.append(Path(sys.argv[0]).resolve().parent)
    except Exception:
        pass

    seen = set()
    for directory in candidate_dirs:
        directory_key = str(directory)
        if directory_key in seen:
            continue
        seen.add(directory_key)

        for candidate_name in candidate_names:
            candidate = directory / candidate_name
            if candidate.exists() and candidate.is_file():
                return str(candidate)

    return None


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)

    frida_path = _find_frida_binary()
    if frida_path is None:
        print("Frida binary not found in PATH: frida", file=sys.stderr)
        return 1

    if not SHIM_JS.strip():
        print("Embedded compatibility shim is empty.", file=sys.stderr)
        return 1

    try:
        rewritten_args, watched_scripts = _rewrite_arguments(args, SHIM_JS)
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    full_command = [frida_path, *rewritten_args]

    stop_event = threading.Event()
    watcher_thread = None
    if watched_scripts:
        watcher_thread = threading.Thread(
            target=_watch_loop,
            args=(stop_event, watched_scripts, SHIM_JS),
            daemon=True,
        )
        watcher_thread.start()

    process: subprocess.Popen[bytes] | None = None
    try:
        process = subprocess.Popen(full_command)
        return process.wait()
    except KeyboardInterrupt:
        if process is not None:
            try:
                process.terminate()
            except OSError:
                pass
            try:
                return process.wait(timeout=5)
            except Exception:
                return 130
        return 130
    except OSError as exc:
        print(f"Failed to run Frida: {exc}", file=sys.stderr)
        return 1
    finally:
        stop_event.set()
        if watcher_thread is not None:
            watcher_thread.join(timeout=1)
        _cleanup_temp_scripts(watched_scripts)
