# Scientific programs, complete formal observations and supplementary documents

These materials accompany robust task-offloading control in satellite–terrestrial networks. Scientific programs, supplied formal inputs, complete saved observations and Supplementary Files S1–S4 are available in this repository.

The programs in this upload set cover revision experiments and their required shared dependencies. Original-paper-only standalone experiments are not included; this is not a complete release of every original-paper program. The two original-derived pool/config definition modules are required by the calibration experiment, together with its revision bridge and worker.

## Specified reproduction environment and timing metadata

**Specified reproduction environment (specified by the authors):** Intel Core i9-10900K CPU @ 3.70 GHz and 128 GB RAM, running CentOS 7.4, with Python 3.10.9.

Execution-platform metadata for the supplied timing results, including the recorded macOS/Python environments, timing scopes and shared-resource conditions, are provided in [S3](supplements/S3.pdf) and [RUNTIME_NOTES.json](data/supplement_s3/RUNTIME_NOTES.json).


## Contents

| Directory | Scientific purpose |
|---|---|
| [scientific](scientific/README.md) | Model/certification/control APIs, extracted pool definitions, guarded single-task interface, scientific requirements and 2,800 formal task inputs |
| [data/supplement_s1](data/supplement_s1/) | All 14,000 control trajectory results and metrics, all 500 common-domain comparisons, complete distributions and paired summaries |
| [data/supplement_s2](data/supplement_s2/) | All 200 calibration instances, 600 pool observations, complete samples/membership, 16 full-precision scientific tables and numerical witnesses |
| [data/supplement_s3](data/supplement_s3/) | All 4,200 retained scale trajectories, 1,200 paired mean60 trajectories, complete certification instance results, strata, adverse tails and denominator evidence |
| [supplements](supplements/) | [S1](supplements/S1.pdf), [S2](supplements/S2.pdf), [S3](supplements/S3.pdf), [S4](supplements/S4.pdf) |

Scientific task inputs and saved truth arrays are local ordinary files. The folder is self-contained; no original project checkout or private working directory is needed for its stated interfaces.

In the S2 sample-reference tables, `member_file` and `fixed_member_file` paths are relative to `data/supplement_s2/`. The original sample identifiers, record-line references and shared-draw relationships are preserved.

## Preserve the scientific denominators

Formal results retain all selected instances, failures/noncompletion, unfavorable tails, numerical precision and shared pairing. The 14,000 S1 result records include 999 trajectories that did not complete within their operation budget. `null`, empty CSV cells and `NA` indicate undefined or unavailable quantities according to the relevant table/document; they are not zero or rejection. S1 raw observations are per-trajectory result records, not step-by-step traces. Timing and candidate-denominator summaries preserve their original scope.

The retained mean60 conditions are B60/H10/H20/H25 on 100 shared backgrounds. H20 includes 40/80 MB capacities, and H10 is a formal capacity condition. Ordinary 40 MB experiments and the Peak 40 MB rule remain. The mean40 H2/H5 heterogeneity comparison and development/pilot cohorts are excluded.

## Start with input preparation

From the repository root:

```bash
python scientific/select_input.py --family control --id 2x4_2632001 --output /tmp/control_prepared
```

Use an output directory that does not exist. Preparation checks the family, identifier, structure, configuration and paired input content; it copies a task without launching a scientific worker. See [the scientific guide](scientific/README.md) for family identifiers and guarded execution contracts.

From another working directory, use an absolute path to `scientific/select_input.py`; its inputs are resolved relative to the script location.

This curated distribution omits standalone plotting programs, plot/layout exports, standalone images, mixed historical archives, development runs, private run receipts, file-index/checksum documents and internal coordination records. Embedded scientific figures in S1–S4 remain.
