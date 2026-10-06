"""The Docker setup stays consistent with the repository: the scripts parse,
compose runs the image as the calling user with every state directory mounted,
and the init script creates the keys the modes check for."""

import re
import subprocess
from pathlib import Path

import yaml

from ppflx_bench.compare.registry import MODES

REPO = Path(__file__).resolve().parents[1]


def test_scripts_parse():
    for script in ("scripts/run_docker_compare.sh", "scripts/docker_init.sh"):
        subprocess.run(["bash", "-n", str(REPO / script)], check=True)


def test_compose_mounts_state_and_runs_as_the_caller():
    compose = yaml.safe_load((REPO / "compose.yaml").read_text())
    assert set(compose["services"]) == {"init", "bench"}
    for service in compose["services"].values():
        assert service["build"] == {"context": "..", "dockerfile": "ppflx-bench/Dockerfile"}
        assert service["user"] == "${PPFLX_UID:-1000}:${PPFLX_GID:-1000}"
        mounts = {v.split(":")[0] for v in service["volumes"]}
        assert mounts == {"./dataset", "./results", "./keys", "./.docker-state"}


def test_init_creates_every_key_a_mode_requires():
    init = (REPO / "scripts" / "docker_init.sh").read_text()
    created = set(re.findall(r"^generate (\S+)", init, re.M))
    required = {cfg.requires_key for cfg in MODES.values() if cfg.requires_key}
    assert required <= created


def test_image_leaves_out_local_state():
    ignore = (REPO / "Dockerfile.dockerignore").read_text().split()
    for path in ("ppflx-bench/dataset", "ppflx-bench/results", "ppflx-bench/keys",
                 "ppflx-bench/.docker-state", "ppflx/ppflx/keys/prebuilt/*", "**/.git"):
        assert path in ignore
