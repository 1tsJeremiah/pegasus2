Mindstack Future Scale Tasks

Context
- Mindstack bundles vector memory (Chroma/Qdrant), DNS filtering (Pi‑hole + Unbound), Traefik, and self‑healing (Autoheal + healthchecks).
- This list is agent‑readable for prioritization and automation.

Conventions
- priority: P1 (now) / P2 (soon) / P3 (later)
- status: todo | planned | doing | done | blocked

Tasks
- id: T-AUTOMERGE-MON | priority: P1 | status: planned
  - Monitor OpenHands automerge mini agent; guard main with Stack Guard, expand invariants; notify on changes.
  - DoD: CI blocks invariant drift; notifications on merges/failures.
  - Links: .github/workflows/stack-guard.yml, scripts/ci/stack_guard.py

- id: T-DEPLOY-AUTO | priority: P1 | status: todo
  - Auto‑deploy on push to main via webhook-server; pull + docker compose up -d.
  - DoD: Host updates within 1 minute of merge; idempotent.

- id: T-AGENT-WATCHDOG | priority: P1 | status: planned
  - Systemd timer watchdog for CLI agent using ETA + x‑factor; complements cron implementation.
  - DoD: User timer active; overruns trigger refresh.

- id: T-BACKUP-VOLUMES | priority: P1 | status: todo
  - Nightly encrypted restic (or borg) backups for pihole_etc, grafana_data, prometheus_data, qdrant/chroma.
  - DoD: Successful nightly backup + test restore.

- id: T-SCALE-WEBHOOK | priority: P2 | status: todo
  - Scale webhook-server to N replicas behind Traefik; optional autoscale on CPU/latency.
  - DoD: Load balanced; health steady under load.

- id: T-DB-CONSOLIDATE | priority: P2 | status: todo
  - Consolidate on Qdrant or Chroma for production.
  - DoD: Single vector store in compose; ingestion/tests updated.

- id: T-OBS-LOGS | priority: P2 | status: todo
  - Add Loki/Promtail; wire Grafana datasource and dashboards.
  - DoD: Container logs queryable by service and label.

- id: T-DNS-HARDEN | priority: P3 | status: todo
  - Unbound DNSSEC + root hints refresh; optional DoT/DoH upstream profile.
  - DoD: Validation on; upstream privacy tested.

- id: T-TRAEFIK-SEC | priority: P3 | status: todo
  - Harden Traefik admin endpoints; stricter security headers/TLS policies.
  - DoD: Admin UIs gated; headers verified.

Notes
- Agents may append, reprioritize, and mark done. Keep items small and actionable.

