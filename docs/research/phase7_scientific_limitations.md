# MARS-X — Phase 7 Research: Scientific Limitations & Operational Disclaimers

## 1. Prototype Scope and Operational Boundaries

MARS-X is an advanced academic and exploratory research platform developed for the NASA Space Apps Challenge 2026. It is **NOT** certified flight software, nor is it an operational autonomous navigation system for crewed Mars surface operations (EVA) or autonomous robotic traverses.

---

## 2. Key Scientific Limitations

### 2.1 Spatial Resolution and Nyquist Sampling Limits
- **MOLA 128 ppd (463 m/px):** The effective spatial Nyquist resolution is approximately $2 \times 463\text{ m} \approx 926\text{ to }1,157\text{ meters}$. Terrain features smaller than 1 kilometer (such as individual boulders, meter-scale crevasses, dune slopes, and gully walls) are completely smoothed and invisible in MOLA topography.
- **USGS CTX DTM (20 m/px):** The effective spatial Nyquist resolution is approximately $40\text{ to }50\text{ meters}$. While resolving large crater rims and regional scarps, rover-scale hazards (< 5 meters) remain below detection thresholds.
- **HiRISE DTM (1 m/px):** While resolving meter-scale boulders and dunes, coverage is confined to isolated swathes (< 0.1% of Mars).

### 2.2 Vertical Accuracy and Ephemeris Drift
- Orbital stereo DTMs (CTX, HiRISE) are subject to localized stereo correlation artifacts, shadow occlusion, and spacecraft orbit ephemeris drift.
- Although rigidly tied to MOLA tracks via ASP `pc_align`, local vertical standard deviations of $\pm 50\text{ to }75\text{ meters}$ remain common in high-relief crater environments.

### 2.3 NoData Sentinels
- NoData pixels (sentinels `-32768` or `-32767.0`) represent unobserved, shadowed, or failed stereo correlation areas. MARS-X strictly masks these pixels and treats them as impassable obstacles; NoData is never assumed to be zero elevation or safe flat plain.

### 2.4 Prohibition of Astronaut Safety Claims
- All cost metrics, slopes, relief values, and calculated path lines represent mathematical optimizations of specified terrain surfaces.
- Traverses must never be represented as guaranteed safe or approved for astronaut Marswalk operations without in-situ ground-truth verification and multi-sensor orbital imaging.

