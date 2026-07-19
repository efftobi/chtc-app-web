"""
Parser für hockey.de-Teamseiten (Portal hockeybundesliga.de / *.hockey.de).

Zwei Strategien:
1. "Portal-Strategie" (primär): exakt auf die echte Seitenstruktur zugeschnitten,
   ermittelt per Diagnose-Lauf vom 19.07.2026:
     - Datums-Überschriften:  <div class="schedule-lite__title">Sonntag, 26. April 2026</div>
     - Spielzeilen:           <div class="table-schedule-condensed__table-row">
         Heim:   .table-schedule-condensed__country--left  .mc-lite__team--desktop
         Gast:   .table-schedule-condensed__country--right .mc-lite__team--desktop
         Stand:  .table-schedule-condensed__time-wrapper   ("3 : 1 2 : 0" = End- u. Halbzeitstand;
                 Klasse ...--final nur bei gespielten Spielen, sonst Anstoßzeit)
         Ort:    .table-schedule-condensed__table-cell--venue
     - Tabelle: <table>, Spalten: Platz | Mannschaft | Sp. | S | SnP | U | N | Tore | Diff | Pkt.
2. Generische Fallback-Strategie: erkennt Tabellen über Spaltenköpfe und Spiele
   über Datums-Muster — falls das Portal sein Layout ändert.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, time

from bs4 import BeautifulSoup

EIGENES_TEAM = "Crefelder"  # Erkennung eigener Zeilen/Spiele

MONATE = {
    "januar": 1, "februar": 2, "märz": 3, "april": 4, "mai": 5, "juni": 6,
    "juli": 7, "august": 8, "september": 9, "oktober": 10, "november": 11, "dezember": 12,
}

RE_DATUM_NUM = re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b")
RE_DATUM_TXT = re.compile(r"\b(\d{1,2})\.\s*([A-Za-zäöüÄÖÜ]+)\s*(\d{4})\b")
RE_UHRZEIT = re.compile(r"\b(\d{1,2}):(\d{2})\s*(?:Uhr)?\b")
RE_ERGEBNIS = re.compile(r"(?<!\d)(\d{1,2})\s*:\s*(\d{1,2})(?!\d)")


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


# ----------------------------------------------------------------- Helpers
def parse_datum(text: str) -> date | None:
    m = RE_DATUM_NUM.search(text)
    if m:
        d, mo, y = (int(x) for x in m.groups())
        if 1 <= mo <= 12:
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
    return time(h, mi) if h < 24 and mi < 60 else None


def _zahl(s: str) -> int:
    m = re.search(r"-?\d+", s)
    return int(m.group()) if m else 0


def _teamname(el) -> str | None:
    """Teamname aus einer Zelle: bevorzugt den Desktop-Span (ohne Kürzel)."""
    if el is None:
        return None
    span = el.select_one(".mc-lite__team--desktop")
    if span:
        t = span.get_text(" ", strip=True)
        if t:
            return t
    t = el.get_text(" ", strip=True)
    if not t:
        return None
    # Angehängtes Kürzel entfernen: "Crefelder HTC CHTC" -> "Crefelder HTC"
    teile = t.split()
    if len(teile) >= 2 and teile[-1].isupper() and 2 <= len(teile[-1]) <= 6:
        t = " ".join(teile[:-1])
    return t.strip() or None


# ----------------------------------------------------------------- Strategie 1: Portal
def parse_spiele_portal(soup: BeautifulSoup) -> list[Spiel]:
    spiele: list[Spiel] = []
    gesehen: set[tuple] = set()
    aktuelles_datum: date | None = None

    def klasse_passt(c):
        return c in ("schedule-lite__title", "table-schedule-condensed__table-row")

    for el in soup.find_all(class_=klasse_passt):
        klassen = el.get("class", [])
        if "schedule-lite__title" in klassen:
            d = parse_datum(el.get_text(" ", strip=True))
            if d:
                aktuelles_datum = d
            continue

        if aktuelles_datum is None:
            continue

        heim = _teamname(el.select_one(".table-schedule-condensed__country--left"))
        gast = _teamname(el.select_one(".table-schedule-condensed__country--right"))
        if not heim or not gast:
            continue

        anpfiff = None
        th = tg = None
        wrapper = el.select_one("[class*='table-schedule-condensed__time-wrapper']")
        if wrapper is not None:
            wtext = wrapper.get_text(" ", strip=True)
            wklassen = " ".join(wrapper.get("class", []))
            if "--final" in wklassen:
                m = RE_ERGEBNIS.search(wtext)   # erster Treffer = Endstand
                if m:
                    th, tg = int(m.group(1)), int(m.group(2))
            else:
                anpfiff = parse_uhrzeit(wtext)

        venue_el = el.select_one(".table-schedule-condensed__table-cell--venue")
        venue = venue_el.get_text(" ", strip=True) if venue_el else None

        key = (aktuelles_datum, heim.lower(), gast.lower())
        if key in gesehen:
            continue
        gesehen.add(key)
        spiele.append(Spiel(aktuelles_datum, anpfiff, heim, gast, th, tg, venue or None))

    spiele.sort(key=lambda s: s.datum)
    return spiele


def parse_tabelle_portal(soup: BeautifulSoup) -> list[TabellenZeile]:
    for table in soup.find_all("table"):
        header = [th.get_text(" ", strip=True).lower().rstrip(".") for th in table.find_all("th")]
        if not header or "pkt" not in header:
            continue

        # Spaltenpositionen dynamisch aus dem Header (2 unbeschriftete Spalten
        # vorweg: Platz + Mannschaft). Fallback auf das bekannte Layout.
        def idx(name: str, fallback: int) -> int:
            return header.index(name) if name in header else fallback

        i_sp, i_s, i_snp = idx("sp", 2), idx("s", 3), idx("snp", -1)
        i_u, i_n, i_tore = idx("u", 5), idx("n", 6), idx("tore", 7)
        i_pkt = idx("pkt", len(header) - 1)

        breite = len(header)
        trs = [tr for tr in table.find_all("tr") if tr.find_all("td")]
        if trs:
            bloecke = [tr.find_all("td") for tr in trs]
        else:  # Zellen ohne <tr>-Struktur: flach in Headerbreite zerlegen
            zellen = table.find_all("td")
            bloecke = [zellen[i:i + breite] for i in range(0, len(zellen), breite)]

        zeilen: list[TabellenZeile] = []
        for tds in bloecke:
            if len(tds) < min(breite, 8):
                continue
            texte = [td.get_text(" ", strip=True) for td in tds]
            platz = _zahl(texte[0])
            name = _teamname(tds[1])
            if platz <= 0 or not name:
                continue
            tm = re.search(r"(\d+)\s*:\s*(\d+)", texte[i_tore]) if i_tore < len(texte) else None
            tore, gegen = (int(tm.group(1)), int(tm.group(2))) if tm else (0, 0)
            siege = _zahl(texte[i_s]) + (_zahl(texte[i_snp]) if 0 <= i_snp < len(texte) else 0)
            zeilen.append(TabellenZeile(
                platz=platz, mannschaft=name,
                spiele=_zahl(texte[i_sp]), siege=siege,
                unentschieden=_zahl(texte[i_u]), niederlagen=_zahl(texte[i_n]),
                tore=tore, gegentore=gegen, punkte=_zahl(texte[i_pkt]),
                ist_eigenes_team=EIGENES_TEAM.lower() in name.lower(),
            ))
        if len(zeilen) >= 3:
            return zeilen
    return []


# ----------------------------------------------------------------- Strategie 2: Fallback
def parse_spiele_generisch(soup: BeautifulSoup) -> list[Spiel]:
    spiele: list[Spiel] = []
    gesehen: set[tuple] = set()

    for el in soup.find_all(["tr", "li", "div", "article"]):
        text = el.get_text(" ", strip=True)
        if len(text) > 400 or EIGENES_TEAM.lower() not in text.lower():
            continue
        datum = parse_datum(text)
        if datum is None:
            continue
        if any(parse_datum(c.get_text(" ", strip=True) or "") and
               EIGENES_TEAM.lower() in (c.get_text(" ", strip=True) or "").lower()
               for c in el.find_all(["tr", "li", "div", "article"])):
            continue

        kandidaten = [c.get_text(" ", strip=True)
                      for c in el.find_all(class_=re.compile(r"(team|club|home|away|heim|gast)", re.I))]
        kandidaten = [k for k in kandidaten if 2 < len(k) < 60]
        rest = RE_UHRZEIT.sub(" ", RE_DATUM_TXT.sub(" ", RE_DATUM_NUM.sub(" ", text)))
        if len(kandidaten) >= 2:
            heim, gast = kandidaten[0], kandidaten[1]
        else:
            m = re.search(r"([A-ZÄÖÜ][^–\-:]{2,50})\s*[–\-]\s*([A-ZÄÖÜ][^–\-:]{2,50})", rest)
            if not m:
                continue
            heim, gast = m.group(1).strip(), m.group(2).strip()

        erg = RE_ERGEBNIS.search(rest)
        th, tg = (int(erg.group(1)), int(erg.group(2))) if erg else (None, None)

        v = el.find(class_=re.compile(r"(venue|ort|location|anlage)", re.I))
        venue = v.get_text(" ", strip=True) if v else None

        key = (datum, heim.lower(), gast.lower())
        if key in gesehen:
            continue
        gesehen.add(key)
        spiele.append(Spiel(datum, parse_uhrzeit(text), heim, gast, th, tg, venue))

    spiele.sort(key=lambda s: s.datum)
    return spiele


def parse_tabelle_generisch(soup: BeautifulSoup) -> list[TabellenZeile]:
    for table in soup.find_all("table"):
        header_text = " ".join(th.get_text(" ", strip=True).lower() for th in table.find_all("th"))
        if "mannschaft" not in header_text or ("punkte" not in header_text and "pkt" not in header_text):
            continue
        zeilen: list[TabellenZeile] = []
        for tr in table.find_all("tr"):
            tds = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
            if len(tds) < 6:
                continue
            try:
                platz, mannschaft = _zahl(tds[0]), tds[1]
                sp, s, u, n = (_zahl(x) for x in tds[2:6])
                tm = re.search(r"(\d+)\s*:\s*(\d+)", tds[6] if len(tds) > 6 else "")
                tore, gegen = (int(tm.group(1)), int(tm.group(2))) if tm else (0, 0)
                punkte = _zahl(tds[7]) if len(tds) > 7 else _zahl(tds[-1])
            except (ValueError, IndexError):
                continue
            if platz <= 0 or not mannschaft:
                continue
            zeilen.append(TabellenZeile(platz, mannschaft, sp, s, u, n, tore, gegen, punkte,
                                        ist_eigenes_team=EIGENES_TEAM.lower() in mannschaft.lower()))
        if len(zeilen) >= 3:
            return zeilen
    return []


# ----------------------------------------------------------------- Einstieg
def parse_teamseite(html: str) -> TeamSeite:
    soup = BeautifulSoup(html, "html.parser")
    spiele = parse_spiele_portal(soup) or parse_spiele_generisch(soup)
    tabelle = parse_tabelle_portal(soup) or parse_tabelle_generisch(soup)
    return TeamSeite(spiele=spiele, tabelle=tabelle)
