"""Build groundhog.html: embeds predictions.csv (groundhog-day.com) into the search page template.

Usage: python3 scripts/build_groundhog.py path/to/predictions.csv
"""
import csv, json, sys, collections
from pathlib import Path

root = Path(__file__).resolve().parent.parent
rows = list(csv.DictReader(open(sys.argv[1], encoding="utf-8")))

# Consensus per year: majority of all predictors with a recorded shadow value.
votes = collections.defaultdict(collections.Counter)
for r in rows:
    if r["shadow"] in ("0", "1"):
        votes[r["year"]][r["shadow"]] += 1
consensus = {}
for y, c in votes.items():
    if c["0"] != c["1"]:
        consensus[y] = "1" if c["1"] > c["0"] else "0"

animals = {}
for r in rows:
    a = animals.setdefault(r["id"], {
        "id": int(r["id"]), "slug": r["slug"], "name": r["name"], "city": r["city"],
        "region": r["region"], "country": r["country"], "type": r["type"],
        "active": r["active"] == "1", "desc": r["description"], "img": r["image"],
        "now": r["currentPrediction"], "p": [],
    })
    s = r["shadow"]
    a["p"].append([int(r["year"]), int(s) if s in ("0", "1") else None])
for a in animals.values():
    a["p"].sort()

data = {
    "consensus": {y: int(v) for y, v in consensus.items()},
    "animals": sorted(animals.values(), key=lambda a: a["name"]),
}
tpl = (root / "scripts" / "groundhog.template.html").read_text(encoding="utf-8")
out = tpl.replace("/*__DATA__*/null", json.dumps(data, separators=(",", ":"), ensure_ascii=False))
(root / "groundhog.html").write_text(out, encoding="utf-8")
print(len(animals), "predictors,", len(rows), "predictions,", len(out) // 1024, "KB")
