# MARS-X — Research Report: Heuristic Data Quality Index & Non-Probabilistic Framing

## 1. Problem Statement (Correction C)

In earlier iterations, the metric:
$$\text{Score} = 100 \times (0.45\, C + 0.35\, S + 0.20\, D)$$
was colloquially termed `data_confidence_score` and displayed as a percentage or confidence indicator.

Without strict qualification, users or mission planners could misinterpret this score as:
- A statistical probability of terrain safety.
- An astronaut EVA risk rating.
- A rover traversability success rate.

---

## 2. Reframing as "Heuristic Data Quality Index"

To prevent unwarranted claims of operational clearance or statistical survival probabilities:
1. **Explicit Scientific Naming:** Renamed primary attribute to `terrain_data_quality_index` (with `data_confidence_score` maintained as a backward-compatible alias).
2. **Deterministic Weight Breakdown:**
   - **$C$ (Valid Coverage Factor, 45% weight):**
     $$C = \min\left(1.0, \max\left(0.0, \frac{\text{valid\_coverage\_pct}}{100.0}\right)\right)$$
   - **$S$ (Scale Suitability Factor, 35% weight):**
     $$\text{ratio} = \frac{\max(\text{res}, W_{\text{target}})}{\max(\min(\text{res}, W_{\text{target}}), 10^{-4})}$$
     $$S = \max(0.2, 1.0 - 0.12 \log_2(\text{ratio}))$$
   - **$D$ (Vertical Datum Quality Factor, 20% weight):**
     $$D = 1.0 \text{ if "Areoid" in datum else } 0.8$$
3. **Mandatory Disclaimer Text:**
   Every API payload and UI presentation carrying this index includes the following limitation:
   > *"Heuristic Data Quality Index reflects data completeness and resolution matching, NOT statistical mission success. Topographic complexity does not imply astronaut or rover operational safety."*
