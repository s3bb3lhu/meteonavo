# Fremdkomponenten, Daten und Medien

Stand: 4. November 2026. Die eigene Projektlizenz erlaubt ausschließlich private,
nicht gewerbliche Nutzung der eigenen geschützten Projektbestandteile. Die eigene Projektlizenz in `LICENSE` gilt **nicht** für
die folgenden Fremdbestandteile. Deren Rechteinhaber und Lizenzbedingungen bleiben
unverändert. Diese Übersicht ist kein Nachweis einer Sendegenehmigung.

## Mitgelieferter Quelltext und Ressourcen

| Bestandteil | Lizenz / Herkunft | Hinweise |
| --- | --- | --- |
| hls.js 1.7.4 Light | Apache-2.0; https://github.com/video-dev/hls.js/tree/v1.7.4 | Unverändert, nur gzip-komprimiert. Volltext: `app/static/vendor/hls-LICENSE`; Herkunft und Prüfsumme: dortige README. Enthält eigene Hinweise auf weitere Urheber, die erhalten bleiben müssen. |
| Vereinfachte Landesgrenzen und Ortsdaten | Natural Earth, Public Domain; https://www.naturalearthdata.com/about/terms-of-use/ | `app/static/maps/radar-geography.json.gz`; Bearbeitung und Quelldateien in `app/static/maps/SOURCES.md`. Nicht unter die Änderungssperre des Projektcodes stellen. |
| Generierte Landschaften und Wettergrafiken | Für dieses Projekt mittels Bildgenerierung erstellt | Keine lizenzierten Stockfoto-Pakete eingebunden. Herkunft siehe `app/static/backgrounds/ASSETS.md` und Grafikdokumentation. Generierte Bilder sind keine Liveaufnahmen; alleinige Urheberrechte an rein KI-generierten Bestandteilen werden nicht zugesichert. |

## Python-Abhängigkeiten

Die Versionen der direkten Abhängigkeiten stehen in `requirements.txt`.
Transitive Pakete können weitere Hinweise mitbringen. Der Docker-Build erzeugt
unter `/studio/third-party-licenses/` ein Inventar der tatsächlich installierten
Python-Pakete samt auffindbaren Lizenz-/NOTICE-Dateien. Das ist eine ergänzende
Bestandsaufnahme, keine vollständige Freigabe des Betriebssystem-Images.

| Komponente | Lizenz | Projekt |
| --- | --- | --- |
| FastAPI | MIT | https://github.com/fastapi/fastapi |
| Starlette | BSD-3-Clause | https://github.com/Kludex/starlette |
| Uvicorn | BSD-3-Clause | https://github.com/Kludex/uvicorn |
| HTTPX / HTTPCore | BSD-3-Clause | https://github.com/encode/httpx / https://github.com/encode/httpcore |
| Pydantic / pydantic-core | MIT | https://github.com/pydantic/pydantic / https://github.com/pydantic/pydantic-core |
| Playwright Python / gebündelter Treiber | Apache-2.0 und dessen Fremdhinweise | https://github.com/microsoft/playwright-python |
| pytest | MIT | https://github.com/pytest-dev/pytest |
| defusedxml | Python Software Foundation License | https://github.com/tiran/defusedxml |
| Python | PSF-Lizenz und enthaltene Hinweise | https://docs.python.org/3/license.html |

Für weitere installierte Pakete gilt jeweils deren eigene Lizenz, unter anderem
MIT-, BSD-, Apache-, PSF- und MPL-Bedingungen. Insbesondere certifi enthält den
Mozilla-Zertifikatsspeicher unter MPL-2.0. Nicht pauschal mit der Projektlizenz
versehen. Die erzeugten Inventare ersetzen die Original-Lizenztexte nicht.

## Docker-Laufzeit: FFmpeg, Linux und Google Chrome

