# HTTPS-Verwaltung und HTTP-Xtream

Nur für private, nicht gewerbliche Nutzung gemäß [LICENSE](LICENSE).
Die Veröffentlichung des Quellcodes erteilt keine gewerbliche Nutzungserlaubnis.

Die Produktionskonfiguration verwendet einen eigenen Nginx-Gateway-Container.
Auf demselben öffentlichen TCP-Port, standardmäßig **7373**, erkennt dieser HTTP
und TLS. Andere Webserver auf Port 80/443 werden dabei nicht umkonfiguriert.

- Verwaltung, Einrichtung, Vorschau und Verwaltungs-API: `https://DEIN-HOST:7373`.
- Xtream, M3U und Streams: weiterhin `http://DEIN-HOST:7373`.
- HTTP-Aufrufe der Verwaltung werden nach HTTPS weitergeleitet. Schreibende
  Verwaltungsanfragen über HTTP werden mit 426 abgewiesen.
- Der API-Container veröffentlicht in dieser Konfiguration keinen eigenen Port.
  Proxy-Header werden nur im abgeschlossenen Compose-Netz verwendet. Dieses Netz
  nicht mit fremden/unvertrauenswürdigen Containern teilen und den API-Port nicht
  zusätzlich veröffentlichen.

## Voraussetzungen

Linux auf AMD64, Docker Compose mindestens 2.24.4 für `!reset`, ein freier
gewählter Projektport und ein **gültiges, vertrauenswürdiges Zertifikat**, das
die gewählte IPv4-Adresse oder den Hostnamen im SAN enthält. Ein Domainzertifikat
deckt nicht automatisch eine IP-Adresse ab.

Der Zertifikatsbaum muss folgendes Layout besitzen; Let's Encrypt verwendet es
bereits. Den gesamten Stamm einbinden, damit erneuerte Symlinks funktionieren:

```text
/etc/letsencrypt/live/DEIN-ZERTIFIKATSNAME/fullchain.pem
/etc/letsencrypt/live/DEIN-ZERTIFIKATSNAME/privkey.pem
```

Zertifikatsdateien und private Schlüssel gehören **nicht** ins Repository oder
in ein veröffentlichtes Image. Der Gateway erhält sie ausschließlich als
schreibgeschützte Laufzeiteinbindung. Die Ausstellung eines Zertifikats und dessen
automatische Erneuerung sind beim eingesetzten Zertifikatsanbieter einzurichten;
das Konfigurationswerkzeug beantragt kein Zertifikat und überschreibt keine
bestehenden Webserver-/ACME-Konfigurationen.

## Einrichten

Im Projektverzeichnis, als Hostadministrator:

```sh
cp .env.example .env   # Nur bei einer NEUEN Installation, vorhandene .env behalten!
# PORT gegebenenfalls vorab in .env ändern.
python3 deploy/configure_https.py DEIN-HOST DEIN-ZERTIFIKATSNAME
docker compose -p weather-studio config --quiet
docker compose -p weather-studio up -d --build
```

Das Werkzeug prüft Zertifikatsnamen und Restlaufzeit, sichert eine vorhandene
`.env` privat unter `/var/backups/meteonavo-https` und setzt `COMPOSE_FILE`,
`PUBLIC_HOST`, `PUBLIC_BASE_URL` sowie die Zertifikatspfade. Unbekannte vorhandene
Einstellungen werden erhalten. Die HTTPS-Überlagerung setzt zusätzlich
`OUTPUT_BASE_URL` auf HTTP; IPTV-Links wechseln deshalb nicht auf HTTPS.

Bei einem anderen Zertifikatsspeicher `--cert-dir /absoluter/zertifikatsstamm`
angeben. Compose aus diesem Verzeichnis starten, damit es `COMPOSE_FILE` aus
`.env` automatisch übernimmt. Für den Produktionsbetrieb keine Befehle verwenden,
die absichtlich nur `-f compose.yaml` laden und damit den TLS-Gateway umgehen.
Die Grunddatei alleine bleibt für lokale Entwicklung/isolierte Tests verfügbar.

Bei einer bestehenden HTTP-Installation beim einmaligen Wechsel alle bisherigen
Administrationssitzungen widerrufen. Dazu nach Sicherung und vor der Freigabe:

