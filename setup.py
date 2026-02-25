from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py


def _generate_embedded_shim() -> None:
    project_root = Path(__file__).resolve().parent
    shim_source = project_root / "src" / "fridac" / "shim.js"
    shim_target = project_root / "src" / "fridac" / "_embedded_shim.py"

    shim_text = shim_source.read_text(encoding="utf-8")
    module_text = (
        '"""Auto-generated file. Run tools/embed_shim.py to regenerate."""\n\n'
        f"SHIM_JS = {shim_text!r}\n"
    )
    shim_target.write_text(module_text, encoding="utf-8")


class build_py(_build_py):
    def run(self) -> None:
        _generate_embedded_shim()
        super().run()


setup(cmdclass={"build_py": build_py})
