# Veröffentlichung ohne private Schlüssel und Betriebsdaten

Dieses Dokument beschreibt den Distributionsumfang. Die veröffentlichbare Software enthält **keinen API-Key des Projektinhabers**, keine fertigen Betreiberzugänge und keine Kopie seiner laufenden Wetterkanäle. Jeder Betreiber richtet seine eigene Installation ein und verwendet bei Bedarf eigene Anbieterzugänge. Die eigene Projektlizenz erlaubt ausschließlich private, nicht gewerbliche Nutzung; Fremdrechte bleiben gesondert zu beachten.

## Was ausgeliefert wird

- Anwendungscode und mitgelieferte öffentliche Gestaltungselemente unter `app/`.
- Dockerfile, Compose-Dateien und ein leeres, generisches `.env.example`.
- Installationswerkzeuge, Tests, Lizenztexte und Dokumentation.
- Ein aus diesen Dateien frisch gebautes Image, falls ein Image veröffentlicht wird. Der Code allein veröffentlicht noch kein Docker-Hub-/GHCR-Image.

## Was niemals als Distributionsquelle verwendet wird

- Docker-Volumes `config`, `media`, `service` oder `hls`.
- Die Betreiberdatei `.env`, private TLS-Schlüssel oder Zertifikatssicherungen.
- SQLite-Datenbanken einschließlich `-wal`-/`-shm`-Dateien.
- API-Keys, Sitzungstokens, Passwort-Hashes oder interne Renderer-Zugangsdaten.
- Eigene hochgeladene Musik, Senderlogos, Ortsbilder, personalisierte Kameralisten oder Streamaufzeichnungen.
- Logs, Browserprofile, Screenshots, Betriebsbackups oder Diagnosearchive.

Ein laufender Produktionscontainer darf deshalb nicht per `docker commit` oder Dateisystemexport als Veröffentlichungsimage übernommen werden. Die eigenen Volumes müssen auf dem privaten Server bleiben. Ein Quellcode-Update oder ein neues Image darf die eigene laufende Installation weiterhin mit ihren bestehenden Volumes verwenden; diese Volumes werden dabei nicht Teil des Images.

## Reproduzierbares Vorgehen für ein Quellpaket

Aus einer sauberen Quellkopie im Projektverzeichnis:

```sh
python3 tools/build_release.py --output ../meteonavo-v0.1-source.zip
```

Das Werkzeug nimmt nur die festgelegten Quellverzeichnisse und öffentlichen Wurzeldateien auf. `.env`, Betriebsverzeichnisse und Sicherungen im Projektwurzelverzeichnis werden nicht ausgewählt. Private Dateien innerhalb eines ausgewählten Quellverzeichnisses, Symlinks und erkennbar vollständige Google-Key-Zeichenfolgen führen zum Abbruch; der Fehler nennt nur den Pfad, nicht den Wert. Öffentliche, mitgelieferte Gzip-Assets sind ausdrücklich freigegeben.

Das ZIP enthält `RELEASE-MANIFEST.json` mit Dateinamen, Größen und SHA-256-Prüfsummen. Daneben entsteht eine SHA-256-Datei für das gesamte ZIP. Das Paket muss außerhalb des Quellverzeichnisses abgelegt werden. Prüfsummen belegen die Unverändertheit des Pakets, ersetzen aber keine Signatur oder Geheimnisprüfung.

Der Dockerfile verwendet explizite `COPY`-Anweisungen für Anwendung, Tests, Werkzeuge, Deployment-Dateien und öffentliche Dokumentation. `.gitignore` und `.dockerignore` ergänzen den Schutz gegen typische Betriebsdateien. Ignore-Dateien entfernen keine bereits eingecheckten Dateien aus der Git-Historie; deshalb wird auch die bisherige Historie geprüft.

## Kontrolle vor Freigabe

1. Quellpaket bauen und seinen Inhalt gegen Manifest und erlaubte Dateipfade prüfen.
2. Tatsächlich konfigurierte API-/Dienstschlüssel **auf dem privaten Server** gegen Paket, entpackte Image-Dateien und veröffentlichte Quelltexte vergleichen. Schlüsselwerte bleiben auf dem Server; der Bericht enthält nur Anzahl, Kategorien und Trefferzahlen. Auch Base64-Darstellungen berücksichtigen.
3. Git-Historie und Dateinamen auf frühere Geheimnisse prüfen. Fehlende Textpatches durch die jeweilige Dateifassung ergänzen; Prüfumfang und Grenzen dokumentieren. Ein Fund muss vor Veröffentlichung geklärt und ein betroffener Zugang nötigenfalls ersetzt werden.
4. Image frisch aus dem Quellpaket bauen. Ohne Produktionsvolumes starten und bestätigen: kein Eigentümerkonto, fünf deaktivierte Kanalplätze, keine Ortskoordinaten, kein Google-/TomTom-Key, keine eigenen Medien und kein aktivierter Xtream-Zugang. Der interne Dienstschlüssel darf ausschließlich neu zur Laufzeit erzeugt werden.
5. Tests und Containerstart prüfen. Ausgehende Anbieteranfragen und technische Tests sind keine Sendefreigabe fremder Inhalte.
6. Repository-Sichtbarkeit, Release-Artefakte und gegebenenfalls Registry separat freigeben. Eine Dokumentationsaktualisierung stellt das private Repository nicht automatisch öffentlich.

Der Paketbauer erkennt bekannte sensible Dateitypen und einen Google-Key-Typ. Er ist kein allgemeiner Beweis für die Abwesenheit beliebig verschleierter oder unbekannter Geheimnisse. Der ergänzende Vergleich der tatsächlich gespeicherten Werte ist deshalb Bestandteil der Freigabeprüfung. Archive aus anderen Quellen oder private Forks sind vom dokumentierten Prüfumfang nicht automatisch erfasst.

## Bedeutung des Google-Browser-Keys

Ein Betreiber trägt seinen eigenen Google-Key erst in seiner laufenden Installation ein. Die interaktive Maps JavaScript API übermittelt diesen Browser-Key bestimmungsgemäß an den Browser und Google. Deshalb ist er dort technisch sichtbar und muss auf zulässige Websites und die Maps JavaScript API beschränkt werden. Er wird **nicht** in Quellcode, Quellpaket oder Distributionsimage übernommen.

Eine Neuinstallation enthält diesen Key nicht. Auch das optionale Google-Modul besitzt keinen gemeinsamen Entwickler-Key, keinen zentralen Key-Server und keinen Rückfall auf den Key des Projektinhabers. Ohne eigenen Key bleiben die bisherigen Karten verfügbar. TomTom- und interne Dienstschlüssel werden getrennt und serverseitig verwendet. Konfigurationsdatenbanken und Backups sind nicht automatisch verschlüsselt.

Die eingebundenen Anbieter erhalten die für ihre Dienste notwendigen Anfragen, etwa Standort, Browser-IP oder ihren eigenen API-Key. „Keine mitgelieferten API-Keys“ bedeutet daher nicht, dass eine aktivierte externe API ohne Anbieterkommunikation betrieben wird. Datenschutz- und Anbieterbedingungen sind pro Installation zu berücksichtigen.
