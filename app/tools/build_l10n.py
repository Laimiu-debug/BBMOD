"""Build the independent package from a user's game archives, without installing it."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.l10n import PACKAGE_NAME, build_localization


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game", type=Path, required=True, help="Game root containing data/")
    parser.add_argument("--output", type=Path, default=Path("dist") / PACKAGE_NAME)
    args = parser.parse_args()
    result = build_localization(args.game, {}, args.output)
    args.output.with_suffix(".manifest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
