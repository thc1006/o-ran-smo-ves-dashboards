# Screenshots

Canonical dashboard screenshots embedded by the top-level `README.md`
and by each dashboard's grafana.com listing.

## File conventions

- PNG, 16:9 aspect, 1600x900 px or 1920x1080 px.
- Trim browser chrome. Keep the Grafana top bar (dashboard title) so
  readers can see which dashboard is which.
- Use the built-in `Asia/Taipei` timezone picker and a populated time
  range (usually the default "now-1h") so panels actually show data.
- Filenames are referenced from the repo README -- do not rename
  without updating the markdown.

## Files

| File | What it shows |
|---|---|
| `ves-nrcell-du-overview.png` | All 4 NRCellDU panels after the demo seeder populates 500 points across 6 gNBs. |
| `ves-nrcell-cu-overview.png` | All 4 NRCellCU panels: RRC attempts vs success, success rate, NG handover attempts vs success, HO success rate. |
| `templating-variables.gif` | Optional animated demo of the `$subnetwork` / `$gnb` dropdowns filtering panels. |

## How to (re)capture

Automated via Playwright:

```bash
pip install playwright && playwright install chromium
cd demo && docker compose up -d && cd ..
INFLUX_ADMIN_TOKEN=$(grep ^INFLUX_ADMIN_TOKEN demo/.env | cut -d= -f2) \
  python scripts/seed-events.py --count 60 --window-seconds 3600 --domains measurement
python scripts/capture-screenshots.py
```

The script logs in, hides nav chrome via CSS (Grafana 12's `?kiosk=tv`
URL param is flaky), waits for panels to render, and writes PNGs back
to this directory. See `scripts/capture-screenshots.py` for the exact
flow.
