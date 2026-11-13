# Mars Coordinate Reference Systems — CRS Projection Notes

> Research notes on coordinate reference systems for Mars geospatial data in MARS-X.

---

## Why Mars Needs Its Own CRS

Earth-centric coordinate reference systems (EPSG:4326 WGS 84, EPSG:3857 Web Mercator) are defined for Earth's geoid and ellipsoid. Mars has fundamentally different physical parameters:

| Parameter | Earth (WGS 84) | Mars (IAU 2000) |
|---|---|---|
| Equatorial radius | 6,378.137 km | 3,396.19 km |
| Polar radius | 6,356.752 km | 3,376.20 km |
| Flattening | 1/298.257 | 1/169.894 |
| Surface gravity | 9.81 m/s² | 3.72 m/s² |

Using EPSG:3857 (Web Mercator) for Mars data introduces systematic distortion because the projection is parameterised on Earth's ellipsoid. Distances, areas, and angles computed in EPSG:3857 on Mars data are **scientifically meaningless**.

---

## Mars CRS Identifiers

### EPSG:104905 — IAU 2000 Mars Geographic

- **Type:** Geographic 2D CRS
- **Datum:** IAU 2000 Mars
- **Coordinate system:** Latitude/longitude on the Mars IAU 2000 ellipsoid
- **Latitude convention:** Areocentric (planetocentric)
- **Longitude convention:** 0°–360° East (positive East from the Mars prime meridian at Airy-0 crater)
- **Usage:** Most NASA/USGS Mars data products

### IAU:49900

- Equivalent to EPSG:104905 in many tools
- Used by USGS Astrogeology and the IAU cartographic standards

### Areocentric vs. Areographic Latitude

- **Areocentric (planetocentric):** Angle from the equatorial plane to a line connecting the point to the planet centre. Used by most NASA PDS data.
- **Areographic (planetographic):** Angle from the equatorial plane to the surface normal. Differs from areocentric by up to ~0.3° due to Mars's oblateness.

> [!IMPORTANT]
> The distinction matters for accurate geolocation. All 11 MARS-X datasets use areocentric (planetocentric) latitude with `crs: "IAU:49900"`.

---

## NASA Mars Trek WMTS Tiles

NASA's [Mars Trek](https://trek.nasa.gov/mars/) provides Web Map Tile Service (WMTS) layers for Mars:

- **Projection:** EPSG:104905 (IAU 2000 Mars)
- **Tile scheme:** Standard WMTS with zoom levels
- **Available layers:** MOLA hillshade, MOLA colorised elevation, THEMIS daytime IR, Viking MDIM 2.1, and others
- **Tile format:** PNG

These tiles are natively in Mars CRS and **cannot be correctly displayed** in a standard EPSG:3857 slippy map without reprojection or CRS-aware rendering.

---

## MapLibre GL JS Limitations

MapLibre GL JS (the open-source fork of Mapbox GL JS) **only natively supports EPSG:3857** (Web Mercator) for its tile rendering pipeline.

### What This Means

- MapLibre can load and render raster tiles from any URL, but it assumes they are in EPSG:3857
- If Mars CRS tiles (EPSG:104905) are loaded directly, they will display but with incorrect geographic coordinates
- Pan, zoom, and coordinate readout will report Earth Web Mercator coordinates, not Mars coordinates
- Distance and area measurements will be wrong

### Why It Still Works (Visually)

For visual-only display (shaded relief, hillshade imagery), the tiles "look correct" because the image pixels are simply painted on screen. The map's coordinate system is wrong, but the visual appearance is acceptable for non-analytical use.

For any **quantitative** use (elevation queries, distance measurement, route planning), correct CRS handling is mandatory.

---

## Options for Mars CRS Support

### Option 1: Server-Side Reprojection *(Simplest)*

Reproject Mars tiles from EPSG:104905 to EPSG:3857 on the backend before serving them to MapLibre.

