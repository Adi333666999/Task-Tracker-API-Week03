# Task Tracker API — End-to-End DevOps & Kubernetes Pipeline

A cloud-native REST API built with Flask and MySQL, containerized with security hardening, and deployed automatically to Kubernetes via a 3-stage GitHub Actions CI/CD pipeline using a self-hosted runner.

---

## Architecture Overview

### CI/CD Delivery Flow
```text
Developer Push (main)
       │
       ▼
GitHub Actions: [Job 1: Test] ──► Ephemeral MySQL 8.0 Service + Pytest Integration Tests
       │
       ▼ (Needs: test)
GitHub Actions: [Job 2: Build & Push] ──► Non-Root Docker Image ──► Docker Hub (:sha & :latest)
       │
       ▼ (Needs: build-and-push)
GitHub Actions: [Job 3: Deploy] ──► Self-Hosted Runner ──► kubectl apply + SHA Rolling Update
```

### Kubernetes Runtime Topology
```text
External Client (NodePort :30079)
       │
       ▼
[Service: task-tracker-api-svc]
       │
       ▼
[Deployment: task-tracker-api (2 Replicas, Gunicorn, UID 10001)]
       │  ├── Readiness & Liveness Probes (/health -> SELECT 1)
       │  └── Credentials injected via Kubernetes Secret (db-secret)
       ▼
[Headless Service: mysql (:3306)]
       │
       ▼
[StatefulSet: mysql (mysql:8.0)] ──► [PVC: mysql-storage-mysql-0 (1Gi)]
```

---

## Tech Stack

* **Application:** Python 3.12, Flask, Gunicorn, `mysql-connector-python`
* **Database:** MySQL 8.0 (`StatefulSet` + `PersistentVolumeClaim`)
* **Containerization:** Docker (`python:3.12-slim`, multi-layer caching, non-root user)
* **CI/CD:** GitHub Actions (GitHub-hosted runners + local Linux self-hosted runner)
* **Orchestration:** Kubernetes (`Deployment`, `StatefulSet`, `Service`, `Secret`, `PVC`)

---

## Engineering & DevOps Highlights

* **Container Hardening & Layer Caching:** Uses `python:3.12-slim`, installs pinned dependencies before copying source code for optimal cache hits, and runs Gunicorn as a dedicated non-root user (`UID 10001`).
* **Startup Resilience:** Implements a bounded database initialization retry loop (`init_db`) at module load time so Gunicorn workers survive cold database startup race conditions without triggering `CrashLoopBackOff`.
* **Deep Health Probes:** `/health` executes a live `SELECT 1` query against MySQL, enabling Kubernetes Readiness and Liveness probes (tuned with `timeoutSeconds: 5`) to route traffic only to healthy pods.
* **Immutable Deployments:** Every build pushes an image tagged with `${{ github.sha }}`. The CD job updates the running `Deployment` with the exact commit SHA (`kubectl set image`) and verifies zero-downtime completion via `kubectl rollout status`.
* **Fail-Fast CI Testing:** Pull requests and pushes run `pytest` against an ephemeral `mysql:8.0` service container before any image is built or pushed.

---

## Project Structure

```text
.
├── .github/
│   └── workflows/
│       └── ci.yaml               # 3-stage CI/CD pipeline (test -> build-and-push -> deploy)
├── k8s/
│   ├── api-deployment.yaml       # 2-replica Flask Deployment with probes & resource limits
│   ├── api-service.yaml          # NodePort Service exposing port 5000 -> 30079
│   ├── mysql-service.yaml        # Headless Service for StatefulSet DNS resolution
│   └── mysql-statefulset.yaml    # MySQL 8.0 StatefulSet with 1Gi volumeClaimTemplate
├── app.py                        # Flask CRUD API with /health endpoint & DB retry logic
├── test_app.py                   # Pytest integration test suite
├── Dockerfile                    # Hardened non-root production image
├── .dockerignore                 # Excludes local virtual environments and git metadata
├── docker-compose.yaml           # Local multi-container smoke-testing stack
└── requirements.txt              # Pinned Python dependencies
```

---

## Local Quickstart (Docker Compose)

1. **Spin up the local API and MySQL stack:**
   ```bash
   docker compose up --build -d
   ```
2. **Verify health and CRUD endpoints:**
   ```bash
   curl http://localhost:5000/health
   curl -X POST http://localhost:5000/tasks \
     -H "Content-Type: application/json" \
     -d '{"title": "Deploy to Kubernetes"}'
   curl http://localhost:5000/tasks
   ```
3. **Tear down cleanly:**
   ```bash
   docker compose down -v
   ```

---

## Kubernetes Deployment

1. **Create the database Secret in your cluster** (kept out of version control):
   ```bash
   kubectl create secret generic db-secret \
     --from-literal=DB_USER=root \
     --from-literal=DB_PASSWORD=<your-password> \
     --from-literal=DB_NAME=taskdb \
     --from-literal=MYSQL_ROOT_PASSWORD=<your-password>
   ```
2. **Apply the Kubernetes manifests:**
   ```bash
   kubectl apply -f k8s/
   ```
3. **Verify Pods, PVC, and Services:**
   ```bash
   kubectl get pods,pvc,svc
   ```
4. **Test the live Kubernetes endpoint:**
   ```bash
   curl http://localhost:30079/health
   ```

---

## Troubleshooting Lessons Learned

* **WSL2 Filesystem I/O:** Running MySQL volumes on `/mnt/c` caused multi-minute InnoDB initialization delays; moving the project into native WSL2 Linux storage (`~/projects`) cut startup time to seconds.
* **Kubernetes Probe Timeouts:** Default 1-second HTTP probe timeouts caused false `Client.Timeout` liveness restarts during initial DB connections; configuring `timeoutSeconds: 5` and `failureThreshold: 5` stabilized rollouts.
* **Immutable Selectors:** Updating `spec.selector.matchLabels` on an existing `Deployment` requires recreating the resource (`kubectl delete deployment`), as Kubernetes selectors are immutable after creation.
