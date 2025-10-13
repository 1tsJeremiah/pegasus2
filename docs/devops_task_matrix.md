# DevOps Task Matrix

## Current Infrastructure Snapshot (2025-10-07)

| Service | Purpose | Health | Persistence | Notes |
|---------|---------|--------|-------------|-------|
| `mindstack-core` | Mindstack Core (Chroma) vector store | `healthy` | `docker/chroma_data` volume | v2 heartbeat active; CLI accessible at `http://127.0.0.1:8000/api/v2` |
| `qdrant-vectordb` | Production-grade vector store (Qdrant) | `healthy` | `docker/qdrant_data` volume | `/healthz` probe configured; ready for future use |
| `meili-search` | Keyword index (Meilisearch) | `healthy` | `docker/meili_data` volume | Requires ≥16-byte key; current default `dev-master-key-123456` |
| `traefik` | Reverse proxy / TLS termination | `Up (no health check)` | Config under `~/traefik/data` | Routed via Cloudflare tunnel |
| `pihole` | DNS filtering | `healthy` | `~/pihole/etc-pihole` bind mount | Admin password placeholder; Traefik proxying |
| `portainer` | Docker UI | `Up` | Portainer volume | Exposed via Traefik/Cloudflare |
| `webhook-server` | Node webhook for automations | `healthy` | N/A | Lives in `~/webhook-server` |

## Verified Working
- Vector CLI (`src/codex_integration/vector_cli.py`) connects to Mindstack Core (Chroma), seeds collections, and responds to searches.
- Keyword CLI (`src/codex_keyword/meili_cli.py`) boots, creates indexes, and ingests files; helper script streamlines indexing.
- Docker compose definitions now pass health checks for Mindstack Core (Chroma)/Qdrant using built-in shells; restart policies on all core containers set to `unless-stopped`.
- Bitwarden-backed helper (`~/bin/docker-master-stack.sh`) remains the control plane for production compose (`docker-compose-master.yml`).

## Known Gaps / Opportunities
- **Secrets hygiene**: Runtime defaults (`dev-master-key-123456`, placeholder Pi-hole password) need rotation from Bitwarden; compose files should consume the exported secrets automatically.
- **Keyword pipeline automation**: nightly indexing + retention policy not yet wired into cron/systemd.
- **GUI hardening**: Pi-hole, Portainer, Traefik dashboards rely on Cloudflare auth only; no multi-factor or rate limiting configured.
- **Monitoring/Alerting**: No centralized logging or metrics (Prometheus/Alertmanager/uptime checks) for the stack.
- **Backups**: Mindstack Core/Qdrant volumes lack snapshot strategy; Mindstack Index (Meilisearch) is not archived.
- **Agent regression tests**: Need smoke tests ensuring CLI + keyword flows pass after updates.

## Proposed Segmented Backlog
1. **Secrets & Configuration Hygiene**
   - Migrate Mindstack Index/Mindstack Core/Qdrant credentials into Bitwarden exports (script now reads `CODEX_MEILI_MASTER_KEY` + optional overrides).
   - Replace Pi-hole admin placeholder and document rotation path.
   - Extend `docker-master-stack.sh` export script to cover new env keys.
2. **Keyword Index Automation**
   - Create systemd timer or cron invoking `scripts/codex/index_keyword.sh` (see `docs/keyword_index_automation.md`).
   - Store indexing logs & add basic success alerting.
3. **GUI Hardening (Pi-hole, Portainer, Traefik)**
   - Confirm Traefik middleware (rate limiting, security headers) and document Cloudflare Access/SSO flow for Pi-hole admin, Portainer, and Traefik dashboards.
   - Schedule dashboard health checks (internal + public tunnel) via uptime monitor.
   - Evaluate access hardening: short-lived auth tokens for Portainer, Pi-hole MFA, Cloudflare Access policies per role.
4. **Monitoring & Observability**
   - Deploy Prometheus node exporter + docker metrics.
   - Integrate Loki or another log forwarder; add alarms for service restarts.
5. **Backup & Disaster Recovery**
   - Define snapshot cadence for `docker/*_data` volumes (rsync or restic).
   - Capture Meilisearch dumps post-index.
   - Test restore runbook end-to-end.
6. **Agent Integration & Testing**
   - Author automated smoke tests (pytest) for vector + keyword CLI.
   - Document agent instructions for keyword usage (manifest, prompts).
   - Validate Cloudflare tunnel workflows after restarts.

## Next Steps for Agents
- Rotate secrets via Bitwarden CLI and re-run the helper script to refresh compose env (`~/bin/docker-master-stack.sh up -d`).
- Schedule keyword indexing (Segment 2) and monitor for runtime errors.
- Prioritize Segment 3 (GUI hardening) to prepare for user-facing rollouts of Pi-hole/Portainer/Traefik dashboards.
