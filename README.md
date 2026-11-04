# Meteonavo

Ein selbst gehostetes Wetter-TV-Studio für Linux auf AMD64/x86-64. Meteonavo erzeugt aus Wetterseiten, Nachrichten und optionalem Audio bis zu fünf eigene Wetterkanäle als Videostream. Bedient wird das Studio im Browser; die Ausgabe lässt sich unter anderem mit VLC und kompatiblen IPTV-Apps abspielen.

Proprietäre Software von **s3bb3lhu**, keine Open-Source-Lizenz. Unveränderte Nutzung und Konfiguration sind ausschließlich für private, nicht gewerbliche Zwecke erlaubt. Gewerbliche, geschäftliche und berufliche Nutzung ist nicht gestattet. Änderungen am eigenen Code sowie Weitergabe/Weiterveröffentlichung benötigen vorherige ausdrückliche Zustimmung in Textform. Siehe [LICENSE](LICENSE), [Fremdlizenzen](THIRD_PARTY_NOTICES.md) und [Veröffentlichungsprüfung](RELEASE-REVIEW.md). Fremdrechte und zwingendes Recht bleiben unberührt. Lizenztexte sind in der Installation unter `/license` und `/third-party-notices` abrufbar.

## Was das Docker-Projekt tatsächlich macht

Eine Installation besteht aus zwei Anwendungscontainern aus demselben Image. Für die HTTPS-Verwaltung kommt ein dritter Container hinzu.

| Dienst | Aufgabe | Daten und Zugriff |
| --- | --- | --- |
| `api` | FastAPI-Backend und Weboberfläche. Speichert Kanäle und Einstellungen, verarbeitet Uploads, fragt Wetter-/Nachrichten-/Regionalquellen ab und liefert Vorschau, Playlists sowie vorhandene Streamsegmente aus. | Konfiguration in `/data`, Musik in `/media`, Streamdateien in `/hls`, interner Dienstschlüssel unter `/run/studio`. |
| `renderer` | Startet Chromium und öffnet für jeden aktivierten Kanal eine eigene Browserseite. Erfasst die 1280×720-Sendeansicht und führt Bilder sowie die gewählte Tonquelle mit FFmpeg zu H.264/AAC zusammen. | Schreibt HLS-Playlists und MPEG-TS-Segmente nach `/hls`. Liest eigene Musik und den internen Dienstschlüssel. |
| `gateway` | Nginx aus der optionalen Produktionskonfiguration `compose.https.yaml`. Erkennt HTTP und TLS auf demselben öffentlichen Port. Liefert die Verwaltung über HTTPS und die IPTV-Ausgaben weiterhin über HTTP aus. | Zertifikate werden nur zur Laufzeit schreibgeschützt eingebunden. Der API-Port wird in dieser Konfiguration nicht öffentlich veröffentlicht. |

Der Datenweg lautet: **Standort und Einstellungen → externe Datenquellen → HTML/CSS-Wetterseiten in Chromium → FFmpeg → HLS/MPEG-TS → Player**. Die Vorschau zeigt die HTML-Ansicht direkt; der Videostream zeigt deren kodierte Ausgabe mit zusätzlicher Pufferverzögerung.

Die Videoausgabe wird einmal pro aktivem Kanal erzeugt. Weitere Zuschauer starten keinen eigenen Browser oder Encoder; sie erhalten die vorhandenen Segmente. Bandbreite und HTTP-Verbindungen steigen trotzdem mit der Zuschauerzahl. Deaktivierte Kanäle werden nicht kodiert. Ein reiner CPU-Betrieb ist vorgesehen; eine AMD-GPU oder GPU-Beschleunigung ist nicht erforderlich und wird nicht automatisch eingerichtet.

## Kanäle, Standorte und Sendeablauf

