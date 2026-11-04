# Cinematic Weather – erzeugte Hintergrundbilder

Erzeugung: integriertes image_gen-Werkzeug (Bildgenerierungs-Skill), keine CLI/API-Schlüssel. Alle Bilder sind eigens erzeugte generische Landschaften ohne Anspruch auf einen realen Ort oder eine Liveaufnahme. Das Programm animiert die Bilder durch Kamerabewegung und zusätzliche Wetter-/Lichtschichten.

Projektdateien:
- cinematic-lake.png: bewölkte Tageslandschaft.
- cinematic-day.png: klare Tagesvariante.
- cinematic-night.png: klare Nachtvariante.

## Prompt: Basisbild

Use case: photorealistic-natural. Asset type: panoramic background photograph for a weather television channel, 16:9 landscape. Create an original photorealistic tranquil central-European lake landscape, gently rolling forested hills in the distance, low horizon in the lower third, wide open softly cloudy sky, subtle reflections on the water, balanced diffuse natural daylight with NO visible sun, no strong directional shadows. Restrained slate blue, natural green, soft grey palette. Premium cinematic landscape photography, realistic fine texture, natural colors. This will be slowly animated with CSS camera motion and receive separate rain, snow and day/night lighting layers; leave generous calm space across the whole frame for readable weather information overlaid by code. No people, buildings, letters, numbers, logos, text, watermark, split screens, UI, forecast graphics, lightning, rain streaks or snowfall. Not an identifiable actual location; a generic landscape illustration in photographic style.

## Prompt: Tagesvariante (Basisbild als Editierreferenz)

Use case: lighting-weather. Edit the reference landscape background for a weather television channel. Preserve exactly the lake, hills, foreground, framing, aspect ratio and photographic realism. Change ONLY lighting and sky to a bright clear daytime with a soft blue sky and just a few distant wispy clouds. No visible sun disk, no dramatic shadows, no text, no watermark, no people, no buildings. This is an original generic landscape, not a live camera.

## Prompt: Nachtvariante (Basisbild als Editierreferenz)

Use case: lighting-weather. Edit the reference landscape background for a weather television channel. Preserve exactly the lake, hills, foreground, framing, aspect ratio and photographic realism. Change ONLY lighting and sky to a beautiful realistic clear night, dark navy sky with small subtle stars, dark silhouetted hills, faint silvery reflections on lake. No visible moon disk (a moon will be layered by code), no artificial lights, no text, no watermark, no people, no buildings, no aurora. A calm original generic landscape, not a live camera.
