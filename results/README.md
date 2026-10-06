# Benchmark results

Each `<dataset>/comparison_report.json` is the merged report for that dataset, and
the source of every number here. Each comes from one complete comparison run, kept
as `<dataset>/keep_<timestamp>/` with its per-mode and per-client benchmarks and
audit ledgers. The reports record paths under the run's original name,
`<dataset>/<timestamp>/`; the `keep_` prefix was added afterwards so the run is tracked.

[`privacy_comparison_analysis.ipynb`](../privacy_comparison_analysis.ipynb) reads these
reports and adds the per-mode properties, figures and per-proof costs.

| Dataset | Run | Modes |
|---|---|---|
| healthcare | `keep_20261003_144700` | 12 |
| creditcard | `keep_20261003_192152` | 12 |
| stock | `keep_20261004_095517` | 12 |
| mnist | `keep_20261004_141445` | 12 |

## Configuration

- 3 clients (one SuperNode each) over a networked SuperLink, 10 rounds, seed 42,
  IID partitions; every client trains and evaluates every round.
- Local epochs and batch size: healthcare 5 and 16, creditcard 5 and 32, stock 5
  and 16, mnist 3 and 64; SGD with learning rate 0.001 and momentum 0.9; CPU.
- DP: ε = 1.0, δ = 1e-5, Gaussian mechanism, noise multiplier 4.84, clipping norm 1.0.
  ε here sets the noise; it is not an end-to-end (ε, δ) guarantee
  ([docs/DP.md](../docs/DP.md)).
- ZKP: Groth16 from gnark-gradient-prover under a local single-party key setup;
  every ZKP round records the key manifest SHA-256
  (`95279d9c3fc2c05dec1aa102037109b18ff9ddb353a3153da4a162f34bbc4ba9` in all runs).
  Sampled modes prove 10% of coordinates.
- TFHE: 14-bit quantization over [-5, 5]; real TFHE on mnist (`FL_CONCRETE_TFHE_FORCE_REAL=1`).
- Code: ppflx `80d85e9`, gnark-gradient-prover `3057802`, ppflx-bench `404983b`
  (the commit that added these results); Python 3.12, Flower 1.36.0, PyTorch 2.3.1 (CPU).
- Machine: Intel Core i5-1035G1 (4 cores, 8 threads), 23 GB RAM, Linux.

Every run met the acceptance criteria in the README: every mode succeeded, every
round aggregated all three clients with no rejections or failures, ZKP validation
passed in every round of every ZKP mode, and Flower installed nothing at run time.

## Summary

Accuracy, AUPRC and F1 come from each client evaluating the global model on its
own validation split (10% of its training shard) after every round, averaged over
all clients and the 10 rounds — not final-round scores, and not the held-out test
split. The reports store them as `test_accuracy`, `test_auprc` and `test_f1`. Times are means per client per round (fit,
proving) or per run (duration). Upload is the mean bytes a client sends per round.

### Healthcare (`healthcare`)

| Mode | Accuracy (%) | AUPRC (%) | F1 (%) | Fit (s) | Proving (s) | Upload (KB) | Duration (h) |
|---|---:|---:|---:|---:|---:|---:|---:|
| `baseline` | 83.78 | 81.29 | 86.46 | 0.2 | — | 11.4 | 0.07 |
| `he_tenseal` | 83.78 | 81.29 | 86.46 | 0.1 | — | 1,934.6 | 0.07 |
| `he_concrete_tfhe` | 83.90 | 81.38 | 86.34 | 0.4 | — | 18,241.5 | 0.10 |
| `zkp` | 83.78 | 81.29 | 86.46 | 0.2 | 50.1 | 14.6 | 0.21 |
| `zkp_sampled` | 83.78 | 81.29 | 86.46 | 0.1 | 5.4 | 11.4 | 0.12 |
| `dp` | 80.27 | 80.72 | 83.72 | 0.2 | — | 11.4 | 0.07 |
| `he_tenseal_zkp` | 83.78 | 81.29 | 86.46 | 0.2 | 51.2 | 1,938.2 | 0.22 |
| `he_concrete_tfhe_zkp` | 83.90 | 81.45 | 86.34 | 0.7 | 56.0 | 18,244.8 | 0.26 |
| `he_elgamal_zkp` | 83.78 | 81.29 | 86.46 | 0.2 | 756.3 | 187.7 | 2.18 |
| `he_elgamal_zkp_sampled` | 83.78 | 81.29 | 86.46 | 0.2 | 79.0 | 182.1 | 0.33 |
| `he_tenseal_zkp_dp` | 80.27 | 80.72 | 83.72 | 0.2 | 51.5 | 1,938.1 | 0.22 |
| `he_concrete_tfhe_zkp_dp` | 80.49 | 80.66 | 83.52 | 0.6 | 54.4 | 18,244.8 | 0.26 |

### Credit card fraud (`creditcard`)

