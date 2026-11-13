# MARS-X — Spatial Scale Limitations & Safety Disclaimers (Phase 6)

## 1. Spatial Resolution & Detectable Feature Scale
The pathfinding engine in Phase 6 operates on the MGS MOLA MEGDR 128 ppd tile (`megt00n000hb`), with a nominal post-spacing of $0.0078125^\circ \approx 463.08\text{ m/pixel}$ at the equator.

- **Nyquist Sampling Threshold:** Discrete topographical features must span at least 2 to 3 pixels to be identified unambiguously.
- **Minimum Detectable Feature Scale:** $\sim 1.15\text{ km}$ ($2.5 \times 463.08\text{ m}$).
- **Unresolved Hazards:**
  - Meter-scale boulders, rock clusters, and field obstacles.
  - Crevasses, fissures, and narrow thermal contraction polygons.
  - Loose drift sand, soft dust deposits, and localized rover-trap slip hazards.
  - Meter-scale terrace scarps or steep ditch walls smaller than 463 metres.

---

## 2. Mandatory Scientific Safeguards
1. **Never Label Routes as Astronaut-Safe:** The prototype computes a mathematical optimization on a regional digital elevation model. It does not evaluate spacesuit biomechanics, metabolic oxygen consumption, radiation shielding, or rover chassis clearance.
2. **Never Claim Upsampling Creates Real Detail:** Interpolating or resampling 463 m MOLA data to 1 m does NOT recover microtopography. HiRISE stereophotogrammetry is required for sub-meter traverse verification.
3. **No Environmental Forecasting:** Historical radiation (RAD) or weather (REMS) observations are research records, not live forecasts of current Martian dust storm or space-weather conditions.
