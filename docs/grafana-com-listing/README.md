# grafana.com listing boilerplate

Ready-to-paste text fields for the
<https://grafana.com/profile/org/dashboards?pg=dashboards&plcmt=usr-upload>
form, one file per form field, one set per dashboard.

| Form field | File |
|---|---|
| Collector / Agent Details (shared by both dashboards) | `collector-agent.md` |
| README (NRCellDU dashboard) | `nrcell-du-readme.md` |
| README (NRCellCU dashboard) | `nrcell-cu-readme.md` |

Screenshots:

- NRCellDU upload → `../screenshots/ves-nrcell-du-overview.png`
- NRCellCU upload → `../screenshots/ves-nrcell-cu-overview.png`

Suggested form values for the other fields:

| Field | Value |
|---|---|
| Category | `Hostmetrics` (closest fit; no Networking / Telecom category exists in the grafana.com catalogue) |
| Data source | `InfluxDB` |
| Logo | leave blank |
| Tags (NRCellDU) | `o-ran, 5g, influxdb, ves, nonrtric, perf3gpp, nrcell-du, pm-counters` |
| Tags (NRCellCU) | `o-ran, 5g, influxdb, ves, nonrtric, perf3gpp, nrcell-cu, rrc, handover` |
| Source code URL | `https://github.com/thc1006/o-ran-smo-ves-dashboards` |

After each dashboard is approved grafana.com assigns a 5-digit numeric ID
and a public URL like `https://grafana.com/grafana/dashboards/<ID>`.
Record those IDs in the top-level README's "Using on grafana.com" section
to close the loop back to this repo.