```sh
docker compose -p weather-studio exec -T api python -c "import sqlite3; c=sqlite3.connect('/data/studio.sqlite'); c.execute('DELETE FROM sessions'); c.commit(); c.close()"
```

Danach über HTTPS neu anmelden. Benutzername, Passwort, Xtream-Zugang und
Kanalkonfiguration werden dabei nicht geändert. Die Produktionssitzung verwendet
ein `__Host-`-Cookie mit Secure, HttpOnly, SameSite=Strict und Path=/.

## Zertifikate automatisch übernehmen

Der Zertifikatsmanager muss nach einer erfolgreichen Erneuerung auch den
Gateway neu laden. Bei Certbot beispielsweise einen eigenen ausführbaren Hook
unter `/etc/letsencrypt/renewal-hooks/deploy/meteonavo-gateway` anlegen:

```sh
#!/bin/sh
set -eu
export METEONAVO_PROJECT_DIR=/opt/weather-channel-studio
exec /bin/sh "$METEONAVO_PROJECT_DIR/deploy/reload-gateway.sh"
```

Projektpfad gegebenenfalls anpassen. Vorhandene Erneuerungstimer und andere Hooks
beibehalten. Der Hook prüft die Nginx-Konfiguration und lädt sie ohne vollständigen
Container-Neustart neu. Der Nginx-Master läuft dafür direkt als PID 1; das
HUP-Signal wird über Docker zugestellt, ohne AppArmor abzuschalten oder Rechte
des Containers zu erweitern. Den Hook nach Einrichtung einmal manuell testen und
Erneuerungstimer, Fehlermeldungen und Zertifikatsablauf überwachen. Nur ein noch
gültiges Zertifikat einzubinden genügt für einen dauerhaften Betrieb nicht.

## Prüfen

```sh
curl -fsS https://DEIN-HOST:7373/health
curl -I http://DEIN-HOST:7373/settings
curl http://DEIN-HOST:7373/playlist.m3u
docker compose -p weather-studio ps
docker compose -p weather-studio port api 8080  # Kein veröffentlichter Backend-Port
```

Für HTTPS kein `curl -k` verwenden: Zertifikatsvertrauen und Namensprüfung müssen
erfolgreich sein. Die HTTP-Weiterleitung muss auf genau den HTTPS-Host und den
öffentlichen Port zeigen. Anmeldung, Speichern, Abmelden, Kamerawechsel und einen
echten Xtream-MPEG-TS-Stream zusätzlich testen.

Nginx schreibt keine vollständigen IPTV-Zugriffs-URLs in seine Logs. HTTP-Xtream
überträgt Benutzername/Passwort weiterhin unverschlüsselt. Die HTTP-Ausgaben sind
bewusst erhalten; HTTPS für die Verwaltung verschlüsselt diese separaten
HTTP-Verbindungen nicht. HSTS wird hier nicht gesetzt, damit keine hostweite
Transportregel die gewünschte HTTP-Nutzung verändert.

## Wetterkamera-Korrektur

Die Mainhattan-Anbieterseite lud ihren Consent-Manager doppelt. Die Voreinstellung
nutzt jetzt das öffentlich vom Anbieter bereitgestellte 1280-Pixel-JPEG und dessen
Bildzeit statt der vollständigen Webseite. Der Abruf ist größenbegrenzt und wird
gemeinsam zwischengespeichert; das hochauflösende Original wird nicht geladen.
Es werden keine Fremdskripte entfernt oder Consent-/Zugangssperren umgangen.

Das Bild bleibt als **aktualisiertes Einzelbild** gekennzeichnet, mit Aufnahmezeit
und Veraltet-Hinweis. Quellenname und Anbieterlink bleiben erhalten. Vorhandene
Auswahl-IDs, Kanalreihenfolge und gespeicherte Kameraeinstellungen bleiben bestehen.
Öffentliche Bildendpunkte sind keine pauschale Erlaubnis zur erneuten Ausstrahlung;
die benötigten Rechte bleiben vor öffentlichem Betrieb zu klären.

Technische Referenzen:
[Nginx ssl_preread](https://nginx.org/en/docs/stream/ngx_stream_ssl_preread_module.html),
[Uvicorn hinter Proxies](https://uvicorn.dev/deployment/),
[Mainhattan-Anbieter](https://www.mainhattan-webcam.de/).
