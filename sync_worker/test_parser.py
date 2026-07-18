from datetime import date, time
from pathlib import Path

from parser import parse_teamseite

HTML = (Path(__file__).parent / "fixtures" / "team_page.html").read_text(encoding="utf-8")


def test_spiele_werden_erkannt():
    seite = parse_teamseite(HTML)
    assert len(seite.spiele) == 4

    s1 = seite.spiele[0]
    assert s1.datum == date(2026, 4, 26)
    assert s1.heim == "Crefelder HTC"
    assert s1.gast == "HTC Schwarz-Weiß Neuss"
    assert (s1.tore_heim, s1.tore_gast) == (3, 1)
    assert "Gerd-Wellen" in s1.venue_rohtext


def test_auswaertsspiel_und_ergebnis():
    seite = parse_teamseite(HTML)
    s = next(x for x in seite.spiele if x.datum == date(2026, 5, 3))
    assert s.heim == "HTC Uhlenhorst Mülheim"
    assert (s.tore_heim, s.tore_gast) == (1, 4)   # CHTC gewinnt auswärts 4:1


def test_geplantes_spiel_ohne_ergebnis_mit_uhrzeit():
    seite = parse_teamseite(HTML)
    s = next(x for x in seite.spiele if x.datum == date(2026, 9, 13))
    assert s.tore_heim is None and s.tore_gast is None
    assert s.anpfiff == time(14, 0)
    assert not s.gespielt


def test_tabelle():
    seite = parse_teamseite(HTML)
    assert len(seite.tabelle) == 5
    erste = seite.tabelle[0]
    assert erste.platz == 1
    assert erste.mannschaft == "Crefelder HTC"
    assert erste.ist_eigenes_team
    assert (erste.spiele, erste.siege, erste.punkte) == (9, 8, 24)
    assert (erste.tore, erste.gegentore) == (32, 9)
    letzte = seite.tabelle[-1]
    assert letzte.mannschaft == "ETB Essen"
    assert not letzte.ist_eigenes_team