Die optionale Produktions-Überlagerung `compose.https.yaml` verwendet zusätzlich
das offizielle Nginx-Image (1.30.6 Alpine, per Digest festgelegt). Nginx steht unter
BSD-2-Clause: https://nginx.org/LICENSE. Das Image enthält weitere Alpine-/System-
komponenten mit eigenen Bedingungen. Die Original-Lizenzhinweise bleiben erhalten;
die eigene Projektlizenz gilt weder für Nginx noch für seine Abhängigkeiten.

Der aktuelle Build verwendet das Debian-FFmpeg mit `--enable-gpl` und
`--enable-libx264`. Es darf **nicht** als ausschließlich LGPL oder als eigener
proprietärer Code ausgegeben werden. Maßgeblich sind der konkrete Build,
`ffmpeg -L`, seine Bibliotheken und `/usr/share/doc/*/copyright` im Image.
Die Anwendung ruft FFmpeg als gesonderten Prozess auf; ihre eigene Lizenz
schränkt FFmpeg und seine Bibliotheken nicht ein.

Bei Weitergabe eines gebauten Images sind zusätzlich die GPL-/LGPL-Pflichten
einschließlich des zur genauen Binärfassung gehörenden vollständigen Quellcodes
und der Buildinformationen nach der jeweils geltenden Lizenz zu erfüllen.
Ein allgemeiner Link auf die FFmpeg-Startseite genügt dafür nicht automatisch.
Siehe https://ffmpeg.org/legal.html und https://www.gnu.org/licenses/gpl-faq.html.
Auch Debian-/Python-Basisimage, Bibliotheken, Schriften und sonstige Systempakete
besitzen eigene Bedingungen. Ihre vorhandenen Lizenzhinweise bleiben im Image.

Das öffentliche Distributionsimage verwendet Debian Chromium, nicht das proprietäre Google-Chrome-Paket. Die Debian-Quellen für Chromium einschließlich seiner mitgelieferten Fremdkomponenten und Debian-Patches werden in exakter Version mit dem Release bereitgestellt. Lizenztexte bleiben unter `/usr/share/doc` im Image. Chromium-Informationen: https://www.chromium.org/ und die jeweiligen Originalhinweise des Debian-Pakets.

Die Veröffentlichung umfasst ein Image und dessen zugehöriges Debian-Quellenpaket. Der Build sammelt die genauen Quellversionen sämtlicher installierter Debian-Binärpakete und erzeugt ein Binär-/Quellmanifest samt Prüfsummen. Die Projektlizenz beschränkt diese Fremdquellen nicht. Konkrete Download- und Wiederzusammensetzungsanleitung: [DISTRIBUTION.md](DISTRIBUTION.md). Images dürfen erst nach erfolgreichem Export der Quellen und Lizenznachweise veröffentlicht werden.

## Externe Dienste und Inhalte (nicht unter der Projektlizenz)

