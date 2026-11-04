# Neue Wettericons und freie Kategorienvorschau · 2. November 2026

Das alte Wetter-Icon-Set wurde vollständig durch lokale SVGs mit eigenen Verläufen ersetzt. Unterstützt werden alle 28 verwendeten WMO-Codes mit passenden Tag-/Nachtvarianten, einschließlich differenzierter Bewölkung, Nebel, Nieselregen, gefrierendem Niederschlag, Schnee, Schneegriesel, Schauern, Gewitter und Hagel. Unbekannte Werte erhalten ein neutrales Symbol. Auch die Windnadel wurde als Vektorgrafik ersetzt.

Jede Browser-Vorschau hat eine Steuerleiste außerhalb des Sendebilds. Alle sechs Seiten sind unabhängig von der gespeicherten Sendeschleife anwählbar. Manuelle Auswahl hält die Seite fest; Automatik setzt die Sendeschleife fort. Vor-/Zurück-Schaltflächen und Pfeiltasten wechseln durch die Kategorien. Der URL-Parameter page ermöglicht direkte Links. Die Bedienung benötigt keine Anmeldung und verändert keine Konfiguration.

Radar ist direkt erreichbar, bleibt aber eine ausdrücklich als nicht verbunden gekennzeichnete Platzhalteransicht. Es wurden keine Radarechos, Messbilder oder Karten erfunden. Regen/Schnee bleibt eine gekennzeichnete Prognose.

## Verifikation

- JavaScript-Syntax und bisherige Darstellungs-/Ticker-/Zeitlogiktests bestanden.
- 28 Wettercodes mit Tag/Nacht, einzigartigen SVG-Verlaufs-IDs und korrekter Icon-Klassifikation geprüft.
- Alle sechs Kategorien über die echte Oberfläche ohne Anmeldung geöffnet.
- Manuelles Anhalten, Automatik, Vor/Zurück, Pfeiltasten, URL-Wechsel und vollständige Vorschau bei kleinen Fenstern geprüft.
- Vorschau sendet keine Schreibanfragen; Kanalkonfiguration bleibt unverändert.
- Renderer verwendet render=1: Steuerung bleibt unsichtbar, 1280×720 bleibt vollständig, manuelle page-Vorgaben werden ignoriert.
- Neuer Icon-Auszug, 7-Tage-Seite, Radarplatzhalter und echter HLS-Videoframe visuell geprüft.
- HLS auf H.264, 720p und AAC geprüft und ein Frame decodiert.
- Bestehende Einstellungen nach Streamtests vollständig wiederhergestellt.

Anwendungsstand: 8682dd1c9655e90c2143283407a2954deb37f668. Kein neuer Fünfkanal-Dauertest.

