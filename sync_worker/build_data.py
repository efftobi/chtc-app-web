"""
Erzeugt data.json für die CHTC-App aus hockey.de + den Konfig-Dateien in data/.

Läuft automatisch per GitHub Actions (.github/workflows/update-data.yml).
Sicherheitsnetz: Wenn eine Teamseite nicht abrufbar/parsebar ist, bleiben
die bisherigen Daten dieses Teams aus der bestehenden data.json erhalten —
die App zeigt dann einfach den letzten bekannten Stand.

Aufruf:
    python sync_worker/build_data.py             # normal (holt hockey.de)
    python sync_worker/build_data.py --offline   # Test ohne Netz (Fixture für wu12)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent))
from parser import parse_teamseite  # noqa: E402

ROOT = Path(__file__).parent.parent
UA = "CHTC-Vereins-App Daten-Update (github.com, Kontakt: tobias@fusten.de)"
OFFENE_ORTE: set[str] = set()   # Spielorte ohne Adresseintrag in data/venues.json


def lade_json(pfad: Path, default):
    try:
        return json.loads(pfad.read_text(encoding="utf-8"))
    except Exception:
        return default


def venue_key(rohtext: str | None, venues: dict) -> str | None:
    if not rohtext:
        return None
    low = rohtext.lower()
    for key, v in venues.items():
        if key.startswith("_"):
            continue
        for muster in v.get("erkennung", []):
            if muster.lower() in low:
                return key
    return None


def hole_team(team: dict, venues: dict, offline: bool):
    """Liefert (matches, standings) im App-Format oder None bei Fehler."""
    if offline:
        html = (Path(__file__).parent / "fixtures" / "team_page.html").read_text(encoding="utf-8")
    else:
        r = httpx.get(team["url"], headers={"User-Agent": UA}, timeout=30, follow_redirects=True)
        r.raise_for_status()
        html = r.text

    seite = parse_teamseite(html)
    if not seite.spiele and not seite.tabelle:
        return None  # nichts erkannt -> alte Daten behalten

    matches = []
    for s in seite.spiele:
        m = {
            "d": s.datum.isoformat(),
            "heim": s.heim,
            "gast": s.gast,
            "h": "crefelder" in s.heim.lower(),
        }
        if s.anpfiff:
            m["zeit"] = s.anpfiff.strftime("%H:%M")
        if s.gespielt:
            m["th"], m["tg"] = s.tore_heim, s.tore_gast
        vk = venue_key(s.venue_rohtext, venues)
        if vk:
            m["ort"] = vk
        elif s.venue_rohtext:
            m["ortName"] = s.venue_rohtext          # unbekannter Ort: Name trotzdem anzeigen
            OFFENE_ORTE.add(s.venue_rohtext)
        matches.append(m)

    standings = []
    for z in seite.tabelle:
        row = [z.platz, z.mannschaft, z.spiele, z.siege, z.unentschieden,
               z.niederlagen, f"{z.tore}:{z.gegentore}", z.punkte]
        if z.ist_eigenes_team:
            row.append(True)
        standings.append(row)

    return matches, standings


def main() -> None:
    offline = "--offline" in sys.argv

    teams_cfg = lade_json(ROOT / "data" / "teams.json", {"teams": []})["teams"]
    infos = {k: v for k, v in lade_json(ROOT / "data" / "infos.json", {}).items() if not k.startswith("_")}
    trainings = {k: v for k, v in lade_json(ROOT / "data" / "trainings.json", {}).items() if not k.startswith("_")}
    venues_cfg = lade_json(ROOT / "data" / "venues.json", {})
    venues = {k: {kk: vv for kk, vv in v.items() if kk != "erkennung"}
              for k, v in venues_cfg.items() if not k.startswith("_")}

    alt = lade_json(ROOT / "data.json", {})
    alt_matches = alt.get("matches", {})
    alt_standings = alt.get("standings", {})

    out_teams, out_matches, out_standings = [], {}, {}
    fehler = []

    for t in teams_cfg:
        eintrag = {k: t[k] for k in ("id", "badge", "name", "liga", "gruppe") if k in t}
        if t.get("jugend"):
            eintrag["jugend"] = True

        if t.get("url"):
            try:
                ergebnis = None if offline and t["id"] != "wu12" else hole_team(t, venues_cfg, offline)
            except Exception as e:
                ergebnis = None
                fehler.append(f"{t['id']}: {e}")
            if ergebnis:
                out_matches[t["id"]], out_standings[t["id"]] = ergebnis
                eintrag["live"] = True
            elif t["id"] in alt_matches:  # Sicherheitsnetz: alten Stand behalten
                out_matches[t["id"]] = alt_matches[t["id"]]
                out_standings[t["id"]] = alt_standings.get(t["id"], [])
                eintrag["live"] = True
                fehler.append(f"{t['id']}: alte Daten beibehalten")
        out_teams.append(eintrag)

    berlin = timezone(timedelta(hours=2))  # Feldsaison = Sommerzeit
    data = {
        # Meta-Felder bewusst am Dateianfang (gut auffindbar):
        "stand": datetime.now(berlin).strftime("%d.%m.%Y %H:%M"),
        "venues_offen": sorted(OFFENE_ORTE),   # Spielorte, denen noch eine Adresse fehlt
        "teams": out_teams,
        "matches": out_matches,
        "standings": out_standings,
        "trainings": trainings,
        "venues": venues,
        "infos": infos,
    }
    (ROOT / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    # Kalender-Dateien (.ics) für alle kommenden Spiele — iOS öffnet echte
    # .ics-URLs mit der nativen "Termin hinzufügen"-Vorschau zuverlässig.
    import re as _re
    import shutil as _shutil
    ics_dir = ROOT / "ics"
    if ics_dir.exists():
        _shutil.rmtree(ics_dir)
    ics_dir.mkdir()

    def _slug(s):
        return _re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

    def _esc(s):
        return s.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;")

    ics_anzahl = 0
    for tid, ms in out_matches.items():
        for m in ms:
            if "th" in m:  # gespielt -> kein Kalendereintrag nötig
                continue
            dt = m["d"].replace("-", "")
            zeilen = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//CHTC//App//DE",
                      "BEGIN:VEVENT", f"UID:chtc-{tid}-{dt}-{_slug(m['gast'])}@chtc"]
            if m.get("zeit"):
                hh, mm = m["zeit"].split(":")
                zeilen.append(f"DTSTART:{dt}T{hh}{mm}00")
                zeilen.append(f"DTEND:{dt}T{int(hh) + 2:02d}{mm}00")
            else:
                zeilen.append(f"DTSTART;VALUE=DATE:{dt}")
            v = venues.get(m.get("ort", ""), {})
            ort_text = ", ".join(x for x in [v.get("name"), v.get("adresse"), v.get("ort")] if x) or m.get("ortName", "")
            zeilen += [f"SUMMARY:{_esc('🏑 ' + m['heim'] + ' – ' + m['gast'])}",
                       f"LOCATION:{_esc(ort_text)}", "END:VEVENT", "END:VCALENDAR"]
            (ics_dir / f"{tid}-{m['d']}-{_slug(m['gast'])}.ics").write_text("\r\n".join(zeilen), encoding="utf-8")
            ics_anzahl += 1
    print(f"{ics_anzahl} Kalender-Dateien in ics/ geschrieben")

    print(f"data.json geschrieben: {len(out_matches)} Teams mit Daten, "
          f"{sum(len(m) for m in out_matches.values())} Spiele, "
          f"{len(OFFENE_ORTE)} Spielorte ohne Adresse")
    for f in fehler:
        print(f"  ⚠ {f}", file=sys.stderr)
    # Fehler führen NICHT zu Exit 1 — alte Daten bleiben ja erhalten.


if __name__ == "__main__":
    main()
