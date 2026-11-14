# Phase 8: Planetary Terrain Intelligence & Region Comparison

**Author:** Mars Terrain Scientist & Planetary Mission Planner  
**Date:** 2026-11-14  
**Project:** MARS-X — Planetary Terrain Intelligence Platform  
**Phase:** 8 — Resolution-Aware Terrain Intelligence  

---

## 1. Scientific Objective

Planetary exploration requires comparing candidate landing, science, or traversal zones using objective, reproducible criteria. MARS-X implements explainable terrain intelligence (`backend/app/science/terrain_intelligence.py`) that contrasts regions strictly at **equivalent physical analysis scales**, preventing the illusion that finer data automatically implies safer terrain.

---

## 2. Transparent Data Confidence Scoring

Rather than arbitrary black-box scores, MARS-X defines a fully documented, linear-weighted formula:
$$\text{Confidence Score} = 100 \times \left(0.45 \cdot C_{\text{valid}} + 0.35 \cdot S_{\text{scale}} + 0.20 \cdot D_{\text{datum}}\right)$$

### Components:
1. **Valid Data Coverage Factor ($C_{\text{valid}} \in [0.0, 1.0]$):**
   $$C_{\text{valid}} = \frac{\text{Valid Non-NoData Pixels}}{\text{Total Pixels in Envelope}}$$
2. **Scale Suitability Factor ($S_{\text{scale}} \in [0.2, 1.0]$):**
   Penalizes resolution mismatch relative to the target analysis window:
   $$S_{\text{scale}} = \max\left(0.2, 1.0 - 0.12 \times \log_2\left(\frac{\max(r, W)}{\min(r, W)}\right)\right)$$
3. **Datum Quality Factor ($D_{\text{datum}} \in [0.0, 1.0]$):**
   - $1.0$: Direct MOLA GMM-3 Areoid realization.
   - $0.8$: Tied to MOLA via documented ASP `pc_align` / bundle adjustment.
   - $0.0$: Undocumented or uncalibrated vertical reference.

---

## 3. Presets & Pairwise Comparison Matrix

Four authoritative candidate regions are integrated into the comparison engine:
1. **Melas Chasma Floor ($[-5.1^\circ, -4.5^\circ\text{N}], [66.1^\circ, 66.5^\circ\text{E}]$):**
   - Active CTX numerical DTM ($20.01\text{ m/px}$) + MOLA 128 ppd.
   - High slope variability along canyon terraces; high data confidence ($> 75/100$).
2. **Schiaparelli Basin Floor ($[-1.1^\circ, -0.8^\circ\text{N}], [13.8^\circ, 13.95^\circ\text{E}]$):**
   - Validated MOLA 128 ppd tile ($463\text{ m/px}$). HiRISE remote catalogued only.
   - Moderate slope ($\sim 2.5^\circ$); planar sedimentary deposits.
3. **Jezero Crater Delta ($[18.3^\circ, 18.55^\circ\text{N}], [77.35^\circ, 77.6^\circ\text{E}]$):**
   - MOLA global baseline. Distant delta scarps unresolvable at regional MOLA scale.
4. **Coprates Chasma Escarpment ($[-14.5^\circ, -14.0^\circ\text{N}], [59.0^\circ, 59.5^\circ\text{E}]$):**
   - Validated MOLA 128 ppd tile. Extreme regional slopes ($> 18^\circ$); high complexity.

### Sample Automated Contrast Output:
> *"At 500m physical scale, 'Melas Chasma Canyon Floor' exhibits higher topographic roughness (mean 18.2m vs 6.4m) than 'Schiaparelli Basin Floor', reflecting dissected canyon terracing. Data confidence score: Melas Chasma = 84.2/100 vs Schiaparelli = 71.5/100."*
