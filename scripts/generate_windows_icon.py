from __future__ import annotations

from pathlib import Path

from PIL import Image


def main() -> int:
    project_root = Path(__file__).resolve().parent.parent
    source = project_root / "windows_app" / "assets" / "app_icon.png"
    target = project_root / "windows_app" / "assets" / "app_icon.ico"

    if not source.exists():
        raise FileNotFoundError(f"Icone PNG nao encontrado: {source}")

    with Image.open(source) as image:
        image.save(
            target,
            format="ICO",
            sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
        )

    print(f"Icone gerado em: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())