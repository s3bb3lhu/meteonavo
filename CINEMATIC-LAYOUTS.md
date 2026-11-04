# Cinematic-Rahmen und Nachrichtenband · 2. November 2026

Neue Vorschläge: Cinematic Glass, Cinematic Prime und Cinematic Panorama. Auch die Basisvorlage Cinematic Weather erhält die neue Gliederung.

## Aufbau

Oben drei dauerhaft sichtbare Rahmen für Ort, aktuelle Ortszeit mit Sekunden und Datum mit Wochentag. In der Mitte eine gesonderte Wetterfläche. Unten ein über die gesamte Breite laufendes Nachrichtenband mit Quellenblock links und Ortszeit rechts.

Glass: transparente Petrolrahmen und ein dunkles Laufband. Prime: markante warme Linien und ein helles Laufband. Panorama: dünne champagnerfarbene Rahmen und mehr sichtbare Landschaft. Die Gliederung orientiert sich an Nachrichtensendern, verwendet aber eigene Farben und keine fremden Senderlogos.

Das Band nutzt den vorhandenen RSS-Link. Ohne Feed bleibt es mit einem ehrlichen Einrichtungshinweis sichtbar. Vorschaubilder aus dem Layouttest enthalten ausdrücklich als DESIGNVORSCHAU gekennzeichnete Platzhaltertexte; sie wurden nicht als Nachrichten in der Konfiguration gespeichert.

## Prüfung

- 17 Backend-Tests sowie JavaScript-Prüfungen bestanden.
- Basisvorlage und alle drei neuen Vorlagen mit allen sechs Wetterseiten geprüft.
- Ort, Zeit und Datum bleiben bei Seitenwechseln sichtbar; Sekundenanzeige aktualisiert sich.
- Datum und Uhrzeit mit der Zeitzone der echten Wetterdaten abgeglichen.
- Geometrie der drei Kopfrahmen, der Wetterfläche und des unteren Nachrichtentickers geprüft.
- Laufendes Band, fehlender Feed und skalierte Vorschau geprüft.
- Vorlage über die Verwaltung gespeichert und nach Neuladen bestätigt.
- Echter Prime-HLS-Stream auf H.264, 720p und AAC geprüft, Frame decodiert und visuell kontrolliert.
- Alle drei Designvorschläge visuell geprüft.
- Bestehende Kanaleinstellungen nach den Tests vollständig wiederhergestellt.

Anwendungsstand: 0b5c3e60fc583b3721f824e31106dcc44486924b. Kein neuer Fünfkanal-Dauertest.

