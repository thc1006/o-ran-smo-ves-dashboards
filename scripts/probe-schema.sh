#!/usr/bin/env bash
# Probe a running nonrtric-plt-influxlogger InfluxDB and record the actual
# schema (measurements, tag keys, field keys) that the upstream component
# produces after processing real VES traffic.
#
# Output: docs/schema-ground-truth-YYYY-MM-DD.md (not committed; excluded
# via .gitignore).
#
# Prerequisites:
# 1. kind/install-ranpm.sh has been run (or you point the env vars below
#    at a different reachable InfluxDB instance).
# 2. Some VES traffic has been sent; otherwise measurements will be empty.
#    Use scripts/seed-events.py first.
#
# Usage:
#   INFLUX_URL=http://localhost:8086 \
#   INFLUX_TOKEN=... \
#   INFLUX_ORG=nonrtric \
#   INFLUX_BUCKET=pm \
#   ./scripts/probe-schema.sh

set -euo pipefail

INFLUX_URL="${INFLUX_URL:-http://localhost:8086}"
INFLUX_TOKEN="${INFLUX_TOKEN:?set INFLUX_TOKEN}"
INFLUX_ORG="${INFLUX_ORG:-nonrtric}"
INFLUX_BUCKET="${INFLUX_BUCKET:-pm}"

DATE="$(date +%F)"
OUT="docs/schema-ground-truth-${DATE}.md"

echo ">>> probing ${INFLUX_URL} org=${INFLUX_ORG} bucket=${INFLUX_BUCKET}"

_query() {
    local q="$1"
    curl -fsSL -X POST "${INFLUX_URL}/api/v2/query?org=${INFLUX_ORG}" \
        -H "Authorization: Token ${INFLUX_TOKEN}" \
        -H "Content-Type: application/vnd.flux" \
        --data-binary "${q}"
}

mkdir -p docs
{
    echo "# Schema ground truth (probed ${DATE})"
    echo
    echo "Source: \`${INFLUX_URL}\`, org=\`${INFLUX_ORG}\`, bucket=\`${INFLUX_BUCKET}\`"
    echo
    echo "## Measurements"
    echo
    echo '```'
    _query "import \"influxdata/influxdb/schema\"
schema.measurements(bucket: \"${INFLUX_BUCKET}\")" || echo "(query failed)"
    echo '```'
    echo
    echo "## Tag keys per measurement (first 10 measurements)"
    echo
    echo '```'
    _query "import \"influxdata/influxdb/schema\"
schema.measurements(bucket: \"${INFLUX_BUCKET}\")
  |> limit(n: 10)
  |> map(fn: (r) => ({r with _value: schema.measurementTagKeys(
       bucket: \"${INFLUX_BUCKET}\", measurement: r._value
  )}))" 2>/dev/null || echo "(query failed)"
    echo '```'
    echo
    echo "## Field keys per measurement (first 10 measurements)"
    echo
    echo '```'
    _query "import \"influxdata/influxdb/schema\"
schema.measurements(bucket: \"${INFLUX_BUCKET}\")
  |> limit(n: 10)
  |> map(fn: (r) => ({r with _value: schema.measurementFieldKeys(
       bucket: \"${INFLUX_BUCKET}\", measurement: r._value
  )}))" 2>/dev/null || echo "(query failed)"
    echo '```'
    echo
    echo "## Notes"
    echo
    echo "- Run on $(uname -a)"
    # pytest-ves may not be installed when running this against a real
    # ranpm; fall back to "(unknown)" rather than failing the probe.
    PYTEST_VES_VERSION="$(pip show pytest-ves 2>/dev/null | awk -F': ' '/^Version:/ {print $2}')"
    echo "- pytest-ves version used for seeding: ${PYTEST_VES_VERSION:-(not installed)}"
} > "${OUT}"

echo ">>> wrote ${OUT}"
