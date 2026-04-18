#!/usr/bin/env python3
"""Seed fake VES events into a local InfluxDB for dashboard iteration.

This is a *development* tool -- it writes InfluxDB points that mimic the
expected ``nonrtric-plt-influxlogger`` schema (measurement = resource Full
Distinguished Name; each field is a counter name). Use it to populate the
docker-compose dev stack. For schema-accurate data you want
``kind/install-ranpm.sh`` + the real upstream plumbing.

Requires: ``pip install pytest-ves influxdb-client requests``.
"""
from __future__ import annotations

import argparse
import os
import random
import sys
import time

try:
    from influxdb_client import InfluxDBClient, Point, WritePrecision
    from influxdb_client.client.write_api import SYNCHRONOUS
except ImportError:
    sys.stderr.write(
        "error: install influxdb-client first: pip install influxdb-client\n"
    )
    sys.exit(1)

try:
    from pytest_ves import (
        FaultEventBuilder,
        HeartbeatEventBuilder,
        MeasurementEventBuilder,
    )
except ImportError:
    sys.stderr.write(
        "error: install pytest-ves first: pip install pytest-ves\n"
    )
    sys.exit(1)


_NRCELL_DU_FDN_TEMPLATES = [
    "SubNetwork=NYCU,ManagedElement=gNB-Taipei-{i:02d},NRCellDU=1",
    "SubNetwork=NYCU,ManagedElement=gNB-Hsinchu-{i:02d},NRCellDU=2",
    "SubNetwork=NYCU,ManagedElement=gNB-Keelung-{i:02d},NRCellDU=1",
]
_NRCELL_CU_FDN_TEMPLATES = [
    "SubNetwork=NYCU,ManagedElement=gNB-Taipei-{i:02d},NRCellCU=1",
    "SubNetwork=NYCU,ManagedElement=gNB-Hsinchu-{i:02d},NRCellCU=1",
    "SubNetwork=NYCU,ManagedElement=gNB-Keelung-{i:02d},NRCellCU=1",
]

# 3GPP TS 28.552 PM counters. Kept here for reference / bucket probes;
# the per-cell generators below produce values that respect the
# physical relationships between these counters (e.g. success <= attempts)
# so dashboards like "success rate = succ / att" render plausible
# percentages in [0, 100] instead of pathological values like 2000%.
_PM_COUNTER_NAMES_DU = [
    "DRB.PdcpSduVolumeDl_Filter",
    "DRB.PdcpSduVolumeUl_Filter",
    "DRB.MeanActiveUeDl",
    "RRU.PrbUsedDl",
    "RRU.PrbUsedUl",
]
_PM_COUNTER_NAMES_CU = [
    "RRC.ConnEstabAtt.sum",
    "RRC.ConnEstabSucc.sum",
    "NG.HOExeAtt",
    "NG.HOExeSucc",
]


def _random_du_counters() -> dict[str, float]:
    # PDCP SDU volume in bytes per granularity window (60s): a busy
    # cell pushes O(10 MiB) DL, O(1 MiB) UL.
    pdcp_dl = random.uniform(2_000_000, 20_000_000)
    pdcp_ul = random.uniform(200_000, 3_000_000)
    # Active UEs per cell, typical small-cell range.
    active_ue = random.uniform(2.0, 30.0)
    # PRB usage counts (raw, not percentage). A 100 MHz NR cell has ~273
    # PRBs; counter is "PRBs used averaged over the window".
    prb_dl = random.uniform(20, 220)
    prb_ul = random.uniform(5, 120)
    return {
        "DRB.PdcpSduVolumeDl_Filter": round(pdcp_dl, 2),
        "DRB.PdcpSduVolumeUl_Filter": round(pdcp_ul, 2),
        "DRB.MeanActiveUeDl": round(active_ue, 2),
        "RRU.PrbUsedDl": round(prb_dl, 2),
        "RRU.PrbUsedUl": round(prb_ul, 2),
    }


def _random_cu_counters() -> dict[str, float]:
    # RRC connection establishment attempts per window; success is a
    # realistic 92-99.5% of attempts -- anything above 100% is
    # physically impossible and makes RAN engineers reflexively
    # close the tab.
    rrc_att = random.randint(500, 5000)
    rrc_succ = random.randint(int(rrc_att * 0.92), int(rrc_att * 0.995))
    # NG handover attempts per window; success is typically 95-99.8%.
    ho_att = random.randint(30, 600)
    ho_succ = random.randint(int(ho_att * 0.95), int(ho_att * 0.998))
    return {
        "RRC.ConnEstabAtt.sum": float(rrc_att),
        "RRC.ConnEstabSucc.sum": float(rrc_succ),
        "NG.HOExeAtt": float(ho_att),
        "NG.HOExeSucc": float(ho_succ),
    }


def _make_du_point(fdn: str, ts_ns: int) -> Point:
    p = Point(fdn)
    for k, v in _random_du_counters().items():
        p = p.field(k, v)
    return p.time(ts_ns, write_precision=WritePrecision.NS)


def _make_cu_point(fdn: str, ts_ns: int) -> Point:
    p = Point(fdn)
    for k, v in _random_cu_counters().items():
        p = p.field(k, v)
    return p.time(ts_ns, write_precision=WritePrecision.NS)


