# Schema ground truth (TEMPLATE)

Use this as the target output shape of `scripts/probe-schema.sh`. Populate
a dated copy (`schema-ground-truth-YYYY-MM-DD.md`) after running the probe
against a real `nonrtric-plt-influxlogger` instance.

---

## Probe context

- Date: `YYYY-MM-DD`
- nonrtric-plt-ranpm version: `x.y.z` (`docker images | grep ranpm`)
- nonrtric-plt-influxlogger version: `x.y.z`
- InfluxDB version: `2.x` or `3.x-core`
- pytest-ves version used to seed: `x.y.z`
- VES events sent: fault=<n>, heartbeat=<n>, measurement=<n>

## Measurements

List one measurement name per line. The official spec says each distinct
resource Full DN becomes a separate measurement, so expect cardinality
matching the number of distinct sources in your seed.

```
SubNetwork=...,ManagedElement=...,NRCellDU=...
...
```

## Tags per measurement

For each measurement above, list tag keys. Tags are the dimensions you can
`GROUP BY` in Grafana.

| Measurement | Tag keys |
|---|---|
| `SubNetwork=..., NRCellDU=1` | `sourceName, granularityPeriod, ...` |

## Fields per measurement

For each measurement above, list field keys and their inferred type. Fields
are the numeric counters you chart.

| Measurement | Field keys (type) |
|---|---|
| `SubNetwork=..., NRCellDU=1` | `DRB.PdcpSduVolumeDl_Filter (float), RRU.PrbUsedDl (float), ...` |

## Domain coverage

Fill in once probed:

- [ ] `fault` domain events land in InfluxDB? If yes, where?
- [ ] `heartbeat` domain events land in InfluxDB? If yes, where?
- [ ] `stndDefined` events land in InfluxDB? If yes, which namespaces?

The answer to these dictates whether `ves-fault-overview.json` and
`ves-heartbeat-status.json` can be built straight from this bucket (Path A
in SDD-001 §4.4) or whether we need a sidecar writer (Paths B/C).

## Retention / shard policies

- Default retention seen: `...`
- Shard group duration: `...`

## Open questions

- ...

## Implications for dashboard authoring

- Variable definitions that should be derived from this schema:
  - `$subnetwork`: query `SHOW TAG VALUES ON "ves" WITH KEY = "SubNetwork"`
  - `$cell`: depends on tag layout; may need regex-extracted from measurement name
- PM counter panels can use InfluxQL ``SELECT LAST("DRB...") FROM "<FDN>"
  WHERE $__timeFilter GROUP BY time($__interval)`` once field names are known.
