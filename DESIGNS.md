# Moderne Designs und Animationen · 2. November 2026

Vier zusätzliche Vorlagen: Aurora Glass, Midnight Broadcast, Solar Horizon und Arctic Minimal. Studio Classic bleibt verfügbar. Jede Vorlage bietet eine Vorschau mit den tatsächlichen Wetterdaten, ohne die gespeicherte Konfiguration zu ändern.

Auswahl: Verwaltung → Kanal bearbeiten → Designvorlage oder Designkarte → Auswählen → Speichern und übernehmen. Ein Vorlagenwechsel schlägt passende Farben vor. Wetter- und Übergangsanimationen sind separat abschaltbar; das Nachrichtenband bleibt unabhängig.

## Animationen

- Langsam bewegte Hintergrundlichter.
- Rotierende Sonnenstrahlen und sanft bewegte Wolken.
- Regen-, Schnee- und Gewitterelemente passend zum Wettercode.
- Windgrafik mit Richtung aus den Wetterdaten.
- Weiche Seitenwechsel und gestaffelt erscheinende Datenkarten.
- Laufende Animationen werden beim sekündlichen Uhr-Update nicht neu gestartet.

## Verifikation auf dem Server

- 17 Backend-Tests bestanden.
- JavaScript-Prüfungen für alle Wetterseiten und den Ticker bestanden.
- Alle sechs Wetterseiten in allen vier neuen Designs gerendert und auf Überlauf geprüft.
- Alle vier aktuellen Wetteransichten visuell geprüft.
- Animationen in Chromium anhand der veränderten Transformation geprüft.
- Abschalten der Wetteranimationen geprüft.
- Vollständige Darstellung in einem kleineren Vorschaufenster geprüft.
- Designauswahl über das echte Verwaltungsformular gespeichert und nach Neuladen bestätigt.
- Neue Vorlage im echten HLS-Stream geprüft: H.264, 720p, AAC; ein Frame wurde decodiert und visuell geprüft.
- Zusätzliche Layoutprüfung aller 24 Kombinationen mit eingeblendetem Testticker. Testtext nur im isolierten Browsertest, nicht in der gespeicherten Konfiguration.
- Ticker-Kontrast bei hellen und dunklen Vorlagen geprüft.
- Ursprüngliche Kanaleinstellungen nach den Tests vollständig wiederhergestellt.

Die HTML-Vorschau läuft mit Browser-Bildrate. Der Serverrenderer bleibt bei den konfigurierten 10 FPS. Kein neuer Fünfkanal-Dauertest. Radar bleibt ausdrücklich ein Platzhalter; Animationen erzeugen keine Radar- oder Messdaten.

Anwendungsstand einschließlich Ticker-Kontrastkorrektur: a711a39158d8c3dc96db703484eeae709c164503.

