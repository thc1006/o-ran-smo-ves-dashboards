  # VES NR cell DU measurement

  Grafana dashboard for **NR cell DU** PM counters (3GPP TS 28.552) stored
  in InfluxDB via O-RAN SC `nonrtric-plt-influxlogger`. Schema validated
  end-to-end against `nexus3.o-ran-sc.org:10002/o-ran-sc/nonrtric-plt-pmlog:1.1.0`
  on 2026-04-19.

  ## Panels

  - **PDCP Downlink Volume** — `DRB.PdcpSduVolumeDl_Filter` per cell
  - **PRB Usage DL / UL** — `RRU.PrbUsedDl` / `RRU.PrbUsedUl` per cell
  - **Active UEs per cell (last value)** — `DRB.MeanActiveUeDl` stat grid

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

  Panels show "No data":
  - Confirm the bucket contains measurements matching
    `^SubNetwork=.*,ManagedElement=.*,NRCellDU=.*$`.
  - Verify the DBRP mapping exists: `influx v1 dbrp list`.

  Legend names render as literal `$1 / cell $2`:
  - Make sure your Grafana is 12.0+ — the per-cell rename is done via
    panel transformations (`renameByRegex`), which capture-group
    substitution requires modern Grafana. Older versions' field override
    `displayName` does not evaluate `$1` / `$2`.

  ## Companion dashboard

  **VES NR cell CU measurement** — RRC connection establishment and NG
  handover execution success rates. Same repo, same schema, imports
  independently.

  ## Source code & schema contract

  - Repo: https://github.com/thc1006/o-ran-smo-ves-dashboards
  - Schema ground-truth document (measurement / tag / field layout as
    emitted by nonrtric-plt-influxlogger):
    https://github.com/thc1006/o-ran-smo-ves-dashboards/blob/main/docs/schema-ground-truth-reference-2026-04-19-influxlogger-source.md

  ## License

  Apache-2.0
