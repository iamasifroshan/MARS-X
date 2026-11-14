# MARS-X — Research Report: Planetary Geographic Identity & CTX Swath Calibration

## 1. Problem Statement (Correction B)

Prior to Phase 8.1, the authentic USGS numerical CTX DTM file:
`data/raw/ctx/P21_009323_1754_XN_04S293W__N02_062992_1754_XI_04S293W_dtm.tif`
was colloquially misattributed in candidate region presets and selection messages as "Melas Chasma Canyon Floor".

### 1.1 Source Raster Geographic Analysis
Parsing the USGS PDS product identifier:
- Identifier: `P21_009323_1754_XN_04S293W...`
- Sub-solar latitude: $04^\circ\text{S}$ ($-4^\circ\text{N}$)
- West Longitude: $293^\circ\text{W}$
- Positive-East Longitude equivalence:
  $$\lambda_{\text{east}} = 360^\circ - 293.5^\circ = 66.5^\circ\text{E}$$
- True Raster Bounds:
  - Latitude: $[-5.18745^\circ\text{N}, -4.00320^\circ\text{N}]$
  - Longitude: $[66.03609^\circ\text{E}, 66.61720^\circ\text{E}]$

### 1.2 Geomorphological Ground Truth
- On Mars, coordinates $(\sim 4.6^\circ\text{S}, 66.3^\circ\text{E})$ are located in **Tyrrhena Terra**, in the dissected cratered highlands bordering northwest Hesperia Planum.
- The actual **Melas Chasma** rift canyon floor within Valles Marineris is located at:
  - Latitude: $-9.8^\circ\text{N}$ ($9.8^\circ\text{S}$)
  - Longitude: $283.6^\circ\text{E}$ ($76.4^\circ\text{W}$)
- Confusing Tyrrhena Terra with Melas Chasma represents a spatial error exceeding $13,000\text{ km}$ across the Martian sphere.

---

## 2. Corrective Implementation

1. **Preset Separation:**
   - `tyrrhena-terra-active` (Lat $[-5.10^\circ, -4.50^\circ\text{N}]$, Lon $[66.10^\circ, 66.50^\circ\text{E}]$):
     - Name: **"Tyrrhena Terra (CTX DTM Swath)"**
     - Geological context: *"Inter-crater highland plains and dissecting valley networks in Tyrrhena Terra near Hesperia Planum margin, covered by authentic 20m USGS CTX DTM (P21_009323_1754)."*
   - `melas-chasma-valles-marineris` (Lat $[-10.50^\circ, -9.00^\circ\text{N}]$, Lon $[282.50^\circ, 285.00^\circ\text{E}]$):
     - Name: **"Melas Chasma Canyon Floor"**
     - Geological context: *"Central deep canyon floor of Valles Marineris (~9.8°S, 283.6°E / 76.4°W), covered by authentic MOLA regional elevation baseline."*
2. **Resolution Selector Diagnostics:**
   Updated rejection explanations to state: *"CTX DTM is confined to the Tyrrhena Terra DTM swath [-5.19°N to -4.00°N, 66.04°E to 66.62°E]."*
3. **Frontend Preset & Map Markers:**
   Updated `MapContainer.tsx`, `TerrainIntelligencePanel.tsx`, and `MultiResolutionTerrain.tsx` with scientifically accurate regional attribution.
