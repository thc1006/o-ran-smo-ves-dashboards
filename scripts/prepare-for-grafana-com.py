#!/usr/bin/env python3
"""Transform provisioning-flavoured dashboard JSONs into grafana.com-uploadable
exports.

What Grafana's UI "Share -> Export -> Enable for sharing externally" does:

1. Replaces every `{"type": "influxdb", "uid": "influxdb-ves"}` datasource
   reference with the string `"${DS_INFLUXDB}"` (a variable).
2. Adds a top-level `__inputs` array declaring the `DS_INFLUXDB` variable
   so the import UI can prompt the user to pick a local datasource.
3. Adds `__elements` and `__requires` sections listing the Grafana
   version and panel plugins we depend on. Keeping these empty lists is
   acceptable for basic dashboards; Grafana fills them at import time.
4. Drops `id` and `version` (or sets id to null) -- grafana.com assigns
   fresh ones.

We run this on every file under `dashboards/` and write the transformed
copies to `dist/grafana-com/` for manual upload. The per-repo dashboards
stay hardcoded to `uid: "influxdb-ves"` because that matches our
provisioning YAML.
"""
from __future__ import annotations

import copy
import json
import pathlib
import re
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "dashboards"
DST_DIR = REPO_ROOT / "dist" / "grafana-com"

HARDCODED_DS_UID = "influxdb-ves"
INPUT_VAR = "DS_INFLUXDB"


def _rewrite_datasource(node):
    """Depth-first walk; replace matching datasource dicts with the var string."""
    if isinstance(node, dict):
        if (
            node.get("type") == "influxdb"
            and node.get("uid") == HARDCODED_DS_UID
            and set(node.keys()) <= {"type", "uid"}
        ):
            return "${" + INPUT_VAR + "}"
        return {k: _rewrite_datasource(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_rewrite_datasource(x) for x in node]
    return node


# The caveat about the hardcoded datasource UID is always the last
# sentence of the description in every source dashboard. Everything
# from "Datasource UID is hardcoded" to end-of-string is noise for the
# grafana.com audience.
_DS_CAVEAT_RE = re.compile(r"\s*Datasource UID is hardcoded.*$", re.DOTALL)


def _scrub_description(desc: str) -> str:
    """Repo-internal description mentions the hardcoded provisioning UID.
    For the grafana.com-facing export we want the description to read as
    if the dashboard has always been portable, so strip that sentence.
    """
    return _DS_CAVEAT_RE.sub("", desc).strip()


def _transform(dashboard: dict) -> dict:
    out = copy.deepcopy(dashboard)
    if isinstance(out.get("description"), str):
        out["description"] = _scrub_description(out["description"])
    out = _rewrite_datasource(out)
    out["__inputs"] = [
        {
            "name": INPUT_VAR,
            "label": "InfluxDB",
            "description": "InfluxDB 2.x datasource with v1 DBRP mapping on the influxlogger bucket.",
            "type": "datasource",
            "pluginId": "influxdb",
            "pluginName": "InfluxDB",
        }
    ]
    out["__elements"] = {}
    out["__requires"] = [
        {"type": "grafana", "id": "grafana", "name": "Grafana", "version": "12.0.0"},
        {"type": "datasource", "id": "influxdb", "name": "InfluxDB", "version": "1.0.0"},
        {"type": "panel", "id": "timeseries", "name": "Time series", "version": ""},
        {"type": "panel", "id": "stat", "name": "Stat", "version": ""},
    ]
    out["id"] = None
    return out


def main() -> int:
    if not SRC_DIR.exists():
        sys.stderr.write(f"error: {SRC_DIR} does not exist\n")
        return 1

    DST_DIR.mkdir(parents=True, exist_ok=True)

    files = sorted(SRC_DIR.rglob("*.json"))
    if not files:
        sys.stderr.write("error: no dashboards found\n")
        return 2

    for src in files:
        rel = src.relative_to(SRC_DIR)
        dst = DST_DIR / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        data = json.loads(src.read_text(encoding="utf-8"))
        transformed = _transform(data)
        dst.write_text(
            json.dumps(transformed, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"  {rel} -> dist/grafana-com/{rel}")

    print(f"done; {len(files)} dashboard(s) ready for grafana.com upload")
    print(f"  source of truth: {SRC_DIR.relative_to(REPO_ROOT)}")
    print(f"  upload these:    {DST_DIR.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
