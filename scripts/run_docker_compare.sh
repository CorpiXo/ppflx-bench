#!/usr/bin/env bash
# Run the comparison in Docker: build the image, generate missing keys, then run
# compare.py with the arguments given (default: --dataset healthcare).
#
#   scripts/run_docker_compare.sh
#   scripts/run_docker_compare.sh --dataset creditcard --modes baseline,zkp --rounds 2
#
# Needs Docker Engine with the compose plugin, and the ppflx and
# gnark-gradient-prover checkouts beside this one. Datasets are read from
# ./dataset (see README.md, "Docker"); results go to ./results as on the host.
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT_DIR"

for repo in ppflx gnark-gradient-prover; do
    if [[ ! -d "../$repo" ]]; then
        echo "[ERROR] ../$repo not found: the image is built from the directory holding all three checkouts" >&2
        exit 1
    fi
done

# Create the mounted directories as you, and run the container as you, so
# everything it writes stays yours.
mkdir -p dataset results keys .docker-state
export PPFLX_UID PPFLX_GID
PPFLX_UID=$(id -u)
PPFLX_GID=$(id -g)

if [[ $# -eq 0 ]]; then
    set -- --dataset healthcare
fi

echo "[1/3] Building the image..."
docker compose build

echo "[2/3] Generating missing keys..."
docker compose run --rm init

echo "[3/3] Running compare.py $*"
docker compose run --rm bench python compare.py "$@"
