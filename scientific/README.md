# Scientific interfaces and complete formal inputs

**Specified reproduction environment (specified by the authors):** Intel Core i9-10900K CPU @ 3.70 GHz and 128 GB RAM, running CentOS 7.4, with Python 3.10.9.

Execution-platform metadata for the supplied timing results, including the recorded macOS/Python environments, timing scopes and shared-resource conditions, are provided in [S3](../supplements/S3.pdf) and [RUNTIME_NOTES.json](../data/supplement_s3/RUNTIME_NOTES.json). New output platform reports use the running Python/platform functions.

Use Python 3.10.9-compatible NumPy, pandas, bidict and psutil as declared in `requirements_science.txt`.

## Supplied formal inputs

| Family | Inputs and identifier examples | Source API |
|---|---|---|
| `control` | 500: `2x4_2632001`, `2x8_2632001`, `2x12_2732001`, `4x8_2732001`, `4x12_2732001`; each configuration has 100 instances | `d026_2leo_v3/worker_api.py:worker` or `d027_v2/worker_api.py:worker` |
| `scale` | 1,400: fourteen configurations, e.g. `S4_1702001`, `L64_1702001`, `S16_1702001`; 100 each | `d032_v1/worker.py:run` |
| `het60` | 400: `B60_1702001`, `H10_1702001`, `H20_1702001`, `H25_1702001`; 100 paired backgrounds | `d039_het60_v3/worker.py:run` |
| `calibration` | 200: `n3_2832001`, `n6_2832001`; 100 each | `d028_v2/worker.py:run` |
| `paired2` | 200: `n3_2832001`, `n6_2832001`; same complete D028 inputs and saved truth | `d033_timing_v1/measurement_worker.py:run` |
| `tristar_truth` | 100: `5342001` through `5342100` | `d035_tristar_v1/worker_truth.py:run` and `worker_timing.py:run` |

All source API paths above start at `03_code/working/` within this directory. Modules use local imports within their own family; use the guarded interface below to select that import context. No module executes a default scientific batch on import. D028's required class/function definitions are extracted ordinary modules; the original Notebook top-level loop and plotting code are absent.

The program scope is revision experiments and their required shared dependencies, rather than the complete set of original-paper standalone experiments. In `03_code/working/d028_v2/`, `pool_config_definitions.py` originates from the author's original `code_with_sample_all/LEO_2_Con_0_UnL_(0,1)_APP_4_50000MK/danci Final_Version/Env/config.py`; `pool_definitions.py` originates from the companion `app creation 所有marking_寻找1000_限制with_sample_更新字典.ipynb`. Both are required shared dependencies of the calibration experiment and remain in this distribution. `run_task.py --family calibration` routes to `worker.py:run`; that worker constructs `legacy_pool.Pool`, which reads both same-directory definition modules and loads the retained class/function AST definitions. `legacy_pool.py` and `worker.py` are revision bridge/worker implementations, retained with those definitions.

`select_input.py --family FAMILY --id ID --output NEW_DIRECTORY` prepares exactly one supplied task. It rejects unknown identities, directory escape, wrong shapes/configurations, development seeds and inconsistent paired capacity backgrounds. Templates retain the original scientific inputs while discarding old parent/session metadata. The preparation step creates new live metadata only when execution is requested.

## Guarded single-task execution

Execution can be expensive. The commands below launch the selected scientific task. Choose a fresh output directory for every attempt. Failed or partial attempts remain separate and must not be silently converted to Boolean rejection or successful completion.

```bash
python scientific/run_task.py --family control --id 2x4_2632001 --method rmba --scenario S4 --output /tmp/control_rerun
python scientific/run_task.py --family scale --id S4_1702001 --scenario N --output /tmp/scale_rerun
python scientific/run_task.py --family het60 --id H20_1702001 --scenario R --output /tmp/paired_capacity_rerun
python scientific/run_task.py --family calibration --id n3_2832001 --output /tmp/calibration_rerun
python scientific/run_task.py --family paired2 --id n3_2832001 --output /tmp/paired_certification_rerun
python scientific/run_task.py --family tristar_truth --id 5342001 --phase truth --output /tmp/tristar_truth_rerun
python scientific/run_task.py --family tristar_truth --id 5342001 --phase timing --truth /tmp/tristar_truth_rerun --output /tmp/tristar_timing_rerun
```

Commands above assume the repository root as the current directory; absolute script paths also work from elsewhere. Control methods are `uncontrolled`, `mba_current`, `peak_remaining`, `rmba`; control scenarios are S0–S6. Scale/mean60 scenarios N/F/R correspond to ND/PD/DR. Configuration declarations and event schedules remain scientific inputs. The public interface runs one task at a time.

The fresh parent starts one child, supplies a real parent PID and a new 24-byte call-watch record, and enforces wall time, worker-tree/parent RSS, per-task disk and free-space limits. Timing calls retain 30-second guards; two-star/tristar timing workers retain 600-second/2-GiB limits, and tristar truth retains 1800-second/4-GiB limits. Calibration retains its phase/worker limits. Resource failures are recorded as failures. Linux `ru_maxrss` KiB are converted to bytes; macOS bytes are retained. Actual running environment information is captured in new outputs.

Before paired timing, `validate_truth.py` validates the complete local truth contents, including physical successor completeness, state/array domains, autonomous event closure, exact/controlled reachable sets, independent full-FS RMBA labels and completion certificates. That potentially expensive validation occurs outside the measured online functions and remains subject to the parent resource limit. Private verification receipts are neither required nor treated as fresh truth. For tristar timing, a newly generated truth directory must also have a successful fresh parent resource record. The included saved tristar arrays can be selected explicitly as `--truth scientific/truth/tristar/seed5342001`; they undergo the same full content verification.

The mean60 public declaration is a real release-interface derivative. Its instance declaration is bound to its actual supplied scientific content; paired B60 data, access, selector streams, balanced capacity positions and fixed component totals are checked. The supplied 100-instance result values are preserved and are not relabeled as output of this interface.

Scientific algorithms preserve full FS/MBA/RMBA, failure/recovery semantics, short-circuit behavior and sampling streams. E100/N100 source differences and the N100 cached up/down-failure timer branch defect are described in S4.
