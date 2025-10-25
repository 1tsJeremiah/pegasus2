# Pi-hole + Traefik Wiring Status (2025-10-04)

## Running containers
- traefik (v3.1) – reverse proxy listening on tcp/80 and tcp/443 (routes `*.localhost`)
- webhook-server – Node service behind Traefik (`docker ps` shows healthy)
- portainer – Docker UI (attached to same `traefik` network, exposed at `http://portainer.localhost`)
- pihole – DNS resolver (port 53 published; admin UI proxied by Traefik; DHCP disabled by default)
- prometheus – local metrics scraper (binds 127.0.0.1:9090)
- grafana – dashboards behind Traefik (`http://grafana.localhost`)
- chroma-dev – Chroma vector database for Codex knowledge ingestion (127.0.0.1:8000)

Check status:
```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

## Traefik routing summary
- Static config: `traefik/data/traefik.yml`
- Dynamic middleware/routers: `traefik/data/dynamic.yml`
- Default hostnames are `traefik.localhost`, `webhook.localhost`, `pihole.localhost`, `portainer.localhost`, and `grafana.localhost`
- No external DNS or Cloudflare tunnel is required; everything resolves to 127.0.0.1 via the `.localhost` TLD

## Pi-hole state
- Configuration persisted under `pihole/etc-pihole/`
- Network: dedicated `pihole_net` (172.22.53.0/24)
- Static IPs: Pi-hole `172.22.53.53`, Unbound upstream `172.22.53.54`
- Upstream DNS: Unbound (local recursive resolver) instead of public resolvers
- `WEBPASSWORD` is managed via compose env; rotate to a strong password and sync to Bitwarden (`PIHOLE_ADMIN_PASSWORD`)
- Blocklists populated via `gravity.db`; check `pihole/etc-pihole/listsCache/`

Password rotation:
```bash
# Set new admin password inside the container
docker exec pihole pihole -a -p
# Update .env and recreate container if needed
```

## Vector knowledge base
- New ingestion script: `vector-db-langchain/src/codex_vector/ingest/infra_docs.py`
- Stored official docs (Cloudflare Tunnel, Pi-hole Docker, Traefik Docker provider + DNS challenge, Docker Compose overview)
- Text snapshots live at `vector-db-langchain/data/infra/docs/`
- Query with:
```bash
cd /home/pegasus2/vector-db-langchain
.venv/bin/python src/codex_integration/vector_cli.py stats --collection infra-docs
```

## MCP stack
- `MASTER-MCP-CONFIG.json` includes Fetch MCP (`npx -y @zcaceres/fetch-mcp`) alongside GitHub, Docker, SQLite, etc.
- Launch helper: `vector-db-langchain/scripts/codex/run_docker_mcp.sh`
- Fetch MCP is the primary tool for grabbing additional documentation to extend the knowledge base.

## Bitwarden workflow (automated)
1. Unlock vault: `bw login` (once) and `bw unlock --raw` (master password now pulled via `~/bin/decrypt-bw-master.sh` if needed).
2. Secrets stored under:
   - `CLOUDFLARE_API_TOKEN_main` (login password)
   - `CLOUDFLARE_ACCOUNT_ID` (custom field `account_id`)
   - `CLOUDFLARE_ZONE_ID` / `_1tsjeremiah.com` (custom field `zone_id`)
   - `PIHOLE_ADMIN_PASSWORD` (login password rotated 2025-10-05)
3. Run Docker Compose from the same shell so Traefik/Pi-hole consume the exported secrets.

## Next actions
1. Confirm clients are using Pi-hole: point the gateway/DHCP server at the host's IP (or re-enable the bundled DHCP service by restoring the UDP/67 publish + `NET_ADMIN` capability in `docker-compose-master.yml`) and monitor `docker logs pihole` for new clients.
2. Rotate the admin password in Bitwarden (`PIHOLE_ADMIN_PASSWORD`) when needed, then run `bin/docker-master-stack.sh up -d` so the container picks up the new secret from `~/.config/docker/master-stack.env`.
3. Populate Bitwarden with `TRAEFIK_DASHBOARD_AUTH`, `GRAFANA_ADMIN_USER`, and `GRAFANA_ADMIN_PASSWORD`, then rerun `bin/docker-master-stack.sh up -d` to replace default credentials.
4. Attach `databases/secrets/bitwarden-master.txt.gpg` to the Bitwarden vault item once attachments are unlocked, then optionally remove the on-disk copy.
5. Extend documentation set (Portainer admin guide, Traefik dashboard hardening, Pi-hole API) and re-run `scripts/codex/sync_documents.sh`.
6. Decide whether to keep both `chroma` (ChromaDB) and `qdrant` services or consolidate on a single vector store.
7. See `docs/STACK_DNS_SELFHEALING.md` for the full DNS self-healing design and operations.
