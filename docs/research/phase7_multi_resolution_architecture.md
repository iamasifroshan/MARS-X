# MARS-X — Phase 7 Research: Multi-Resolution Architecture

## 1. Architectural Philosophy

The MARS-X multi-resolution terrain architecture prevents the catastrophic error of false upsampling while enabling seamless multi-tier elevation intelligence:
- Coarser baseline models (MOLA 463 m/px) provide planetary continuity.
- High-resolution models (CTX 20 m/px, HiRISE 1 m/px) provide tactical obstacle detection and slope calibration.
- Each dataset retains its native grid post-spacing, native CRS, native vertical datum, and native uncertainty bounds.

---

## 2. Controlled 4-Tier Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│ Tier 1: Global Coarse (14.8 km/px) — MOLA MEGDR 4 ppd       │
│ Global planetary continuity, Olympus Mons / Tharsis relief  │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│ Tier 2: Global Base (463 m/px) — MOLA MEGDR 128 ppd         │
│ 3 verified tiles covering 26.05% of Mars; regional routing  │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│ Tier 3: Regional High-Res (20 m/px) — USGS Controlled CTX   │
│ Stereo photogrammetry DTMs; resolves crater rims & gullies  │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│ Tier 4: Local Tactical (1 m/px) — HiRISE Meter-Scale DTMs   │
│ Microtopography; resolves boulder hazards, dunes, scarps    │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. The 10-State Dataset Lifecycle

All terrain rasters in MARS-X are governed by a deterministic lifecycle state machine:

1. **`registered`**: Listed in the authoritative dataset catalogue.
2. **`discovered`**: Remote archive endpoints, STAC items, and PDS labels verified.
3. **`downloaded`**: Physical file retrieved to local disk storage.
4. **`integrity_verified`**: Cryptographic SHA-256 hash verified against upstream manifest.
5. **`metadata_validated`**: Header dimensions, data types, and scale factors verified.
6. **`geospatially_validated`**: Bounding box, CRS, and pixel-registration verified.
7. **`scientifically_validated`**: Elevation value ranges, landmark features, and NoData masks confirmed.
8. **`analysis_ready`**: Integrated into terrain analysis, hazard engine, and routing services.
9. **`failed`**: Ingestion, validation, or corruption error detected.
10. **`unavailable`**: Product known but currently inaccessible.

---

## 4. Anti-Upsampling Guarantee

To prevent dangerous pathfinding over synthetic data:
- MARS-X strictly prohibits interpolating a coarser DTM (e.g. 463 m/px) into finer grid cells (e.g. 20 m/px) to fabricate high-resolution navigation grids.
- If a route region requests high-resolution pathfinding, MARS-X inspects the multi-resolution catalog. If only MOLA 128 is available, the route planner operates at 463 m/px grid spacing and explicitly reports the minimum detectable feature limit (~1,157 m Nyquist threshold).

