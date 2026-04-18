#!/usr/bin/env bash
# Bring up a kind cluster and install O-RAN SC nonrtric-plt-ranpm +
# influxlogger end-to-end, so scripts/probe-schema.sh has something to
# point at.
#
# This is the "heavy" layer; budget ~15-20 minutes + ~4 GB of container
# images on first run.
#
# Manual reference:
#   https://docs.o-ran-sc.org/projects/o-ran-sc-nonrtric-plt-ranpm/en/latest/
#
# Assumes: kind, kubectl, helm, curl are installed.

set -euo pipefail

CLUSTER_NAME="o-ran-smo"
KIND_CONFIG="$(dirname "$0")/cluster.yaml"

need() {
    command -v "$1" >/dev/null 2>&1 \
        || { echo "ERROR: $1 not installed or not on PATH"; exit 1; }
}

need kind
need kubectl
need helm
need curl

if kind get clusters | grep -qx "${CLUSTER_NAME}"; then
    echo ">>> kind cluster '${CLUSTER_NAME}' already exists"
else
    echo ">>> creating kind cluster"
    kind create cluster --name "${CLUSTER_NAME}" --config "${KIND_CONFIG}"
fi

# O-RAN SC publishes ranpm install scripts at:
#   https://gerrit.o-ran-sc.org/r/gitweb?p=nonrtric/plt/ranpm.git
# Rather than vendor them, point users at the canonical install
# instructions. When you clone the ranpm repo, the sequence is:
#
#   cd nonrtric-plt-ranpm/install
#   edit helm/global-values.yaml
#   ./install-ranpm.sh
#
# After that completes, scripts/probe-schema.sh should find the
# influxlogger-backed InfluxDB at the NodePort mapped above.

cat <<'EOF'

>>> kind cluster is up.

Next step -- install ranpm into this cluster:

    git clone "https://gerrit.o-ran-sc.org/r/nonrtric/plt/ranpm"
    cd nonrtric-plt-ranpm/install
    # Review helm/global-values.yaml (image registry, storage class)
    ./install-ranpm.sh

Then seed VES events:
    python scripts/seed-events.py --influx-url http://localhost:30001 ...

Then probe the schema:
    INFLUX_TOKEN=... ./scripts/probe-schema.sh

EOF
