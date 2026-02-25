from pathlib import Path


def generate_embedded_shim() -> None:
    project_root = Path(__file__).resolve().parents[1]
    shim_source = project_root / "src" / "fridac" / "shim.js"
    shim_target = project_root / "src" / "fridac" / "_embedded_shim.py"

    shim_text = shim_source.read_text(encoding="utf-8")
    module_text = (
        '"""Auto-generated file. Run tools/embed_shim.py to regenerate."""\n\n'
        f"SHIM_JS = {shim_text!r}\n"
    )
    shim_target.write_text(module_text, encoding="utf-8")


if __name__ == "__main__":
    generate_embedded_shim()
