import httpx
from pathlib import Path
from bs4 import BeautifulSoup

URL = ("https://www.hockeybundesliga.de/club/crefelder-hockey-und-tennisclub-1890-chtc/"
       "feld-2026-jugend/whv-regionalliga-wu12-2026-whvrlwu12-1642/crefelder-htc-chtc-47875")

out = []
r = httpx.get(URL, headers={"User-Agent": "CHTC-Vereins-App Diagnose"}, timeout=30, follow_redirects=True)
out.append(f"STATUS {r.status_code} | FINAL-URL {r.url} | LAENGE {len(r.text)}")
soup = BeautifulSoup(r.text, "html.parser")
out.append(f"TITLE: {soup.title.get_text(strip=True) if soup.title else '-'}")
tables = soup.find_all("table")
out.append(f"ANZAHL TABLES: {len(tables)}")
for i, t in enumerate(tables[:6]):
    ths = [th.get_text(' ', strip=True) for th in t.find_all("th")[:12]]
    tds = [td.get_text(' ', strip=True) for td in t.find_all("td")[:14]]
    out.append(f"TABLE {i}: th={ths}")
    out.append(f"TABLE {i}: erste td={tds}")
treffer = 0
for el in soup.find_all(True):
    txt = el.get_text(" ", strip=True)
    if "Crefelder" in txt and len(txt) < 300:
        klasse = " ".join(el.get("class", []))
        out.append(f"EL <{el.name} class='{klasse}'> :: {txt[:220]}")
        treffer += 1
        if treffer >= 25:
            break
pos = r.text.find("Crefelder")
out.append("=== ROH-HTML-AUSSCHNITT ===")
out.append(r.text[max(0, pos - 1500):pos + 3500])
Path("debug.txt").write_text("\n".join(out), encoding="utf-8")
print("debug.txt geschrieben")