**Pros:**
- MapLibre works out of the box
- No client-side projection code

**Cons:**
- Introduces reprojection distortion (Mars ellipsoid → Earth ellipsoid)
- All coordinate readouts show Earth-referenced values
- Must back-transform coordinates for any Mars-specific computation

### Option 2: Custom Projection with proj4js

Add a custom Mars CRS definition to [proj4js](http://proj4js.org/) and transform coordinates on the client.

```javascript
proj4.defs("EPSG:104905", "+proj=longlat +a=3396190 +b=3376200 +no_defs");
```

**Pros:**
- Correct Mars coordinates throughout the application
- Can display accurate lat/lon readout on the map
- Distance/area calculations can use Mars parameters

**Cons:**
- MapLibre still renders tiles in its internal 3857 grid
- Need custom coordinate transform layer between MapLibre events and Mars coordinates
- More complex implementation

### Option 3: Deck.gl or CesiumJS *(Alternative Renderers)*

Use a 3D globe renderer (CesiumJS) or a projection-agnostic renderer (deck.gl) that supports custom ellipsoids.

**Pros:**
- Native support for non-Earth bodies (CesiumJS)
- True 3D terrain rendering
- Correct coordinate handling

**Cons:**
- Different API and rendering model from MapLibre
- Heavier client-side dependencies
- May require significant frontend refactoring

### Current Decision

**Option 2 (proj4js)** is the intended approach. MapLibre is retained for its performance and ecosystem, with a coordinate transformation layer added for Mars-specific calculations. CRS validation is pending implementation.

---

## Shaded Relief vs. Numerical DTM

> [!CAUTION]
> Shaded relief and numerical DTM data products serve different purposes and **must never be conflated**.

### Shaded Relief (Visual Imagery)

- **What it is:** A pre-rendered hillshade image showing terrain illumination
- **Pixel values:** RGB or grayscale intensity representing visual appearance
- **Use:** Map background, terrain visualisation, context imagery
- **Example:** MOLA hillshade tiles from Mars Trek

### Numerical DTM (Elevation Model)

- **What it is:** A grid of quantitative elevation values
- **Pixel values:** Floating-point metres (or other units) relative to a reference datum
- **Use:** Elevation queries, slope/aspect calculation, route planning cost surfaces, volumetric analysis
- **Example:** MOLA MEGDR gridded elevation data

### Why Separation Matters

Reading pixel values from a shaded relief image and treating them as elevations produces **scientifically meaningless results**:

- Shaded relief pixel values encode illumination angle, not elevation
- A bright pixel does not mean "high elevation" — it means "facing the light source"
- Slope calculations on shaded relief produce the derivative of the illumination function, not terrain gradient

MARS-X maintains this separation by distinguishing `product_type` in the dataset catalogue (e.g., "Topographic grid (DTM)" vs. visual imagery products).

---

## Current Status

| Item | Status |
|---|---|
| Mars CRS identified (EPSG:104905 / IAU:49900) | ✅ Complete |
| Dataset metadata uses correct CRS references | ✅ Complete |
| proj4js Mars CRS definition researched | ✅ Complete |
| MapLibre coordinate transform layer | ⏳ Pending |
| Server-side reprojection pipeline | ⏳ Pending |
| CRS validation in data ingestion | ⏳ Pending |
| Elevation query from DTM (not hillshade) | ⏳ Pending |

---

## References

- [IAU Working Group on Cartographic Coordinates and Rotational Elements](https://astrogeology.usgs.gov/groups/IAU-WGCCRE)
- [EPSG:104905 — IAU 2000 Mars](https://epsg.io/104905)
- [NASA Mars Trek](https://trek.nasa.gov/mars/)
- [proj4js](http://proj4js.org/)
- [MapLibre GL JS](https://maplibre.org/maplibre-gl-js/docs/)
- [MOLA MEGDR Data](https://pds-geosciences.wustl.edu/missions/mgs/megdr.html)
