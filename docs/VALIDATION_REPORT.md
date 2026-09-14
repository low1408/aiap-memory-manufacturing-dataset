# Synthetic HBM dataset validation

**356 of 356 checks passed.** The generated cohort contains 17,793 assembled stacks, including 916 final acceptance failures (5.15%). Final acceptance requires both assembly and electrical acceptance.

The checks establish internal consistency, lineage, units, availability and selected physical relationships. They do not establish calibration to SK hynix manufacturing distributions, yields or process capability. All records are synthetic. Public product context and engineering assumptions are documented in `docs/SOURCES.md`.

This is the preserved output from the original validation utility, which was
removed from the cleaned data-only package. `metadata/validation.json` contains
every check, its result, tolerances and numerical diagnostics.

## Cohort and split outcomes

| Split | Lots | Wafers | Sampled core dies | Stacks | Final failures | Failure rate | Reliability tested | Reliability failures |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| train | 168 | 4,200 | 134,400 | 12,564 | 653 | 5.20% | 2,378 | 97 |
| validation | 36 | 900 | 28,800 | 2,640 | 126 | 4.77% | 492 | 26 |
| test | 36 | 900 | 28,800 | 2,589 | 137 | 5.29% | 510 | 24 |

Reliability failures are counted only among sampled final-test passers. Unsampled outcomes remain null.

## Verified invariants

- All 18 manifest checksums, row counts and column counts match. Every table has its expected primary key and resolvable foreign keys.
- Sampled rectangular dies fit the assumed wafer grid. Every wafer has ten ordered, nonoverlapping modeled process modules with recipe-specific structural nulls.
- Every stack has exactly 8 or 12 eligible core dies and one passed base die. No physical core or base die is reused. Inventory and dispositions account for every die.
- Capacity is the sum of core capacities. Stack height includes all core thicknesses, interface gaps, base thickness and mold cap. Placement aggregates reconcile with layer-level records.
- TSV aspect ratios and conductor lengths reconcile. Resistance is checked in milliohms against SI geometry with the assumed series term and multiplicative noise.
- Assembly, electrical and final acceptance verdicts reconcile with measurements and latent modes. BER, bandwidth conversion and offered-rate behavior are consistent.
- Detailed metrology nulls match sampling and instrument-dropout reasons exactly. Reliability nulls preserve both failed-final-test and not-sampled states.
- Lot, wafer, core and base genealogy respects split boundaries. Measurement availability precedes placement or prediction, and later labels are excluded from model inputs.
- Every model-ready aggregate is independently recomputed from source records. The single training CSV matches the separate feature and label views.
- Sampled traces reproduce process means, sample standard deviations, slopes and durations within the documented CSV rounding tolerances.

## Temporal boundaries

| Boundary | Lot-release gap | Earlier final label to next feature |
|---|---:|---:|
| train → validation | 21.50 days | 20.56 days |
| validation → test | 21.50 days | 20.58 days |

The lot-release gap includes the configured 21-day embargo plus ordinary 12-hour lot spacing. Earlier final-test and sampled reliability labels are available before the next partition's lot release. Tools recur across partitions because the intended task predicts later production on the same simulated fleet.

## Sampling and dimensional diagnostics

Detailed metrology was selected for 24.75% of core dies. Among selected dies, 2.07% suffered an instrument dropout. Overall, 24.24% have observed detailed metrology. 1,214 stacks have no detailed measurements from any constituent core; their sampled means remain null.

Reliability sampling covers 20.03% of final acceptance passers. The trace subset contains 600 process runs and 72,600 temperature samples.

Median TSV resistance is 30.966 mΩ. The median observed resistance / geometry-derived resistance ratio is 1.00000. Its log-ratio standard deviation is 0.02510, compared with the assumed 0.025 measurement-noise scale.

## Manufacturing relationship diagnostics

These descriptive correlations include common causes, product differences and sampling effects. They are diagnostics of this realized simulation, not independent causal estimates. Spearman correlation uses average ranks for ties.

