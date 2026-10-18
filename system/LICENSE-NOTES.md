# Data-Licensing Notes — Hormuz Watch demo

Per-source commercial-use terms. **If a source's terms are unclear, this file
says "unverified — check before commercial use" rather than guessing.**
Recheck terms before any commercial launch: providers change them.

## Sources actually used in this demo

### OpenStreetMap (base map tiles + data)
- **What we use:** map tiles (`tile.openstreetmap.org`) + attribution in the UI.
- **Terms:** Map data © OpenStreetMap contributors, available under the
  **Open Database License (ODbL)** — share-alike: if you build on the data and
  publicly distribute the result, you must share it under ODbL and attribute
  "© OpenStreetMap contributors".
- **Tiles:** the OSM tile servers are a free community resource with a
  [Tile Usage Policy](https://operations.osmfoundation.org/policies/tiles/) —
  no heavy/bulk use, no scraping, proper attribution required. A commercial
  product should switch to a paid tile provider or self-hosted tiles.
- **Commercial use:** allowed under ODbL + tile policy, with attribution.
  Check the tile policy before shipping a commercial map.

### Leaflet (map library, via CDN)
- **Terms:** **BSD-2-Clause** — free for commercial use with copyright notice.
- No data licensing impact.

### Open-Meteo (Marine + Forecast APIs — live sea state + wind)
- **What we use:** keyless API calls for wave height/direction/period, SST, wind.
- **Terms (as stated on open-meteo.com):** free for **non-commercial** use, no key;
  fair-use limits apply. Commercial use requires their paid/commercial offering.
- **This demo:** non-commercial research prototype — within the free tier.
- **Before commercial use:** check Open-Meteo's current pricing/terms page;
  budget for the commercial tier. **Unverified beyond the non-commercial statement
  above — check before commercial use.**

### USGS Earthquake feed (GeoJSON, past day)
- **What we use:** public GeoJSON feed, filtered to the corridor bbox.
- **Terms:** USGS data is a **U.S. federal government work — public domain**,
  free for any use including commercial. USGS asks for (does not legally
  require) credit: "U.S. Geological Survey".
- **Commercial use:** allowed. Attribute as a courtesy.

### GDACS RSS (disaster alerts)
- **What we use:** public RSS feed; the feed itself declares "public domain"
  in its copyright tag (observed in the live feed on 2026-10-13).
- **Terms:** treated as public-domain / free-to-use alert notices. GDACS is a
  UN/EU (JRC) cooperation framework.
- **Commercial use:** alerts themselves are factual notices; republishing
  short factual alert text with attribution is low-risk. The underlying
  GDACS branding/terms were not exhaustively reviewed —
  **check before commercial use** if GDACS content becomes a core product input.

### AISStream (live AIS — pipeline built, NOT yet active)
- **What we use:** free WebSocket AIS feed (terrestrial AIS), key-gated signup.
- **Terms:** AISStream is free to use with a free API key for the stream.
  Its full terms of service / redistribution / commercial-use conditions were
  **not fully verified** from primary sources in this build.
- **Before commercial use:** read the AISStream terms at aisstream.io in full.
  **Unverified — check before commercial use**, especially: redistribution of
  raw AIS data to third parties, commercial resale, and rate/usage limits.
- **Note:** AIS vessel data itself is broadcast publicly by vessels, but the
  *feed* (aggregation, delivery) is AISStream's service — its terms govern.

### News sources cited as provenance (Lokmat Times / TankerTrackers.com quote, MarineLink, SAFETY4SEA, Marine Log)
- **What we use:** short factual values (date/time, coordinates, IMOs, speeds,
  cargo, outcome) + hyperlinks to the original articles. No article text is
  copied into this repo beyond brief factual paraphrase.
- **Terms:** facts are not copyrightable; article text is. We cite, we don't republish.
- **Commercial use:** linking + factual summary is standard practice. Do not
  scrape, copy, or re-host these sites' content.

## Sources NOT used (mentioned in research only)

- **MarineTraffic / VesselFinder / Kpler / Vortexa:** NOT used. Do not scrape them.
  Their data is commercial/proprietary and their ToS prohibit scraping.
- **Copernicus Sentinel-1/2:** NOT yet integrated. When added: Copernicus data
  is free for all uses (including commercial) with attribution, subject to
  Copernicus terms — verify at dataspace.copernicus.eu at integration time.
- **OFAC / EU / UN sanctions lists:** NOT checked in this demo. If a future
  version matches vessels against an official list, cite the exact list +
  retrieval date in every output, and note that list matches still require
  legal review before any public claim.

## Summary table

| Source | Licence / terms | Commercial use |
|---|---|---|
| OpenStreetMap data | ODbL (share-alike) + attribution | Allowed, with attribution + share-alike |
| OSM tiles | Tile Usage Policy (no bulk use) | Use a paid tile provider for production |
| Leaflet | BSD-2-Clause | Allowed |
| Open-Meteo | Free non-commercial; paid commercial tier | Check pricing before commercial use |
| USGS earthquakes | U.S. public domain | Allowed (credit as courtesy) |
| GDACS RSS | Feed declares public domain | Likely allowed; check before commercial use |
| AISStream | Free stream, key required | Unverified — check ToS before commercial use |
| News citations | Facts + links only | Allowed as citations; never scrape/re-host |
