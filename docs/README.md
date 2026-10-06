# Guides

How ppflx-bench runs the comparison, and how each mechanism is implemented and
measured here. They describe this code; general background is kept short and
points to the original papers.

| Guide | Covers |
|-------|--------|
| [FL.md](FL.md) | The federated setup: Flower deployment, data and partitioning, models, local training, aggregation per mode, evaluation, the alpha sweep |
| [DP.md](DP.md) | The DP mechanism as implemented, what it does and does not guarantee, its parameters, the epsilon sweep |
| [FHE.md](FHE.md) | Homomorphic encryption as used here: CKKS (TenSEAL), TFHE (Concrete), exponential ElGamal; keys, costs and limits |
| [BC.md](BC.md) | The audit ledger: what each event records, the backends, and what the ledger does and does not show |

Start elsewhere for:

- **Running the benchmark** — the [README](../README.md), "Benchmark on a new machine".
- **The published results** — [results/README.md](../results/README.md) and
  [privacy_comparison_analysis.ipynb](../privacy_comparison_analysis.ipynb).
- **What each mode protects** — ppflx's
  [SECURITY.md](https://github.com/CorpiXo/ppflx/blob/main/SECURITY.md).
- **The proof protocols, keys and trusted setup** — ppflx's
  [docs/ZKP.md](https://github.com/CorpiXo/ppflx/blob/main/docs/ZKP.md).
- **Environment variables and troubleshooting** — the [README](../README.md).
