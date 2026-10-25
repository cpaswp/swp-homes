#!/usr/bin/env python3
"""Static release gate for SWP-HOMES; does not replace Django/PostgreSQL integration tests."""
from pathlib import Path
import ast
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
errors = []
py_files = sorted(p for p in ROOT.rglob("*.py") if "__pycache__" not in p.parts)
for path in py_files:
    try:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError) as exc:
        errors.append(f"Python syntax: {path.relative_to(ROOT)}: {exc}")

required = [
    ROOT / "manage.py",
    ROOT / "requirements.txt",
    ROOT / "config" / "settings.py",
    ROOT / "core" / "models.py",
    ROOT / "leasing" / "services.py",
]
for path in required:
    if not path.is_file():
        errors.append(f"Missing required file: {path.relative_to(ROOT)}")

if errors:
    print("STATIC RELEASE GATE: FAIL")
    print("\n".join(f"- {e}" for e in errors))
    sys.exit(1)

print(f"STATIC RELEASE GATE: PASS ({len(py_files)} Python files parsed)")
print("LIMITATION: Django checks, migrations, PostgreSQL integration, email OTP, tenant DB isolation, and accounting reconciliation are not tested by this script.")