- Fünf unabhängig konfigurierbare Kanalplätze, bei einer Neuinstallation alle deaktiviert.
- Je Kanal eigener Name, Standort, GPS-Punkt, Design, Seitenfolge, Nachrichtenquelle und Tonquelle.
- Europäische Länderauswahl einschließlich kleiner Staaten und angrenzender Regionen; bei Deutschland zusätzlich Bundesländer. Die Länderauswahl garantiert keine vollständige Datenabdeckung jeder externen Quelle.
- Adresssuche über Photon/OpenStreetMap mit Auswahl eines Treffers und Übernahme der Koordinaten. Die Treffergenauigkeit wird angegeben; Hausnummern können fehlen.
- Alternativ direkte Eingabe von Breitengrad und Längengrad oder eines Koordinatenpaars. Dezimalpunkt und Dezimalkomma werden unterstützt. Der im Fernsehbild sichtbare Ortsname ist separat bearbeitbar.
- Wetterseiten per Checkbox aktivieren und über Auswahlmenüs anordnen. Normale Seitendauer: 5–120 Sekunden. Die Verkehrsrubrik hat zusätzlich eine automatische Seitengruppierung.
- Direkte Vorschau in einem neuen Tab mit manueller Kategorienwahl, Automatik und Vollbild. Die manuelle Vorschau verändert nicht die gespeicherte Sendefolge.

## Die neun Wetter- und Programmseiten

| Seite | Inhalt |
| --- | --- |
| Aktuell | Aktuelle Open-Meteo-Modellwerte, Wetterzustand, Temperatur und Tageswerte. |
| Sieben Tage | Mehrtagesprognose mit Temperatur- und Wetterdarstellung. |
| Stunden | Die nächsten sechs Stunden mit Verlaufsgrafiken. |
| Wind | Windrichtung, Geschwindigkeit, Böen und Ausblick. |
| Niederschlag | Regen, Schnee und Niederschlagswahrscheinlichkeit; Prognose statt erfundenem Messradar. |
| Radar | Animierte vergangene Niederschlagskomposite von RainViewer, Abdeckungsmaske, Zeitachse und GPS-Stecknadel. |
| Landeswetter | Landesumriss mit Ortsnamen, Wettersymbolen und aktuellen Modelltemperaturen. Bis zu acht eigene Übersichtsorte. |
| Verkehr | Regionale Ereignisse im Radius von 1–100 km, mit bevorzugter Anzeige von Autobahnen und Bundes-/Fernstraßen. |
| Wetterkameras | Eingebettete, geeignete Anbieterplayer, HLS-Quellen, regelmäßig aktualisierte Bilder oder offizielle YouTube-Player mit automatischem Wechsel. |

Open-Meteo liefert Modellwerte und Prognosen; Meteonavo ist keine eigene Wetterstation. Der lokale Wettercache wird regulär nach etwa zehn Minuten erneuert. Bei Ausfällen können vorhandene Werte mit Veraltet-Hinweis weiterlaufen. Ohne Daten erscheint ein Fehlerhinweis. Messwerte und Meldungen werden nicht erfunden.

### Radar und Karten

- Bestehende Karten: OpenStreetMap-Straßenkarte, dunkle Straßenkarte, Esri-Satellitenbild, abgedunkelte Satellitenansicht und vereinfachte Natural-Earth-Übersicht.
- Optional mit eigenem Google-Maps-Browser-Key: Karte, Satellit, Hybrid mit Straßenbeschriftung oder Gelände.
- Radar-Radius pro Kanal: **1–5000 km**, ungefähr Mittelpunkt bis seitlicher Rand des nominalen Kartenformats. Das tatsächliche sichtbare Gebiet hängt auch vom Bildformat ab. Ohne Radius gilt die bisherige Ausschnittwahl.
- Karte, Radarüberlagerung und GPS-Pin verwenden denselben Mittelpunkt und Maßstab. Kleinerer Radius vergrößert die Darstellung, nicht die Auflösung der Radarquelle.
- Der Radarfilm besteht aus vergangenen Kompositen. Er ist keine Zukunftsprognose und keine lückenlose Live-Messung. Fehlende Echos können auch fehlende Abdeckung bedeuten.
- Satellitenbilder sind Archivaufnahmen. „Nachtoptik“ ist ein Farbfilter und kein aktuelles nächtliches Satellitenbild.
- Google ist optional und im Sendestream zunächst ausgeschaltet. Für die Streamnutzung gibt es einen separaten Schalter nach Prüfung der Nutzungsrechte. Google-Logo und Datenquellenangaben bleiben sichtbar; Google-Kacheln werden nicht über unseren Kartenproxy gespeichert.

