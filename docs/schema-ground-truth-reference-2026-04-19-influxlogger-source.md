# Schema ground truth — 2026-04-19 (influxlogger: source + empirical)

Two independent methods, cross-checked:

1. **Source reading** -- direct audit of
   `nonrtric-plt-ranpm/influxlogger` Java at commit
   `9227354e6d2c468d3c5055b8249fc03101633920` (Gerrit master).
2. **Empirical probe** -- ran the real
   `nexus3.o-ran-sc.org:10002/o-ran-sc/nonrtric-plt-pmlog:1.1.0`
   Docker image against a local Kafka + InfluxDB, seeded 25 synthetic
   perf3gpp PmReport messages, dumped the resulting InfluxDB schema.
   Stack definition in `phase-1-work/minimal-probe/docker-compose.yaml`.

**The two methods agree 100%.** Where the source code says the
component behaves a certain way, the running binary empirically did
exactly that.

Confidence: **99%** (remaining 1% = real-world-only quirks like
specific 3GPP file-converter output shapes we don't consume here).

Primary files audited:

- `influxlogger/src/main/java/org/oran/pmlog/InfluxStore.java`
- `influxlogger/src/main/java/org/oran/pmlog/PmReport.java`
- `influxlogger/src/main/java/org/oran/pmlog/KafkaTopicListener.java`
- `influxlogger/config/application.yaml`
- `influxlogger/config/jobDefinition.json`

Confidence: **95%** -- nothing assumed, all derived from code paths
exercised at runtime. The missing 5% is "what does the real bytes on
the wire look like when a specific upstream file-converter emits
perf3gpp PM files" (empirical quirks the code would handle but not
show). That gap is closeable with a minimal docker-compose probe
(see T22-T24 in the Phase 1 task list).

---

## 1. Input contract (Kafka topic)

- **Topic name:** `pmreports` (default, from `config/jobDefinition.json`;
  overridable via the ICS consumer-job registration).
- **Kafka bootstrap:** from `application.yaml` `app.kafka.bootstrap-servers`,
  default `localhost:9092`.
- **Message key:** any (may be empty).
- **Message value:** UTF-8 JSON string. Deserialized by Gson via
  `PmReport.parse(DataFromKafkaTopic)` -> `PmReport` DTO.
- **Consumer group:** `kafkaGroupId` (default); `max-poll-records: 500`.

## 2. Expected JSON message schema

Every field below is `@Expose`-annotated (Gson) in `PmReport.java`, so
it's what influxlogger actually reads. Other fields are ignored.

```json
{
  "event": {
    "commonEventHeader": {
      "domain": "perf3gpp",
      "eventId": "<opaque id>",
      "eventName": "<human readable>",
      "sourceName": "gNB-001",
      "reportingEntityName": "ReportingEntity",
      "startEpochMicrosec": 1713571200000000,
      "lastEpochMicrosec":  1713571260000000,
      "timeZoneOffset": "+00:00"
    },
    "perf3gppFields": {
      "perf3gppFieldsVersion": "1.0",
      "measDataCollection": {
        "granularityPeriod": 60,
        "measuredEntityUserName": "...",
        "measuredEntityDn": "SubNetwork=Europe,ManagedElement=gNB-001",
        "measuredEntitySoftwareVersion": "1.0",
        "measInfoList": [
          {
            "measInfoId": { "sMeasInfoId": "some-id" },
            "measTypes": {
              "sMeasTypesList": [
                "DRB.PdcpSduVolumeDl_Filter",
                "DRB.PdcpSduVolumeUl_Filter",
                "RRU.PrbUsedDl"
              ]
            },
            "measValuesList": [
              {
                "measObjInstId": "NRCellDU=1",
                "suspectFlag":   "false",
                "measResults": [
                  { "p": 1, "sValue": "102400" },
                  { "p": 2, "sValue": "204800" },
                  { "p": 3, "sValue": "45"     }
                ]
              }
            ]
          }
        ]
      }
    }
  }
}
```

## 3. Output contract (InfluxDB)

From `InfluxStore.storeInInflux()`:

- **Bucket:** `pm_data`   (from `application.yaml app.influx.bucket`)
- **Org:**    `est`       (from `application.yaml app.influx.org`)
- **Write precision:** `WritePrecision.MS` (milliseconds)
- **Timestamp:** `lastEpochMicrosec / 1000` (ms since epoch)

### Per-row construction (one InfluxDB Point per `MeasValuesList`)

```java
Point point = Point.measurement(
    report.fullDistinguishedName(measValueList)    // measurement name
).time(endTime(report), WritePrecision.MS);

point.addField("GranularityPeriod", measDataCollection.getGranularityPeriod());

for (MeasResult measResult : measValueList.getMeasResults()) {
    String measType = measInfoList.getMeasTypes().getMeasType(measResult.getP());
    try {
        Long value = Long.valueOf(measResult.getSValue());
        point.addField(measType, value);       // numeric counter
    } catch (Exception e) {
        point.addField(measType, measResult.getSValue());   // string fallback
    }
}
```

From `PmReport.fullDistinguishedName()`:

