# Changelog

## [Unreleased]

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
