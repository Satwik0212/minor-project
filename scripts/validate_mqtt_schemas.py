import json
from pathlib import Path
base=Path(__file__).resolve().parents[1]/"docs"/"schemas"
files=sorted(base.glob("*.schema.json"))
if not files: raise SystemExit("No schema files found")
for f in files:
 json.loads(f.read_text(encoding="utf-8")); print("OK", f.name)
