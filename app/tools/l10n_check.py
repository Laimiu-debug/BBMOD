"""Run isolated independent-localization acceptance checks. Never touches game files."""
from pathlib import Path
import subprocess
import sys

if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    raise SystemExit(subprocess.call([sys.executable, '-B', '-m', 'pytest',
        str(root / 'tests/test_independent_l10n.py'), '-q', '-p', 'no:cacheprovider'], cwd=root))
