# Release-Prüfung 0.1.0

Der Veröffentlichungsworkflow führt die Python-Tests und einen isolierten Erststart aus, bevor das Container-Image hochgeladen wird. Auf dem privaten Prüfserver erfolgen zusätzlich ein echter Chromium-/FFmpeg-Test sowie der Vergleich des Quellpakets und Images mit bekannten privaten Werten. Keine Rohwerte werden als Bericht oder Artefakt veröffentlicht.

Der Erststart muss fünf deaktivierte Kanäle, kein eingerichtetes Eigentümerkonto, keinen Google-/TomTom-Key und keine persönlichen Medien zeigen. Die Prüfergebnisse des veröffentlichten Commits sind im zugehörigen GitHub-Actions-Lauf sichtbar. Eine erfolgreiche technische Prüfung ersetzt keine Nutzungsrechte für externe Karten, Radios, Nachrichten oder Kameras und garantiert keine Kapazität auf beliebigen Servern.
