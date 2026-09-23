# Generating model and feature dictionary

Every data column is documented in `data/data_dictionary.csv`: meaning, units, observation level, availability, role, missingness, generating family, source expressions and parent-symbol definitions. Source references identify locations in the original generator, which was removed from this cleaned data-only package. Some names occur at multiple grains; all matching source expressions are shown, while the table grain and generation family identify their context. The preserved source expressions and equations below document the numerical specification.

This release documents 318 table-column entries across 18 data tables, covering 214 distinct column names.

## Dependency order

Product/lot/material -> selected wafer process modules and chamber history -> spatial core-die measurements and TSV states -> imperfect incoming screens -> single-use core/base allocation -> placement/reflow/molding -> package inspection -> realized electrical/mechanical faults -> final acceptance -> sampled reliability screen.

Wafer-to-die and die-to-stack are separate relationships: stacks combine eligible dies from multiple wafers in one lot. The base pool is independent and linked by receiving lot. Sampled observations and simulator truth are stored separately.

## Distribution and dependency rules

| Component | Generator | Important dependence |
|---|---|---|
| Lot/product | Bernoulli 12-high choice; Normal lot/material offsets; deterministic release and partition times | Shared material effects across six-lot blocks; configurable embargo |
| Process runs | Stage-specific additive temperature noise; multiplicative lognormal pressure/gas/power noise; Poisson alarms | Chamber bias, maintenance age, persistent excursions, lot and wafer effects |
| Spatial die variation | Radial term plus occasional Gaussian-shaped local cluster and Normal die noise | Shared wafer and upstream process state |
| Die quality | Normal dimensional variation, positive/lognormal measurements, Poisson particles/repairs, Bernoulli faults | CD and process stress affect cell risk; imperfect screen can miss faults |
| TSVs | Noisy etched diameter/depth; lognormal void fraction; physical resistance proxy; Bernoulli faults | Etch/fill process state and final thinned conductor length |
| Thinning/bumping | Product-specific nominal thickness and bump height plus process/radial noise; nonnegative variation | Shared thinning and bump-process states; greater assumed bending sensitivity for 12-high |
| Assembly | Gaussian placement offsets; noisy temperature/force; lognormal viscosity/vacuum | Assembly-line bias, run age, excursion and material-batch state |
| Package quality | Conditional lognormal void/delamination and nonnegative warpage | Gaps, vacuum, viscosity, cure deficit, molding pressure, die warpage and accumulated shift |
| Fault modes | Independent Bernoulli draws conditional on shared state and mechanism-specific logistic probabilities | Seven modes may co-occur; marginal dependence arises from shared causes |
| Final acceptance | Logical AND of mechanical and electrical gates | Outcome measurements follow fault realization; never included in primary-task predictors |
| Reliability | Bernoulli sample of final passers, then Bernoulli stress failure | Warpage, voids, thermal response and inherited faults; all untested labels null |
| Telemetry | AR(1) temperature series centered/rescaled to run mean and sample SD | Fixed conditional summary and elapsed times; not a full ramp/soak waveform |

## Physical accounting

`tsv_etch_aspect_ratio = tsv_etched_depth_um / tsv_diameter_um`. The via etch is before thinning; final conductor length is the thinned silicon thickness.

`R_mOhm = (rho * length_m / (pi * (diameter_m / 2)^2) * 1000 / (1 - void_pct / 100) + 3) * exp(Normal(0, 0.025))`. Copper resistivity is assumed 1.72e-8 ohm*m. The 3 mOhm contact contribution and void adjustment are approximations, not fitted device measurements.

`stack_height_um = sum(core_die_thickness_um) + sum(interface_gap_um) + base_die_thickness_um + mold_cap_thickness_um`. There are N core-to-lower-layer interfaces for N core dies, including the base interface.

`capacity_gb = stack_layer_count * 3`; `nominal_peak_bandwidth_gb_s = offered_data_rate_gbps * 1024 / 8`; `bit_error_rate = uncorrected_error_count / tested_bit_count`.

## Failure equations

The exact sigmoid expressions are reproduced below. Every intercept and coefficient is an illustrative assumption. `shift` is configurable via `fault_logit_shift`. The referenced parent variables are defined in the dictionary.

```python
dram_electrical = sigmoid(-5.4+3.0*inherited_cell+0.3*die_stress[di].mean()+shift)
tsv_open_short = sigmoid(-5.7+3.5*inherited_tsv+0.4*void[di].max()+shift)
microbump_open_bridge = sigmoid(-5.3+1.1*(maxoffset-0.5)+0.4*ast+0.07*abs(peak-245)+0.025*abs(tal-55)+shift)
die_crack = sigmoid(-6.6+0.75*(warpage[di].max()-1)+0.2*abs(ast)+0.2*(hh==12)+0.6*max(force.max()-1.2,0)+shift)
warpage = sigmoid(-5.1+0.32*(pwarp-11)+shift)
underfill_void = sigmoid(-5.1+1.6*vfrac+0.25*(hh==12)+shift)
delamination = sigmoid(-5.7+2.0*delam+0.15*ast+shift)
```

Conditional fault draws are made after pre-test features exist. An observation cannot reveal the Bernoulli draw exactly. Incoming test false negatives and unobserved variation create residual uncertainty. This does not claim a particular manufacturer has these failure frequencies.

## Starter modeling columns

