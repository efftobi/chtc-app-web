"""
Parser für hockey.de-Teamseiten (neues Portal, serverseitig gerendert).

Bewusst ROBUST statt selektor-genau gebaut: Statt auf konkrete CSS-Klassen
zu setzen (die sich ändern können), werden
  - die Ligatabelle über ihre Spaltenüberschriften erkannt und
  - Spiele über Datums-/Ergebnismuster im Text erkannt.
Damit übersteht der Parser kleinere Layout-Änderungen des Portals.
Vor dem Produktivbetrieb einmal gegen die echten Seiten laufen lassen
(`python sync.py --dry-run`) und die Ausgabe prüfen.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, time

from bs4 import BeautifulSoup

EIGENES_TEAM = "Crefelder HTC"  # Erkennung "eigene" Zeile/Spiele (auch "Crefelder HTC 2" etc.)

MONATE = {
    "januar": 1, "februar": 2, "märz": 3, "april": 4, "mai": 5, "juni": 6,
    "juli": 7, "august": 8, "september": 9, "oktober": 10, "november": 11, "dezember": 12,
}

RE_DATUM_NUM = re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b")
RE_DATUM_TXT = re.compile(r"\b(\d{1,2})\.\s*([A-Za-zäöüÄÖÜ]+)\s*(\d{4})\b")
RE_UHRZEIT = re.compile(r"\b(\d{1,2}):(\d{2})\s*(?:Uhr)?\b")
RE_ERGEBNIS = re.compile(r"(?<!\d)(\d{1,2})\s*:\s*(\d{1,2})(?!\d)(\s*n\.[PV]\.)?")

TABELLEN_HEADER = {"platz", "mannschaft", "punkte"}  # Muss-Spalten einer Ligatabelle


@dataclass
class Spiel:
    datum: date
    anpfiff: time | None
    heim: str
    gast: str
    tore_heim: int | None
    tore_gast: int | None
    venue_rohtext: str | None = None

    @property
    def gespielt(self) -> bool:
        return self.tore_heim is not None


@dataclass
class TabellenZeile:
    platz: int
    mannschaft: str
    spiele: int
    siege: int
    unentschieden: int
    niederlagen: int
    tore: int
    gegentore: int
    punkte: int
    ist_eigenes_team: bool = False


@dataclass
class TeamSeite:
    spiele: list[Spiel] = field(default_factory=list)
    tabelle: list[TabellenZeile] = field(default_factory=list)


def parse_datum(text: str) -> date | None:
    m = RE_DATUM_NUM.search(text)
    if m:
        d, mo, y = (int(x) for x in m.groups())
        return date(y, mo, d)
    m = RE_DATUM_TXT.search(text)
    if m:
        d, name, y = m.group(1), m.group(2).lower(), m.group(3)
        if name in MONATE:
            return date(int(y), MONATE[name], int(d))
    return None


def parse_uhrzeit(text: str) -> time | None:
    m = RE_UHRZEIT.search(text)
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2))
    if 0 <= h < 24:
        return time(h, mi)
    return None


def _zahl(s: str) -> int:
    m = re.search(r"-?\d+", s)
    return int(m.group()) if m else 0


def parse_tabelle(soup: BeautifulSoup) -> list[TabellenZeile]:
    """Findet die Ligatabelle anhand ihrer Kopfzeile (Platz/Mannschaft/Punkte)."""
    for table in soup.find_all("table"):
        header = [th.get_text(" ", strip=True).lower() for th in table.find_all("th")]
        header_text = " ".join(header)
        if not header:
            continue
        if not all(any(k in h for h in header) or k in header_text for k in TABELLEN_HEADER):
            # Erkennt auch Kurzformen wie "Pkt." über das Fallback unten
            if "pkt" not in header_text or "mannschaft" not in header_text:
                continue
        zeilen: list[TabellenZeile] = []
        for tr in table.find_all("tr"):
            tds = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
            if len(tds) < 6:
                continue
            # Erwartete Reihenfolge: Platz, Mannschaft, Spiele, S, U, N, Tore, Punkte
            try:
                platz = _zahl(tds[0])
                mannschaft = tds[1]
                sp, s, u, n = (_zahl(x) for x in tds[2:6])
                tore_txt = tds[6] if len(tds) > 6 else "0:0"
                tm = re.search(r"(\d+)\s*:\s*(\d+)", tore_txt)
                tore, gegentore = (int(tm.group(1)), int(tm.group(2))) if tm else (0, 0)
                punkte = _zahl(tds[7]) if len(tds) > 7 else _zahl(tds[-1])
            except (ValueError, IndexError):
                continue
            if platz <= 0 or not mannschaft:
                continue
            zeilen.append(TabellenZeile(
                platz, mannschaft, sp, s, u, n, tore, gegentore, punkte,
                ist_eigenes_team=EIGENES_TEAM.lower() in mannschaft.lower(),
            ))
        if len(zeilen) >= 3:  # plausible Ligatabelle
            return zeilen
    return []


def parse_spiele(soup: BeautifulSoup) -> list[Spiel]:
    """
    Erkennt Spiel-Container: kleinste HTML-Elemente, die ein Datum UND
    zwei Mannschaftsnamen (davon einer das eigene Team) enthalten.
    """
    spiele: list[Spiel] = []
    gesehen: set[tuple] = set()

    for el in soup.find_all(["tr", "li", "div", "article"]):
        text = el.get_text(" ", strip=True)
        if len(text) > 400 or EIGENES_TEAM.lower() not in text.lower():
            continue
        datum = parse_datum(text)
        if datum is None:
            continue
        # Kleinstes Element wollen wir: Kinder, die selbst schon passen, überspringen
        if any(parse_datum(c.get_text(" ", strip=True) or "") and
               EIGENES_TEAM.lower() in (c.get_text(" ", strip=True) or "").lower()
               for c in el.find_all(["tr", "li", "div", "article"])):
            continue

        teams = _extrahiere_teams(el, text)
        if teams is None:
            continue
        heim, gast = teams

        erg = RE_ERGEBNIS.search(_ohne_datum_und_zeit(text))
        th, tg = (int(erg.group(1)), int(erg.group(2))) if erg else (None, None)

        venue = _extrahiere_venue(el)
        key = (datum, heim.lower(), gast.lower())
        if key in gesehen:
            continue
        gesehen.add(key)
        spiele.append(Spiel(datum, parse_uhrzeit(text), heim, gast, th, tg, venue))

    spiele.sort(key=lambda s: s.datum)
    return spiele


def _ohne_datum_und_zeit(text: str) -> str:
    """Entfernt Datums-/Zeitangaben, damit '26.04.2026' oder '14:00' nicht als Ergebnis zählt."""
    text = RE_DATUM_NUM.sub(" ", text)
    text = RE_DATUM_TXT.sub(" ", text)
    text = RE_UHRZEIT.sub(" ", text)
    return text


def _extrahiere_teams(el, text: str) -> tuple[str, str] | None:
    """Heim/Gast aus Struktur (bevorzugt) oder Text 'A - B' ermitteln."""
    kandidaten = [c.get_text(" ", strip=True) for c in el.find_all(class_=re.compile(r"(team|club|home|away|heim|gast)", re.I))]
    kandidaten = [k for k in kandidaten if 2 < len(k) < 60]
    if len(kandidaten) >= 2:
        return kandidaten[0], kandidaten[1]
    # Fallback: "Mannschaft A – Mannschaft B" im Text
    m = re.search(r"([A-ZÄÖÜ][^–\-:]{2,50})\s*[–\-]\s*([A-ZÄÖÜ][^–\-:]{2,50})", _ohne_datum_und_zeit(text))
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return None


def _extrahiere_venue(el) -> str | None:
    v = el.find(class_=re.compile(r"(venue|ort|location|anlage)", re.I))
    if v:
        t = v.get_text(" ", strip=True)
        return t or None
    m = re.search(r"(?:Spielort|Ort)\s*:\s*([^|\n]+)", el.get_text(" ", strip=True))
    return m.group(1).strip() if m else None


def parse_teamseite(html: str) -> TeamSeite:
    soup = BeautifulSoup(html, "html.parser")
    return TeamSeite(spiele=parse_spiele(soup), tabelle=parse_tabelle(soup))
