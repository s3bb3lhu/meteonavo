# Installation und Betrieb von Meteonavo

Diese Anleitung enthält ausschließlich generische Beispielwerte. Betreiberadressen, API-Keys und vorhandene Zugänge werden nicht mitgeliefert. Funktionsübersicht und Containeraufgaben: [README.md](README.md). Veröffentlichung ohne private Daten: [PUBLICATION.md](PUBLICATION.md).

## Voraussetzungen

Linux mit AMD64/x86-64, Docker Engine und Compose, Internetzugang zu den ausgewählten Quellen und ein freier TCP-Port (standardmäßig 7373). Vorher auf dem eigenen Server mit `ss -lnt` und `docker ps` prüfen, ob der Port bereits verwendet wird. Keine anderen Anwendungen oder Firewalls pauschal umkonfigurieren.

## Öffentliche Installation

1. Projekt aus der autorisierten Veröffentlichung beziehen und entpacken beziehungsweise klonen.
2. Im Projektverzeichnis `cp .env.example .env` ausführen und den eigenen Port sowie zunächst `FPS=15` wählen.
3. Ein gültiges Zertifikat für den eigenen Host/die eigene IP bereitstellen. Ausstellung und Erneuerung beim gewählten Zertifikatsanbieter einrichten.
4. [HTTPS-DEPLOYMENT.md](HTTPS-DEPLOYMENT.md) befolgen. Das HTTPS-Overlay hält Verwaltung und Vorschau auf HTTPS sowie Xtream und die vorgesehenen IPTV-Ausgaben auf HTTP desselben Projektports.
5. Container mit `docker compose build` und `docker compose up -d` erstellen/starten. Mit `docker compose ps` den Zustand prüfen.
6. `https://DEIN-HOST:7373` öffnen und das Eigentümerkonto anlegen. Keine Standardzugangsdaten, kein manuell einzutragender Admin-Token, kein SSH-Tunnel für die Einrichtung.
7. Einen Kanal konfigurieren, Ort/GPS bestätigen, Seiten auswählen und den Kanal aktivieren. Anschließend Vorschau und echten Stream separat prüfen.

Die Basis-Compose-Datei ohne HTTPS-Overlay stellt HTTP bereit und ist nur für lokale Entwicklung beziehungsweise ein isoliertes Testnetz vorgesehen. Sie installiert keine Zertifikate automatisch. Die normale Compose-Konfiguration bindet keinen Docker-Socket in die Anwendung ein und startet die Anwendung nicht als privilegierten Container. Chromium wird innerhalb des Containers mit `--no-sandbox` betrieben; Docker-Isolation ersetzt keine Garantie gegen alle Browserrisiken.

## Optionale Betreiberzugänge

- Google Maps: eigener Browser-Key mit Abrechnung sowie Website-/API-Beschränkungen; siehe [GOOGLE-MAPS.md](GOOGLE-MAPS.md). Für den Sendestream separat freischalten, nachdem die Nutzungsrechte geklärt sind.
- TomTom Traffic: eigener optionaler serverseitiger Key unter Ausgaben & Quellen, einschließlich Testfunktion.
- Xtream: eigenes Ausgabekonto unter Ausgaben & Quellen. Es ersetzt keinen Zugriffsschutz der direkten öffentlichen HLS-/M3U-Ausgaben.

Die grundlegenden Wetterseiten benötigen keinen Key des Projektinhabers. Jeder Betreiber richtet eigene benötigte Anbieterzugänge ein.

## Wiedergabe prüfen

Browser-Vorschau: `https://DEIN-HOST:7373/view/1`.

Gemeinsame M3U für VLC/IPTV: `http://DEIN-HOST:7373/playlist.m3u`.

Einzelkanal: `http://DEIN-HOST:7373/live/1/index.m3u8`; Einzelplaylist: `http://DEIN-HOST:7373/playlist/1.m3u`.

Eine funktionierende HTML-Vorschau bestätigt noch keinen funktionierenden Encoder. Nach Aktivierung auf eine frische HLS-Playlist warten und mindestens einen tatsächlichen Videostream abspielen. Video ist 1280×720, H.264/AAC; 15 FPS sind der Standard. Zuschauerzahl, Netz und Playerpuffer beeinflussen die Wiedergabe.

## Updates und Sicherungen

Vor Updates `.env`, Zertifikatskonfiguration und die Volumes `config`, `media` und `service` privat sichern. SQLite mit einer geeigneten Datenbanksicherung oder im gestoppten Zustand sichern; keine unvollständige Kopie einer schreibenden Datenbank verwenden. `hls` enthält laufend erzeugte Streamdaten und ist keine dauerhafte Inhaltsbibliothek.

Quellcode aktualisieren, `docker compose build` und `docker compose up -d` ausführen. Ein Containerneustart kann Streams kurz unterbrechen. Vorhandene Volumes erhalten die eigenen Einstellungen. `docker compose down -v` löscht Volumes und gehört nicht zum normalen Update.

Vor dem Teilen von Logs, Backups oder Konfigurationsdateien private Daten prüfen. HTTP-Xtream-URLs können Zugangsdaten enthalten. Ein Google-Browser-Key bleibt in der betriebenen Kartenansicht sichtbar; niemals stattdessen einen unbeschränkten Server-Key verwenden.
