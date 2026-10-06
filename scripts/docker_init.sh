#!/usr/bin/env bash
# Generate the keys a benchmark run needs, inside the container (compose service
# "init"). Each step is skipped when its output already exists.
set -euo pipefail

if [[ ! -f "$FL_ZKP_KEYS_DIR/manifest.json" ]]; then
    echo "[init] ZKP: local key setup into $FL_ZKP_KEYS_DIR (proving keys: $FL_ZKP_PK_DIR); this takes a while"
    mkdir -p "$FL_ZKP_KEYS_DIR" "$FL_ZKP_PK_DIR"
    "$FL_GNARK_BINARY" setup --keys-dir "$FL_ZKP_KEYS_DIR" --pk-dir "$FL_ZKP_PK_DIR"
else
    echo "[init] ZKP: key set present in $FL_ZKP_KEYS_DIR"
fi
mkdir -p "$FL_CONCRETE_TFHE_KEYS_DIR"

generate() {  # generate <file it creates> <python -m ppflx.keys generate arguments...>
    local out=$1
    shift
    if [[ -f "$out" ]]; then
        echo "[init] $1: $out present"
    else
        echo "[init] $1: generating $out"
        python -m ppflx.keys generate "$@"
    fi
}

generate keys/he_tenseal/secret_context.bin he_tenseal
generate keys/zkp/zkp_params.json zkp --output keys/zkp/zkp_params.json
generate keys/dp/dp_params.json dp --output keys/dp/dp_params.json
generate keys/he_elgamal/secret_key.json he_elgamal

echo "[init] done"