Einrichtung und Schlüsselbeschränkungen: [GOOGLE-MAPS.md](GOOGLE-MAPS.md).

### Nachrichten und amtliche Wetterwarnungen

Je Kanal kann ein öffentlicher RSS-/Atom-Link hinterlegt werden. Schlagzeilen laufen als animierter Ticker unten im Bild und erscheinen auch im Videostream. Die Senderansicht zeigt keine zusätzliche Ticker-Uhr oder RSS-Quellenbeschriftung; Quelleninformationen bleiben in Verwaltung und Datenantworten verfügbar.

Aktive, zugeordnete amtliche Wetterwarnungen werden vor gewöhnlichen RSS-Schlagzeilen angezeigt. Für Deutschland erfolgt die Zuordnung über DWD-Regionen; für andere unterstützte Quellen sind passende Adressregionen beziehungsweise bestätigte Warnregionen erforderlich. Keine eindeutige Zuordnung oder ein Quellenausfall wird kenntlich gemacht. Meteonavo ersetzt keinen amtlichen Warndienst.

RSS wird regulär etwa alle fünf Minuten erneuert. Vorhandene Schlagzeilen können bei Ausfall höchstens 24 Stunden als veraltet angezeigt werden. Maximal 20 Schlagzeilen mit je 240 Zeichen werden übernommen. XML-/HTML-Inhalte werden nicht ungeprüft als ausführbarer Seiteninhalt übernommen.

### Verkehr und Wetterkameras

Deutsche Autobahnmeldungen stehen über die Autobahn-GmbH-Quelle ohne eigenen API-Key zur Verfügung. Optional erweitert ein eigener TomTom-Traffic-Key die Abdeckung. Die Verwaltung besitzt einen TomTom-API-Test; Schlüssel-, Kontingent- und Quellenausfälle werden unterschieden. Verfügbarkeit und Straßenabdeckung hängen vom Anbieter ab.

Verkehrsmeldungen erscheinen zu dritt pro Seite. Alle aktuellen Meldungsseiten werden nacheinander gezeigt, bevor die normale Sendefolge weiterläuft. Bei null gemeldeten Ereignissen erscheint zehn Sekunden ein entsprechender Hinweis; bei einem Quellenausfall ein Fehlerhinweis. Keine Meldungen sind keine Zusage freier Straßen. Der Radius ist eine Luftlinienauswahl anhand der Ereignispositionen.

Kameraverzeichnisse und Quellenprüfungen werden täglich erneuert, soweit die Anbieter erreichbar sind. Eigene Kameraquellen sind möglich; die regionale Auswahl liegt innerhalb von 100 km. Geeignete eingebettete Bilder und Player werden direkt in Vorschau und Sendestream erfasst. Automatischer Wechsel: 30, 60, 120 oder 300 Sekunden. Einzelbilder werden höchstens alle 30 Sekunden abgefragt.

YouTube wird über den offiziellen Player eingebettet, ohne Download oder Medienextraktion. Einbettungssperren, Autoplay-Regeln, Consent-Seiten oder technische Schutzmaßnahmen können die Wiedergabe verhindern. Ein erreichbarer Link garantiert kein aktuelles Kamerabild und keine Sendefreigabe. Ein europaweit vollständiges Verzeichnis wird nicht versprochen. Commons-/Wikidata-Abfragen können vom Anbieter blockiert sein; eigene Quellen funktionieren davon unabhängig.

## Design und Senderauftritt

