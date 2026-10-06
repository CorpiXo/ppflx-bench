# The audit ledger

Every run can record a per-round audit trail of what the server aggregated and
which proofs it accepted. This guide describes what is recorded, where, and what
the record does and does not show. The code is ppflx's `ppflx/chain.py` and
`ppflx/chain_contract/FLLedger.sol`.

## 1. Events

The server writes two kinds of event per round, after aggregating:

| Event | Written | Fields |
|---|---|---|
| `ModelCommit` | every aggregated round, every mode | `round`, `model_hash` (SHA-256 of the aggregated parameters), `client_hashes` (SHA-256 of each admitted client's update), `num_clients`, `metadata` (the mode) |
| `ProofAnchor` | every aggregated round of a ZKP mode | `round`, `proof_hashes` (SHA-256 of each accepted proof payload, canonical JSON), `client_ids`, `num_proofs` |

Each event also has a `block` number, a `timestamp` and a `tx` identifier. A round
that does not aggregate (for example `no_quorum`) writes nothing.

In the published runs every mode has one `ModelCommit` per round, and each ZKP
mode one `ProofAnchor` per round; on healthcare `zkp`, each anchor holds 45 proof
hashes (15 proofs from each of 3 clients).

## 2. Backends

Chosen with `--chain-backend` (or `FL_CHAIN_BACKEND`):

| Backend | What it does |
|---|---|
| `mock` (default) | Keeps the events in the ServerApp process with sequential block numbers and writes them to `ledgers/ledger_<mode>.json` after every round. No network, no signatures. |
| `web3` | Sends each event to an EVM node over web3.py (ppflx's `web3` extra). With `FL_CHAIN_CONTRACT_ADDR` set, it calls `commitModel` and `anchorProofs` on a deployed `FLLedger.sol`; without it, it sends a zero-value self-transfer carrying a keccak fingerprint of the event. Node and key: `FL_CHAIN_RPC_URL`, `FL_CHAIN_PRIVATE_KEY`. |
| `none` | Records nothing. |

The published runs used `mock`. `compare.py` combines the per-mode files into
`ledger_comparison.json` in the run directory and prints a per-mode summary.

## 3. What the ledger shows, and what it does not

- **It shows** what the server says it aggregated and which proofs it accepted,
  round by round, as hashes. Anyone holding a model, an update or a proof payload
  can check it against the recorded hash.
- **It does not show that the proofs verified.** The verifier's decisions are in
  the report's `round_outcomes`; `ppflx_bench/compare/validation.py` checks both
  (every round has a `ModelCommit` and a `ProofAnchor`, every aggregated client
  appears in the anchor with the same number of proofs, and every round
  aggregated with no rejections).
- **It does not show that aggregation was computed correctly.** The server
  writes the hashes; nothing in the ledger proves the committed model is the
  average of the committed updates.
- **The `mock` ledger is a local file written by the server.** It is not
  tamper-evident to anyone else. With `web3` the events are ordered and public
  on the chain, but they are still the server's own statements, signed with its
  key.

## 4. Commands

```bash
python compare.py --dataset healthcare --chain-backend mock        # default
python compare.py --dataset healthcare --chain-backend none        # no ledger
python compare.py --dataset healthcare --chain-ledger-dir /tmp/ledgers
```

ZKP run validation reads the ledger, so ZKP modes run with `--chain-backend none`
cannot be validated.
