# ppflx-bench

Benchmarks for [ppflx](https://github.com/CorpiXo/ppflx): the same federated
learning run under twelve privacy configurations — homomorphic encryption,
zero-knowledge proofs of bounded updates, differential privacy and their
combinations — on four datasets (healthcare, creditcard, stock and MNIST),
with a blockchain audit ledger.

The library lives in [ppflx](https://github.com/CorpiXo/ppflx) and the proof
service in
[gnark-gradient-prover](https://github.com/CorpiXo/gnark-gradient-prover).

> **Results:** all twelve modes on healthcare, creditcard, stock and MNIST, with
> 3 clients and 10 rounds over a networked SuperLink, are in
> [`results/`](results/README.md), which summarises them and describes the setup.

## Install

ppflx-bench is one of three repositories: the library
[ppflx](https://github.com/CorpiXo/ppflx), the proof service
[gnark-gradient-prover](https://github.com/CorpiXo/gnark-gradient-prover) and this
harness. [Benchmark on a new machine](#benchmark-on-a-new-machine) sets up all
three from scratch.

---

## Benchmark on a new machine

The full path for a new developer on Linux, from clone to accepted results.
Commands after step 2 run from the directory that holds the three checkouts
unless they `cd`.

### 1. Prerequisites

- git, with SSH access to the CorpiXo repositories on GitHub
- Go 1.26 or later (the version in gnark-gradient-prover's `go.mod`)
- Python 3.12 (Concrete-ML needs < 3.13, Flower 1.36 needs > 3.11); conda is used below
- A [Kaggle API token](https://www.kaggle.com/docs/api) for the tabular datasets

### 2. Clone the three repositories side by side

```bash
mkdir ppflx-stack && cd ppflx-stack
git clone git@github.com:CorpiXo/ppflx.git
git clone git@github.com:CorpiXo/gnark-gradient-prover.git
git clone git@github.com:CorpiXo/ppflx-bench.git
```

The steps below assume this layout, with the three checkouts in one directory;
the relative paths (`../ppflx`) depend on it.

### 3. Build the proof service and make local ZKP keys

```bash
(cd gnark-gradient-prover && go build -o gnark_service .)
export FL_GNARK_BINARY=$PWD/gnark-gradient-prover/gnark_service

$FL_GNARK_BINARY setup --keys-dir ~/.cache/ppflx/keys --pk-dir ~/.cache/ppflx/pk
export FL_ZKP_KEYS_DIR=~/.cache/ppflx/keys
export FL_ZKP_PK_DIR=~/.cache/ppflx/pk
```

Setup writes hundreds of MB of proving keys and takes a while. It runs once;
export the three variables in every shell that runs tests or benchmarks (for
example from your shell profile).

The keys stay outside every repository and nothing is committed. The pinned
keys that ship with ppflx have no proving keys on a new machine, and they are
never re-generated to get started. A local setup is enough for a benchmark:
one operator runs prover, verifier and clients, so the keys are
self-consistent; proving and verification cost depend on the circuit and the
witness, not on the setup randomness; and it has the same single-party trust
status as the pinned keys ([docs/ZKP.md, section 7](https://github.com/CorpiXo/ppflx/blob/main/docs/ZKP.md#7-keys-and-trusted-setup)).

### 4. Create the Python environment

```bash
conda create -n ppflx python=3.12 -y && conda activate ppflx
cd ppflx-bench

# Optional, on machines without a GPU: the CPU build of torch is a much smaller download
pip install torch==2.3.1 torchvision==0.18.1 --index-url https://download.pytorch.org/whl/cpu

pip install -r requirements.txt       # the harness, and ppflx v0.9.0 from git
pip install -e "../ppflx[tfhe]"       # ppflx from the checkout beside this one, with Concrete-ML for the TFHE modes
pip install pytest
```

Concrete-ML grants no patent rights; see ppflx's `NOTICE` before commercial use.

### 5. Run both test suites

```bash
(cd ../ppflx && pytest tests)    # the ZKP tests use FL_GNARK_BINARY with their own small keys
pytest tests
```

### 6. Generate the other keys

From `ppflx-bench/`; they land in `keys/`, which is gitignored.

```bash
python -m ppflx.keys generate he_tenseal                                  # keys/he_tenseal/
python -m ppflx.keys generate zkp --output keys/zkp/zkp_params.json
python -m ppflx.keys generate dp --output keys/dp/dp_params.json
python -m ppflx.keys generate he_elgamal                                  # keys/he_elgamal/, needs FL_GNARK_BINARY
python -m ppflx.keys generate he_concrete_tfhe                            # checks Concrete works; nothing is saved
```

### 7. Download the datasets

```bash
python download_datasets.py --list     # what is present
python download_datasets.py            # all five into ppflx-bench/dataset/
```

The first TFHE run compiles its circuits and writes the shared TFHE keys to
`ppflx/keys/prebuilt/` inside the installed ppflx (or `FL_CONCRETE_TFHE_KEYS_DIR`).

`creditcard`, `healthcare` and `stock` come from Kaggle: place the token at
`~/.kaggle/kaggle.json` or set `KAGGLE_USERNAME` and `KAGGLE_KEY`. The full
stock corpus is about 8 GB; `python download_datasets.py --datasets stock --stock-minimal`
fetches only the ticker the loader uses. `compare.py` reads `./dataset/` by default.

### 8. Run the benchmark

A short run first checks the whole chain, proof service included:

```bash
python compare.py --dataset healthcare --modes baseline,zkp,he_elgamal_zkp --rounds 2 --num-clients 2 --max-epochs 1
```

Then one full run per dataset. Without flags, `compare.py` runs all 12 modes
with 3 clients, 10 rounds and the dataset's default epochs, over a networked
SuperLink with one SuperNode per client, and starts the prover and verifier
itself:

```bash
python compare.py --dataset healthcare
python compare.py --dataset creditcard
python compare.py --dataset stock
FL_CONCRETE_TFHE_FORCE_REAL=1 python compare.py --dataset mnist
```

Real TFHE on an image dataset needs `FL_CONCRETE_TFHE_FORCE_REAL=1`; without
it the TFHE modes refuse to run rather than send plaintext. On mnist each TFHE
client peaks at about 1.5 GB.

CIFAR-10 (`--dataset cifar10`) is supported but not part of the published
comparison. On a 4-core, 8-thread laptop with 23 GB of RAM each real-TFHE client reached about
5.7 GB on the model's 120×400 layer and the kernel killed one of the three in
every round, and `he_elgamal_zkp` would need about 490 proofs per client per
round (about 4.6 h a round, estimated from mnist). MNIST already covers an image
model; CIFAR-10 needs more memory and about two more days of proving.

Full ZKP modes on `mnist` and `cifar10` are memory-intensive: the harness warns
that they can run the Python process and the proof service out of memory.
Keep `FL_ZKP_PARALLELISM=1` (the default) and run nothing else heavy alongside.

`he_elgamal_zkp` proves every model coordinate, 128 per proof, so its cost grows
with the model. On a 4-core, 8-thread laptop CPU (Intel Core i5-1035G1) a round took about 13 min on
healthcare, 21 min on creditcard and 3.3 h on mnist (352 proofs per client), so
a 10-round mnist run takes about a day and a half. The harness sizes each run's time
budget from the number of rounds, with a larger per-round budget for the ElGamal
modes on the image datasets; `FL_SERVER_TIMEOUT` overrides it. To run that mode
on its own after the others:

```bash
python compare.py --dataset mnist --modes he_elgamal_zkp
```

### 9. Accept the results

A run counts only if all of these hold:

- `compare.py` finishes without `mode(s) did not produce valid results`, and the
  summary shows `[OK] OK` for every mode (`[SIM] OK` is simulated, not networked);
- every entry in each mode's `round_outcomes` is `aggregated` (sampled modes:
  `committed`, then `aggregated`), with no rejected clients and no Flower failures;
- every ZKP mode has `"zkp_validation": {"ok": true, ...}`;
- no `runtime-envs` directory appeared under a run's `.flwr/`, so Flower
  installed nothing at run time.

Results are in `results/<dataset>/<timestamp>/comparison_report.json`, and
successful modes are merged into `results/<dataset>/comparison_report.json`.
Figures come only from these files. Every ZKP round outcome records the SHA-256
of the key manifest it was verified under (`key_manifest_sha256`), so the keys
a run used are traceable.

Only accepted runs are committed: rename the run directory to
`results/<dataset>/keep_<timestamp>/`, and git tracks its JSON and comparison
figure along with the dataset's merged report. Everything else under `results/`
is ignored.

---

## Docker

The benchmark also runs in a container, built from the same side-by-side
checkouts. It needs Docker Engine with the compose plugin.

```bash
cd ppflx-bench
scripts/run_docker_compare.sh                                   # all 12 modes on healthcare
scripts/run_docker_compare.sh --dataset creditcard --modes baseline,zkp --rounds 2
```

The script builds the image (`compose.yaml`, `Dockerfile`), runs `init` to
generate whatever keys are missing (the local ZKP key set, then the HE, DP and
ElGamal keys), and runs `compare.py` with your arguments. The proof service,
ppflx and the harness are inside the image; these directories are mounted from
`ppflx-bench/` and stay on the host:

| Host | Holds |
|---|---|
| `dataset/` | the datasets; the container does not download them |
| `results/` | the run results, as for a run on the host |
| `keys/` | the HE, DP and ElGamal keys |
| `.docker-state/` | the ZKP key set and the TFHE circuits and keys |

The container runs as your user, so everything written there stays yours. To
download the datasets inside the container instead of on the host, mount your
Kaggle token:

```bash
docker compose run --rm -v ~/.kaggle:/tmp/.kaggle:ro bench python download_datasets.py
```

When you call `docker compose` yourself, first
`export PPFLX_UID=$(id -u) PPFLX_GID=$(id -g)` so the container runs as you.
Any harness command runs the same way, for example
`docker compose run --rm bench pytest tests` or
`docker compose run --rm -e FL_CONCRETE_TFHE_FORCE_REAL=1 bench python compare.py --dataset mnist`.

---

## Privacy Modes

What each mode protects is set out in ppflx's
[SECURITY.md](https://github.com/CorpiXo/ppflx/blob/main/SECURITY.md); the proof
protocols are in [docs/ZKP.md](https://github.com/CorpiXo/ppflx/blob/main/docs/ZKP.md).
*Confidentiality* is against the aggregation server; *integrity* means the server
checks a proof about each upload before aggregating it.

| # | Mode | Key | Mechanism | Protects |
|---|------|-----|-----------|----------|
| 1 | Baseline | `baseline` | FedAvg | Nothing |
| 2 | HE TenSEAL | `he_tenseal` | CKKS (TenSEAL) | Confidentiality |
| 3 | HE Concrete TFHE | `he_concrete_tfhe` | TFHE (Concrete), 14-bit quantized weights | Confidentiality |
| 4 | ZKP Sampled | `zkp_sampled` | Groth16 over server-sampled coordinates (commit–challenge) | Nothing beyond `zkp`: the server already sees the plaintext. A benchmark of sampled proving cost |
| 5 | ZKP Full | `zkp` | Groth16 over every coordinate | Integrity: the update against the downloaded model is norm-bounded |
| 6 | DP | `dp` | Batch-gradient clipping and Gaussian noise during training (see below) | Noise only; no end-to-end (ε, δ) guarantee |
| 7 | HE TenSEAL + ZKP | `he_tenseal_zkp` | CKKS + Groth16 (unbound) | Confidentiality only: the proof is not bound to the ciphertext |
| 8 | HE Concrete + ZKP | `he_concrete_tfhe_zkp` | TFHE + Groth16 (unbound) | Confidentiality only: the proof is not bound to the ciphertext |
| 9 | HE TenSEAL + ZKP + DP | `he_tenseal_zkp_dp` | Mode 7 + the DP noise of mode 6 | Confidentiality; noise only |
| 10 | HE Concrete + ZKP + DP | `he_concrete_tfhe_zkp_dp` | Mode 8 + the DP noise of mode 6 | Confidentiality; noise only |
| 11 | HE ElGamal + ZKP | `he_elgamal_zkp` | Exponential ElGamal + ciphertext-bound Groth16 | Confidentiality + integrity: each uploaded value is range-checked and its update against the encrypted global model is norm-bounded |
| 12 | HE ElGamal + sampled ZKP | `he_elgamal_zkp_sampled` | As mode 11, proving only server-sampled committed coordinates (commit–challenge, two Flower rounds per round) | Confidentiality + probabilistic integrity: m out-of-bound coordinates are detected with probability 1 − C(n−m, s)/C(n, s) ([ZKP.md, section 6.4](https://github.com/CorpiXo/ppflx/blob/main/docs/ZKP.md#64-he_elgamal_zkp_sampled)) |

**Integrity in modes 7–10.** Their proof covers a client-chosen plaintext vector
and is not bound to the ciphertext the server aggregates, so a client can prove
an honest vector and upload a poisoned one (ppflx's
`tests/test_zkp_binding_attack.py`). Only modes 11 and 12 bind proofs to the
aggregated ciphertexts. Their remaining limits — a bounded update can still be
malicious (the bound caps per-round influence, not direction), a single-party
trusted setup, a client key shared by all clients, and per-chunk update norms
visible to the server — are listed in ppflx's `ppflx/privacy/he_elgamal_zkp.py`.

**DP as implemented.** During local training, each batch's mean gradient is
clipped to norm C and Gaussian noise with standard deviation σ·C/B is added (B is
the batch size), with σ = √(2 ln(1.25/δ))/ε. That calibration is for a single
Gaussian-mechanism step; there is no per-example clipping and no accounting
across steps, epochs or rounds, so the recorded ε is a noise setting, not an
(ε, δ) guarantee for the published model. See [docs/DP.md](docs/DP.md).

**HE keys.** In every HE mode the clients share one secret key, so HE hides
updates from the server, not from other clients.

---

## Datasets

| Key | Description | Samples | Classes | Input |
|-----|-------------|---------|---------|-------|
| `healthcare` | Heart disease (Statlog, Cleveland and Hungary combined) | 1,190 | 2 | 11 tabular features |
| `creditcard` | Credit card fraud detection, 0.17% positive | 284,807 | 2 | 30 tabular features |
| `stock` | Next-day up/down move of one stock (CERN), from its daily prices | 3,180 | 2 | 11 tabular features |
| `mnist` | MNIST handwritten digits | 70,000 | 10 | 1×28×28 image |
| `cifar10` (alias `cifar`) | CIFAR-10 object recognition; supported, not benchmarked | 60,000 | 10 | 3×32×32 image |

Tabular data is split 80/20 into train and test; each client keeps 10% of its
training shard for validation. Every dataset supports **non-IID Dirichlet
partitioning** via `--dirichlet-alpha`:

| α | Distribution character |
|---|----------------------|
| `0.1` | Extreme non-IID — each client holds ~1–2 classes |
| `0.5` | Moderate heterogeneity |
| `1.0` | Mild heterogeneity |
| `10.0` | Near-IID — roughly uniform label distribution |

Omitting `--dirichlet-alpha` splits the training set uniformly at random (IID).

---

## Keys and the proof service

[Benchmark on a new machine](#benchmark-on-a-new-machine) covers the whole
setup. In short, key material for the HE, DP and ElGamal modes is generated
with `python -m ppflx.keys generate <mode>` into `keys/`, and the ZKP modes need
the proof service binary and a key set:

| Variable | Points at |
|---|---|
| `FL_GNARK_BINARY` | `gnark_service`, built in gnark-gradient-prover |
| `FL_ZKP_KEYS_DIR` | the key manifest and verifying keys (a local setup: `~/.cache/ppflx/keys`) |
| `FL_ZKP_PK_DIR` | the proving keys (a local setup: `~/.cache/ppflx/pk`) |

ZKP modes use a Go Groth16 service, split into two roles: clients prove against a **prover**, and the server verifies against a separate **verifier** that holds only verifying keys. Neither role runs setup. Both load the keys in `FL_ZKP_KEYS_DIR` and refuse to start if a key is missing or doesn't match the manifest (see [docs/ZKP.md, section 7](https://github.com/CorpiXo/ppflx/blob/main/docs/ZKP.md#7-keys-and-trusted-setup)).

`compare.py` starts both roles itself. To run them by hand:

```bash
$FL_GNARK_BINARY serve --role prover --keys-dir "$FL_ZKP_KEYS_DIR" --pk-dir "$FL_ZKP_PK_DIR" --port 9000 &
$FL_GNARK_BINARY serve --role verifier --keys-dir "$FL_ZKP_KEYS_DIR" --port 9001 &
```

Every proof carries the SHA-256 of the verifying key it was made under. The server rejects any proof whose key isn't the pinned one, and each `round_outcomes` entry records the manifest hash. The setup is **single-party**: whoever ran `setup` could forge proofs. See [docs/ZKP.md, section 7.3](https://github.com/CorpiXo/ppflx/blob/main/docs/ZKP.md#73-what-a-single-party-setup-does-and-does-not-give) for what a multi-party ceremony would change.

---

## Quick Start

### Default modes

```bash
python compare.py --dataset healthcare
```

The default set is all 12 registered modes. The ElGamal modes are the slowest; to run only them:

```bash
python compare.py --dataset healthcare --modes he_elgamal_zkp,he_elgamal_zkp_sampled
```

### Select specific modes

```bash
python compare.py --dataset healthcare --modes baseline,dp
python compare.py --dataset healthcare --modes he_tenseal,he_concrete_tfhe
python compare.py --dataset healthcare --modes he_tenseal_zkp_dp,he_concrete_tfhe_zkp_dp
```

### Image datasets with non-IID partitioning

```bash
python compare.py --dataset mnist --dirichlet-alpha 0.1 --simulation
python compare.py --dataset cifar10 --dirichlet-alpha 0.5 --simulation
```

### Single runs (`python -m ppflx_bench.launch`)

Runs use Flower 1.36 (Python 3.12). `ppflx_bench.launch` starts a local SuperLink and one SuperNode per client, submits the Flower App declared in [pyproject.toml](pyproject.toml) with `flwr run`, waits for it and stops every process. The ServerApp and ClientApp are `ppflx_bench.app:server_app` and `ppflx_bench.app:client_app`, which build ppflx's FedPrivate strategy and FlowerClient; every run config key in `[tool.flwr.app.config]` is also a flag.

```bash
python -m ppflx_bench.launch --mode baseline --dataset healthcare --data-path ./dataset/ --num-clients 3 --num-rounds 3
python -m ppflx_bench.launch --mode he_tenseal --data-path ./dataset/ --num-rounds 2 --results-dir results/he_single/
python -m ppflx_bench.launch --mode dp --simulation --data-path ./dataset/ --num-rounds 2
```

`--simulation` uses Flower's Simulation Runtime instead of SuperNode processes; HE modes then transport plaintext and their results are marked `[SIM]`. Logs go to the results directory: `server.log` (SuperLink), `serverapp.log` (ServerApp), `client_<i>.log` (SuperNode and its ClientApp processes). ZKP modes need the proof service, which `compare.py` starts for you.

---

## Sweep Experiments

### Epsilon Sweep

Runs the `dp` mode at ε ∈ {0.5, 1.0, 2.0, 3.0, 5.0, 8.0}, each ε setting the noise
multiplier σ = √(2 · ln(1.25 / δ)) / ε:

```bash
python compare.py --dataset healthcare --simulation --epsilon-sweep
```

Output: `results/healthcare/dp_eps_<ε>/healthcare/<timestamp>/comparison_report.json`
per value, plus `results/healthcare/dp_epsilon_sweep_summary.json`. ε here is a
noise setting (see [DP as implemented](#privacy-modes)), so the sweep measures
accuracy against noise, not against a privacy guarantee.

### Alpha Sweep — Non-IID Heterogeneity

Runs the selected modes (default: all 12) at α ∈ {0.1, 0.5, 1.0, 10.0}:

```bash
python compare.py --dataset healthcare --simulation --alpha-sweep
```

Output: `results/healthcare/alpha_<α>/healthcare/<timestamp>/comparison_report.json`
per value, plus `results/healthcare/alpha_sweep_summary.json`.

### DP epsilon for a single run

`compare.py` takes ε from `keys/dp/dp_params.json`. To run one ε without
regenerating the file, use the single-run launcher:

```bash
python -m ppflx_bench.launch --mode dp --dp-epsilon 0.5 --simulation --data-path ./dataset/
```

---

## Statistical Significance

Each run uses a fixed random seed (default `42`). To estimate **mean ± std** across runs, pass `--seed` with different values and then aggregate with `scripts/aggregate_statistics.py`.

### Seed control

```bash
# --seed is forwarded to every simulation subprocess; default is 42
python compare.py --dataset healthcare --modes baseline,dp --rounds 5 --seed 42 --simulation
python compare.py --dataset healthcare --modes baseline,dp --rounds 5 --seed 123 --simulation
python compare.py --dataset healthcare --modes baseline,dp --rounds 5 --seed 456 --simulation
```

Each run creates a new `results/healthcare/<timestamp>/` directory. The seed used is recorded in every `comparison_report.json` entry as `"seed": 42`.

### Aggregate statistics

```bash
# After N runs, compute mean ± std per mode:
python scripts/aggregate_statistics.py --root results/healthcare/

# Warn if any mode has fewer than 5 runs:
python scripts/aggregate_statistics.py --root results/healthcare/ --min-runs 5

# Filter to specific modes only:
python scripts/aggregate_statistics.py --root results/healthcare/ --modes baseline,dp

# Skip the bar-chart PNG:
python scripts/aggregate_statistics.py --root results/healthcare/ --no-plot
```

The script scans only direct `YYYYMMDD_HHMMSS` children of `--root` — it ignores the merged dataset-level `comparison_report.json`, sweep subdirs (`alpha_*/`, `dp_eps_*/`) and runs renamed with a `keep_` prefix. Outputs:

| File | Description |
|------|-------------|
| `results/healthcare/statistical_summary.json` | Per-mode mean, std, min, max, 95% CI, N |
| `results/healthcare/statistical_summary.png` | Grouped bar chart with ± std error bars (requires matplotlib) |

The console summary lists, per mode, the number of runs and mean ± std of
accuracy, F1 and run time.

### Automated multi-run loop

`scripts/run_repeated_experiments.sh` runs the full experiment loop automatically:

```bash
# baseline and dp with 5 seeds; he_tenseal, zkp_sampled and the two triple modes with 3; then aggregate
bash scripts/run_repeated_experiments.sh healthcare
bash scripts/run_repeated_experiments.sh creditcard 20 5   # dataset rounds clients
```

---

## Blockchain Audit Ledger

Every run records a per-round audit trail. Three backends:

| Backend | Description |
|---------|-------------|
| `mock` (default) | An in-process ledger saved as JSON — no external node |
| `web3` | Sends transactions to an EVM node running ppflx's `FLLedger.sol` (`chain_rpc_url`, `chain_contract_addr` in ppflx's `FLConfig`; needs `web3.py`) |
| `none` | Disables the ledger |

```bash
python compare.py --dataset healthcare --chain-backend mock        # default
python compare.py --dataset healthcare --chain-backend none        # disable
python compare.py --dataset healthcare --chain-ledger-dir /tmp/ledgers
```

After every run a summary is printed; from the published healthcare run:

```
────────────────────────────────────────────────────────────────────────
  BLOCKCHAIN AUDIT SUMMARY
────────────────────────────────────────────────────────────────────────
  Mode                   Events   ModelCommit   ProofAnchor  Last Block
────────────────────────────────────────────────────────────────────────
  baseline                   10            10             0          10
  he_tenseal                 10            10             0          10
  he_concrete_tfhe           10            10             0          10
  zkp                        20            10            10          20
  zkp_sampled                20            10            10          20
  dp                         10            10             0          10
  he_tenseal_zkp             20            10            10          20
  he_concrete_tfhe_zkp       20            10            10          20
  he_elgamal_zkp             20            10            10          20
  he_elgamal_zkp_sampled     20            10            10          20
  he_tenseal_zkp_dp          20            10            10          20
  he_concrete_tfhe_zkp_dp     20            10            10          20
────────────────────────────────────────────────────────────────────────
```

- **ModelCommit** — every aggregated round, every mode: the SHA-256 of the
  aggregated model and of each admitted client update.
- **ProofAnchor** — every round of the ZKP modes: the SHA-256 of each accepted
  proof payload (for example 45 on healthcare `zkp`: 15 proofs from each of 3 clients).

The combined ledger is saved to `results/<dataset>/<timestamp>/ledger_comparison.json`.
The mock ledger is a local record of what the server did, not a tamper-proof one.

---

## Results Directory Structure

```
results/
├── README.md                          ← summary of the published runs
└── healthcare/
    ├── comparison_report.json         ← merged report: the latest result of every mode
    ├── keep_<timestamp>/              ← a published run (tracked by git)
    └── <timestamp>/                   ← one compare.py run (ignored by git)
        ├── comparison_report.json
        ├── comparison.png
        ├── ledger_comparison.json     ← all modes' ledgers
        ├── ledgers/ledger_<mode>.json
        └── <mode>/
            ├── benchmark.json         ← server and client metrics merged
            ├── client_<i>_benchmark.json
            ├── run_config.toml
            ├── server.log, serverapp.log, client_<i>.log
            └── .flwr/                 ← Flower state for the run
```

Sweeps add `dp_eps_<ε>/` and `alpha_<α>/` directories and their summaries, and
`scripts/aggregate_statistics.py` writes `statistical_summary.json`.

**Result merging**: re-running a mode replaces only that mode's entry in the merged report.

**Seed tracking**: each `comparison_report.json` entry records `"seed"`.

**Quality metrics** (`test_accuracy`, `test_auprc`, …) are each client's
evaluation of the global model on its own validation split (10% of its training
shard), averaged over clients and rounds. The held-out test split is evaluated
on the server only in non-HE modes, and only to the log.

---

## Architecture

```
ppflx-stack/                       ← any directory holding the three checkouts side by side
├── ppflx/                         ← the library: privacy modes, FedPrivate strategy, keys CLI, pinned verifying keys
├── gnark-gradient-prover/         ← Go proof service: Groth16 prover and verifier roles, key setup
└── ppflx-bench/                   ← this repository
    ├── compare.py                 ← main CLI: all 12 modes, sweeps, blockchain ledger
    ├── download_datasets.py       ← fills dataset/ (Kaggle and torchvision)
    ├── pyproject.toml             ← Flower App: ServerApp/ClientApp components and run config
    ├── requirements.txt           ← harness dependencies; ppflx as a git dependency
    ├── ppflx_bench/
    │   ├── launch.py              ← SuperLink/SuperNode launcher (python -m ppflx_bench.launch)
    │   ├── app.py                 ← the Flower App's ServerApp and ClientApp, built on ppflx
    │   ├── runner.py              ← run_mode() for scripts/run_comparison.py
    │   ├── datasets/              ← dataset registry, loaders and Dirichlet partitioning
    │   └── compare/
    │       ├── registry.py        ← dataset and mode registries, defaults
    │       ├── runner.py          ← run_comparison() and sweeps
    │       ├── experiment.py      ← one mode per run; starts the proof service
    │       ├── validation.py      ← ZKP run validation (ledger and round outcomes)
    │       └── report.py          ← summary table
    ├── privacy_comparison_analysis.ipynb ← analysis of the published results
    ├── results/                   ← published runs (see results/README.md)
    ├── scripts/                   ← statistics, repeated runs, ZKP-bound calibration
    ├── tests/                     ← pytest suite for the harness
    └── docs/                      ← reference guides (see docs/README.md)
        ├── README.md              ← guides index
        ├── FL.md                  ← the federated setup: data, model, aggregation, evaluation
        ├── DP.md                  ← the DP mechanism as implemented and the epsilon sweep
        ├── FHE.md                 ← CKKS and TFHE as used here
        └── BC.md                  ← the audit ledger
```

The ZKP guide lives with the library: [ppflx docs/ZKP.md](https://github.com/CorpiXo/ppflx/blob/main/docs/ZKP.md).

---

## Documentation


| File | Purpose |
|------|---------|
| [docs/README.md](docs/README.md) | Index of the guides on FL, DP, HE and the audit ledger |
| [results/README.md](results/README.md) | The published runs: setup and summary |
| [privacy_comparison_analysis.ipynb](privacy_comparison_analysis.ipynb) | Tables and figures from the published runs |
| [compare.py](compare.py) | Main comparison CLI for the 12 privacy modes |
| [ppflx_bench/launch.py](ppflx_bench/launch.py) | Single runs on a local SuperLink and SuperNodes (`python -m ppflx_bench.launch`) |
| [ppflx_bench/compare/registry.py](ppflx_bench/compare/registry.py) | Dataset and mode registry, prerequisites, defaults |
| [ppflx `ppflx/keys/cli.py`](https://github.com/CorpiXo/ppflx/blob/main/ppflx/keys/cli.py) | Key / parameter generation CLI (`python -m ppflx.keys ...`) |
| [scripts/aggregate_statistics.py](scripts/aggregate_statistics.py) | Mean ± std aggregation over repeated runs |
| [scripts/run_repeated_experiments.sh](scripts/run_repeated_experiments.sh) | Convenience loop for repeated runs |
| [gnark-gradient-prover](https://github.com/CorpiXo/gnark-gradient-prover) | gnark prove/verify HTTP service and key setup |
| [download_datasets.py](download_datasets.py) | Dataset download into `dataset/` |

---

## Performance Reference

End-to-end timings, bandwidth and accuracy for every mode are in [`results/README.md`](results/README.md), from runs on an Intel Core i5-1035G1 laptop CPU.

Single-proof measurements from ppflx's ZKP.md (Apple M3 Pro, 18 GB, one proof at a time):

| Circuit | Constraints | Prove | Verify |
|---|---|---|---|
| Norm (`zkp`, CKKS/TFHE composites), 256 values per proof | 103,365 | 0.65 s | 2.3–3.6 ms |
| ElGamal (`he_elgamal_zkp`), 128 coordinates per proof | 1,274,949 | 3.13 s | 7.4 ms |

See [docs/ZKP.md, section 11](https://github.com/CorpiXo/ppflx/blob/main/docs/ZKP.md#11-performance) for proofs per round, key sizes and end-to-end timings.

---

## Environment Variables

These variables tune the runs without code changes; the SuperLink and SuperNodes inherit them from the shell that starts `compare.py`.

### ZKP

| Variable | Default | Description |
|----------|---------|-------------|
| `FL_ZKP_BACKEND` | `gnark` | `gnark` = Groth16 zk-SNARK; `pedersen` = legacy commitment stub (no verification), refused unless `FL_ZKP_ALLOW_PEDERSEN_STUB=1` |
| `FL_ZKP_ALLOW_PEDERSEN_STUB` | `0` | `1` = knowingly run the unverified pedersen stub; every round is recorded as `unverified_stub` |
| `FL_ZKP_SAMPLE_PCT` | `0.1` | Sampled modes: fraction of model coordinates proven per client per round, in (0, 1]. Set on the server; the per-round seed is drawn by the server after clients commit and recorded in `round_outcomes` |
| `FL_ZKP_PARALLELISM` | `1` | Proofs generated concurrently per client (each proof uses several cores inside the prover service) |
| `FL_ZKP_SCALE` | `1000000` | Float→int64 scale for the proof circuit |
| `FL_ZKP_MAX_NORM` | calibrated per dataset | Overrides the server's **update**-norm bound B on ‖w_local − w_global‖₂ (not a weight norm). Default: `PER_STEP_UPDATE_NORM[dataset] × local_epochs × max_client_batches` in `ppflx/core/update_bound.py` (the server computes the batch count from the same partition clients use), calibrated with `scripts/calibrate_update_norm.py`. Clients clip their update to B before proving. DP runs need their own calibration (DP noise enlarges honest updates); the DP clipping norm is a per-step gradient clip and is not a valid value |
| `FL_ZKP_TIMEOUT` | `600` | Fallback HTTP timeout (seconds) for the proof services; `FL_ZKP_PROVE_TIMEOUT` (default 1800) and `FL_ZKP_VERIFY_TIMEOUT` / `FL_ZKP_VERIFY_LIGHT_TIMEOUT` (default 900) take precedence |

**Failure handling.** Security-relevant paths fail closed:

- A client whose proof generation fails raises instead of uploading.
- The server checks every upload against its own model schema and proof policy: full coverage, shapes, scale and bound. Clients that fail are rejected; the round aborts if the proof service is unreachable.
- If fewer clients are admitted than `min_fit_clients`, the global model is unchanged and nothing is written to the ledger.
- Every round's outcome (`aggregated`, `no_quorum`, `infrastructure_abort`), including rejected clients and reasons, is recorded under `round_outcomes` in `comparison_report.json`. ZKP runs with any non-aggregated round fail validation.
- Sampled modes (`zkp_sampled`, `he_elgamal_zkp_sampled`) use two Flower rounds per round (commit, then challenge). A client that commits but doesn't answer the challenge, or answers without having committed, is rejected.
- DP without a params file refuses to run unless `--dp_epsilon` is passed explicitly.

### HE

| Variable | Default | Description |
|----------|---------|-------------|
| `FL_ENCRYPT_LAYERS` | `ALL` | TenSEAL layers to encrypt; unlisted layers are sent in plaintext. Names not in the model are an error |
| `FL_CONCRETE_TFHE_FORCE_REAL` | `0` | `1` = run real TFHE on image datasets (high RAM) |
| `FL_CONCRETE_TFHE_ALLOW_SIMULATED` | `0` | `1` = knowingly send plaintext quantized weights on image datasets; otherwise TFHE on images refuses to run |
| `FL_ELGAMAL_SCALE` | `10000` | `he_elgamal_zkp` quantization: q = round(w·scale), \|q\| < 2¹⁷ (so \|w\| < 13.1). The proven bound is W²·⌈B·scale + √n/2⌉²; the √n/2 rounding slack is small only when B·scale ≫ √n, which is why the default rose from 1000 |
| `FL_ZKP_PROVER_URL` | `http://127.0.0.1:9000` | gnark prover role (clients) |
| `FL_ZKP_VERIFIER_URL` | `http://127.0.0.1:9001` | gnark verifier role (server) |
| `FL_GNARK_BINARY` | none | Proof service binary built in gnark-gradient-prover; required for ZKP modes and `generate he_elgamal` |
| `FL_ZKP_KEYS_DIR` | ppflx's packaged pinned keys | Key manifest and verifying keys; a local setup puts them in `~/.cache/ppflx/keys`. The circuit sizes (norm chunk, ElGamal coordinates per proof) come from this manifest |
| `FL_ZKP_PK_DIR` | `~/.cache/ppflx/pk` | Proving keys (prover only) |
| `FL_CONCRETE_TFHE_BIT_WIDTH` | `14` | TFHE quantization bit width (2–16). Lower = more accuracy loss |
| `FL_CONCRETE_TFHE_ADAPTIVE_QUANT` | `0` | `1` = per-tensor quantization range instead of the fixed [-5, 5]; not used in the published runs |
| `FL_CONCRETE_TFHE_KEYS_DIR` | `ppflx/keys/prebuilt/` in the installed ppflx | Where TFHE circuits and the shared TFHE keys are compiled to and loaded from |

### Transport

| Variable | Default | Description |
|----------|---------|-------------|
| `FL_CLIENT_TIMEOUT` | the larger of 2 h and 6 min per round (HE/ZKP modes: 6 h and 30 min per round) | Harness: time budget per run in seconds, plus 30 min headroom; `FL_SERVER_TIMEOUT` sets the total directly |
| `FL_CLIENT_WAIT_TIMEOUT` | `600` | ServerApp: seconds to wait for enough SuperNodes before a round, then stop the run with an error instead of Flower's 24-hour wait |
| `FL_SERVER_GRACE` | `600` | Harness: seconds a run may stay active after every SuperNode exited before it is stopped and the mode marked failed |

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| ZKP modes: `Connection refused :9000`/`:9001` | gnark prover/verifier not running | see "Keys and the proof service" above; `compare.py` starts both |
| `FL_GNARK_BINARY is not set` | proof service not built or not exported | build gnark-gradient-prover and export `FL_GNARK_BINARY` ([step 3](#3-build-the-proof-service-and-make-local-zkp-keys)) |
| `No ZKP key manifest` / `Proving keys … not in` | no local key set, or the variables are not exported | run the local setup and export `FL_ZKP_KEYS_DIR` and `FL_ZKP_PK_DIR` ([step 3](#3-build-the-proof-service-and-make-local-zkp-keys)); never re-key the pinned keys |
| `HTTP 503 … verifying key` | service started from different keys than the manifest | stop the services on :9000/:9001 and rerun; `compare.py` starts them from `FL_ZKP_KEYS_DIR` |
| `proof_verification = 0.0` in results | Pedersen backend selected | `export FL_ZKP_BACKEND=gnark` |
| DP accuracy drops significantly | ε too small, so σ is large | Raise ε when generating the DP parameters, e.g. `python -m ppflx.keys generate dp --epsilon 2.0 --output keys/dp/dp_params.json` |
| TFHE modes on `mnist`/`cifar10` refuse to start | real TFHE on images is off by default | `FL_CONCRETE_TFHE_FORCE_REAL=1`; check memory first (about 1.5 GB per client on mnist; cifar10 ran out of memory on 23 GB with three clients) |
| ZKP modes refuse to start: `no calibrated ZKP update-norm bound for dataset 'cifar'` | the legacy `cifar` key has no calibrated bound | use `--dataset cifar10`, or set `FL_ZKP_MAX_NORM` |
| A run stops with `run timeout after …s` | the run outlived the harness time budget | raise `FL_CLIENT_TIMEOUT` or `FL_SERVER_TIMEOUT` (see Transport above) |
| `FileNotFoundError: keys/he_tenseal/secret_context.bin` | HE keys not generated | `python -m ppflx.keys generate he_tenseal` |
| TenSEAL `RuntimeError: incompatible version` | key files written by another TenSEAL version | `python -m ppflx.keys generate he_tenseal --overwrite` |
| TFHE rounds end `no_results`, `ClientApp stopped responding`; client log shows an LLVM `Assertion failed` | `ppflx/keys/prebuilt/` bundles compiled by another Concrete version abort the ClientApp natively | move the bundles out of `ppflx/keys/prebuilt/`; fresh ones are generated on the next run |
| `FileNotFoundError: keys/dp/dp_params.json` | DP params not generated | `python -m ppflx.keys generate dp --output keys/dp/dp_params.json` |
| `port 1909x is in use` from `ppflx_bench.launch` | a SuperLink or SuperNode from an interrupted run is still running | stop it (`lsof -ti tcp:19093`), or wait for the other run to finish; runs use fixed ports |
| `ledger_comparison.json` missing | `--chain-backend none` was set | Re-run without `--chain-backend none` |
| `node partition … does not match num-clients` | SuperNode `--node-config` disagrees with the run's `num-clients` | start SuperNodes with `partition-id=<i> num-partitions=<num-clients>` |

---

## References

- [Flower Federated Learning Framework](https://flower.ai)
- [TenSEAL — CKKS Homomorphic Encryption](https://github.com/OpenMined/TenSEAL)
- [Concrete — TFHE compiler by Zama](https://github.com/zama-ai/concrete) (installed with Concrete ML)
- [gnark — Groth16 zk-SNARK in Go](https://github.com/consensys/gnark)
- McMahan et al., "Communication-Efficient Learning of Deep Networks from Decentralized Data", AISTATS 2017
- Abadi et al., "Deep Learning with Differential Privacy", CCS 2016
- Bonawitz et al., "Towards Federated Learning at Scale", SysML 2019
