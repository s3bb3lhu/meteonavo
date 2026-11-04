# Animierte Hintergründe · 2. November 2026

Auf dem Server verfügbar: Living Sky, City Weather, Nature Window, Cinematic Weather und Atmosphere Flow. Die bisherigen Vorlagen bleiben erhalten. Auswahl und Speichern erfolgen im Kanalformular.

## Verhalten

- Automatische Stimmung für Morgen, Tag, Abend und Nacht anhand der Ortszeitzone und der Open-Meteo-Sonnenzeiten.
- Fallback auf is_day bei fehlenden Sonnenzeiten; neutraler Zustand ohne verwertbare Zeitdaten.
- Passende Wolken-, Regen-, Schnee-, Nebel- und Gewittereffekte.
- Sterne nur bei passender Bewölkung; bei geschlossener Wolkendecke ausgeblendet.
- Stadtfenster leuchten bei Abend und Nacht; See und Lichtflächen bewegen sich langsam.
- Abschaltbare Wetteranimationen; Nachrichtenticker bleibt unabhängig.
- Tag-/Nachttests sind als HINTERGRUNDSIMULATION markiert und verändern keine gespeicherten Werte.

Cinematic Weather verwendet drei erzeugte PNGs mit Kamerabewegung, Licht- und Wetterebenen. Es handelt sich um animierte Bildszenen, keine gefilmten Videos oder Livekameras. Modus der Bilderzeugung: integriertes image_gen-Werkzeug. Dateien und vollständige Prompts: app/static/backgrounds/ASSETS.md.

## Verifiziert

17 Backend-Tests bestanden. JavaScript-Tests prüfen Zeitzonen, Dämmerung, DST-Umstellung, Polarnacht-Fallback, Wettercodes, Nachtgrafik und bisherige Wetterseiten/Ticker.

Auf dem Server wurden alle fünf Hintergründe in Tag- und Nachtansicht mit jeweils allen sechs Wetterseiten und eingeblendetem Testticker auf vollständige Darstellung geprüft (60 Kombinationen). Zusätzlich wurden Wettereffekte, Animation, Abschalten, verkleinerte Vorschau, Speichern und Neuladen geprüft. Die Simulation änderte keine Konfiguration.

Echte API-Antworten mit Sonnenaufgang, Sonnenuntergang und Tag-/Nachtflag wurden bestätigt. Ein echter Cinematic-HLS-Stream wurde auf H.264, 720p und AAC geprüft; ein Frame wurde decodiert und visuell kontrolliert. Alle fünf Hintergrundtypen wurden visuell geprüft. Die endgültige Wolkendeckenregel wurde separat in Chromium bestätigt.

Die drei PNGs sind öffentlich vom Anwendungsserver erreichbar; ihre GitHub-Blob-Hashes stimmen mit den lokalen Dateien überein. Alle vorherigen Kanaleinstellungen wurden nach Tests wiederhergestellt. Kein neuer Fünfkanal-Dauertest; HLS bleibt bei den konfigurierten 10 FPS.

Endgültiger Anwendungsstand: 089df50f969748d4515bf287b7e0fe1e5c663b16.

