import re
import httpx
from pathlib import Path
from bs4 import BeautifulSoup

URL = ("https://www.hockeybundesliga.de/club/crefelder-hockey-und-tennisclub-1890-chtc/"
       "feld-2026-jugend/whv-regionalliga-wu12-2026-whvrlwu12-1642/crefelder-htc-chtc-47875")

r = httpx.get(URL, headers={"User-Agent": "CHTC-Vereins-App Diagnose"}, timeout=30, follow_redirects=True)
soup = BeautifulSoup(r.text, "html.parser")
out = [f"STATUS {r.status_code} LAENGE {len(r.text)}"]

classes = set()
for el in soup.find_all(True):
    for c in el.get("class", []):
        if re.search(r"(schedule|date|match|game|day|kick|time)", c, re.I):
            classes.add(c)
out.append("KLASSEN: " + " | ".join(sorted(classes)))

row = soup.find(class_=re.compile("table-schedule"))
if row is None:
    out.append("KEIN table-schedule-Element gefunden!")
else:
    cont = row
    for _ in range(3):
        if cont.parent is not None:
            cont = cont.parent
    out.append(f"CONTAINER: <{cont.name} class='{' '.join(cont.get('class', []))}'>")
    out.append("=== STRUKTUR (Element / Klassen / Textanfang) ===")
    zeilen = 0
    for el in cont.find_all(True):
        cls = " ".join(el.get("class", []))
        if not cls:
            continue
        eigen = el.get_text(" ", strip=True)[:100]
        out.append(f"<{el.name}> [{cls}] :: {eigen}")
        zeilen += 1
        if zeilen >= 220:
            out.append("... (gekürzt)")
            break

Path("debug.txt").write_text("\n".join(out), encoding="utf-8")
print("debug.txt geschrieben")
