"""Build out-of-context.html: pulls recent Daily Nebraskan stories (RSS + article pages)
and embeds a pool of pull-quotes into the game template.

Usage: python3 scripts/build_ootc.py
Stdlib only. Re-run (e.g. daily via GitHub Actions) to refresh the pool.
The pool holds only stories published today; the puzzle is keyed to that date.
"""
import html, json, re, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

root = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0 (OutOfContext game builder)"}
RSS = "https://www.dailynebraskan.com/search/?f=rss&t=article&l=50&s=start_time&sd=desc"
STOP = set("the a an of in on to for and at is are was were with by from as it its be this that his her their has have had will after over into".split())


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read().decode("utf-8", "replace")


def words(s):
    return [w for w in re.findall(r"[a-z']+", s.lower()) if w not in STOP and len(w) > 2]


def paragraphs(page):
    m = re.search(r'id="article-body".*?>(.*?)(?:id="asset-footer|class="[^"]*article-bottom|</article>)', page, re.S)
    body = m.group(1) if m else page
    body = re.sub(r"<(figure|figcaption|script|style|aside)\b.*?</\1>", " ", body, flags=re.S)
    out = []
    for p in re.findall(r"<p\b[^>]*>(.*?)</p>", body, re.S):
        t = html.unescape(re.sub(r"<[^>]+>", "", p)).replace("\xa0", " ")
        t = re.sub(r"\s+", " ", t).strip()
        if len(t) > 40:
            out.append(t)
    return out


def stem(w):
    return re.sub(r"(ing|ed|es|s|'s)$", "", w) if len(w) > 4 else w


def leaks(q, title):
    """True if the quote shares ANY keyword with the headline (it would give the answer away)."""
    return bool({stem(w) for w in words(title)} & {stem(w) for w in words(q)})


def quotes(paras, title):
    tw = set(words(title))
    res = []
    for p in paras:
        for q in re.findall(r"[“\"]([^”\"]{30,260})[”\"]", p):
            q = q.strip()
            n = len(q.split())
            if n < 7 or n > 34:
                continue
            # skip quotes that are fragments or just echo the headline
            if q[0].islower() or leaks(q, title):
                continue
            if not re.search(r"\b(said|says|told|added|explained|noted|stated|wrote|expressed|according|continued|recalled|joked|emphasized|shared)\b", p) and not re.match(r"(I|We|It|My|This|That|There|You|They)\b", q):
                continue  # narration, not a spoken quote
            q = re.sub(r"[,;:]$", ".", q)
            if not re.search(r"[.!?]$", q):
                q += "."
            res.append({"q": q, "ctx": p})
    return res


SUMS = json.loads((root / "scripts" / "summaries.json").read_text())


def summary(q, ps, title):
    """Hand-written summary of what the quote refers to (summaries.json, keyed by the quote's opening words).
    Falls back to the story's opening paragraph when a new quote has no summary yet."""
    for k, v in SUMS.items():
        if q.startswith(k):
            return v
    print("  ! no summary for:", q[:60])
    lede = next((p for p in ps if not p.startswith(("“", '"'))), title)
    return "From a story that begins: " + lede


root_xml = ET.fromstring(get(RSS))
stories = []
for it in root_xml.iter("item"):
    title = html.unescape(it.findtext("title", "")).strip()
    link = it.findtext("link", "").strip()
    if not title or not link or title.lower().startswith(("opinion:", "podcast")):
        continue
    try:
        ps = paragraphs(get(link))
    except Exception as e:
        print("skip", title, e)
        continue
    qs = quotes(ps, title)[:2]
    if not qs:
        continue
    for q in qs:
        q["sum"] = summary(q["q"], ps, title)
        del q["ctx"]
    section = link.split("dailynebraskan.com/")[1].split("/")[0]
    date = datetime.strptime(it.findtext("pubDate")[:16], "%a, %d %b %Y").strftime("%Y-%m-%d")
    stories.append({"title": title, "url": link, "section": section, "date": date,
                    "author": it.findtext("{http://purl.org/dc/elements/1.1/}creator", "").strip(),
                    "quotes": qs})
    print(f"{len(qs):2d} quotes  {title}")

print(len(stories), "new stories with quotes")

# Only stories published today (the feed's own dates, Central time).
MIN_POOL = 5
today = datetime.now().strftime("%Y-%m-%d")
pool = [st for st in stories if st["date"] == today]
if len(pool) < MIN_POOL:
    raise SystemExit(f"Only {len(pool)} stories with usable quotes were published today ({today}); need {MIN_POOL}. "
                     "Not overwriting out-of-context.html. Try again later in the day.")
sections = {}
for st in pool:
    sections[st["section"]] = sections.get(st["section"], 0) + 1
print(len(pool), f"stories published {today}:", sections)

tpl = (root / "scripts" / "ootc.template.html").read_text()
built = datetime.now().strftime("%Y-%m-%d")
data = json.dumps(pool, ensure_ascii=False).replace("</", "<\\/")
(root / "out-of-context.html").write_text(tpl.replace("/*POOL*/[]", data).replace("{{BUILT}}", built).replace("{{POOLDATE}}", today))