| Relationship | Observed pairs | Pearson | Spearman |
|---|---:|---:|---:|
| Nonuniform thinning and die warpage share process state | 192,000 | 0.520 | 0.439 |
| Contamination and latent die stress affect repairs | 192,000 | 0.259 | 0.208 |
| Longer copper TSV conductors increase resistance | 192,000 | 0.988 | 0.707 |
| Higher molding viscosity raises void formation | 17,793 | 0.479 | 0.477 |
| Higher absolute pressure means poorer evacuation | 17,793 | 0.565 | 0.523 |
| Warpage contributes to delamination risk | 17,793 | 0.547 | 0.573 |
| Voids increase package thermal resistance | 17,793 | 0.447 | 0.378 |

## Failure mechanisms

Mechanisms can overlap within a stack; these counts need not sum to the number of rejected stacks. Stochastic realizations need not equal the mean generating probabilities exactly.

| Mode | Active stacks | Observed rate | Mean generating probability |
|---|---:|---:|---:|
| dram_electrical | 97 | 0.545% | 0.620% |
| tsv_open_short | 108 | 0.607% | 0.607% |
| microbump_open_bridge | 137 | 0.770% | 0.824% |
| die_crack | 47 | 0.264% | 0.263% |
| warpage | 247 | 1.388% | 1.470% |
| underfill_void | 206 | 1.158% | 1.169% |
| delamination | 96 | 0.540% | 0.490% |

Mutually exclusive reported defect categories by split:

| Split | Reported defect | Stacks | Share of split |
|---|---|---:|---:|
| train | delamination | 64 | 0.509% |
| train | die_crack | 34 | 0.271% |
| train | dram_electrical | 53 | 0.422% |
| train | microbump_open_bridge | 89 | 0.708% |
| train | multiple | 17 | 0.135% |
| train | none | 11,911 | 94.803% |
| train | tsv_open_short | 72 | 0.573% |
| train | underfill_void | 147 | 1.170% |
| train | warpage | 177 | 1.409% |
| validation | delamination | 14 | 0.530% |
| validation | die_crack | 5 | 0.189% |
| validation | dram_electrical | 20 | 0.758% |
| validation | microbump_open_bridge | 18 | 0.682% |
| validation | multiple | 2 | 0.076% |
| validation | none | 2,514 | 95.227% |
| validation | tsv_open_short | 14 | 0.530% |
| validation | underfill_void | 25 | 0.947% |
| validation | warpage | 28 | 1.061% |
| test | delamination | 14 | 0.541% |
| test | die_crack | 6 | 0.232% |
| test | dram_electrical | 17 | 0.657% |
| test | microbump_open_bridge | 23 | 0.888% |
| test | multiple | 2 | 0.077% |
| test | none | 2,452 | 94.708% |
| test | tsv_open_short | 18 | 0.695% |
| test | underfill_void | 23 | 0.888% |
| test | warpage | 34 | 1.313% |

## Verified table inventory

| File | Rows | Columns |
|---|---:|---:|
| `data/manufacturing/lots.csv` | 240 | 10 |
| `data/manufacturing/wafers.csv` | 6,000 | 9 |
| `data/manufacturing/recipes.csv` | 20 | 10 |
| `data/manufacturing/wafer_process.csv` | 60,000 | 23 |
| `data/manufacturing/die_metrology.csv` | 192,000 | 30 |
| `data/manufacturing/tsv_inspection.csv` | 192,000 | 15 |
| `data/manufacturing/base_die.csv` | 20,068 | 10 |
| `data/assembly/stack_membership.csv` | 198,441 | 13 |
| `data/assembly/stack_assembly.csv` | 17,793 | 32 |
| `data/assembly/electrical_test.csv` | 17,793 | 26 |
| `data/assembly/reliability_test.csv` | 17,793 | 9 |
| `data/ml/ml_stack_features.csv` | 17,793 | 39 |
| `data/ml/ml_stack_labels.csv` | 17,793 | 9 |
| `data/ml/stack_training.csv` | 17,793 | 40 |
| `data/simulation_truth/simulation_truth_stack.csv` | 17,793 | 19 |
| `data/assembly/die_disposition.csv` | 192,000 | 3 |
| `data/simulation_truth/simulation_truth_die.csv` | 192,000 | 11 |
| `data/manufacturing/sensor_trace.csv` | 72,600 | 10 |
