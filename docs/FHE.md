# Homomorphic encryption

How the HE modes hide client updates from the aggregation server. Three schemes
are used: CKKS (TenSEAL), TFHE (Concrete) and exponential ElGamal. In all of them
the server adds ciphertexts and never decrypts; the clients decrypt the
aggregate. Measured costs are in [results/README.md](../results/README.md).

## 1. What HE protects here

- **Against the server:** it sees ciphertexts of the updates, not the updates.
  It does see metadata: the number of clients, ciphertext sizes, and in the CKKS
  and ElGamal modes each client's sample count (the aggregation weights). The
  ElGamal modes also reveal per-chunk update norms to the server (ppflx's
  ZKP.md).
- **Not against other clients:** in every HE mode all clients share one secret
  key, so any client could decrypt another's upload if it saw it.
- **Not against a malicious server:** a server that sends clients a crafted
  global model, or a wrong aggregate, is not detected by HE.
- **Not integrity:** HE alone does not stop a client uploading a poisoned
  update. Only the ElGamal modes bind a proof to the ciphertext
  ([ZKP.md](https://github.com/CorpiXo/ppflx/blob/main/docs/ZKP.md)).

With `--simulation`, HE modes transport plaintext and are marked `[SIM]`; their
results are not evidence of encrypted runs.

## 2. CKKS with TenSEAL (`he_tenseal`, `he_tenseal_zkp`, `he_tenseal_zkp_dp`)

CKKS (Cheon et al., 2017) encrypts vectors of real numbers and supports
approximate addition and multiplication; TenSEAL (Benaissa et al., 2021) wraps
Microsoft SEAL.

- **Parameters:** polynomial modulus degree 8192, coefficient moduli
  [60, 40, 40, 60] bits, scale 2⁴⁰ (`ppflx/core/security.py`).
- **Keys:** `python -m ppflx.keys generate he_tenseal` writes
  `keys/he_tenseal/secret_context.bin` (clients) and `public_context.bin`
  (server, no secret key).
- **Upload:** each layer is flattened into CKKS vectors. `FL_ENCRYPT_LAYERS`
  selects layers; the default `ALL` encrypts every layer, and unlisted layers
  would be sent in plaintext.
- **Aggregation:** the server computes Σₖ (nₖ/N)·Enc(wₖ) homomorphically and
  sends the result back. Round 1's model comes encrypted from one client.
- **Accuracy:** CKKS is approximate, but the error is far below the update
  sizes; in the published runs `he_tenseal` matches the baseline's metrics.

## 3. TFHE with Concrete (`he_concrete_tfhe`, `he_concrete_tfhe_zkp`, `he_concrete_tfhe_zkp_dp`)

TFHE (Chillotti et al., 2020) encrypts integers; Zama's Concrete compiles a
circuit for it. Here the circuit is a single addition of two encrypted tensors.

- **Quantization:** each weight is clipped to [−5, 5] and quantized to a 14-bit
  integer (`FL_CONCRETE_TFHE_BIT_WIDTH`). The 14-bit step is about 0.0006; in the
  published runs it cost a few tenths of a point of accuracy at most.
- **Shares:** each of K clients divides its integers by K before encrypting, so
  the sum of K uploads fits the circuit's range; each ciphertext records its
  share, and decryption divides by the total, so a single upload or a partial
  aggregate decrypts correctly. The average is unweighted.
- **Keys and circuits:** the first run compiles one circuit per tensor shape and
  writes the shared secret key, evaluation keys and circuits to
  `ppflx/keys/prebuilt/` (or `FL_CONCRETE_TFHE_KEYS_DIR`). The server loads only
  the compiled circuit and the evaluation keys; it never loads the secret key.
- **Cost:** about 6.3 KB per parameter uploaded (about 1,600 times the plaintext
  update), and encryption and decryption take seconds per client per round.
- **Images:** real TFHE on `mnist`/`cifar10` is off by default and needs
  `FL_CONCRETE_TFHE_FORCE_REAL=1` (`FL_CONCRETE_TFHE_ALLOW_SIMULATED=1` instead
  sends plaintext quantized weights, knowingly). On mnist each client peaked at
  about 1.5 GB; on cifar10 a client reached about 5.7 GB on the 120×400 layer and
  three clients ran out of memory on a 23 GB machine.

## 4. Exponential ElGamal (`he_elgamal_zkp`, `he_elgamal_zkp_sampled`)

ElGamal (1985) in the exponent (Cramer, Gennaro and Schoenmakers, 1997):
Enc(m) = (r·G, m·G + r·PK) on BabyJubJub, the twisted Edwards curve over BN254's
scalar field, so the proof circuit can check it natively. Adding
ciphertexts adds the messages; decrypting needs a discrete logarithm, so values
are small integers: each weight is quantized as q = round(w · 10,000)
(`FL_ELGAMAL_SCALE`), |q| < 2¹⁷.

These are the only HE modes whose proofs are bound to the uploaded ciphertexts;
the protocol, bounds and limits are in ppflx's
[ZKP.md, sections 6.3–6.4](https://github.com/CorpiXo/ppflx/blob/main/docs/ZKP.md#63-he_elgamal_zkp).
Each parameter costs about 66 bytes uploaded (a compressed two-point ciphertext
plus framing); the cost is dominated by proving (see the results).

## References

- Cheon, Kim, Kim and Song. *Homomorphic Encryption for Arithmetic of
  Approximate Numbers.* ASIACRYPT 2017.
- Benaissa, Retiat, Cebere and Belfedhal. *TenSEAL: A Library for Encrypted
  Tensor Operations Using Homomorphic Encryption.* arXiv:2104.03152, 2021.
- Chillotti, Gama, Georgieva and Izabachène. *TFHE: Fast Fully Homomorphic
  Encryption over the Torus.* Journal of Cryptology 33, 2020.
- ElGamal. *A Public Key Cryptosystem and a Signature Scheme Based on Discrete
  Logarithms.* IEEE Transactions on Information Theory 31(4), 1985.
- Cramer, Gennaro and Schoenmakers. *A Secure and Optimally Efficient
  Multi-Authority Election Scheme.* EUROCRYPT 1997.