- Klassische, moderne, Cinematic-, Glas-, Panorama-, Verlauf- und Retro-Designs, je Kanal wählbar.
- Fotorealistische Wettergrafiken oder grafische Studio-Icons mit Tag-/Nachtvarianten.
- Hintergrundauswahl nach Wetterlage und Tageszeit mit Licht-, Regen-, Schnee- und Nebeleffekten. Mitgelieferte gestaltete Fotolandschaften sind keine Liveaufnahmen oder Garantie eines exakten Ortsfotos.
- Eigene Ortsfotos für unterstützte Fotodesigns: Standardbild oder getrennte Varianten nach Tageszeit/Wetterlage. Optionale lizenzgefilterte Archivfotosuche, ohne Verfügbarkeitsgarantie.
- Sechs zusätzliche Rahmenvarianten: Fine Line, Broadcast Edge, Contour, Retro Chrome, Soft Ribbon und Corner Brackets sowie die ursprünglichen Designrahmen.
- Rahmenfarbe, Strichbreite, Rundung und Deckkraft; Hintergrunddeckkraft oben und in der Mitte separat. Der Ticker behält seine eigene Gestaltung.
- Ortsname, Uhrzeit und Datum zentriert in den Kopfrahmen.
- Eigenes TV-Logo pro Kanal: im Ortsrahmen links oder frei positioniert. Größe, Position und Deckkraft sind einstellbar; visuelle Platzierung und Größenänderung per Ziehen in einer gesonderten Vorschau.
- Logo-Upload: PNG, JPEG oder WebP bis 5 MB. Transparenz geeigneter PNG-/WebP-Dateien bleibt erhalten. Eigene Ortsbilder: bis 8 MB und 40 Megapixel.

## Musik und Radio

Die eigene Seite **Musik / Radio** verwaltet Musik-Uploads, Playlists und Radioquellen. MP3, WAV, FLAC, OGG und M4A werden unterstützt, soweit FFmpeg sie dekodieren kann. Pro Upload maximal 100 MB; die Konvertierung verarbeitet höchstens zwei Stunden Audio und erzeugt AAC-Dateien. Titel können in geordneten Playlists mit bis zu 500 Einträgen zusammengestellt werden.

Das Radio-Browser-Verzeichnis wird regelmäßig, grundsätzlich täglich, aktualisiert. Sender sind nach Land und bei Deutschland zusätzlich nach Bundesland filterbar. Suche, Blättern, Aktualisierung und M3U-Export stehen zur Verfügung. Das Verzeichnis ist keine vollständige oder garantiert stets erreichbare Liste aller europäischen Sender.

Jeder Kanal wählt unabhängig zwischen **ohne Ton**, **eigener Playlist** und **Radiosender**, einschließlich Lautstärke. Bei einem Audioausfall läuft die Bildausgabe mit Stille weiter. Ein Radiosender oder Musik-Upload verleiht keine Rechte zur Weiterverbreitung.

## Verwaltung und Benutzerkonto

Beim ersten Browseraufruf werden Benutzername und Passwort vergeben. Es gibt keine mitgelieferten Standardzugangsdaten und keinen erforderlichen manuell einzugebenden Admintoken. Passwort: mindestens acht Zeichen, ein Großbuchstabe, eine Zahl und ein Sonderzeichen. Die Installation bietet ein Eigentümerkonto; keine Mehrbenutzer-/Rollenverwaltung.

Passwörter werden gehasht gespeichert. Die HTTPS-Produktionskonfiguration verwendet sichere Sitzungscookies und CSRF-/Origin-Prüfungen. Ein interner Renderer-Dienstschlüssel wird je Installation erzeugt; er ist kein vom Betreiber benötigter öffentlicher API-Key.

Die Verwaltung ist aufgeräumt in **Kanäle & Adressen**, **Designauswahl**, **Musik / Radio**, **Ausgaben & Quellen** und **Wetterkameras** gegliedert. Drei Backend-Layouts stehen zur Wahl: Redline Control, Crimson Glass und Broadcast Desk. Sieben Akzentfarben: Rot, Grün, Blau, Royal Blau, Lila, Dark Purple und Anthrazit. Hinzu kommen Tag-/Nachtmodus und Deutsch, Englisch, Französisch oder Spanisch. Diese Browserpräferenzen sind von den Kanaldesigns unabhängig und übersetzen keine eigenen Nachrichtentexte oder Sendernamen. `/help` enthält eine viersprachige Anleitung mit Download-/Druckansicht.

