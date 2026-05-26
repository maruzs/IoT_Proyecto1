# Design: Spec 00 — Infraestructura de Contenedores (Docker Compose)

## Technical Approach

Create a `deploy/` directory at project root with Docker Compose v2 orchestrating two services: `mosquitto` (official eclipse-mosquitto:2 image) and `nodered` (custom Dockerfile from nodered/node-red:3-lts). Fully isolated — no modifications to existing `src/`, `openspec/`, or firmware code.

## Architecture Decisions

| Decision | Option A | Option B | Decision | Rationale |
|----------|----------|----------|----------|-----------|
| Compose version | `version: "3.8"` | No version key (Compose spec) | **No version key** | Compose v2 ignores version key; spec format is the modern standard |
| Mosquitto image | `eclipse-mosquitto:2` | `eclipse-mosquitto:latest` | **`eclipse-mosquitto:2`** | Pin major version to avoid breaking changes; `latest` is unpredictable |
| Node-RED base | `nodered/node-red:3-lts` | `nodered/node-red:latest` | **`nodered/node-red:3-lts`** | LTS tag guarantees stability; matches spec requirement |
| Node-RED data | Bind mount `./nodered/data:/data` | Named volume | **Bind mount** | Flows must be visible/editable on host filesystem; survives `down` |
| Mosquitto data | Named volume `mosquitto_data` | Bind mount | **Named volume** | Broker data is internal; named volume avoids host permission issues |
| Mosquitto config mount | `:ro` (read-only) | `:rw` | **`:ro`** | Config should not be modified at runtime; security best practice |
| Node install | Build-time `RUN npm install` | Runtime `npm install` in entrypoint | **Build-time** | Faster startup, deterministic image, nodes available immediately |
| Network | Default compose network | Explicit custom network | **Default compose network** | Two services only; default network provides DNS resolution by service name |

## Data Flow

```
Host (localhost:1880) ──→ nodered:1880 (HTTP UI)
Host (localhost:1883) ──→ mosquitto:1883 (MQTT)

nodered ──[docker network: hostname "mosquitto"]──→ mosquitto:1883
     │                                                    │
     └── /data ←── bind mount ←── deploy/nodered/data/   │
                                                        └── /mosquitto/data ←── named volume: mosquitto_data
                                                        └── /mosquitto/log  ←── named volume: mosquitto_logs
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `deploy/docker-compose.yml` | Create | Compose v2 file with mosquitto + nodered services |
| `deploy/nodered/Dockerfile` | Create | Custom Node-RED image with 4 preinstalled nodes |
| `deploy/mosquitto/config/mosquitto.conf` | Create | Broker config: port 1883, anonymous, persistence |
| `deploy/nodered/data/` | Create (dir) | Empty bind mount target for flows/settings |
| `deploy/README.md` | Create | Setup docs, quick start, troubleshooting |
| `.gitignore` | Modify | Add `deploy/nodered/data/flows_cred.json` and `deploy/mosquitto/log/` |

## Exact File Contents

### `deploy/docker-compose.yml`

```yaml
services:
  mosquitto:
    image: eclipse-mosquitto:2
    ports:
      - "1883:1883"
    volumes:
      - ./mosquitto/config/mosquitto.conf:/mosquitto/config/mosquitto.conf:ro
      - mosquitto_data:/mosquitto/data
      - mosquitto_logs:/mosquitto/log
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "mosquitto_sub", "-t", "$SYS/broker/uptime", "-C", "1", "-E"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 5s

  nodered:
    build: ./nodered
    ports:
      - "1880:1880"
    volumes:
      - ./nodered/data:/data
    depends_on:
      mosquitto:
        condition: service_healthy
    environment:
      - TZ=${TZ:-America/Argentina/Buenos_Aires}
    restart: unless-stopped

volumes:
  mosquitto_data:
  mosquitto_logs:
```

### `deploy/nodered/Dockerfile`

```dockerfile
FROM nodered/node-red:3-lts

RUN npm install --no-audit --no-fund \
    node-red-dashboard \
    node-red-contrib-tfjs-coco-ssd \
    node-red-node-email \
    node-red-contrib-telegrambot
```

### `deploy/mosquitto/config/mosquitto.conf`

```
listener 1883 0.0.0.0
allow_anonymous true
persistence true
persistence_location /mosquitto/data/
log_dest file /mosquitto/log/mosquitto.log
```

### `.gitignore` (append)

```
deploy/nodered/data/flows_cred.json
deploy/mosquitto/log/
```

## Implementation Order

1. **Create directory structure**: `mkdir -p deploy/mosquitto/config deploy/nodered/data`
2. **Write config files**: `mosquitto.conf`, `Dockerfile`, `docker-compose.yml`
3. **Create README.md**: Full documentation
4. **Update .gitignore**: Add credential and log exclusions
5. **Build and verify**: `cd deploy && docker compose up -d --build`
6. **Run verification commands**: All 8 commands from spec

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Structure | R-1 directory tree | `ls -R deploy/` matches expected tree |
| Compose | R-2 valid compose file | `docker compose config` exits 0 |
| Mosquitto | R-3 config, R-7 network | `mosquitto_sub` test from another container |
| Node-RED | R-4, R-5 nodes | `npm ls` inside container + HTTP 200 on :1880 |
| Persistence | R-6 bind + named volumes | `touch` file, `down`, verify file exists |
| Read-only | R-7 config mount | `docker inspect` mount mode |
| Docs | R-8 README | `test -f deploy/README.md` + content checks |

## Migration / Rollout

No migration required. This is greenfield infrastructure. Rollback = `rm -rf deploy/` + `docker compose down -v` from deploy directory.

## Open Questions

- [ ] Timezone: Spec says "local timezone" — using `America/Argentina/Buenos_Aires` as default via env var `${TZ:-...}`. Confirm if this matches the deployment location.
- [ ] Health check: `mosquitto_sub -t '$SYS/broker/uptime'` requires `$SYS` messages to be enabled (default in Mosquitto 2.x). If disabled, fallback to `["CMD-SHELL", "nc -z localhost 1883"]`.
