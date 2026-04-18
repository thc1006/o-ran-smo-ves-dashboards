# Schema ground truth — 2026-04-19 (demo-layer run)

## Probe context

- **Date:** 2026-04-19
- **Source:** `demo/docker-compose.yaml` InfluxDB 2.7.12
- **NOT** a probe of the real `nonrtric-plt-influxlogger`. This is the
  schema that our own `scripts/seed-events.py` writes. **A proper Phase 1
  probe against the upstream component is still pending** and tracked in
  SDD-001 §9.1.

  What this run does prove:
  - The toolchain (pytest-ves -> seeder -> InfluxDB -> Grafana) is
    fully working end-to-end.
  - The schema shape that SDD-001 §4.1 predicted for influxlogger
    (measurement = resource Full DN, field = counter name) is achievable
    and queryable. Dashboard authoring against it is tractable.

- **Seeder:** `pytest-ves==0.2.0` via `scripts/seed-events.py --count 200 --rate 0`
- **Bucket:** `ves` (org `winlab`)
- **Total points written:** 600 (200 each for measurement, heartbeat, fault)

## Measurements observed

11 distinct measurement names.

### (a) NR cell DU counters — 9 measurements

Names take the form of the resource Full Distinguished Name:

```
SubNetwork=NYCU,ManagedElement=gNB-Taipei-01,NRCellDU=1
SubNetwork=NYCU,ManagedElement=gNB-Taipei-02,NRCellDU=1
SubNetwork=NYCU,ManagedElement=gNB-Taipei-03,NRCellDU=1
SubNetwork=NYCU,ManagedElement=gNB-Hsinchu-01,NRCellDU=2
SubNetwork=NYCU,ManagedElement=gNB-Hsinchu-02,NRCellDU=2
SubNetwork=NYCU,ManagedElement=gNB-Hsinchu-03,NRCellDU=2
SubNetwork=NYCU,ManagedElement=gNB-Keelung-01,NRCellDU=1
SubNetwork=NYCU,ManagedElement=gNB-Keelung-02,NRCellDU=1
SubNetwork=NYCU,ManagedElement=gNB-Keelung-03,NRCellDU=1
```

Confirmed: **measurement name IS the FDN** (commas and equals signs and
all). This matches the upstream `nonrtric-plt-influxlogger` documentation.

#### Tag keys
_None user-defined._ Only the Flux meta tags (`_start`, `_stop`, `_field`,
`_measurement`) appear. For dashboard `GROUP BY`, this means we must
derive groupings from the measurement name itself (regex extraction on
`_measurement`).

**Dashboard implication:** `$subnetwork`, `$gnb`, `$cell` variables must
be extracted via regex capture groups from the measurement name pattern
``SubNetwork=([^,]+),ManagedElement=([^,]+),NRCellDU=([^,]+)``.

#### Field keys (5, all float)

```
DRB.MeanActiveUeDl
DRB.PdcpSduVolumeDl_Filter
DRB.PdcpSduVolumeUl_Filter
RRU.PrbUsedDl
RRU.PrbUsedUl
```

These follow 3GPP TS 28.552 counter naming and represent a minimal but
realistic subset. Real `nonrtric-plt-influxlogger` will expose many more
counters per the PM file contents.

### (b) `ves_fault` — 1 measurement

#### Tag keys
```
severity
sourceName
```

#### Field keys
```
alarmCondition
specificProblem
```

**Dashboard implication:** fault panels can `GROUP BY severity, sourceName`
directly without regex tricks. **Caveat:** the real
`nonrtric-plt-influxlogger` is scoped to PM only; whether fault events land
here at all is an open question (SDD-001 §4.4 Plan A/B/C). Our seeder
decided to write them to a dedicated measurement name because that's the
simplest way to make fault dashboards queryable from the same bucket.

### (c) `ves_heartbeat` — 1 measurement

#### Tag keys
```
sourceName
```

#### Field keys
```
heartbeatInterval
```

**Dashboard implication:** a missed-heartbeat detector is cheap: group
by `sourceName` and compare `_time` to `now()`.

## Sample row (actual query output)

```
,_result,0,2026-04-18T16:53:19Z,2026-04-18T17:53:19Z,2026-04-18T17:51:52.188Z,184305.17,DRB.MeanActiveUeDl,"SubNetwork=NYCU,ManagedElement=gNB-Taipei-01,NRCellDU=1"
```

Shape: `start, stop, time, value, field, measurement`.

## Verified end-to-end

- InfluxDB 2.7.12 accepts line-protocol writes via `influxdb-client` Python.
- Grafana 12.2.0 is healthy and auto-provisioned the `InfluxDB-VES` datasource
  (UID `PE7195F5C1213A95D`) via `demo/grafana-provisioning/datasources/`.
- Datasource HTTP mode = `GET`, `InfluxQL` version set per SDD-001 D1
  (InfluxQL chosen over Flux because InfluxDB 3 Core deprecates Flux).

## Open questions (for Phase 1 real-influxlogger probe)

1. Do fault / heartbeat / stndDefined events land in the SAME bucket as
   measurement events? Our demo writes them to separate synthetic
   measurements; real influxlogger focuses on PM and may ignore these
   domains entirely.
2. Are there additional Influx tags injected by influxlogger that the
   seeder does not mimic (e.g. a `granularityPeriod` tag derived from
   `collectionBeginTime` / `collectionEndTime`)?
3. What's the default retention policy and shard-group duration?
4. How are counter arrays (measurement fields like CPU usage per instance)
   mapped to Influx — do they become multiple measurements, multiple
   fields with index suffix, or a single JSON-encoded field?

These cannot be answered from demo data; they require the kind + ranpm
install described in `kind/install-ranpm.sh`.

## Proceed-with-caution note

Dashboards built against this demo-layer schema should be clearly marked
as **prototypes** rather than as production-ready. They will likely need
query adjustments once the real influxlogger schema is probed. The value
right now is twofold:

- Prove Grafana JSON can target the expected shape.
- Give contributors something to iterate UX/UI on before Phase 1 unblocks.