Ressourcenempfehlungen berücksichtigen CPU-/RAM-Limits und aktive Kanäle. Sie sind Orientierungshilfen, kein Lasttest, und ändern die FPS nicht automatisch.

## Wiedergabe und Ausgaben

Standardport: **7373/TCP**. Mit dem HTTPS-Overlay gilt:

| Adresse | Zweck |
| --- | --- |
| `https://DEIN-HOST:7373/` | Verwaltung, Einrichtung, HTML-Vorschau und Webplayer. |
| `http://DEIN-HOST:7373/playlist.m3u` | Gemeinsame M3U aller aktiven Kanäle. |
| `http://DEIN-HOST:7373/playlist/1.m3u` | Einzel-M3U für Kanal 1; entsprechend bis Kanal 5. |
| `http://DEIN-HOST:7373/live/1/index.m3u8` | Direkter HLS-Stream von Kanal 1. |
| `http://DEIN-HOST:7373/player_api.php` | Live-orientierte Xtream-kompatible API mit selbst eingerichteten Zugangsdaten. |

Xtream unterstützt Live-Kategorien, Live-Sender, authentifizierte M3U-Ausgabe sowie HLS und kontinuierliches MPEG-TS. Vorhandene HLS-Segmente werden für MPEG-TS weitergereicht; es wird nicht für jeden Zuschauer neu kodiert. Kein VOD, keine Serien, keine Aufnahme-/Archivfunktion und kein echtes Programm-EPG; XMLTV und Kurz-EPG bleiben leer. Es handelt sich nicht um einen vollständigen Xtream-Codes-Server.

**Direkte HLS- und M3U-Adressen sind öffentlich erreichbar.** Das Verwaltungskonto oder der zusätzliche Xtream-Zugang macht daraus keine geschlossene Senderverteilung. HTTP-IPTV überträgt Inhalte und gegebenenfalls URL-Zugangsdaten unverschlüsselt. HTTPS schützt die Verwaltung, nicht die bewusst über HTTP bereitgestellten IPTV-Adressen.

## Persistenz, Internetzugriffe und API-Keys

| Laufzeitbereich | Inhalt | Teil einer Veröffentlichung? |
| --- | --- | --- |
| Volume `config` → `/data` | SQLite mit Konto, Kanälen, eigenen API-Keys, Playlists, Radio-/Regionaldaten, Logos, Ortsbildern und Caches. | Nein. |
| Volume `media` → `/media` | Eigene konvertierte Musikdateien. | Nein. |
| Volume `service` → `/run/studio` | Installationsspezifischer interner Dienstschlüssel. | Nein. |
| Volume `hls` → `/hls` | Erzeugte Streamplaylists und Segmente; zur Laufzeit neu erstellt. | Nein. |
| `.env`, Zertifikatsverzeichnis, Sicherungen | Lokale Konfiguration, TLS-Schlüssel und Betriebsdaten. | Nein. |

**Es werden keine API-Keys des Projektinhabers mitgeliefert.** Jede Neuinstallation beginnt ohne Google-/TomTom-Key, ohne eingerichteten Eigentümer und ohne persönliche Kanaleinstellungen. Jeder Betreiber trägt bei Bedarf eigene Schlüssel über die Verwaltung ein. Die grundlegenden Wetterseiten funktionieren ohne Google oder TomTom.

Die laufende Installation benötigt ausgehenden Internetzugriff zu den gewählten Daten- und Medienquellen. Dazu gehören je nach Funktion Open-Meteo, Photon/OpenStreetMap, RainViewer, Kartenanbieter, DWD/MeteoAlarm, RSS-Anbieter, Radio Browser/Radiosender, Verkehrsquellen und Kameraanbieter. Standortdaten und Anfragen werden an die jeweils verwendeten Anbieter übermittelt. Es gibt keinen eingebauten zentralen Meteonavo-Dienst zum Einsammeln der Betreiber-API-Keys.