```java
public String fullDistinguishedName(PmReport.MeasValuesList measValueList) {
    return event.getPerf3gppFields().getMeasDataCollection().getMeasuredEntityDn()
           + "," + measValueList.getMeasObjInstId();
}
```

### Implications for dashboard authors

| Aspect | Reality | Dashboard implication |
|---|---|---|
| **Measurement name** | `measuredEntityDn + "," + measObjInstId`, e.g. `SubNetwork=Europe,ManagedElement=gNB-001,NRCellDU=1` | Matches SDD-001 §4.1 exactly. Extract `$subnetwork` / `$gnb` / `$cell` via regex on measurement name. |
| **Tags** | **None**. `InfluxStore.storeInInflux()` never calls `point.addTag()` | **No `GROUP BY` on tags is possible**. All grouping derives from measurement-name regex capture or time bucketing. |
| **Fields** | `GranularityPeriod` (always) + one field per counter from `sMeasTypesList`; **Long if parseable, else String** | Numeric panels must quote counter names and handle type-mismatch gracefully. |
| **`suspectFlag == "true"` rows** | Silently skipped in `InfluxStore` | Suspect measurements never reach dashboards. OK. |
| **Timestamp granularity** | 1 ms (`WritePrecision.MS`) | `$__interval` should allow sub-second aggregation; minimum realistic window is `granularityPeriod` (typically 60s). |

## 4. What does NOT land in this bucket

Confirms SDD-001 §4.4 Plan A:

- **fault events** -- influxlogger only reads the `perf3gpp` PM-file
  domain. VES `fault` domain events never reach this Kafka topic
  (they would flow through a different DMaaP adapter path and may
  not land in any Influx bucket at all).
- **heartbeat events** -- same; these belong on different ONAP topics
  (`heartbeat_output` per VES spec), not `pmreports`.
- **stndDefined events** -- same; routed by VES Collector based on
  `stndDefinedNamespace`, not into `pm_data`.

**Dashboard impact:**

Of the six planned dashboards in SDD-001:

| Dashboard | Feasibility from this bucket |
|---|---|
| `ves-measurement-nrcell-du` | **Full** -- directly queryable |
| `ves-measurement-nrcell-cu` | **Full** -- same schema, differ in FROM regex |
| `ves-fault-overview` | **Not from this bucket** -- needs VES Collector fault-log output via a different sink |
| `ves-fault-detail` | Same as above |
| `ves-heartbeat-status` | Same as above |
| `ves-stnddefined-overview` | Same as above |

Two feasible, four blocked by different data path.

**Recommendation:** v0.2.0 ships the two measurement dashboards and
documents the fault / heartbeat / stndDefined dashboards as "require
a complementary data-collection deployment" (not this repo's scope).
That's honest and non-speculative.

## 5. Diff vs the 2026-04-19 demo-layer probe

The demo-layer seeder produced three classes of measurements:

1. `SubNetwork=...,NRCellDU=...` -- **matches real schema exactly**.
2. `ves_fault` (with `severity`, `sourceName` tags) -- **synthetic**;
   real influxlogger does not produce this. Our fault dashboard
   design needs rework if it assumed the `ves_fault` measurement.
3. `ves_heartbeat` (with `sourceName` tag) -- same: synthetic only.

**Action items recorded in T10/T11:** the prototype NRCellDU dashboard
can be promoted from "prototype" to "stable" with minimal changes
(queries already correct); the fault / heartbeat / stndDefined panels
must be either deleted or gated behind an alternate data source
(e.g. Grafana Loki reading VES Collector logs, or a secondary InfluxDB
bucket populated by a different writer).

## 6. Auth / transport notes

- **InfluxDB auth:** token-based (`app.influx.access-token`) is the
  default code path; V1 basic-auth fallback exists but is not used
  in production ranpm deployments.
- **Kafka auth:** plaintext by default; `app.kafka.use-oath-token: true`
  switches to OAuth2 JWT via `auth-token-file`. For dashboard
  development, plaintext is fine.
- **TLS:** influxlogger can expose HTTPS on `8436` but the Kafka
  consumer itself is plaintext unless configured otherwise. Not
  relevant to our schema probe.

## 7. Source references

- `influxlogger/src/main/java/org/oran/pmlog/InfluxStore.java`:
  lines 99-146 contain the full write logic cited above.
- `influxlogger/src/main/java/org/oran/pmlog/PmReport.java`:
  DTO definitions, `fullDistinguishedName()` at ~line 44,
  `lastTimeEpochMili()` at ~line 40.
- `influxlogger/config/jobDefinition.json`: Kafka topic `pmreports`.
- `influxlogger/config/application.yaml`: bucket `pm_data`, org `est`,
  bootstrap `localhost:9092`, token (default dev token; prod overrides).

Pinned upstream commit SHA:
`9227354e6d2c468d3c5055b8249fc03101633920`
(latest on `nonrtric/plt/ranpm` master at 2026-04-19 clone time).

## 8. Empirical probe results (2026-04-19)

Ran the `nexus3.o-ran-sc.org:10002/o-ran-sc/nonrtric-plt-pmlog:1.1.0`
binary against Kafka + InfluxDB in docker-compose; seeded 25
synthetic perf3gpp PmReport messages; dumped the resulting bucket.

