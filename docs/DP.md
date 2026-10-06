# Differential privacy

What the DP modes (`dp`, `he_tenseal_zkp_dp`, `he_concrete_tfhe_zkp_dp`) do, and
what they do not guarantee.

## 1. The guarantee DP-SGD is designed to give

A randomized algorithm M is (ε, δ)-differentially private if, for any two
datasets D and D′ that differ in one record and any set of outputs S,

  Pr[M(D) ∈ S] ≤ e^ε · Pr[M(D′) ∈ S] + δ

(Dwork and Roth, 2014). DP-SGD (Abadi et al., 2016) trains a model with this
property by, at every step: clipping **each example's** gradient to norm C, so one
record changes the batch sum by at most C; adding Gaussian noise with standard
deviation σ·C to the sum; and tracking the privacy spent across all steps with an
accountant (the moments accountant, or Rényi DP; Mironov, 2017). The ε reported
is the accountant's total for the whole training run.

## 2. What ppflx implements

In local training (`ppflx/core/engine.py`), after each batch's backward pass:

1. The batch's **mean** gradient, over all parameters, is clipped to L2 norm C
   (`max_grad_norm`).
2. Gaussian noise with standard deviation σ·C/B is added to it, where B is the
   batch size and σ = √(2 ln(1.25/δ)) / ε (`noise_multiplier`). With
   `mechanism = "laplace"`, Laplace noise of scale (C/ε)/B is added instead.
3. The optimizer steps on the noisy gradient. The client then uploads its model
   as usual, so the noise is applied on the client, before the server or the
   encryption sees anything.

## 3. What that does and does not give

- **No end-to-end (ε, δ) guarantee.** Clipping the mean gradient does not bound
  one record's influence the way per-example clipping does, and σ is the
  calibration of a single Gaussian-mechanism release; nothing accounts for the
  steps, epochs and rounds of a run. The recorded ε is therefore a noise
  setting, not the privacy of the published model.
- **What it does do.** It adds noise to every training step, which costs
  accuracy; the published runs measure that cost (see
  [results/README.md](../results/README.md)). Less noise (larger ε) costs less.
- **What a guarantee would need.** Per-example clipping (for example with
  Opacus, which ppflx does not use) and an accountant over the whole run, with
  the resulting ε reported per run.

## 4. Parameters

`compare.py` reads `keys/dp/dp_params.json`, created with

```bash
python -m ppflx.keys generate dp --output keys/dp/dp_params.json
```

Options: `--epsilon` (default 1.0), `--delta` (default 1e-5), `--max_grad_norm`
(default 1.0), `--mechanism` (`gaussian` or `laplace`), `--noise_multiplier`.
The published runs used ε = 1.0, δ = 1e-5, Gaussian, σ = 4.84, C = 1.0.

A run's ε can be overridden without changing the file with the single-run
launcher's `--dp-epsilon`; σ is then recomputed from it. In ppflx's config,
`dp_epsilon = 10.0` means "not overridden" (the run config's 0 maps to it), so
10.0 itself cannot be requested as an override.

DP modes refuse to run without a parameter file unless an ε is passed
explicitly.

## 5. DP with the composites

In `he_tenseal_zkp_dp` and `he_concrete_tfhe_zkp_dp` the noise is added during
training, then the update is proved and encrypted as in the non-DP composites.
Their proofs are not bound to the ciphertext, and they do not enforce the
update-norm bound, because DP noise makes honest updates exceed the non-DP
calibration (ppflx's ZKP.md, section 4). They add confidentiality from the
server to the noise above, and no integrity.

## 6. Epsilon sweep

```bash
python compare.py --dataset healthcare --simulation --epsilon-sweep
```

Runs `dp` at ε ∈ {0.5, 1.0, 2.0, 3.0, 5.0, 8.0}, writing
`results/healthcare/dp_eps_<ε>/healthcare/<timestamp>/comparison_report.json` per
value and `results/healthcare/dp_epsilon_sweep_summary.json`. Given section 3, the
sweep measures accuracy against the amount of noise, not against a privacy
guarantee. No sweep is part of the published results.

## References

- Dwork and Roth. *The Algorithmic Foundations of Differential Privacy.*
  Foundations and Trends in Theoretical Computer Science 9(3–4), 2014.
- Abadi, Chu, Goodfellow, McMahan, Mironov, Talwar and Zhang. *Deep Learning with
  Differential Privacy.* ACM CCS 2016.
- Mironov. *Rényi Differential Privacy.* IEEE CSF 2017.
