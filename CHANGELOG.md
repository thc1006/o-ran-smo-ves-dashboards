# Changelog

## [Unreleased]

## [0.2.0] - 2026-04-19

### Added
- `dashboards/measurement/ves-measurement-nrcell-du.json` -- promoted
  from prototype to stable. Queries validated end-to-end against real
  `nonrtric-plt-pmlog:1.1.0` via the `phase-1-work/minimal-probe` stack
  (Kafka 3.9 KRaft -> pmlog -> InfluxDB 2.7). Panels: PDCP DL volume,
  PRB usage DL/UL, active UEs per cell.
- `dashboards/measurement/ves-measurement-nrcell-cu.json` -- new. Four
  panels for NRCellCU PM counters: RRC connection establishment
  (attempts vs success + success-rate stat) and NG handover execution
  (attempts vs success + success-rate stat).
- `docs/schema-ground-truth-reference-2026-04-19-influxlogger-source.md`
  -- canonical schema contract: measurement = full DN
  `SubNetwork=...,ManagedElement=...,<cell>=...`, no user tags, fields
  are `GranularityPeriod` plus the raw perf3gpp counter names. Source
  audit (InfluxStore.storeInInflux) + empirical probe agree 100%
  (confidence 99%).

### Changed
- README "light local dev" section now points at the stable dashboard
  uids (`ves-nrcell-du`, `ves-nrcell-cu`) and at the influxlogger-source
  schema doc; demo-layer caveat removed.
- CI `Dashboard loads in Grafana` check updated to look for
  `ves-nrcell-du` (was `ves-nrcell-du-proto`).

### Removed
- `dashboards/measurement/ves-measurement-nrcell-du-prototype.json` --
  superseded by the stable `ves-measurement-nrcell-du.json`.

### Scope note
- Dashboards for fault / heartbeat / stndDefined event domains are
  deliberately out of scope for influxlogger: the service only consumes
  perf3gpp PM data, so those events never reach the `pm_data` bucket.
  Visualising them belongs to a different downstream (tracked for a
  future `ves-dmaap-dashboards` spin-off if demand appears).

## [0.1.0] - 2026-04-19

### Added
- Repo skeleton (Apache-2.0, docs/, scripts/, demo/, dashboards/, kind/).
- SDD-001 imported from winlab-o1ves/design/; tracked here as canonical.
- `demo/docker-compose.yaml` -- minimal InfluxDB 2.x + Grafana 12 stack
  for dashboard iteration without kind dependency.
- `demo/grafana-provisioning/datasources/influxdb.yaml` -- auto-provision
  InfluxDB datasource when Grafana starts.
- `scripts/seed-events.py` -- Python seeder using pytest-ves; emits
  VES 7.2.1 events and writes as InfluxDB line-protocol points that mirror
  the expected `nonrtric-plt-influxlogger` schema (measurement = Full DN,
  field per counter).
- `scripts/probe-schema.sh` -- harness that dumps InfluxDB measurements /
  tags / fields from a real `nonrtric-plt-influxlogger` instance to a
  dated Markdown file.
- `kind/cluster.yaml` + `kind/install-ranpm.sh` -- one-shot installers
  for a local O-RAN SC Non-RT RIC `ranpm` + `influxlogger` stack.
- `docs/schema-ground-truth-TEMPLATE.md` -- output template for probe
  results, to be filled in once Phase 1 completes.

### Deliberately NOT in v0.1.0
- Actual dashboard JSON files. These are blocked on the Phase 1 schema
  probe (see SDD-001 §9.1). Pushing dashboards built on guessed schemas
  would create tech debt that is harder to remove than not having them.
