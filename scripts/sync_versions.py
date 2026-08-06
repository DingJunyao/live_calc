"""将根目录 app-info.json 中的版本号同步到各包元数据文件。"""

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
APP_INFO_PATH = ROOT / "app-info.json"
FRONTEND_PACKAGE = ROOT / "frontend" / "package.json"
FRONTEND_LOCK = ROOT / "frontend" / "package-lock.json"
BACKEND_PYPROJECT = ROOT / "backend" / "pyproject.toml"


def _read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data: dict) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main() -> None:
    version = _read_json(APP_INFO_PATH)["version"]

    for path in (FRONTEND_PACKAGE, FRONTEND_LOCK):
        data = _read_json(path)
        data["version"] = version
        packages = data.get("packages")
        if isinstance(packages, dict) and "" in packages:
            packages[""]["version"] = version
        _write_json(path, data)

    pyproject = BACKEND_PYPROJECT.read_bytes().decode("utf-8")
    pyproject = re.sub(
        r'(?m)^(version = ")[^"]*(")',
        rf"\g<1>{version}\g<2>",
        pyproject,
        count=1,
    )
    BACKEND_PYPROJECT.write_bytes(pyproject.encode("utf-8"))

    print(f"Synced version {version} to frontend/package.json, frontend/package-lock.json, backend/pyproject.toml")


if __name__ == "__main__":
    main()
