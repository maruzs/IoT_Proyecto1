# Tasks: Spec 00 — Infraestructura de Contenedores (Docker Compose)

## Task 1: Create deploy/ directory structure

**Description**: Create the full directory tree required by R-1 of the spec. All subdirectories must exist before any config files are written.

**Commands**:
```bash
mkdir -p deploy/mosquitto/config deploy/nodered/data
```

**Files affected**:
- `deploy/` (new directory)
- `deploy/mosquitto/config/` (new directory)
- `deploy/nodered/data/` (new directory)

**Verification**:
```bash
ls -R deploy/
# Must show: deploy/docker-compose.yml (not yet), deploy/mosquitto/config/, deploy/nodered/data/, deploy/README.md (not yet)
# At minimum: mosquitto/config/ and nodered/data/ must exist
```

**Dependencies**: None (first task)

---

## Task 2: Create mosquitto.conf

**Description**: Write the Mosquitto broker configuration file at `deploy/mosquitto/config/mosquitto.conf` per spec A-3. Must enable anonymous access, port 1883 on all interfaces, and disk persistence.

**File contents** (exact):
```
listener 1883 0.0.0.0
allow_anonymous true
persistence true
persistence_location /mosquitto/data/
log_dest file /mosquitto/log/mosquitto.log
```

**Files affected**:
- `deploy/mosquitto/config/mosquitto.conf` (new file)

**Verification**:
```bash
cat deploy/mosquitto/config/mosquitto.conf
# Must contain all 5 lines above
grep "allow_anonymous true" deploy/mosquitto/config/mosquitto.conf
grep "persistence true" deploy/mosquitto/config/mosquitto.conf
```

**Dependencies**: Task 1

---

## Task 3: Create docker-compose.yml

**Description**: Write the Docker Compose v2 file at `deploy/docker-compose.yml` per spec A-1 and design. Must define exactly two services (mosquitto, nodered) with correct ports, volumes, health checks, and dependency ordering. No `version:` key (Compose spec format).

**Key requirements**:
- Mosquitto: `eclipse-mosquitto:2`, port 1883, read-only config mount, named volumes for data/logs, healthcheck
- Node-RED: build from `./nodered`, port 1880, bind mount `./nodered/data:/data`, `depends_on` mosquitto healthy, TZ env var
- Named volumes: `mosquitto_data`, `mosquitto_logs`

**Files affected**:
- `deploy/docker-compose.yml` (new file)

**Verification**:
```bash
cd deploy && docker compose config
# Must exit 0 with valid resolved config
cd deploy && docker compose config | grep -E "mosquitto|nodered"
# Must show both services
```

**Dependencies**: Task 1, Task 2 (mosquitto.conf must exist for volume mount reference)

---

## Task 4: Create nodered/Dockerfile with pre-installed nodes

**Description**: Write the Dockerfile at `deploy/nodered/Dockerfile` per spec A-2 and design. Must extend `nodered/node-red:3-lts` and pre-install 4 npm packages at build time.

**File contents** (exact):
```dockerfile
FROM nodered/node-red:3-lts

RUN npm install --no-audit --no-fund \
    node-red-dashboard \
    node-red-contrib-tfjs-coco-ssd \
    node-red-node-email \
    node-red-contrib-telegrambot
```

**Files affected**:
- `deploy/nodered/Dockerfile` (new file)

**Verification**:
```bash
cd deploy && docker compose build nodered
# Must complete without errors
cd deploy && docker compose run --rm nodered npm ls --depth=0 2>/dev/null | grep -E "node-red-dashboard|tfjs-coco-ssd|node-red-node-email|telegrambot"
# Must show all 4 packages
```

**Dependencies**: Task 1

---

## Task 5: Create deploy/README.md

**Description**: Write comprehensive documentation at `deploy/README.md` per spec A-5 and R-8. Must include all required sections.

