# Optional Google Maps radar basemap

The existing OpenStreetMap, Esri and overview maps remain available and are the defaults. Google is loaded only for a channel that explicitly selects a Google map. Weather echoes and coverage continue to come from RainViewer; Google supplies the basemap, not live radar. Satellite imagery is archival, not a live/night camera image.

## Setup

1. Create your own Google Cloud project, enable **Maps JavaScript API** and billing. Set appropriate quotas and billing alerts. Google charges for map loads; video frames do not each create a new map load. One map instance is reused across page rotations within a browser session. Renderer restarts, reloads and additional browser sessions can create additional loads.
2. Create a dedicated **browser API key**. Apply both website (HTTP referrer) restrictions and an API restriction to **Maps JavaScript API**. Authorize only your actual administration/preview origin. Do not use an unrestricted server key. Never commit your key to GitHub.
3. Open **Settings → Outputs & sources → Google Maps for radar**. Enter the key and save. An empty field preserves it; use the removal checkbox to delete it. The settings status never returns the raw key.
4. Under **Channels & addresses → Radar map style**, select Google Map, Satellite, Hybrid or Terrain and save the channel. Hybrid combines satellite imagery with roads and labels.
5. Choose a radar radius of **1–5000 km**. This is approximately the center-to-side distance for the nominal 800×300 map; different viewport proportions crop the map around the same center. Smaller radii enlarge streets, but cannot improve RainViewer's measurement resolution. For example, 5 km is approximately 10 km across before viewport cropping. The maximum radar source zoom remains 7 and is enlarged at closer distances.

## Browser key visibility and privacy

A Maps JavaScript API browser key is necessarily visible in the browser and requests to Google. The public client configuration endpoint exposes it only for channels configured with Google; this is intentional, not a secret-storage guarantee. Website and API restrictions are mandatory operational protection. The TomTom server credential is separate and remains server-side. The key is stored in the private configuration SQLite volume, not encrypted at rest; protect database backups.

Loading Google sends the map location, visitor IP, referrer and browser request information to Google. Inform users in the privacy notice for your installation and establish any necessary consent before enabling this optional provider. The unconfigured/default maps make no Google Maps API requests.

## HLS / Xtream renderer

Google is **off in broadcast mode by default**, even if selected for browser preview. Enable **Use Google map in broadcast (usage permission checked)** only after checking the rights for your particular TV/IPTV use. This switch is a configuration choice, not a grant of rights from Google. The software's private-use license does not grant rights to Google's content.

The renderer currently loads `http://api:8080/view/...` inside Docker. If you authorize broadcast use, configure the browser key's allowed referrers for the actual renderer origin as well as your public HTTPS origin. Verify this in Google's console; a key restricted solely to the public address will reject the internal renderer. Keep this dedicated browser key API-restricted and monitor usage. Do not remove all restrictions to work around an error.

Google's SDK renders its own logo and map-data credits. Radar overlays are clipped above the bottom attribution area. No Google tiles are proxied, scraped or stored in our existing tile cache. Without a key, without broadcast enabled, or on SDK/authorization failure, the view uses OpenStreetMap (Map/Terrain) or Esri (Satellite/Hybrid) and displays a fallback message. A changed key requires reloading an already open preview; the SDK is loaded only once per document.

## Sources and validation

- [Google API loading](https://developers.google.com/maps/documentation/javascript/load-maps-js-api)
- [Map types and overlays](https://developers.google.com/maps/documentation/javascript/maptypes)
- [API key restrictions](https://developers.google.com/maps/api-security-best-practices)
- [Current prices](https://developers.google.com/maps/billing-and-pricing/pricing)
- [Geo guidelines, including TV and online video](https://about.google/brand-resource-center/products-and-services/geo-guidelines/)
- [EEA terms](https://cloud.google.com/terms/maps-platform/eea)

Automated tests cover persistence, authentication, intentional browser-key delivery, default broadcast exclusion, preserved/removed keys, existing providers, 1 km bounds, projection alignment, SDK loading, map reuse and fallback behavior. A successful real Google authorization/billing test requires the operator's configured key; mocked SDK tests do not establish that permission.
