# ADR-001 — Demo secrets live in .env, never in tracked files

- **Status:** Accepted
- **Date:** 2026-04-19
- **Related:** none (first ADR in this repo)

## Context

The `demo/` stack ships InfluxDB + Grafana preconfigured for local-
dashboard iteration. Both services need an admin password, and Grafana
reads its InfluxDB token from provisioning. In the v0.1.0 scaffold the
admin token literal `"dev-token-not-for-production"` appeared in **four
tracked files**:

- `demo/docker-compose.yaml` (twice — InfluxDB init env, bootstrap
  container script)
- `demo/grafana-provisioning/datasources/influxdb.yaml`
- `scripts/seed-events.py` (argparse default)

That pattern is dangerous for two reasons:

1. **Copy-paste to production**: anyone who grabs this stack as a
   starter is one `git clone` away from an internet-reachable Grafana
   speaking to an InfluxDB that accepts a world-known token. The
   "-not-for-production" suffix doesn't actually stop the deploy.
2. **Token rotation friction**: changing the literal requires editing
   four files. Users will forget one, get mysterious 401s, and blame
   the stack.

## Decision

All secrets and environment-specific values live in **`demo/.env`**,
which is gitignored. `demo/.env.example` is a template that documents
every variable and uses obvious "CHANGE-ME" placeholder values.

Referenced by:

- `docker-compose.yaml` uses `env_file: .env` plus `${VAR:?set in .env}`
  expansion, so a missing key fails compose-up with a clear message
  rather than a silent default.
- `grafana-provisioning/datasources/influxdb.yaml` uses
  `"Token $INFLUX_ADMIN_TOKEN"` in `secureJsonData.httpHeaderValue1`;
  Grafana expands the `$VAR` at datasource-load time.
- `scripts/seed-events.py` defaults to `os.environ.get("INFLUX_ADMIN_TOKEN")`
  and refuses to run with exit 2 if neither CLI flag nor env var
  provides a value.

## Why not secrets managers (Vault, Doppler, SOPS, etc.)

Overkill for a local demo. The target persona is "I have Docker and
want to see a dashboard in 10 minutes"; making them learn Vault is a
regression in onboarding. If/when the stack moves to a shared lab, we
add SOPS on top of this ADR rather than replacing .env.

## Why env-var substitution, not compose `secrets:`

Compose `secrets:` is nicer but Grafana's datasource provisioning YAML
doesn't read `/run/secrets/*` — it expects inlined values at parse
time. Env-var substitution is the simplest shape that all three
consumers (docker-compose, Grafana, Python seeder) agree on.

## Consequences

- First-run ceremony becomes `cp demo/.env.example demo/.env` before
  `docker compose up -d`. README documents this.
- `demo/.env` is in .gitignore; accidental commit is blocked by the
  pattern, not by hope.
- If the env var is missing, compose and the seeder both fail loudly
  rather than silently using a stale default.
- No literal tokens in any tracked file (verified via
  `grep -r dev-token` from repo root → 0 hits in the `demo/` source,
  only in `.env.example` which is explicitly templated with
  `CHANGE-ME` markers).

## References

- `demo/.env.example`
- `demo/docker-compose.yaml`
- `demo/grafana-provisioning/datasources/influxdb.yaml`
- `scripts/seed-events.py::_build_parser`
