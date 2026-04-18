Data is written to InfluxDB by nonrtric-plt-influxlogger (O-RAN SC
Non-RT RIC plane, release 1.1.0+). It consumes 3GPP perf3gpp PmReport
JSON messages from a Kafka topic (default: `pmreports`) and stores each
counter as an InfluxDB field under a measurement named after the full
distinguished name, e.g.
`SubNetwork=NYCU,ManagedElement=gNB-Taipei-01,NRCellDU=1`.
No user tags are written — only the measurement name carries the topology.

Minimum setup (3 steps):

1. Deploy nonrtric-plt-influxlogger pointing at an existing InfluxDB
   2.x bucket. Helm chart and source code:
   https://gerrit.o-ran-sc.org/r/admin/repos/nonrtric/plt/ranpm

2. Wire an upstream PM source (real RAN PM collector, or the reference
   test producer) that pushes perf3gpp PmReport JSON into the Kafka
   topic influxlogger consumes.

3. Create a v1 DBRP mapping on the InfluxDB bucket — once per bucket —
   so this dashboard's InfluxQL queries work against InfluxDB 2.x:

       influx v1 dbrp create \
         --db pm_data --rp autogen \
         --bucket-id <bucket-id> --default

Reference implementation, minimal docker-compose probe stack that
reproduces the full pipeline in under 2 minutes, and the formal schema
contract (source audit + empirical probe, confidence 99%):
https://github.com/thc1006/o-ran-smo-ves-dashboards
