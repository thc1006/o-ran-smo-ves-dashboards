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

_PM_COUNTER_NAMES = [
    # A minimal selection from 3GPP TS 28.552 NR cell DU counters.
    "DRB.PdcpSduVolumeDl_Filter",
    "DRB.PdcpSduVolumeUl_Filter",
    "DRB.MeanActiveUeDl",
    "RRU.PrbUsedDl",
    "RRU.PrbUsedUl",
]


def _random_counter_values() -> dict[str, float]:
    return {
        name: round(random.uniform(0, 1_000_000), 2) for name in _PM_COUNTER_NAMES
    }


def _make_measurement_point(fdn: str, ts_ns: int) -> Point:
    p = Point(fdn)
    for k, v in _random_counter_values().items():
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
    p.add_argument("--influx-url", default="http://localhost:8086")
    p.add_argument("--influx-token", default="dev-token-not-for-production")
    p.add_argument("--influx-org", default="winlab")
    p.add_argument("--influx-bucket", default="ves")
    p.add_argument("--count", type=int, default=500, help="points per domain")
    p.add_argument("--rate", type=float, default=10.0, help="points per second")
    p.add_argument(
        "--domains", default="measurement,heartbeat,fault",
        help="comma-separated subset of: measurement,heartbeat,fault"
    )
    return p


def main() -> int:
    args = _build_parser().parse_args()
    domains = [d.strip() for d in args.domains.split(",") if d.strip()]
    # Up-front sanity check: pytest-ves is importable, not only reachable.
    # Failing this early avoids confusing partial writes.
    for builder in (FaultEventBuilder(), HeartbeatEventBuilder(), MeasurementEventBuilder()):
        assert "commonEventHeader" in builder.build()["event"]

    client = InfluxDBClient(
        url=args.influx_url, token=args.influx_token, org=args.influx_org,
    )
    try:
        write_api = client.write_api(write_options=SYNCHRONOUS)
        try:
            interval = 1.0 / args.rate if args.rate > 0 else 0
            fdns = [
                tpl.format(i=i)
                for tpl in _NRCELL_DU_FDN_TEMPLATES
                for i in range(1, 4)
            ]

            print(
                f"seeding {args.count} points/domain ({','.join(domains)}) "
                f"@ {args.rate}/s into {args.influx_url} bucket={args.influx_bucket}"
            )

            for i in range(args.count):
                ts_ns = time.time_ns()
                points = []
                if "measurement" in domains:
                    points.append(_make_measurement_point(random.choice(fdns), ts_ns))
                if "heartbeat" in domains:
                    points.append(
                        Point("ves_heartbeat")
                        .tag("sourceName", random.choice(fdns))
                        .field("heartbeatInterval", 60)
                        .time(ts_ns, write_precision=WritePrecision.NS)
                    )
                if "fault" in domains:
                    points.append(_make_fault_point(random.choice(fdns), ts_ns))
                write_api.write(bucket=args.influx_bucket, record=points)
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
