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

See `scripts/capture-screenshots.md` at repo root for the step-by-step
manual procedure (bring up demo stack, seed data, open Grafana, shoot
each dashboard, save to this directory).
