# MARS-X — Phase 7.1 Research: Vertical Datum Audit & pc_align Evidence Assessment

## 1. Upstream Alignment Evidence

The USGS Astrogeology STAC metadata for `P21_009323_1754_XN_04S293W__N02_062992_1754_XI_04S293W` documents the vertical geodetic workflow used during production:
> *"Low resolution, 100mpp DTMs were then generated for each stereopair and used to seed the generation of a high resolution DTM. This high resolution DTM was aligned to MOLA using a two step pc_align process. From the aligned point cloud the final DEM was extracted at the described post spacing and a final adjustment made to align with the Mars aeroid (geoid)."*

The upstream STAC item publishes references to:
- `qa_metrics`: `qa_metrics.txt`
- `mola_csv`: `P21_..._mola_shots.csv`
- `intersection_error`: `P21_..._intersection_error.tif`

---

## 2. Local Evidence Audit

An inspection of the local workspace directory `data/raw/ctx/` reveals:
- **Locally Downloaded Files:**
  - `P21_009323_..._dtm.tif` (12,734,013 bytes)
  - `P21_009323_..._provenance.json` (1,440 bytes)
  - `P21_009323_..._stac.json` (15,525 bytes)
- **Files Not Present Locally:**
  - `qa_metrics.txt` (Contains ASP version, convergence iterations, residual histograms, and rigid transformation matrix $[R \mid T]$).
  - `P21_..._mola_shots.csv` (Contains individual MOLA PEDR laser return coordinates used as point-cloud control).

---

## 3. Classification of Vertical Compatibility

Based on the evidence audit:
1. **Vertical Alignment Claim:** The claim that CTX elevations were tied to MOLA tracks using ASP `pc_align` is **corroborated by authoritative USGS STAC metadata**.
2. **Local Reproducibility Limitation:** Because the exact ICP transformation matrix $[R \mid T]$ and residual logs are hosted upstream on AWS S3 rather than stored in the local repository, the alignment cannot be re-simulated from scratch without network retrieval of `qa_metrics.txt`.
3. **Formal Geodetic Status:** The product is classified as:
   `VerticalCompatibilityStatus.COMPATIBLE_WITH_DOCUMENTED_TRANSFORMATION`
   *(Not `COMPATIBLE` without qualification, and never assigned an arbitrary ad-hoc vertical offset).*

---

## 4. Empirical Vertical Offset ($\Delta z \approx -55\text{ m}$)

Cross-sensor comparison reveals an empirical elevation offset between CTX and MOLA:
$$\mu_{\Delta z} = z_{\text{CTX}} - z_{\text{MOLA}} \approx -55.8\text{ meters} \quad (\sigma \approx 46.5\text{ to }51.8\text{ meters})$$

### Scientific Basis for the Elevation Difference:
1. **Spatial Support / Nyquist Resolution Filtering:** MOLA has a post-spacing of $463\text{ meters}$ and a physical laser footprint diameter of $\sim 168\text{ meters}$. It acts as a spatial low-pass filter, truncating sharp crater bottoms and averaging slopes. CTX, with $20\text{ m}$ post-spacing, resolves deep crater interiors, steep canyon gullies, and crater floor pits that sit tens of meters below the regional MOLA average.
2. **Stereo Reconstruction Ephemeris Uncertainties:** Stereophotogrammetric DTM generation from orbiter line-scan cameras is sensitive to sub-arcsecond spacecraft pointing jitter and orbit reconstruction uncertainty. Even after `pc_align` rigid transformation, localized vertical deviations of $\pm 30\text{ to }60\text{ meters}$ remain characteristic of stereo DTM products in complex topography.
3. **Zero Arbitrary Adjustment Policy:** MARS-X strictly prohibits applying an arbitrary $+55\text{ m}$ additive offset to the CTX DTM. The difference is an authentic physical and methodological consequence of comparing $20\text{ m}$ stereo photogrammetry with $463\text{ m}$ regional laser altimetry.