| Quelle | Bedingungen und Konsequenz |
| --- | --- |
| Open-Meteo | Wetterdaten CC-BY-4.0 mit Namensnennung; freie API nur nichtkommerziell und innerhalb der Kontingente. https://open-meteo.com/en/terms und https://open-meteo.com/en/licence. Das Projekt verwendet die freie API; ein kommerzieller API-Tarif ist noch nicht integriert. |
| RainViewer | Eigene API-Bedingungen für persönliche/Bildungs-/kleine Gemeinschaftsprojekte; sichtbarer Quellennachweis. Kommerzielle oder umfangreiche Nutzung gesondert klären. https://www.rainviewer.com/api.html |
| OpenStreetMap / Photon | Kartendaten ODbL, sichtbare Attribution; für öffentliche OSM-Kacheln zusätzlich die Betriebsrichtlinie. https://www.openstreetmap.org/copyright und https://operations.osmfoundation.org/policies/tiles/. Öffentlicher Photon-Dienst ohne garantierte Verfügbarkeit: https://photon.komoot.io/ |
| Esri World Imagery | Eigene Service-/Datenbedingungen und anbieter-/gebietsabhängige Bildnachweise. Allgemeines „Esri“ ersetzt nicht alle benötigten Credits. Vor öffentlicher Satelliten-Ausstrahlung Lizenz und konkrete Credits klären: https://www.arcgis.com/home/item.html?id=10df2279f9684e4a9f6a7f08febac2a9 |
| MeteoAlarm / nationale Warndienste | Bedingungen und Quellenangaben des jeweiligen Warnanbieters beachten. https://meteoalarm.org/ |
| Autobahn GmbH / TomTom | Abdeckung, Abrufkontingent und Nutzungs-/Weitergaberechte gelten unabhängig von einem funktionierenden API-Schlüssel. https://verkehr.autobahn.de/o/autobahn/ und https://developer.tomtom.com/terms-and-conditions |
| Radio Browser | Verzeichnisschnittstelle: https://www.radio-browser.info/. Ein Verzeichniseintrag erlaubt weder die Weiterübertragung des Senders noch die öffentliche Musiknutzung. Rechte der Sender und Musikrechte gesondert klären. |
| Wikimedia Commons / Wikidata | Jeweilige Datei-/Datenlizenz beachten. Commons-Bilder können CC-BY oder CC-BY-SA sein: Urheber, Quelle, Lizenzlink und vorgenommene Bearbeitung nennen; bei ShareAlike entsprechende Rechte am bearbeiteten Bild einräumen. Nicht mit eigener Änderungssperre versehen. https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia |
| Eigene Uploads und RSS-Nachrichten | Betreiber benötigt Rechte zur konkreten Nutzung/Ausstrahlung. Öffentliche Erreichbarkeit oder RSS-Bereitstellung allein erteilt keine allgemeine Sendelizenz. Die Software prüft diese Rechte nicht. |
| Wetterkameras / YouTube | Einbettung im offiziellen Player und erneute Ausstrahlung des Bildes in eigenem HLS/MPEG-TS sind unterschiedliche Nutzungen. Ein funktionierender Embed ist keine Sendegenehmigung. Vor öffentlichem Weiterstreamen Rechte des Kamerabetreibers sowie Plattformbedingungen prüfen und erforderliche Zustimmungen beschaffen. https://www.youtube.com/t/terms und https://developers.google.com/youtube/terms/developer-policies. Keine Zustimmung wird vom Projekt behauptet. |

## Veröffentlichung und öffentliche GitHub-Repositories

Ein sichtbares Repository ist nicht automatisch Open Source. Die eigene
Änderungs-/Weitergabesperre gilt nur im Rahmen bestehender Rechte, zwingenden
Rechts und geltender Plattformbedingungen. GitHub-Rechte für Anzeige und Forks
öffentlicher Repositories müssen bei der Entscheidung berücksichtigt werden:
https://docs.github.com/en/site-policy/github-terms/github-terms-of-service.
Ein absolutes technisches Verbot aller Kopien ist mit einer öffentlichen
Quelltextanzeige nicht erreichbar.

Der Betreiber muss vor einem öffentlichen Dienst außerdem seine tatsächliche
Datenverarbeitung und erforderlichen Betreiber-/Datenschutzhinweise prüfen.
Eingebettete Drittplayer kontaktieren ihre Anbieter; die nocookie-Domain ist
keine Garantie, dass keine personenbezogenen Daten verarbeitet werden.


## Optionaler Google-Maps-Anbieter

Google Maps JavaScript API wird nur für ausdrücklich gewählte Google-Karten mit eigenem Betreiber-Key direkt von Google geladen. SDK und Karteninhalte bleiben unter Googles Nutzungsbedingungen; die Projektlizenz erteilt dafür keine Rechte. Google-Logo und Datenquellenangaben bleiben im Kartenfenster sichtbar. Google-Kacheln werden nicht über den Kartenproxy geladen oder im lokalen Kartencache gespeichert. Abrechnung, Datenschutzhinweise, Website-/API-Beschränkungen und insbesondere TV-/IPTV-Rechte sind vom Betreiber zu prüfen. Details und offizielle Links: [GOOGLE-MAPS.md](GOOGLE-MAPS.md).
