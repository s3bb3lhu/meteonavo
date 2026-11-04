# Meteonavo 0.1.0 · öffentliche Veröffentlichung

Veröffentlicht wird ausschließlich ein bereinigter Quellstand mit neuer Git-Historie. Die private Entwicklungshistorie und der laufende Betreiberzustand sind nicht enthalten.

Keine Produktionsvolumes, Datenbanken, Betreiber-API-Keys, Sitzungsschlüssel, eigenen Uploads, persönlichen Koordinaten oder privaten Serveradressen werden übernommen. Adress-Testfälle sind synthetisch. Betreiber richten ein eigenes Konto und gegebenenfalls eigene Anbieterzugänge ein.

Das Distributionsimage enthält Debian Chromium und FFmpeg als getrennte Programme. Google Chrome wird nicht weitergegeben. Die genauen Debian-Quellpakete, Originalhinweise und ein Versions-/Prüfsummenmanifest werden mit dem Release bereitgestellt. Fremdlizenzen behalten Vorrang für ihre jeweiligen Komponenten. Die Projektlizenz erlaubt ausschließlich private, nicht gewerbliche Nutzung der eigenen geschützten Bestandteile.

Veröffentlichung und Build laufen aus dem bereinigten Repository. Der temporäre GitHub-Actions-Token dient ausschließlich zur Veröffentlichung in GitHub/GHCR und wird nicht in das Image eingebaut. Es werden keine Betreiber-API-Keys als Actions-Secrets benötigt. Tests, Erststart und der Browser-/FFmpeg-Pfad werden vor dem Push geprüft.