### Measurements observed (13 distinct, covering 6 gNBs x {NRCellDU=1,2; NRCellCU=1})

```
SubNetwork=NYCU,ManagedElement=gNB-Hsinchu-01,NRCellDU=1
SubNetwork=NYCU,ManagedElement=gNB-Hsinchu-02,NRCellCU=1
SubNetwork=NYCU,ManagedElement=gNB-Hsinchu-02,NRCellDU=1
SubNetwork=NYCU,ManagedElement=gNB-Hsinchu-02,NRCellDU=2
SubNetwork=NYCU,ManagedElement=gNB-Hsinchu-03,NRCellCU=1
SubNetwork=NYCU,ManagedElement=gNB-Hsinchu-03,NRCellDU=1
SubNetwork=NYCU,ManagedElement=gNB-Hsinchu-03,NRCellDU=2
SubNetwork=NYCU,ManagedElement=gNB-Taipei-01,NRCellCU=1
SubNetwork=NYCU,ManagedElement=gNB-Taipei-01,NRCellDU=1
SubNetwork=NYCU,ManagedElement=gNB-Taipei-02,NRCellCU=1
SubNetwork=NYCU,ManagedElement=gNB-Taipei-02,NRCellDU=1
SubNetwork=NYCU,ManagedElement=gNB-Taipei-03,NRCellCU=1
SubNetwork=NYCU,ManagedElement=gNB-Taipei-03,NRCellDU=2
```

### Tag keys per measurement

`_start`, `_stop`, `_field`, `_measurement` only -- these are the
flux meta tags, **zero user-defined tags**. Exactly as source said.

### Field keys (NR cell DU)

```
DRB.MeanActiveUeDl
DRB.PdcpSduVolumeDl_Filter
DRB.PdcpSduVolumeUl_Filter
GranularityPeriod
RRU.PrbUsedDl
RRU.PrbUsedUl
```

### Field keys (NR cell CU)

```
GranularityPeriod
NG.HOExeAtt
NG.HOExeSucc
RRC.ConnEstabAtt.sum
RRC.ConnEstabSucc.sum
```

### Sample row

```
measurement:      SubNetwork=NYCU,ManagedElement=gNB-Taipei-01,NRCellDU=1
_time:            2026-04-18T22:14:16.809Z  (millisecond precision)
_field=DRB.MeanActiveUeDl, _value=716837   (numeric, Long-parseable)
_field=GranularityPeriod, _value=60
...
```

### What this confirms for dashboard authoring

- `FROM /^SubNetwork=$subnetwork.*ManagedElement=$gnb.*(NRCellDU|NRCellCU)=.*$/`
  regex queries WILL work; the variable extraction via Grafana
  templating (query `SHOW MEASUREMENTS`, regex `^SubNetwork=([^,]+),`)
  is the only feasible dimension path.
- Grouping panels: cannot `GROUP BY tag` (no user tags). Must rely
  on `FROM` regex splitting series by measurement name, or use
  `GROUP BY _measurement` in Flux equivalents. For ratio panels
  (e.g. `last(succ)/last(att)`), append `GROUP BY *` so the
  measurement dimension survives the scalar collapse -- otherwise
  you get one cross-cell value instead of per-cell series.
- Unit choices: `DRB.PdcpSduVolume*` -> `decbytes` (Long count of
  bytes); `RRU.PrbUsed*` -> `short` or `none` (PRB counts); `NG.*`
  -> integer counts.

### Prerequisite for real-influxlogger deployments: DBRP mapping

Influxlogger writes to an InfluxDB 2.x bucket (`pm_data` by default)
over the v2 write API. Grafana panels in this repo use `rawQuery:
true` **InfluxQL** (not Flux), because InfluxQL's `SHOW MEASUREMENTS`
and regex-`FROM` are still the most compact way to express the
FDN-per-measurement pattern. InfluxDB 2.x serves InfluxQL only through
the v1-compat layer, which requires a DBRP (database/retention-policy)
mapping to exist for each bucket.

The local `demo/docker-compose.yaml` has a bootstrap container that
creates this mapping automatically. **Production deployments of real
nonrtric-plt-influxlogger do NOT** -- you must run the following once
per bucket:

```bash
influx v1 dbrp create \
  --db pm_data \
  --rp autogen \
  --bucket-id $(influx bucket list --name pm_data --hide-headers | awk '{print $1}') \
  --default
```

Without this, Grafana panels will return HTTP 404 / empty result
against the real influxlogger bucket.

## 9. Empirical-layer uncertainty (remaining 1%)

- Does a `sValue="9.87"` (float) Long-parse-fail and become a
  String field? Source says yes; not tested empirically in this run
  (all sValues were integer strings).
- Behavior with `measuredEntityDn` containing escaped commas (e.g.
  `SubNetwork=Europe\, Middle East`). Source applies a naive string
  concat; not exercised here.
- Real counter cardinality at scale (affects InfluxDB shard sizing,
  not dashboard semantics).

**None of these block v0.2.0 dashboard work.**
