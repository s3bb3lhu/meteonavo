# Vorgebautes Image und Fremdquellen

Das öffentliche Image `ghcr.io/s3bb3lhu/meteonavo:0.1.0` wird frisch aus dem bereinigten öffentlichen Quellstand gebaut. Es enthält keine Produktionsdatenbank, API-Keys, Betreiberzugänge, Medienuploads oder private Entwicklungshistorie. Zielarchitektur: Linux/AMD64.

Der Browser ist **Debian Chromium**, nicht das proprietäre Google-Chrome-Paket. FFmpeg und Chromium sind getrennte Programme mit ihren eigenen Lizenzen und unveränderten Debian-Patches. Lizenztexte unter `/usr/share/doc/*/copyright` und die Python-Inventare unter `/studio/third-party-licenses` bleiben im Image erhalten. Die eigene Projektlizenz gilt ausschließlich für die eigenen geschützten Programmteile und ändert keine Rechte an diesen Fremdkomponenten.

## Exakte zugehörige Debian-Quellen

Zu jedem veröffentlichten Image gehören die Versions- und Prüfsummenliste sowie die vollständigen Debian-Quellpakete der enthaltenen Debian-Binärpakete: Upstream-Archive, `.dsc`-Dateien und Debian-Patches. Der Build lädt die jeweils **exakte** Quellversion aus den signierten Debian-Quellen. Fehlt eine Version, wird die Veröffentlichung angehalten; es wird keine vermeintlich passende neuere Quelle untergeschoben.

Die Quellen werden als Release-Dateien auf derselben GitHub-Release-Seite bereitgestellt. Bei großen Archiven entstehen mehrere fortlaufende Teile. Herunterladen, SHA-256 prüfen und auf Linux zusammenfügen:

```sh
sha256sum -c SHA256SUMS
cat corresponding-sources.tar.part-* > corresponding-sources.tar
mkdir corresponding-sources
tar -xf corresponding-sources.tar -C corresponding-sources
```

`debian-source-manifest.json` ordnet jedes installierte Debian-Binärpaket seiner Quellversion zu. Die Buildrezepte und Patches liegen in den Debian-Quellpaketen; der Projekt-Dockerfile beschreibt die Zusammenstellung des Images. FFmpeg-Buildinformationen und Chromium-Version werden ebenfalls mitgeliefert. Die Quellen sind zu denselben Fremdlizenzbedingungen weiter nutzbar; die Änderungssperre des eigenen Projektcodes gilt nicht für sie.

Für den Image-Build ohne Registry:

```sh
docker build --target distribution -t meteonavo:local .
docker build --target corresponding-sources --output type=local,dest=./corresponding-sources .
```

Quellen nicht innerhalb des normalen Buildkontexts aufbewahren. Betreiber-API-Keys sind keine Buildargumente und keine benötigten Workflow-Secrets. GitHub Actions nutzt nur seinen kurzlebigen Veröffentlichungstoken für GitHub/GHCR. Der Token gehört nicht in das Image.

Die Originalhinweise des offiziellen Python-/Debian-Basisimages und der installierten Pakete bleiben erhalten. Weitere Hinweise und Dienstbedingungen: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