TomTom wird serverseitig angesprochen. Ein Google-Maps-Browser-Key ist dagegen technisch in der Browserkarte und den Anfragen an Google sichtbar; Website- und API-Beschränkungen sind erforderlich. Diese betriebsbedingte Sichtbarkeit ist von der Veröffentlichung des Quellcodes zu unterscheiden. Die lokale Konfigurationsdatenbank ist nicht automatisch verschlüsselt. Backups entsprechend schützen. Details zur Veröffentlichung ohne private Daten: [PUBLICATION.md](PUBLICATION.md).

## Vorgebautes Container-Image

```sh
docker pull ghcr.io/s3bb3lhu/meteonavo:0.1.0
```

Zielarchitektur: Linux/AMD64. Das Image enthält Debian Chromium und FFmpeg, keine Betreiberkonfiguration. Zu jedem Release gehören die exakten Debian-Quellpakete und Lizenznachweise; siehe [DISTRIBUTION.md](DISTRIBUTION.md).

## Installation

Voraussetzungen: Linux auf AMD64/x86-64, Docker Engine mit Compose, ausgehender Internetzugriff und ein freier Projektport. Intel-x86-64 ist dieselbe Docker-Zielarchitektur; ARM wird mit dieser Konfiguration nicht zugesichert. Für einen ersten Kanal sind vier CPU-Kerne und 4 GB freier RAM eine vorsichtige Startempfehlung; fünf Kanäle und aufwendige Kameras/Designs brauchen mehr Reserven. Andere Anwendungen auf dem Server berücksichtigen. Keine gemessene Kapazitätszusage.

```sh
git clone https://github.com/s3bb3lhu/meteonavo.git
cd meteonavo
cp .env.example .env
```

Für eine öffentlich erreichbare Installation anschließend [HTTPS-DEPLOYMENT.md](HTTPS-DEPLOYMENT.md) befolgen. Benötigt werden Compose ab 2.24.4 und ein gültiges Zertifikat für den verwendeten Host beziehungsweise die IP. Zertifikatsausstellung und Erneuerung sind Betreiberaufgaben; das Projekt übernimmt keine fremde Serverkonfiguration.

Die Basisdatei allein stellt HTTP bereit und ist für lokale Entwicklung oder ein isoliertes Testnetz gedacht:

```sh
docker compose build
docker compose up -d
docker compose ps
```

Danach die erste Einrichtung im Browser abschließen, einen Kanal konfigurieren und aktivieren. Standardmäßig wird mit 15 FPS gerendert; `FPS` in `.env` steuert die Ausgabe. Es werden 1–30 FPS unterstützt. Ein geänderter Umgebungswert benötigt eine Neuerstellung der betroffenen Container; eine angezeigte Serverempfehlung ist keine automatische Änderung.

Konfigurations- und Medienvolumes bleiben bei einem normalen Containerupdate erhalten. `docker compose down -v` löscht Volumes und ist **kein** gewöhnlicher Updateschritt. Nie einen laufenden Produktionscontainer mitsamt Daten als Veröffentlichung exportieren oder per `docker commit` zum Distributionsimage machen.

## Prüfungen und bekannte Grenzen

Der zuletzt geprüfte Funktionsstand umfasst 122 Python-Tests und die JavaScript-Testsuiten sowie Browser-/Streamprüfungen. Die optionale Google-Karte wurde mit einem Betreiber-Key in Vorschau, Renderer und HLS geprüft; dieser Key wird nicht mitgeliefert. Das garantiert keine dauerhafte Erreichbarkeit, zulässige Nutzung oder Funktionsfähigkeit mit fremden Keys.

```sh
docker compose run --rm --no-deps api python -m pytest tests -q
```

Tests nutzen temporäre Datenbanken und Testzugänge. Weitere Details: [TEST-REPORT.md](TEST-REPORT.md), [RELEASE-REVIEW.md](RELEASE-REVIEW.md), [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Externe Anbieter können Kontingente, Abdeckung, Gebühren, Formate oder Einbettungsregeln ändern. Ein erreichbarer RSS-Feed, Radiosender, Kartendienst oder Kameralink verleiht keine Senderechte. Eigene Inhalte und Drittquellen müssen zum vorgesehenen privaten Einsatz passen. Hinweise und Logos fremder Rechteinhaber dürfen nicht entfernt werden.
