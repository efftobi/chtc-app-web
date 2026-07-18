# CHTC-App — Betrieb über GitHub

Die App läuft komplett über dein GitHub-Repository, kostenlos:

- **GitHub Pages** liefert die App aus (hast du schon eingerichtet).
- **GitHub Actions** (Automatik-Dienst von GitHub) holt nach Zeitplan die
  Spieldaten von hockey.de und schreibt sie in die Datei `data.json`.
- Die App lädt bei jedem Öffnen die aktuelle `data.json` — niemand muss
  etwas neu installieren.

## Einmalig einrichten (nach dem Hochladen dieses Pakets)

1. **Alle Dateien/Ordner dieses Pakets ins Repository hochladen** („Add file
   → Upload files", alles markieren und hineinziehen — auch die Ordner
   `data`, `sync_worker` und `.github`). Bestehende Dateien werden ersetzt.
   Falls der versteckte Ordner `.github` sich nicht ziehen lässt: im Repo
   „Add file → Create new file", als Namen
   `.github/workflows/update-data.yml` eintippen und den Inhalt der Datei
   hineinkopieren.
2. Im Repository auf den Reiter **Actions** klicken und ggf. bestätigen
   („I understand my workflows, enable them").
3. Links den Workflow **„Daten-Update von hockey.de"** anklicken →
   rechts **„Run workflow"** → grüner Button. Das ist ein manueller Testlauf.
4. Nach ca. 1 Minute zeigt der Lauf einen grünen Haken ✓ und im Repository
   erscheint ein neuer Commit „Daten-Update …" vom `chtc-daten-bot`.
   Beim ersten Mal bitte das Ergebnis an Claude melden (grüner Haken oder
   rotes ✗ und was im Log steht) — falls hockey.de anders aufgebaut ist als
   erwartet, wird der Parser einmalig nachjustiert.

## Wie aktualisiert sich die App danach?

**Spiele, Ergebnisse, Tabellen — vollautomatisch.** Der Zeitplan läuft
tagsüber alle 2 Stunden, am Wochenende (Spieltage) alle 20 Minuten.
Findet der Lauf neue Daten, ändert sich `data.json`; jeder, der die App
öffnet, sieht sofort den neuen Stand. Ist hockey.de mal nicht erreichbar,
bleibt einfach der letzte bekannte Stand stehen — die App geht nie kaputt.

**Trainingszeiten, Adressen, neue Teams — per Klick auf GitHub.** Die
Dateien im Ordner `data/` sind bewusst einfach gehalten:
`trainings.json` (Trainingszeiten), `venues.json` (Spielort-Adressen),
`teams.json` (Mannschaften + ihre hockey.de-Adresse). Auf GitHub die Datei
anklicken → Stift-Symbol → ändern → „Commit changes". Beim nächsten
Daten-Lauf (oder sofort per „Run workflow") übernimmt die App die Änderung.
So kann später auch die Geschäftsstelle Zeiten pflegen — ganz ohne
Programmierung.

**Die App selbst (Design, Funktionen) — Dateien hochladen.** Wenn Claude
eine neue Version liefert, lädst du die Dateien wie gewohnt hoch. Die App
auf den Handys holt sich die neue Version beim nächsten Öffnen von selbst.

## Gut zu wissen

- Bei öffentlichen Repositories sind GitHub Actions und Pages kostenlos,
  ohne Minuten-Limit.
- GitHub pausiert Zeitpläne, wenn in einem Repository ~60 Tage gar nichts
  passiert. Sollte das (z. B. nach der Winterpause) passieren: Reiter
  Actions öffnen — dort erscheint ein Hinweis mit „Enable"-Knopf.
- Saisonwechsel Feld ↔ Halle: in `data/teams.json` die neuen Team-URLs der
  Hallensaison eintragen (macht Claude gern mit dir zusammen).
- Was noch fehlt bzw. später kommt: Push-Benachrichtigungen (dafür braucht
  es die native App oder einen kleinen Zusatzdienst) und die Team-URLs der
  übrigen Mannschaften, sobald deren Saison 2026/27 auf hockey.de angelegt ist.