**Required sections**:
- Prerequisites (Docker v24+, Docker Compose v2+)
- Quick start (`cd deploy && docker compose up -d`)
- Access URLs (http://localhost:1880, localhost:1883)
- How to stop (`docker compose down`)
- Persistence behavior explanation (bind mount vs named volume)
- Resource requirements (Mosquitto: 64MB RAM, Node-RED: 256MB+ RAM)
- Troubleshooting (port conflicts, permission issues on bind mounts)
- How to verify services are running

**Files affected**:
- `deploy/README.md` (new file)

**Verification**:
```bash
test -f deploy/README.md && echo "EXISTS" || echo "MISSING"
grep -c "Prerequisites\|Quick start\|Troubleshooting\|Persistence" deploy/README.md
# Must find all required section headers
```

**Dependencies**: Task 1 (can be done in parallel with Tasks 2-4)

---

## Task 6: Update .gitignore for deploy/ artifacts

**Description**: Append entries to the project `.gitignore` to exclude sensitive credentials and generated logs per spec A-6.

**Entries to append** (if not already present):
```
deploy/nodered/data/flows_cred.json
deploy/mosquitto/log/
```

**Files affected**:
- `.gitignore` (modified — append only)

**Verification**:
```bash
grep "deploy/nodered/data/flows_cred.json" .gitignore
grep "deploy/mosquitto/log/" .gitignore
# Both must be present
```

**Dependencies**: Task 1 (can be done in parallel with Tasks 2-5)

---

## Task 7: Verify end-to-end (docker compose up, connectivity, persistence)

**Description**: Run the full verification suite from the spec. Start services, test MQTT connectivity, test Node-RED HTTP, verify installed nodes, test persistence across restart, and confirm read-only config mount.

**Verification steps**:
```bash
# 1. Start services
cd deploy && docker compose up -d --build

# 2. Check both running
docker compose ps
# Both mosquitto and nodered must show "running"

# 3. Wait for health
sleep 10
docker compose ps
# mosquitto must show "healthy"

# 4. Test Mosquitto accepts connections
docker run --rm --network deploy_default eclipse-mosquitto:2 \
  mosquitto_pub -h mosquitto -t "test/topic" -m "hello"
# Must exit 0

# 5. Test Node-RED HTTP
curl -s -o /dev/null -w "%{http_code}" http://localhost:1880
# Must return 200 or 302

# 6. Verify installed nodes
docker exec deploy-nodered-1 npm ls --depth=0 2>/dev/null | grep -cE "node-red-dashboard|tfjs-coco-ssd|node-red-node-email|telegrambot"
# Must find 4 packages

# 7. Test persistence
touch deploy/nodered/data/test_persistence
docker compose down
test -f deploy/nodered/data/test_persistence && echo "PERSISTENCE OK" || echo "FAILED"
rm -f deploy/nodered/data/test_persistence

# 8. Verify directory tree
ls -R deploy/
# Must match R-1 structure
```

**Files affected**: None (verification only)

**Dependencies**: Tasks 1-6 (all must be complete)

---

## Review Workload Forecast

| Task | Estimated changed lines | Complexity |
|------|------------------------|------------|
| Task 1: Directory structure | 0 (mkdir only) | Trivial |
| Task 2: mosquitto.conf | 5 lines | Trivial |
| Task 3: docker-compose.yml | ~35 lines | Low |
| Task 4: nodered/Dockerfile | 6 lines | Low |
| Task 5: deploy/README.md | ~80-120 lines | Medium |
| Task 6: .gitignore update | 2 lines | Trivial |
| Task 7: E2E verification | 0 (commands only) | Medium (runtime) |
| **Total** | **~130-170 lines** | |

**Chained PR recommendation**: NOT recommended. Total changed lines (~130-170) is well below the 400-line threshold. This is a single cohesive change that should be one PR. All tasks are tightly coupled — the compose file references the Dockerfile and mosquitto.conf, and verification requires everything to exist. Splitting would create PRs that cannot be independently tested.

**Single PR structure**: One PR with all 7 tasks. Tasks 2-6 can be parallel commits within the PR. Task 7 is the verification step before merge.
