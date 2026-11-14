# MARS-X — Phase 7 Research: MOLA 128 ppd Regional Expansion

## 1. Executive Summary

In Phase 7, the regional baseline coverage of MARS-X was expanded from a single MOLA 128 pixels/degree tile (`megt00n000hb`) to three authentic, contiguous NASA PDS MOLA MEGDR tiles. This expansion increases verified high-resolution regional topography coverage from **8.68% to 26.05% of Mars' total spherical surface area** while maintaining complete bit-for-bit cryptographic traceability.

---

## 2. Acquired Tile Inventory & Cryptographic Provenance

All tiles were retrieved directly from the authoritative NASA Planetary Data System (PDS) Geosciences Node archive:
- Archive Base URL: `https://pds-geosciences.wustl.edu/mgs/mgs-m-mola-5-megdr-l3-v1/mgsl_300x/meg128/`
- Binary Format: 16-bit signed big-endian integer raster (`MSB_INTEGER`), raw uncompressed binary (`.img`)
- Associated Metadata: NASA PDS v3 detached label file (`.lbl`)

| Tile Identifier | Geographic Coverage | File Size (bytes) | SHA-256 Checksum | Spherical Surface Area | Local Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `megt00n000hb` | Lat: [-44°, 0°], Lon: [0°, 90°E] | 129,761,280 | `f57274b54e3d06e23297a7e174c8612feea118ca8611ea89dbf99276d8da7cb5` | 8.6832% | Acquired & Validated |
| `megt44n000hb` | Lat: [0°, 44°N], Lon: [0°, 90°E] | 129,761,280 | `14022166079edafc99650f354e5a634e6eb2c2ea544b444c01cd8ee55437df36` | 8.6832% | Acquired & Validated |
| `megt00n090hb` | Lat: [-44°, 0°], Lon: [90°, 180°E] | 129,761,280 | `764946162d4c650abfb22aa284595a15374a7185f302a639c19e6602c67a1d6e` | 8.6832% | Acquired & Validated |

**Total Verified Physical Raster Storage:** 389,283,840 bytes (~371.25 MB)
**Total Verified Spherical Mars Coverage:** **26.0496%**

---

## 3. Spatial Adjacency and Boundary Seam Verification

The three acquired tiles form a continuous L-shaped regional corridor spanning the Martian equatorial and southern mid-latitude zones:

```
Latitude Band 44°N - 0°:       [ megt44n000hb ] (0°-90°E)
                                       │ (Shared edge at 0°N)
Latitude Band 0° - 44°S:       [ megt00n000hb ] ── (Shared edge at 90°E) ── [ megt00n090hb ] (90°-180°E)
```

1. **North-South Boundary (`megt44n000hb` and `megt00n000hb`):**
   - Shared edge: Exactly 0.0° Latitude (equator) spanning 0.0°E to 90.0°E.
   - Coordinate registration: Both tiles employ pixel-is-point center registration with exact 1/128° spacing (0.0078125°/px).
   - Seam alignment: Verified seamless boundary alignment with identical projection parameters (Equirectangular IAU:49900).

2. **East-West Boundary (`megt00n000hb` and `megt00n090hb`):**
   - Shared edge: Exactly 90.0°E Longitude spanning -44.0° to 0.0° Latitude.
   - Seam alignment: Verified identical vertical reference datum (MOLA Areoid) and zero geodetic step discontinuity across meridian 90°E.

---

## 4. Rigorous Coverage Tier Separation

MARS-X strictly separates theoretical archive potential from verified on-disk availability:
- **Theoretical Archive Coverage:** 99.94% (covers -88° to +88° across 16 tiles).
- **Downloaded Tile Coverage:** 26.05% (3 tiles on disk).
- **Integrity-Verified Coverage:** 26.05% (all 3 tiles match authoritative SHA-256 hashes).
- **Geospatially Validated Coverage:** 26.05% (bounds, projection, and pixel size verified).
- **Single-Tile Route Planning Sandbox:** 8.68% (`megt00n000hb`).

No UI or API endpoint is permitted to represent the theoretical 99.94% archive coverage as locally available terrain.