| Column | Unit | Meaning | Role |
|---|---|---|---|
| `stack_id` | category/text | Fictional stack identifier for traceability or configuration. | identifier_or_metadata |
| `lot_id` | category/text | Fictional lot identifier for traceability or configuration. | identifier_or_metadata |
| `split` | category/text | Preassigned time-ordered lot partition: train, validation or test. | identifier_or_metadata |
| `stack_layer_count` | count/index | Number of core DRAM dies, excluding the base die. | allowed_primary_task_predictor |
| `capacity_gb` | GB | Stack DRAM capacity; core layer count times 3 GB per core die. | allowed_primary_task_predictor |
| `assembly_tool_id` | category/text | Fictional assembly-line group containing multiple stations; not a single-resource schedule. | allowed_primary_task_predictor |
| `feature_available_time_utc` | UTC ISO-8601 | Feature available time, in a wholly simulated chronology. | identifier_or_metadata |
| `stack_height_um` | um | Sum of N core thicknesses, N interface gaps, base thickness and mold cap. | allowed_primary_task_predictor |
| `inter_die_gap_mean_um` | um | Arithmetic mean of the N core-to-lower-layer interface gaps. | allowed_primary_task_predictor |
| `max_alignment_offset_um` | um | Maximum Euclidean incremental placement-offset magnitude over core layers. | allowed_primary_task_predictor |
| `cumulative_die_shift_um` | um | Euclidean magnitude of the sum of incremental X/Y offsets over core layers. | allowed_primary_task_predictor |
| `emc_viscosity_pa_s` | Pa*s | Assumed epoxy molding-compound viscosity at dispensing conditions. | allowed_primary_task_predictor |
| `molding_pressure_mpa` | MPa | Applied molding-pressure scenario variable; not converted from a published press load. | allowed_primary_task_predictor |
| `molding_vacuum_absolute_kpa` | kPa absolute | Absolute evacuation pressure: a larger value means weaker vacuum. | allowed_primary_task_predictor |
| `reflow_peak_temperature_c` | degC | Peak mass-reflow temperature. | allowed_primary_task_predictor |
| `time_above_liquidus_sec` | s | Reflow time above the scenario solder liquidus. | allowed_primary_task_predictor |
| `heating_rate_c_sec` | degC/s | Reflow heating-rate summary. | allowed_primary_task_predictor |
| `cure_temperature_c` | degC | Molding compound curing temperature. | allowed_primary_task_predictor |
| `cure_duration_min` | min | Molding compound cure duration. | allowed_primary_task_predictor |
| `underfill_void_pct` | percent 0..100 | Void area as percent of inspected underfill cross-section area. | allowed_primary_task_predictor |
| `delamination_area_pct` | percent 0..100 | Separated area as percent of inspected package interface area. | allowed_primary_task_predictor |
| `package_warpage_um` | um | Package-curvature magnitude after molding. | allowed_primary_task_predictor |
| `stacks_since_tool_service` | count/index | Run-age proxy modulo 200 for the synthetic assembly-line group. | allowed_primary_task_predictor |
| `core_thickness_mean_um` | um | Mean measured silicon thickness of the core dies assigned to the stack. | allowed_primary_task_predictor |
| `core_thickness_std_um` | um | Population SD (ddof=0) of the core-die thicknesses in the stack. | allowed_primary_task_predictor |
| `core_warpage_max_um` | um | Largest measured warpage among the assigned core dies. | allowed_primary_task_predictor |
| `core_ttv_mean_um` | um | Mean within-die thickness variation among the assigned core dies. | allowed_primary_task_predictor |
| `core_leakage_mean_ua` | uA | Mean incoming leakage current of the assigned core dies. | allowed_primary_task_predictor |
| `core_repair_count_sum` | count/index | Total incoming repair resources used by the assigned core dies. | allowed_primary_task_predictor |
| `core_particle_count_sum` | count/index | Total inspected contamination particles across the assigned core dies. | allowed_primary_task_predictor |
| `core_tsv_resistance_mean_mohm` | mOhm | Mean incoming TSV path-resistance proxy across the assigned core dies. | allowed_primary_task_predictor |
| `core_tsv_resistance_max_mohm` | mOhm | Largest incoming TSV path-resistance proxy among the assigned core dies. | allowed_primary_task_predictor |
| `core_bump_coplanarity_max_um` | um | Largest incoming bump-height variation among the assigned core dies. | allowed_primary_task_predictor |
| `n_source_wafers` | count/index | Distinct source wafer count among core dies in the stack. | allowed_primary_task_predictor |
| `n_dies_with_detailed_metrology` | count/index | Number of core dies with sampled metrology successfully observed. | allowed_primary_task_predictor |
| `sampled_core_tsv_void_mean_pct` | percent 0..100 | Mean of observed constituent TSV void measurements only; null when none were observed. | allowed_primary_task_predictor |
| `sampled_core_cd_mean_nm` | nm | Mean of observed constituent critical dimensions only; null when none were observed. | allowed_primary_task_predictor |
| `base_leakage_current_ua` | uA | Base-die incoming leakage measurement. | allowed_primary_task_predictor |
| `base_die_thickness_um` | um | Base-die silicon thickness, separate from core DRAM thickness. | allowed_primary_task_predictor |
| `final_test_fail` | 0/1 | Primary target: 1 minus final_test_pass. One means final acceptance rejection. | outcome_label |

The primary model uses only the allowlist in `metadata/ml_task.json`. Other tables require timestamp-aware joins appropriate to the chosen prediction checkpoint. The package/baseline reports document simulated results, not empirical fab calibration.