| Mode | Accuracy (%) | AUPRC (%) | F1 (%) | Fit (s) | Proving (s) | Upload (KB) | Duration (h) |
|---|---:|---:|---:|---:|---:|---:|---:|
| `baseline` | 99.94 | 77.37 | 83.66 | 71.0 | — | 16.1 | 0.28 |
| `he_tenseal` | 99.94 | 77.37 | 83.66 | 66.4 | — | 1,935.0 | 0.27 |
| `he_concrete_tfhe` | 99.94 | 77.31 | 83.66 | 77.3 | — | 25,853.4 | 0.34 |
| `zkp` | 99.94 | 77.37 | 83.66 | 68.8 | 66.8 | 20.4 | 0.47 |
| `zkp_sampled` | 99.94 | 77.37 | 83.66 | 67.7 | 5.9 | 16.1 | 0.32 |
| `dp` | 99.89 | 52.33 | 67.91 | 81.7 | — | 16.1 | 0.31 |
| `he_tenseal_zkp` | 99.94 | 77.37 | 83.66 | 67.5 | 67.4 | 1,939.2 | 0.46 |
| `he_concrete_tfhe_zkp` | 99.94 | 77.32 | 83.66 | 77.7 | 72.6 | 25,857.6 | 0.54 |
| `he_elgamal_zkp` | 99.94 | 77.32 | 83.66 | 73.3 | 1030.7 | 265.7 | 3.18 |
| `he_elgamal_zkp_sampled` | 99.94 | 77.32 | 83.66 | 72.1 | 111.2 | 258.1 | 0.65 |
| `he_tenseal_zkp_dp` | 99.89 | 52.33 | 67.91 | 83.8 | 68.5 | 1,939.0 | 0.51 |
| `he_concrete_tfhe_zkp_dp` | 99.88 | 51.64 | 67.21 | 95.7 | 72.8 | 25,857.7 | 0.60 |

### Stock (`stock`)

| Mode | Accuracy (%) | AUPRC (%) | F1 (%) | Fit (s) | Proving (s) | Upload (KB) | Duration (h) |
|---|---:|---:|---:|---:|---:|---:|---:|
| `baseline` | 54.76 | 56.02 | 72.07 | 0.5 | — | 11.4 | 0.07 |
| `he_tenseal` | 54.76 | 56.02 | 72.07 | 0.4 | — | 1,934.7 | 0.07 |
| `he_concrete_tfhe` | 55.07 | 57.28 | 72.44 | 0.8 | — | 18,241.5 | 0.10 |
| `zkp` | 54.76 | 56.02 | 72.07 | 0.4 | 50.4 | 14.6 | 0.21 |
| `zkp_sampled` | 54.76 | 56.02 | 72.07 | 0.3 | 5.8 | 11.4 | 0.11 |
| `dp` | 55.17 | 59.66 | 72.02 | 0.5 | — | 11.4 | 0.07 |
| `he_tenseal_zkp` | 54.76 | 56.02 | 72.07 | 0.6 | 51.5 | 1,938.1 | 0.22 |
| `he_concrete_tfhe_zkp` | 54.93 | 57.26 | 72.45 | 1.1 | 56.0 | 18,244.8 | 0.26 |
| `he_elgamal_zkp` | 54.76 | 56.01 | 72.07 | 0.6 | 781.2 | 187.7 | 2.25 |
| `he_elgamal_zkp_sampled` | 54.76 | 56.01 | 72.07 | 0.4 | 83.5 | 182.1 | 0.34 |
| `he_tenseal_zkp_dp` | 55.17 | 59.66 | 72.02 | 0.7 | 53.5 | 1,938.0 | 0.23 |
| `he_concrete_tfhe_zkp_dp` | 54.83 | 59.34 | 72.10 | 1.1 | 54.2 | 18,244.8 | 0.26 |

### MNIST (`mnist`)

| Mode | Accuracy (%) | AUPRC (%) | F1 (%) | Fit (s) | Proving (s) | Upload (KB) | Duration (h) |
|---|---:|---:|---:|---:|---:|---:|---:|
| `baseline` | 96.68 | 99.21 | 96.64 | 51.5 | — | 173.5 | 0.22 |
| `he_tenseal` | 96.68 | 99.21 | 96.63 | 49.6 | — | 6,127.3 | 0.22 |
| `he_concrete_tfhe` | 96.55 | 99.18 | 96.53 | 59.1 | — | 278,096.8 | 0.55 |
| `zkp` | 96.68 | 99.21 | 96.64 | 53.3 | 635.3 | 212.2 | 2.00 |
| `zkp_sampled` | 96.68 | 99.21 | 96.64 | 50.3 | 61.3 | 173.5 | 0.43 |
| `dp` | 88.87 | 94.68 | 88.75 | 52.9 | — | 173.5 | 0.22 |
| `he_tenseal_zkp` | 96.68 | 99.21 | 96.64 | 51.7 | 622.6 | 6,165.8 | 1.96 |
| `he_concrete_tfhe_zkp` | 96.57 | 99.18 | 96.55 | 58.3 | 655.6 | 278,135.5 | 2.36 |
| `he_elgamal_zkp` | 96.68 | 99.21 | 96.64 | 57.1 | 10901.2 | 2,852.3 | 30.65 |
| `he_elgamal_zkp_sampled` | 96.68 | 99.21 | 96.64 | 55.9 | 1073.4 | 2,776.6 | 3.34 |
| `he_tenseal_zkp_dp` | 88.89 | 94.69 | 88.77 | 54.9 | 645.1 | 6,166.1 | 2.03 |
| `he_concrete_tfhe_zkp_dp` | 88.99 | 94.97 | 88.86 | 63.9 | 691.9 | 278,135.5 | 2.50 |

## Reading the numbers

- Modes that do not change the model (ZKP, CKKS, ElGamal and their sampled
  variants) train the same model as baseline and report the same metrics, up to
  the fixed-point encoding of the ElGamal update and floating-point noise. Differences in accuracy come from
  TFHE's 14-bit quantization (a few tenths of a point) and from DP.
- creditcard is about 0.17% fraud, so accuracy is near 100% for any model; use
  AUPRC and F1.
- stock is close to chance (about 55%); it does not separate modes by accuracy.
- `he_elgamal_zkp` encrypts inside the proof service, so its encryption time is
  part of Proving; the sampled variant encrypts at commit time.
- CIFAR-10 is supported but not benchmarked; see the README.
