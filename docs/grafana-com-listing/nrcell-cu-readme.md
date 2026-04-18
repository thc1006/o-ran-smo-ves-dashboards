# VES NR cell CU measurement

Grafana dashboard for **NR cell CU** PM counters (3GPP TS 28.552) stored
in InfluxDB via O-RAN SC `nonrtric-plt-influxlogger`. Schema validated
end-to-end against `nexus3.o-ran-sc.org:10002/o-ran-sc/nonrtric-plt-pmlog:1.1.0`
on 2026-04-19.

## Panels

- **RRC Connection Establishment (attempts vs success) per cell** —
  `RRC.ConnEstabAtt.sum`, `RRC.ConnEstabSucc.sum` time series
- **RRC Connection Success Rate (last value)** — per-cell stat grid
  with thresholds at 90% (orange) and 98% (green)
- **NG Handover Execution (attempts vs success) per cell** —
  `NG.HOExeAtt`, `NG.HOExeSucc` time series
- **NG Handover Success Rate (last value)** — per-cell stat grid with
  thresholds at 95% (orange) and 99% (green)

## Templating

- `$subnetwork` — filter by SubNetwork
- `$gnb` — multi-select filter by ManagedElement

Both variables run `SHOW MEASUREMENTS` and extract DN components via
regex, so the dashboard is deployment-agnostic.

## Prerequisites

1. **InfluxDB 2.x** bucket populated by `nonrtric-plt-influxlogger`.
2. **v1 DBRP mapping** on the bucket (one-time):

       influx v1 dbrp create --db pm_data --rp autogen \
         --bucket-id <id> --default

   Without this, InfluxQL queries return HTTP 404 against InfluxDB 2.x.
3. **Grafana 12.0+** (dashboard schemaVersion 41).

## Troubleshooting

Success rate panels show values greater than 100%:
- The upstream data has `succ > att`, which is physically impossible.
  Check the PM source — real 3GPP PmReport counters always respect
  `ConnEstabSucc <= ConnEstabAtt` and `HOExeSucc <= HOExeAtt`.

Success rate panels show a single card instead of per-cell:
- The stat panel queries use `GROUP BY *` to preserve the per-measurement
  series dimension. If you modified the query, restore that clause.

Legend names render as literal `$1 / cell $2 ($3)`:
- Make sure your Grafana is 12.0+ — the rename is done via panel
  `renameByRegex` transformations, which require modern Grafana.

## Companion dashboard

**VES NR cell DU measurement** — PDCP volume, PRB usage, active UEs.
Same repo, same schema, imports independently.

## Source code & schema contract

- Repo: https://github.com/thc1006/o-ran-smo-ves-dashboards
- Schema ground-truth document (measurement / tag / field layout as
  emitted by nonrtric-plt-influxlogger):
  https://github.com/thc1006/o-ran-smo-ves-dashboards/blob/main/docs/schema-ground-truth-reference-2026-04-19-influxlogger-source.md

## License

Apache-2.0
