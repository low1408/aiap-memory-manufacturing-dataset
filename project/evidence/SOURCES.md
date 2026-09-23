# Source and modeling provenance

Dataset scenario: SK hynix-like HBM3E, 8-high and 12-high. Public source review began on 2026-09-10; the synthetic release was generated on 2026-09-14.

This is an independently constructed synthetic manufacturing simulation. It contains no SK hynix factory records, recipes, customer data, or measured production yields. Public product descriptions anchor the architecture; the generator's numeric process distributions, correlations, noise, defect probabilities, and operating limits are illustrative assumptions. The dataset has not been statistically calibrated against an actual HBM production line.

## Public facts used

| Source | Publication date | Supported facts and scope |
|---|---|---|
| [SK hynix: 12-layer HBM3E volume production](https://news.skhynix.com/en/sk-hynix-begins-volume-production-of-the-world-first-12-layer-hbm3e/) | 2024-09-26 | HBM3E has 8-high/24 GB and 12-high/36 GB configurations built from 3 GB DRAM dies. The 12-high product uses DRAM chips described as 40% thinner than the earlier 8-high product while maintaining package thickness. TSV stacking and Advanced MR-MUF address warpage and heat dissipation. The release reports 9.6 Gbps memory speed. These facts support configuration choices and a relative thinning scenario, not absolute die dimensions or factory process windows. |
| [SK hynix: HBM3E volume production](https://news.skhynix.com/en/sk-hynix-begins-volume-production-of-industry-first-hbm3e/) | 2024-03-19 | Describes vertical DRAM interconnection, Advanced MR-MUF, warpage control, and up to 1.18 TB/s data throughput. The reported 10% heat-dissipation improvement is a product comparison; it does not supply an absolute thermal-resistance distribution or a yield parameter. |
| [SK hynix: team behind 12-layer HBM3](https://news.skhynix.com/en/meet-the-sk-hynix-team-behind-the-worlds-first-12-layer-hbm3/) | 2023-05-19 | Explains thinning control, stacking heat, vacuum-assisted application of epoxy molding compound, and bump testing. This is an HBM3 process narrative used only for qualitative process relationships. Its HBM3 capacities, relative gap change, press loading, and performance comparisons are not treated as HBM3E recipe specifications. |
| [SK hynix: TSMC collaboration](https://news.skhynix.com/en/sk-hynix-partners-with-tsmc-to-strengthen-hbm-technological-leadership/) | 2024-04-19 | Describes a base die beneath the core DRAM dies, TSV connections, and CoWoS system integration. It says SK hynix used its proprietary base-die technology through HBM3E, with TSMC's advanced logic process planned for HBM4. This dataset is an HBM3E scenario and does not import the HBM4 base-die sourcing arrangement. |

## What is simulated

All absolute means, standard deviations, bounds, sampling fractions, tool offsets, maintenance intervals, batch effects, spatial patterns, missingness rates, acceptance criteria, and failure coefficients are simulation choices unless explicitly identified as a public product fact above. Tool, chamber, lot, material-batch, and die identifiers are fictional. Simulated dates describe a fabricated chronology, not a company's production schedule.

Physical relationships and manufacturing logic guide the equations. Examples include deriving aspect ratio from TSV dimensions, increasing geometric electrical resistance with via length and decreasing it with cross-sectional area, applying shared wafer/tool effects, retaining die-to-stack membership, and admitting only dies that passed the simulated qualification gate into stacks. The magnitudes of these effects are assumptions and must not be interpreted as measured SK hynix process capability.

Reported defect frequencies and yields characterize this synthetic scenario. They support algorithm development, data-pipeline testing, and demonstrations of inspection and yield analytics. Their validation demonstrates internal consistency and learnable process structure; it cannot establish predictive validity on a real manufacturing line. SME review and measurements from a permitted real source would be needed for that calibration.

## Interpretation and units

- The layer count refers to core DRAM dies. A base die is additional and should be accounted for separately in package geometry and traceability.
- Capacity is expressed in GB according to the product descriptions: 8 × 3 GB = 24 GB and 12 × 3 GB = 36 GB. The thinner-die comparison is a relative product fact; any absolute thickness in micrometres is assumed.
- Distinguish per-pin transfer rate in Gbit/s from package bandwidth in GB/s or TB/s. A field labeled GB/s must not be interpreted as Gbit/s. A simulated measured bandwidth also depends on the declared test conditions.
- Vacuum values need an explicit reference, preferably kPa absolute. Lower absolute pressure represents stronger vacuum. Press loading expressed as force cannot be converted to MPa without the loaded area.
- TSV copper void percentage denotes a mean per-via copper-fill void-volume fraction surrogate. Underfill void percentage uses inspected underfill cross-section area; delamination uses inspected interface area. Those denominators differ and the percentages cannot be added together.
- TSV resistance derived from geometry is a physical proxy. Effective material resistivity, contacts, temperature, and fill quality influence the total. Passing an electrical test may also involve repair and redundancy.
- The simulated thermal resistance is effective junction-to-package-top resistance at a controlled 85°C package-top case boundary. The cited relative heat-dissipation claims do not determine its numerical distribution.
- Final electrical measurements and latent simulator failure probabilities must not enter a feature set intended to predict outcomes before final testing. A failed, untested, or uninspected unit must be distinguishable from a measured zero.

## Relationship to the original Kaggle dataset
The [Semiconductor Wafer Defect Classification Dataset](https://www.kaggle.com/datasets/meruvakodandasuraj/semiconductor-wafer-defect-classification-dataset) provided the starting topic for this project. It is not HBM manufacturing evidence and is not a calibration source for this simulation. The HBM tables are generated afresh; original Kaggle records and its simple defect-label relationship are not used to infer SK hynix process parameters.

The Kaggle page was reachable but did not return machine-readable description text through the web reader during this provenance check. No new claims about its record count, license, or empirical quality are inferred here.
