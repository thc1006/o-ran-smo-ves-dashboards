# Releasing o-ran-smo-ves-dashboards

## Pre-flight

- [ ] Local `main` up to date with `origin/main`
- [ ] `docker compose -f demo/docker-compose.yaml config` exits 0
- [ ] `python -c "import json; [json.load(open(p, encoding='utf-8'))
      for p in __import__('pathlib').Path('dashboards').rglob('*.json')]"`
      exits 0 (all dashboard JSONs are valid)
- [ ] The dashboards still render against the demo stack:
  ```bash
  cp demo/.env.example demo/.env
  docker compose -f demo/docker-compose.yaml up -d
  # wait for grafana health
  INFLUX_ADMIN_TOKEN=$(grep ^INFLUX_ADMIN_TOKEN demo/.env | cut -d= -f2) \
    python scripts/seed-events.py --count 100 --rate 0
  curl -sf -u admin:$(grep ^GRAFANA_ADMIN_PASSWORD demo/.env | cut -d= -f2) \
    http://localhost:3000/api/search?type=dash-db
  ```

## Version scheme

[Semantic Versioning](https://semver.org/) 2.0.0 but with
dashboard-specific semantics:

| Change | Bump |
|---|---|
| New dashboard JSON file | minor |
| Breaking change to query structure (users must re-import) | major |
| Panel / variable / legend tweak | patch |
| Bump targeted Grafana major version | major |
| Bump targeted InfluxDB major version (2 -> 3) | major |
| docs-only | patch |

## Release steps

1. Bump `CHANGELOG.md`: move `## [Unreleased]` items to
   `## [X.Y.Z] — YYYY-MM-DD`. This repo has no single "version" field
   yet (JSON files carry their own `"version"` property which Grafana
   manages); the CHANGELOG is the source of truth.

2. Per-dashboard version bumps: open each changed dashboard JSON in
   Grafana, click *Settings → Versions* to let Grafana increment
   `"version"`. Alternatively, edit by hand.

3. Commit + tag:
   ```bash
   git add CHANGELOG.md dashboards/
   git commit -m "release: X.Y.Z"
   git tag -a vX.Y.Z -m "o-ran-smo-ves-dashboards X.Y.Z"
   git push origin main vX.Y.Z
   ```

4. Publish each NEW dashboard to grafana.com
   (https://grafana.com/grafana/dashboards/). `gh dashboard` doesn't
   exist; the upload is a manual UI step:
   a. Export each new or significantly-changed dashboard from our
      local Grafana as JSON.
   b. Upload via grafana.com's "Upload a dashboard" form.
   c. Note the assigned community ID in `README.md`'s catalogue.

5. Announce: post a release note (GitHub release + optional mailing
   list) linking to:
   - The new CHANGELOG section.
   - The grafana.com dashboard IDs.

## Grafana / InfluxDB compatibility matrix

| This release targets | Minimum version | Tested version |
|---|---|---|
| Grafana | 12.0 | 12.2.0 |
| InfluxDB | 2.7 | 2.7 (demo); 3.x probed via Phase 1 |
| InfluxQL DBRP compat layer | required | auto-bootstrapped by demo compose |

## Deprecating a dashboard

If a dashboard is superseded or structurally unsound:

1. Keep the JSON file (don't delete) for one full minor cycle; add a
   `"tags": [..., "deprecated-in-X.Y"]` marker.
2. Update CHANGELOG `### Deprecated`.
3. At the next MAJOR bump, remove the file and note it under
   `### Removed`.

## Why dashboards are not on a Helm chart release flow yet

The v0.2.0 catalogue (NRCellDU + NRCellCU) is still small enough that
a Helm wrapping adds more moving parts than it earns. Once the catalogue
grows past ~5 dashboards, wrap them in a Helm library chart with a proper
chart `version:` field, and that chart version becomes the canonical
version number.
