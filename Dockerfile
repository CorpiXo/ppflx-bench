# The benchmark in a container: the proof service, ppflx and this harness.
#
# Built from the directory that holds the three checkouts side by side (the
# layout in README.md, "Benchmark on a new machine"), so the image runs whatever
# is checked out there:
#
#   ppflx/  gnark-gradient-prover/  ppflx-bench/
#
# compose.yaml sets that context; scripts/run_docker_compare.sh builds and runs it.
# Keys, datasets and results are mounted at run time, never copied in.

FROM golang:1.26-bookworm AS prover
WORKDIR /src
COPY gnark-gradient-prover/go.mod gnark-gradient-prover/go.sum ./
RUN go mod download
COPY gnark-gradient-prover/*.go ./
RUN CGO_ENABLED=0 go build -o /out/gnark_service .

# Every Python package as a wheel. Some of Concrete ML's dependencies (onnxoptimizer)
# have no wheel for Python 3.12 and compile from source, which needs cmake and a
# compiler; they stay in this stage.
FROM python:3.12-bookworm AS wheels
RUN apt-get update \
 && apt-get install -y --no-install-recommends cmake \
 && rm -rf /var/lib/apt/lists/*
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
# The CPU build of torch: the benchmark runs on CPU, and it is a much smaller download.
RUN pip wheel --no-deps --wheel-dir /wheels --index-url https://download.pytorch.org/whl/cpu \
      torch==2.3.1+cpu torchvision==0.18.1+cpu
COPY ppflx /src/ppflx
COPY ppflx-bench/requirements.txt /tmp/requirements.txt
# ppflx comes from the checkout above, not from git.
RUN { echo "torch==2.3.1+cpu"; echo "torchvision==0.18.1+cpu"; echo "ppflx[tfhe]"; echo "pytest"; \
      grep -v '^ppflx' /tmp/requirements.txt; } > /wheels/requirements-image.txt \
 && CMAKE_BUILD_PARALLEL_LEVEL=$(nproc) pip wheel --wheel-dir /wheels --find-links /wheels \
      /src/ppflx -r /wheels/requirements-image.txt

FROM python:3.12-slim-bookworm
# libgomp: OpenMP runtime for the Concrete (TFHE) and TenSEAL native libraries.
# binutils: Concrete links each compiled TFHE circuit into a shared library with `ld`.
RUN apt-get update \
 && apt-get install -y --no-install-recommends libgomp1 binutils \
 && rm -rf /var/lib/apt/lists/*
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN --mount=type=bind,from=wheels,source=/wheels,target=/wheels \
    pip install --no-index --find-links /wheels -r /wheels/requirements-image.txt

COPY --from=prover /out/gnark_service /usr/local/bin/gnark_service
COPY ppflx-bench /app/ppflx-bench
WORKDIR /app/ppflx-bench
# Runs use any uid. Concrete writes debug artifacts (.artifacts/) into the working
# directory when a compilation fails; without write access that error is hidden.
RUN chmod 1777 /app/ppflx-bench

# State the runs write lives under /state (mounted); HOME is writable for any user.
ENV FL_GNARK_BINARY=/usr/local/bin/gnark_service \
    FL_ZKP_KEYS_DIR=/state/zkp/keys \
    FL_ZKP_PK_DIR=/state/zkp/pk \
    FL_CONCRETE_TFHE_KEYS_DIR=/state/tfhe \
    HOME=/tmp \
    PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg \
    FLWR_TELEMETRY_ENABLED=0 \
    FLWR_DISABLE_UPDATE_CHECK=1 \
    FLWR_DISABLE_RUNTIME_DEPENDENCY_INSTALLATION=1

CMD ["python", "compare.py", "--help"]
