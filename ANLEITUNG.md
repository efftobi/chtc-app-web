# CHTC Hockey Web-App — in 10 Minuten auf deinem iPhone

Die App in diesem Ordner ist eine fertige PWA (Progressive Web App).
Damit sie auf dein iPhone kommt, muss sie einmal ins Internet (kostenlos),
danach installierst du sie in Safari mit zwei Tipps.

## Schritt 1: Veröffentlichen (einmalig, kostenlos)

**Variante A — GitHub Pages (empfohlen, passt zum Sync-Worker-Repo):**
1. Auf github.com ein neues Repository anlegen, z. B. `chtc-app-web` (public).
2. Alle Dateien aus diesem Ordner hochladen (auch per Drag & Drop im Browser:
   „uploading an existing file").
3. Im Repo: **Settings → Pages** → unter „Branch" `main` und `/ (root)` wählen → Save.
4. Nach 1–2 Minuten ist die App erreichbar unter:
   `https://DEIN-GITHUB-NAME.github.io/chtc-app-web/`

**Variante B — Netlify:** Auf netlify.com anmelden → „Add new site → Deploy manually"
→ diesen Ordner ins Fenster ziehen. Fertige URL erscheint sofort.

Später kann die App auf eine eigene Domain umziehen (z. B. app.crefelder-htc.de
per DNS-Eintrag) — für den Test ist das nicht nötig.

## Schritt 2: Auf dem iPhone installieren

1. Die URL in **Safari** öffnen (wichtig: Safari, nicht Chrome).
2. Teilen-Symbol (Quadrat mit Pfeil) → **„Zum Home-Bildschirm"** → Hinzufügen.
3. Auf dem Home-Bildschirm liegt jetzt „CHTC" mit eigenem Icon — startet
   im Vollbild wie eine normale App und funktioniert dank Offline-Cache
   auch bei schlechtem Empfang am Platz.

Den Link kannst du genauso an alle Eltern/Spielerinnen der wU12 weitergeben.

## Was die App aktuell kann

- wU12 (WHV Regionalliga Feld 2026) mit **echten Daten**: alle Spiele &
  Ergebnisse, komplette Tabelle, kommende Spiele mit Spielort, Route
  (Apple Maps) und „In Kalender"-Funktion.
- Favoriten (Stern) werden auf dem Gerät gespeichert.
- Übrige Teams sind angelegt; ihre Spieldaten kommen mit der Backend-Anbindung.
- Trainingszeiten aller drei wU12-Teams sind hinterlegt (Di/Do „Tokio",
  Fr „Paris" nur wU12-1).

## Nächster Ausbauschritt

In `index.html` oben steht ein `CONFIG`-Block. Sobald das Supabase-Backend
aus dem Phase-1-Paket eingerichtet ist, werden dort `SUPABASE_URL` und
`SUPABASE_ANON_KEY` eingetragen — dann lädt die App live die Daten aller
Teams, die der Sync-Worker von hockey.de holt. (Die Lade-Logik dafür bauen
wir ein, wenn das Backend steht.)
