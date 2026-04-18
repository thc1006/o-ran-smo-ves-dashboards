# o-ran-smo-ves-dashboards

Grafana dashboard pack for O-RAN SMO VES events stored in InfluxDB via
`nonrtric-plt-influxlogger`. Covers the four SMO-relevant VES 7.2.1 domains
(fault, measurement, heartbeat, stndDefined) that the Prometheus/KPM path
does **not** already serve.

**Status:** **v0.1.0 — repo skeleton + kind-based schema probing harness**.
Dashboard JSON files are intentionally empty until the probe of a real
`nonrtric-plt-influxlogger` InfluxDB instance produces the ground-truth
schema (measurement names, tag keys, field keys). See
`docs/SDD-001-design.md` §9.1 for the exit criterion of Phase 1.

## Why this exists

Search results as of 2026-04-19:

- `grafana.com/grafana/dashboards/22297` — OAI 5G para: Prometheus path only.
- NIST `O-RAN-Testbed-Automation`, OpenRAN Gym, BubbleRAN — KPM xApp
  dashboards via Prometheus / VictoriaMetrics.
- Aarna AMCOP — commercial SMO dashboard (closed source).
- LFN 5G Super Blueprint — results dashboard still WIP.
- No public Grafana dashboard targeting the `nonrtric-plt-influxlogger`
  InfluxDB schema for VES domain events.

This pack fills that gap. Not the Prometheus/KPM gap — that's already served.

## Planned dashboard catalogue

| File | Domain | Purpose |
|---|---|---|
| `dashboards/fault/ves-fault-overview.json` | fault | active alarms by severity / source; alarm aging |
| `dashboards/fault/ves-fault-detail.json` | fault | per-alarm-condition affected resources + time series |
| `dashboards/measurement/ves-measurement-nrcell-du.json` | measurement | NR cell DU PM counters (3GPP TS 28.552) |
| `dashboards/measurement/ves-measurement-nrcell-cu.json` | measurement | NR cell CU PM counters |
| `dashboards/heartbeat/ves-heartbeat-status.json` | heartbeat | sourceName last-seen + missed-heartbeat detector |
| `dashboards/stnddefined/ves-stnddefined-overview.json` | stndDefined | routing by stndDefinedNamespace |

## How to help right now (Phase 1 blocker)

The single most valuable contribution is a **dump of the actual InfluxDB
schema** that `nonrtric-plt-influxlogger` produces after it has processed
real VES traffic. Run `scripts/probe-schema.sh` against a kind cluster that
has `nonrtric-plt-ranpm` installed, and file the resulting
`docs/schema-ground-truth.md` as a PR.

Until that PR lands, dashboard authoring is blocked on guesswork.

## Local development layers

### Layer 0 -- offline, no network

```bash
# Verifies dashboard JSON schema compliance against Grafana's schema.
# (Added once we have dashboards to validate.)
```

### Layer 1 -- light local dev (docker-compose; no kind; no ranpm)

```bash
cd demo
docker compose up -d         # influxdb + dbrp-bootstrap + grafana
# open Grafana  http://localhost:3000 (admin / admin)
# open InfluxDB http://localhost:8086

# Seed fake VES events directly into InfluxDB using pytest-ves:
pip install -r ../scripts/requirements.txt
python ../scripts/seed-events.py --count 500 --rate 10
```

After the seeder finishes, open Grafana and browse the `VES` folder. The
`ves-nrcell-du-proto` dashboard should render data on its 4 panels.

This layer is good for iterating on dashboard visuals. It is **not**
representative of the real `nonrtric-plt-influxlogger` schema; Phase 1
(Layer 2 below) addresses that. See
`docs/schema-ground-truth-reference-2026-04-19-demo.md` for the exact
schema the dashboard targets right now.

### Layer 2 -- kind + real nonrtric-plt-ranpm (heavy, for schema probing)

```bash
./kind/install-ranpm.sh            # kind cluster + full ranpm stack
./scripts/probe-schema.sh          # dump SHOW MEASUREMENTS / FIELDS / TAGS
```

The probe writes `docs/schema-ground-truth-<date>.md` summarising what
measurements, tags, and fields appear in InfluxDB after we send sample
VES events via pytest-ves.

## Sister project

`pytest-ves` (PyPI, Apache-2.0) is used by this repo's seeder and probe
scripts to emit VES 7.2.1 events. That project is maintained separately;
see https://github.com/thc1006/pytest-ves (TBD).

## License

Apache-2.0.
