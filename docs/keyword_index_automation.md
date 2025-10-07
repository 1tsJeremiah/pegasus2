# Keyword Index Automation

Use systemd to refresh the Meilisearch keyword index on a schedule.

## 1. Create service unit

Save as `~/.config/systemd/user/keyword-index.service`:

```ini
[Unit]
Description=Refresh Meilisearch keyword index
After=network-online.target

[Service]
Type=oneshot
WorkingDirectory=%h/vector-db-langchain
EnvironmentFile=%h/.config/docker/master-stack.env
ExecStart=/bin/bash -lc 'source %h/vector-db-langchain/.venv/bin/activate && scripts/codex/index_keyword.sh'
```

> `EnvironmentFile` is optional but allows reuse of secrets exported by Bitwarden. Remove the line if running in an isolated environment.

## 2. Create timer unit

Save as `~/.config/systemd/user/keyword-index.timer`:

```ini
[Unit]
Description=Schedule Meilisearch keyword index refresh

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
```

Adjust `OnCalendar` as needed (e.g., `OnCalendar=*-*-* 02:15:00` for nightly runs).

## 3. Enable and verify

```bash
systemctl --user daemon-reload
systemctl --user enable --now keyword-index.timer
systemctl --user list-timers keyword-index.timer
journalctl --user -u keyword-index.service -n 50 --no-pager
```

## 4. Manual run

To trigger a refresh immediately:

```bash
systemctl --user start keyword-index.service
```

Ensure the Meilisearch container is running before each execution.
