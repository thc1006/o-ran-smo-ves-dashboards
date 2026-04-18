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

_PM_COUNTER_NAMES_DU = [
    # A minimal selection from 3GPP TS 28.552 NR cell DU counters.
    "DRB.PdcpSduVolumeDl_Filter",
    "DRB.PdcpSduVolumeUl_Filter",
    "DRB.MeanActiveUeDl",
    "RRU.PrbUsedDl",
    "RRU.PrbUsedUl",
]
_PM_COUNTER_NAMES_CU = [
    # 3GPP TS 28.552 NR cell CU counters -- RRC + NG handover.
    "RRC.ConnEstabAtt.sum",
    "RRC.ConnEstabSucc.sum",
    "NG.HOExeAtt",
    "NG.HOExeSucc",
]


def _random_counter_values(names: list[str]) -> dict[str, float]:
    return {name: round(random.uniform(0, 1_000_000), 2) for name in names}


def _make_measurement_point(fdn: str, ts_ns: int, counters: list[str]) -> Point:
    p = Point(fdn)
    for k, v in _random_counter_values(counters).items():
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

            failed_in_a_row = 0
            for i in range(args.count):
                ts_ns = time.time_ns()
                points = []
                if "measurement" in domains:
                    points.append(
                        _make_measurement_point(
                            random.choice(du_fdns), ts_ns, _PM_COUNTER_NAMES_DU
                        )
                    )
                    points.append(
                        _make_measurement_point(
                            random.choice(cu_fdns), ts_ns, _PM_COUNTER_NAMES_CU
                        )
                    )
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
