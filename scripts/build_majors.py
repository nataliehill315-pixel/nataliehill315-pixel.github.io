"""Build majors.html: embeds the UNL "Majors by College" enrollment workbook into the search page template.

Usage: python3 scripts/build_majors.py "path/to/DR12573 - Majors by College (Fall25-Fall16).xlsx"

Needs openpyxl (pip install openpyxl). One sheet per fall term; columns are
College, Major Name, Maj 1, Deg ID, Total Students.
"""
import json, re, sys
from pathlib import Path
import openpyxl

root = Path(__file__).resolve().parent.parent
wb = openpyxl.load_workbook(sys.argv[1], data_only=True)

# The registrar renamed this college partway through the data.
COLLEGE_ALIAS = {"Business Administration": "Business"}
KEEP_UPPER = {"UNL", "UNO", "UNK", "UNMC", "NCTA", "IEP", "CASNR", "ANR", "EHS", "FPA", "ENG", "CYAF",
              "HRTM", "RNAS", "CFA", "IT", "II", "III", "K-3", "US", "N2V", "EV", "NDEG", "JMC", "TV", "GIS", "PHD"}
SMALL = {"and", "of", "in", "for", "the", "to", "a", "an", "or", "on"}


def pretty(name):
    def fix(m):
        w = m.group(0)
        if w.upper() in KEEP_UPPER:
            return w.upper()
        return w.capitalize()
    s = re.sub(r"[A-Za-z0-9'\-]+", fix, name.strip())
    # lowercase small words except at the start
    parts = s.split(" ")
    return " ".join(p if i == 0 or p.lower() not in SMALL else p.lower() for i, p in enumerate(parts))


years, table = [], {}
for ws in wb:
    y = int(re.search(r"20\d\d", ws.title).group())
    years.append(y)
for ws in wb:
    y = int(re.search(r"20\d\d", ws.title).group())
    for r in list(ws.iter_rows(values_only=True))[1:]:
        college, name, _code, deg, n = (list(r) + [None] * 5)[:5]
        if not name or not str(name).strip():
            continue  # blank rows / sheet totals
        try:
            n = int(float(n))
        except (TypeError, ValueError):
            continue
        college = COLLEGE_ALIAS.get(college, college)
        deg = (deg or "").strip() or "—"
        key = str(name).strip()
        row = table.setdefault(key, {}).setdefault((college, deg), {})
        row[y] = row.get(y, 0) + n

years.sort()
majors = []
for name, groups in table.items():
    rows = [[c, d, [g.get(y) for y in years]] for (c, d), g in sorted(groups.items())]
    majors.append({"n": pretty(name), "raw": name, "r": rows})
majors.sort(key=lambda m: m["n"])

data = {"years": years, "majors": majors}
tpl = (root / "scripts" / "majors.template.html").read_text(encoding="utf-8")
out = tpl.replace("/*__DATA__*/null", json.dumps(data, separators=(",", ":"), ensure_ascii=False))
(root / "majors.html").write_text(out, encoding="utf-8")
print(len(majors), "majors,", years[0], "-", years[-1], ",", len(out) // 1024, "KB")
