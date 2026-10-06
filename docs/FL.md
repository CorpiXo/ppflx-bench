# The federated setup

What every mode in the comparison shares: how the federation runs, the data and
models, local training, how each mode aggregates, and what the quality metrics
measure. The privacy mechanisms are in [DP.md](DP.md), [FHE.md](FHE.md) and
ppflx's [docs/ZKP.md](https://github.com/CorpiXo/ppflx/blob/main/docs/ZKP.md).

## 1. Deployment

Each mode is one run of a [Flower](https://flower.ai) 1.36 App
(`pyproject.toml`; ServerApp and ClientApp in `ppflx_bench/app.py`, built on
ppflx's `FedPrivate` strategy and `FlowerClient`).

- `compare.py` starts a SuperLink and one SuperNode per client as local
  processes (`ppflx_bench/launch.py`), submits the run with `flwr run`, and
  stops everything when it ends. `--simulation` uses Flower's Simulation
  Runtime instead; HE modes then transport plaintext and their results are
  marked `[SIM]`.
- Every ClientApp message runs in a new process. State a client keeps between
  rounds (keys, the decrypted global model, commitments) lives in Flower's
  `Context.state`.
- The server waits until all clients are connected before round 1
  (`min-avail-clients` = number of clients), then samples every client for
  training (`frac-fit` = 1.0) and every client for evaluation (`frac-eval` = 1.0,
  `min-eval-clients` = number of clients). A round aggregates if at least
  `min-fit-clients` (2) clients are admitted.
- The published runs use 3 clients and 10 rounds (the defaults). Commit–challenge
  modes (`zkp_sampled`, `he_elgamal_zkp_sampled`) use two Flower rounds per
  federated round.

## 2. Data

| Dataset | Source | Samples | Features | Classes |
|---|---|---|---|---|
| `healthcare` | Heart disease, Statlog + Cleveland + Hungary combined (Kaggle) | 1,190 | 11 | 2 |
| `creditcard` | Credit card fraud (Kaggle, mlg-ulb), 0.17% positive | 284,807 | 30 | 2 |
| `stock` | Daily prices of one stock (CERN, Kaggle "Price Volume Data for All US Stocks & ETFs"); target: next close up or down | 3,180 | 11 | 2 |
| `mnist` | MNIST (torchvision) | 70,000 | 1×28×28 | 10 |
| `cifar10` | CIFAR-10 (torchvision); supported, not benchmarked | 60,000 | 3×32×32 | 10 |

- **Train/test.** Tabular data is split 80/20 at random (stratified by label)
  and standardized; the image datasets use their standard train/test splits.
  `stock` is a time series split at random, not by date, so training and test
  days interleave.
- **Client shards.** By default the training set is split into equal shards at
  random (IID). With `--dirichlet-alpha α`, each class's samples are divided
  among the clients in proportions drawn from Dir(α·1): small α gives each client
  few classes, large α approaches IID (Hsu, Qi and Brown, 2019).
- **Validation.** Each client keeps 10% of its shard as a validation split.

The tabular loaders read `dataset/` relative to the working directory.

## 3. Models and local training

| Data | Model | Parameters |
|---|---|---|
| Tabular | MLP, hidden layers 64 and 32, ReLU | 2,914 (11 features), 4,130 (creditcard) |
| MNIST | CNN: two 5×5 convolutions (6, 16 channels) with max-pooling, then 120–84–10 fully connected | 44,426 |
| CIFAR-10 | The same CNN on 3×32×32 input | 62,006 |

Each round, a client loads the global model and trains it for the dataset's local
epochs (healthcare, creditcard and stock 5; mnist 3) with SGD (learning rate
0.001, momentum 0.9) on cross-entropy, batch size 16 (healthcare, stock), 32
(creditcard) or 64 (mnist). DP modes add their noise inside this loop
([DP.md](DP.md)).

## 4. Aggregation

All modes compute a FedAvg-style average (McMahan et al., 2017); they differ in
what the server sees and how the average is weighted.

| Modes | Server computes | Weights |
|---|---|---|
| `baseline`, `dp`, `zkp`, `zkp_sampled` | the average of the plaintext updates | sample counts |
| CKKS modes (`he_tenseal*`) | Σₖ (nₖ/N)·Enc(wₖ) on ciphertexts | sample counts, which the server sees |
| TFHE modes (`he_concrete_tfhe*`) | Σₖ Enc(wₖ/K) on ciphertexts | equal (each of K clients contributes a 1/K share) |
| ElGamal modes (`he_elgamal_zkp*`) | Σₖ nₖ·Encₖ on ciphertexts | sample counts |

In ZKP modes the server first verifies each client's proofs and aggregates only
admitted clients. In HE modes clients decrypt the aggregate themselves.

## 5. Evaluation

After each round every client evaluates the new global model on its own
validation split. The quality metrics in the reports (`test_accuracy`,
`test_auprc`, `test_f1`, precision, recall) are the mean of those evaluations
over all clients and rounds. The held-out test split is evaluated on the server
only in non-HE modes, and only to the log (`serverapp.log`); it is not in the
reports.

Because every client evaluates every round, modes that train the same model
report the same metrics.

## 6. Round outcomes

Every round is recorded in the report's `round_outcomes`: `aggregated`,
`committed` (first half of a commit–challenge round), `no_quorum` or
`infrastructure_abort`, with admitted and rejected clients, Flower failures, and
for ZKP modes the key manifest hash. A run counts only if every round aggregated
(or committed) with no rejections or failures; see the README's "Accept the
results".

## 7. Alpha sweep

```bash
python compare.py --dataset healthcare --simulation --alpha-sweep
```

Runs the selected modes (default: all) at α ∈ {0.1, 0.5, 1.0, 10.0}, writing
`results/healthcare/alpha_<α>/healthcare/<timestamp>/comparison_report.json` and
`results/healthcare/alpha_sweep_summary.json`. A single non-IID run takes
`--dirichlet-alpha α`. No alpha sweep is part of the published results.

## References

- McMahan, Moore, Ramage, Hampson and Agüera y Arcas. *Communication-Efficient
  Learning of Deep Networks from Decentralized Data.* AISTATS 2017.
- Hsu, Qi and Brown. *Measuring the Effects of Non-Identical Data Distribution
  for Federated Visual Classification.* arXiv:1909.06335, 2019.
- Beutel et al. *Flower: A Friendly Federated Learning Research Framework.*
  arXiv:2007.14390, 2020.
