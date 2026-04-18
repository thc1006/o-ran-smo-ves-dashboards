# Capturing dashboard screenshots

Manual procedure for (re)populating `docs/screenshots/*.png` when
dashboards change. ~3 minutes end-to-end once Docker is warm.

## Prereqs

- Docker Desktop running
- `pytest-ves>=0.2.1` installed in the local Python environment
  (`pip install -r scripts/requirements.txt`)
- A native screenshot tool (Windows: Snipping Tool / `Win+Shift+S`;
  macOS: `Cmd+Shift+4`; Linux: `gnome-screenshot -a` or `flameshot`)

## Steps

### 1. Bring up the demo stack

```bash
cd demo
cp -n .env.example .env                  # only on first run
docker compose up -d
# wait ~30s for Grafana; check:
curl -sf http://localhost:3000/api/health
```

### 2. Seed enough data that all panels render

```bash
cd ..
INFLUX_ADMIN_TOKEN=$(grep ^INFLUX_ADMIN_TOKEN demo/.env | cut -d= -f2) \
  python scripts/seed-events.py --count 500 --rate 25
```

The seeder writes ~500 points per domain across 6 gNBs and both
NRCellDU / NRCellCU FDNs. Takes ~20s at rate=25.

### 3. Open each dashboard and capture

Login as `admin / $(grep ^GRAFANA_ADMIN_PASSWORD demo/.env | cut -d= -f2)`.

| Dashboard | URL (after login) | Save as |
|---|---|---|
| NR cell DU measurement | <http://localhost:3000/d/ves-nrcell-du> | `docs/screenshots/ves-nrcell-du-overview.png` |
| NR cell CU measurement | <http://localhost:3000/d/ves-nrcell-cu> | `docs/screenshots/ves-nrcell-cu-overview.png` |

Recommended capture settings:

- Time range: `Last 1 hour` (default)
- Refresh: `30s` (default)
- Theme: dark (default)
- Crop: include the dashboard title bar, exclude the browser chrome
- Resolution: 1600x900 or 1920x1080, 16:9

### 4. (Optional) Templating GIF

To capture the `templating-variables.gif`, record a short (<10s) screen
clip of you toggling `$subnetwork` = All -> NYCU and cycling `$gnb`
through 2-3 gNBs. Any tool works (ShareX, Kap, peek). Target
<2 MiB for README render quality.

### 5. Tear down

```bash
cd demo
docker compose down                      # keeps volumes
# or: docker compose down -v             # also nukes influxdb/grafana data
```

## Troubleshooting

- **Panels say "No data"** -- seeder didn't run, or Grafana datasource
  UID mismatch. Check `demo/grafana-provisioning/datasources/influxdb.yaml`
  still sets `uid: influxdb-ves`.
- **Dashboards not listed** -- provisioning file path drift; confirm
  `demo/grafana-provisioning/dashboards/` points at `../../dashboards/`.
- **DBRP errors in Grafana** -- `demo-influxdb-dbrp-bootstrap-1` exited
  non-zero. `docker logs demo-influxdb-dbrp-bootstrap-1` to debug.
