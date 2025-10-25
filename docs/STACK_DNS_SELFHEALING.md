Mindstack DNS + Self‑Healing

Overview
- Pi‑hole provides DNS filtering for host and containers.
- Unbound runs as a local recursive resolver; Pi‑hole upstreams to Unbound.
- All services are attached to `pihole_net` and use Pi‑hole DNS.
- Docker daemon is configured to use Pi‑hole globally.
- Autoheal restarts containers labeled `autoheal=true` when unhealthy.

Key Components
- Network: `pihole_net` (172.22.53.0/24)
  - Pi‑hole: 172.22.53.53
  - Unbound: 172.22.53.54
- Host DNS: NetworkManager/systemd‑resolved set to 127.0.0.1
- Docker daemon DNS: `/etc/docker/daemon.json` contains `{"dns": ["172.22.53.53"]}`
- Autoheal: `willfarrell/autoheal` monitors health and restarts as needed

Healthchecks (compose)
- traefik: built‑in healthcheck
- webhook-server: HTTP GET http://127.0.0.1:3000
- pihole: `dig @127.0.0.1 localhost`
- unbound: `drill @127.0.0.1 cloudflare.com A`
- grafana: GET /api/health
- prometheus: GET /-/ready
- chroma-vectordb: TCP 127.0.0.1:8000
- qdrant-vectordb: TCP 127.0.0.1:6333

Operate
- Recreate stack (safe): `docker compose up -d --remove-orphans`
- Pull updates: `docker compose pull pihole unbound autoheal` (or `docker compose pull`)
- Check health: `docker ps --format '{{.Names}}\t{{.Status}}'`
- Inspect failing health log:
  `docker inspect -f '{{range $e := .State.Health.Log}}{{printf "%s exit=%d\n%s\n" $e.End $e.ExitCode $e.Output}}{{end}}' <container>`

Verify DNS
- Host: `resolvectl query doubleclick.net` → 0.0.0.0 / ::
- Container: `docker exec grafana getent hosts doubleclick.net`
- Direct: `dig +short cloudflare.com @127.0.0.1`

Scaling
- Stateless HTTP (via Traefik):
  - `docker compose up -d --scale webhook-server=2`
  - Traefik balances across replicas automatically.
- Stateful services (Prometheus, Grafana, Qdrant, Chroma) are not scaled here; prefer single‑instance unless cluster configs are applied.

Change/rollback DNS
- Host: revert NM settings
  - `sudo resolvectl revert wlp3s0` (or via nm-connection-editor)
- Docker daemon:
  - Backup file: `/etc/docker/daemon.json.bak.*`
  - Remove the `dns` key or restore backup; then `sudo systemctl restart docker` and `docker compose up -d`.

Notes
- Pi‑hole admin: http(s)://pihole.localhost/admin (via Traefik)
- Password via compose env `WEBPASSWORD`.
- Tune blocklists/allowlists in Pi‑hole UI; upstreams are Unbound by default.