def _make_fault_point(source: str, ts_ns: int) -> Point:
    # fault path is event-based, not counter-based. We keep this optional;
    # real influxlogger may route faults elsewhere.
    severity = random.choice(["CRITICAL", "MAJOR", "MINOR", "WARNING", "NORMAL"])
    return (
        Point("ves_fault")
        .tag("sourceName", source)
        .tag("severity", severity)
        .field("alarmCondition", random.choice(["28", "29", "30"]))
        .field("specificProblem", "CUS Link Failure")
        .time(ts_ns, write_precision=WritePrecision.NS)
    )


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--influx-url",
        default=os.environ.get("INFLUX_URL", "http://localhost:8086"),
    )
    # Token default now comes from env, not a hard-coded string in source.
    # Matches the .env.example pattern used by demo/docker-compose.yaml.
    p.add_argument(
        "--influx-token",
        default=os.environ.get("INFLUX_ADMIN_TOKEN"),
        help="InfluxDB admin token; defaults to $INFLUX_ADMIN_TOKEN",
    )
    p.add_argument(
        "--influx-org",
        default=os.environ.get("INFLUX_ORG", "winlab"),
    )
    p.add_argument(
        "--influx-bucket",
        default=os.environ.get("INFLUX_BUCKET", "ves"),
    )
    p.add_argument("--count", type=int, default=500, help="points per domain")
    p.add_argument("--rate", type=float, default=10.0, help="points per second")
    p.add_argument(
        "--domains", default="measurement,heartbeat,fault",
        help="comma-separated subset of: measurement,heartbeat,fault"
    )
    p.add_argument(
        "--window-seconds", type=float, default=3600.0,
        help=(
            "Spread generated timestamps retroactively across this many "
            "seconds ending at 'now'. Default: 3600 (1 hour) so a Grafana "
            "'Last 1 hour' view renders a smooth curve instead of a "
            "single vertical spike at the right edge."
        ),
    )
    return p


def main() -> int:
    args = _build_parser().parse_args()
    if not args.influx_token:
        sys.stderr.write(
            "error: no InfluxDB token. Either pass --influx-token or set "
            "$INFLUX_ADMIN_TOKEN (see demo/.env.example).\n"
        )
        return 2
    domains = [d.strip() for d in args.domains.split(",") if d.strip()]
    # Up-front sanity check: pytest-ves is importable, not only reachable.
    # Failing this early avoids confusing partial writes.
    for builder in (FaultEventBuilder(), HeartbeatEventBuilder(), MeasurementEventBuilder()):
        assert "commonEventHeader" in builder.build()["event"]

    try:
        client = InfluxDBClient(
            url=args.influx_url, token=args.influx_token, org=args.influx_org,
        )
    except Exception as exc:
        sys.stderr.write(
            f"error: cannot open InfluxDB connection at {args.influx_url}: {exc}\n"
            f"  is the demo stack running? (docker compose -f demo/docker-compose.yaml up -d)\n"
        )
        return 3

    try:
        write_api = client.write_api(write_options=SYNCHRONOUS)
        try:
            interval = 1.0 / args.rate if args.rate > 0 else 0
            du_fdns = [
                tpl.format(i=i)
                for tpl in _NRCELL_DU_FDN_TEMPLATES
                for i in range(1, 4)
            ]
            cu_fdns = [
                tpl.format(i=i)
                for tpl in _NRCELL_CU_FDN_TEMPLATES
                for i in range(1, 4)
            ]
            # heartbeat/fault use a shared pool of source names. These
            # two domains are dev-only: real influxlogger only consumes
            # perf3gpp PM data, so ves_heartbeat / ves_fault points
            # never appear in a production pm_data bucket.
            fdns = du_fdns + cu_fdns

            print(
                f"seeding {args.count} points/domain ({','.join(domains)}) "
                f"@ {args.rate}/s into {args.influx_url} bucket={args.influx_bucket}"
            )

            # Spread timestamps retroactively across the requested window
            # so Grafana's default "Last 1 hour" view shows a populated
            # curve rather than a single vertical spike at the right edge.
            now_ns = time.time_ns()
            window_ns = int(args.window_seconds * 1_000_000_000)
            step_ns = window_ns // max(args.count, 1)

            failed_in_a_row = 0
            for i in range(args.count):
                # Oldest point first, newest at end-of-loop.
                ts_ns = now_ns - window_ns + (i * step_ns)
                # For measurement points, rotate through every cell each
                # iteration so every series gets enough data density to
                # render. Random.choice left gaps.
                points = []
                if "measurement" in domains:
                    for fdn in du_fdns:
                        points.append(_make_du_point(fdn, ts_ns))
                    for fdn in cu_fdns:
                        points.append(_make_cu_point(fdn, ts_ns))
                if "heartbeat" in domains:
                    points.append(
                        Point("ves_heartbeat")
                        .tag("sourceName", random.choice(fdns))
                        .field("heartbeatInterval", 60)
                        .time(ts_ns, write_precision=WritePrecision.NS)
                    )
                if "fault" in domains:
                    points.append(_make_fault_point(random.choice(fdns), ts_ns))
                try:
                    write_api.write(bucket=args.influx_bucket, record=points)
                except Exception as exc:
                    failed_in_a_row += 1
                    sys.stderr.write(
                        f"warning: write failed at batch {i} "
                        f"({type(exc).__name__}: {str(exc)[:120]})\n"
                    )
                    if failed_in_a_row > 5:
                        sys.stderr.write(
                            "error: >5 consecutive write failures; aborting.\n"
                        )
                        return 4
                else:
                    failed_in_a_row = 0
                if i % 50 == 0 and i > 0:
                    print(f"  {i}/{args.count}")
                if interval > 0:
                    time.sleep(interval)
        finally:
            write_api.close()
    finally:
        client.close()
    print("done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
