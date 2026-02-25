import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from fridac import cli  # noqa: E402


class DummyProcess:
    def __init__(self, command):
        self.command = command
        self.returncode = 0

    def wait(self, timeout=None):
        return self.returncode

    def terminate(self):
        self.returncode = 130


class CliTests(unittest.TestCase):
    def test_rewrite_arguments_replaces_dash_l_script(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / "old.js"
            script_path.write_text("console.log('hello');\n", encoding="utf-8")

            rewritten, watched = cli._rewrite_arguments(
                ["-U", "-l", str(script_path), "com.example.app"],
                "/*shim*/",
            )

            self.assertEqual(rewritten[0], "-U")
            self.assertEqual(rewritten[1], "-l")
            self.assertNotEqual(rewritten[2], str(script_path))
            self.assertEqual(rewritten[3], "com.example.app")
            self.assertEqual(len(watched), 1)

            shimmed_path = Path(rewritten[2])
            self.assertTrue(shimmed_path.exists())
            shimmed_text = shimmed_path.read_text(encoding="utf-8")
            self.assertIn("/*shim*/", shimmed_text)
            self.assertIn("console.log('hello');", shimmed_text)

            cli._cleanup_temp_scripts(watched)
            self.assertFalse(shimmed_path.exists())

    def test_rewrite_arguments_replaces_load_equals(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / "old.js"
            script_path.write_text("send('ok');\n", encoding="utf-8")

            rewritten, watched = cli._rewrite_arguments(
                [f"--load={script_path}", "target_process"],
                "/*shim*/",
            )

            self.assertEqual(len(watched), 1)
            self.assertTrue(rewritten[0].startswith("--load="))
            shimmed_path = Path(rewritten[0].split("=", 1)[1])
            self.assertTrue(shimmed_path.exists())
            self.assertEqual(rewritten[1], "target_process")

            cli._cleanup_temp_scripts(watched)

    def test_main_proxies_to_frida_and_cleans_up_temp_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / "legacy.js"
            script_path.write_text("console.log('legacy');\n", encoding="utf-8")

            created_commands = []

            def fake_popen(command):
                created_commands.append(command)
                return DummyProcess(command)

            with patch("fridac.cli.shutil.which", return_value="frida"), patch(
                "fridac.cli.subprocess.Popen",
                side_effect=fake_popen,
            ):
                exit_code = cli.main(["-l", str(script_path), "target"])

            self.assertEqual(exit_code, 0)
            self.assertEqual(len(created_commands), 1)
            self.assertEqual(created_commands[0][0], "frida")
            self.assertEqual(created_commands[0][1], "-l")
            self.assertEqual(created_commands[0][3], "target")

            shimmed_path = Path(created_commands[0][2])
            self.assertFalse(shimmed_path.exists())

    def test_main_returns_error_when_frida_missing(self):
        with patch("fridac.cli._find_frida_binary", return_value=None):
            exit_code = cli.main([])
        self.assertEqual(exit_code, 1)

    def test_find_frida_binary_checks_python_sibling_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            scripts_dir = Path(temp_dir)
            fake_python = scripts_dir / "python.exe"
            fake_frida = scripts_dir / "frida.exe"
            fake_python.write_text("", encoding="utf-8")
            fake_frida.write_text("", encoding="utf-8")

            with patch("fridac.cli.shutil.which", return_value=None), patch.object(
                sys,
                "executable",
                str(fake_python),
            ):
                frida_binary = cli._find_frida_binary()

            self.assertEqual(frida_binary, str(fake_frida))


if __name__ == "__main__":
    unittest.main()
