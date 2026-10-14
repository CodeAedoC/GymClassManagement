# Gym & Fitness Facility Membership Portal

[![CI/CD & DevSecOps Pipeline](https://github.com/CodeAedoC/GymClassManagement/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/CodeAedoC/GymClassManagement/actions/workflows/ci-cd.yml)

A production-ready SaaS Gym & Fitness Facility Management Portal featuring automated attendance streaks protected by lives, automated late-cancellation penalty tiers, support appeal workflows, Celery background scheduling, containerization, DevSecOps scanning, AWS infrastructure as code, Kubernetes Helm packaging, and Prometheus/Grafana observability.

---

## 1. System Architecture

```text
                  +----------------------------------------------+
                  |         React + Vite + Tailwind UI           |
                  |  (Streak Flame, 3-Hearts Container, Modals)  |
                  +-----------------------+----------------------+
                                          |
                                          v
                  +----------------------------------------------+
                  |            FastAPI ASGI Backend              |
                  |     (/health, /ready, /metrics, REST API)    |
                  +-----------+----------------------+-----------+
                              |                      |
                              v                      v
                +-------------------------+  +-------------------+
                | PostgreSQL 16 (Alembic) |  |   Redis 7 Broker  |
                +-------------------------+  +---------+---------+
                                                       |
                                                       v
                                             +-------------------+
                                             |   Celery Worker   |
                                             | (Cron Evaluations)|
                                             +-------------------+
```

---

## 2. Core Features & Business Logic

### A. Weekly Target Commitment & Streak Protection
- **Target Commitment**: Members set a weekly target of $N$ days ($1 \le N \le 7$).
- **Weekly Evaluation (Sunday 23:59 UTC)**:
  - **Success (`attended >= target`)**: Streak increments (`current_streak_weeks += 1`).
  - **Achievements & Life Cap**: Triggering achievements (e.g. `OVER_ACHIEVER_1_WEEK` or `ATTENDED_5_PLUS_CLASSES`) awards +1 protective life **only if** `lives_earned_this_week < 1` and `lives_remaining < 3`.
  - **Deficit (`attended < target`)**:
    - If `lives_remaining > 0`: Deducts 1 life while maintaining the streak.
    - If `lives_remaining == 0`: Resets streak to 0 and restores default 3 lives.

### B. Late Cancellation & Penalty Escalation Engine
- **Grace Window**:
  - Cancellations $\ge 2$ hours before class: Clean cancellation, 0 penalty points.
  - Cancellations $< 2$ hours before class: +1 penalty point applied.
- **Escalation Tiers**:
  - **Tier 1 (0–2 Points)**: No restrictions (`restriction_status = NONE`).
  - **Tier 2 (3 Points)**: `SAME_DAY_ONLY` booking ban for 7 days (cannot book slots $> 2$ hours in advance).
  - **Tier 3 (Offense while restricted)**: Active restriction extended to 14 days.
  - **Tier 4 (Further offenses)**: Account `FROZEN` for 7 days (all bookings blocked).
- **Monthly Reset**: On the 1st of every month at 00:00 UTC, penalty points reset to 0.
- **Support Appeals**: Customer support ticket approval immediately clears all penalty points and lifts bans.

---

## 3. Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend** | Python 3.12, FastAPI, Uvicorn, SQLAlchemy 2.0, Alembic, Celery, Redis |
| **Frontend** | React 18, Vite, Tailwind CSS, Lucide Icons |
| **Database** | PostgreSQL 16 (Relational tables with foreign key constraints) |
| **Containers** | Docker (Multi-stage non-root builds), Docker Compose |
| **CI/CD & Security** | GitHub Actions, AquaSecurity Trivy (CVE scanner), GHCR |
| **Infrastructure as Code** | Terraform (AWS VPC with 4 subnets across 2 AZs, NAT Gateway, EKS Cluster) |
| **Orchestration & Packaging**| Kubernetes, Helm 3, Ingress, Horizontal Pod Autoscaler (HPA) |
| **Observability** | Prometheus (`/metrics`), ServiceMonitor, Grafana Custom Dashboard |

---

## 4. Quick Start (Local Docker Compose)

### Prerequisites
- Docker Desktop / Docker Engine & Docker Compose

### Run Application
```bash
# Clone the repository
git clone https://github.com/CodeAedoC/GymClassManagement.git
cd GymClassManagement

# Start the full stack
docker compose up --build -d
```

### Access Points
- **Frontend Dashboard**: [http://localhost:3100](http://localhost:3100)
- **Backend API Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check Endpoint**: [http://localhost:8000/health](http://localhost:8000/health)
- **Readiness Check Endpoint**: [http://localhost:8000/ready](http://localhost:8000/ready)
- **Prometheus Metrics (Raw)**: [http://localhost:8000/metrics](http://localhost:8000/metrics)
- **Prometheus UI**: [http://localhost:9090](http://localhost:9090)
- **Grafana Visual Dashboard**: [http://localhost:3200/d/fg17pd20blz40f/gym-portal-observability-and-domain-metrics](http://localhost:3200/d/fg17pd20blz40f/gym-portal-observability-and-domain-metrics) *(Direct access enabled — opens live dashboard instantly with no login required)*

To stop the stack:
```bash
docker compose down
```

---

## 5. Automated Testing Suite

The backend contains **19 comprehensive test cases** validating business rules with deterministic time freezing (`freezegun`):

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run pytest suite
pytest -v tests/test_gym_portal.py
```

### Mandatory Test Coverage:
1. `test_01_health_and_ready_endpoints` — Verifies `/health` (200 OK) and `/ready` (DB ping).
2. `test_02_create_booking_success` — Verifies reservation when capacity is available.
3. `test_03_booking_exceeds_capacity_failure` — Asserts 400 Bad Request on full slot.
4. `test_04_duplicate_booking_failure` — Asserts 409 Conflict for double booking.
5. `test_05_inactive_member_booking_failure` — Asserts 403 Forbidden for deactivated accounts.
6. `test_06_cancellation_grace_period_success` — Cancelling $\ge 2$ hours applies 0 penalties.
7. `test_07_late_cancellation_applies_penalty_point` — Cancelling $< 2$ hours applies +1 penalty point.
8. `test_08_no_show_applies_penalty_point` — No-show marks penalty point.
9. `test_09_penalty_tier2_same_day_ban_trigger` — 3 penalty points triggers 7-day `SAME_DAY_ONLY` ban.
10. `test_10_same_day_ban_rejects_advance_booking` — Blocks advance booking (> 2 hrs) under ban.
11. `test_11_same_day_ban_allows_short_notice_booking` — Permits short notice booking ($\le 2$ hrs).
12. `test_12_repeated_offense_extends_ban_and_freezes_account` — Validates 14-day extension and `FROZEN` status.
13. `test_13_customer_support_ticket_clears_penalty_and_ban` — Support resolution clears all restrictions.
14. `test_14_weekly_target_achieved_increments_streak` — Target reach increments streak +1.
15. `test_15_streak_deficit_consumes_life_and_protects_streak` — Target missed consumes 1 life, saves streak.
16. `test_16_exhausted_lives_resets_streak_to_zero` — Zero lives breaks streak to 0, resets 3 lives.
17. `test_17_achievement_awards_life_respects_max_cap_of_3` — Enforces strict cap of 3 lives max.
18. `test_18_weekly_earned_life_limit_enforced` — Enforces maximum 1 earned life per weekly cycle.
19. `test_19_monthly_cron_resets_penalty_points` — Monthly reset task resets points to 0.

---

## 6. Infrastructure as Code (Terraform)

Located in `terraform/`:
- **VPC (`vpc.tf`)**: 2 Public and 2 Private Subnets across 2 Availability Zones (`us-west-2a`, `us-west-2b`), Internet Gateway, and NAT Gateway.
- **EKS (`eks.tf`)**: AWS EKS Cluster with IAM Roles and managed node group (`t3.medium`).

```bash
cd terraform
terraform init
terraform plan
```
*(Execution plan records 22 cloud resources planned with 0 errors in `terraform/terraform_plan_output.txt`)*

---

## 7. Kubernetes & Helm Deployment

Located in `helm/gym-portal/` and `k8s/`:
- **Namespace**: `gym-portal` (`k8s/namespace.yaml`)
- **Deployments**: Backend and frontend with $\ge 2$ replicas, liveness/readiness probes, and non-root security context.
- **Autoscaling (HPA)**: Horizontal Pod Autoscaler targeting CPU utilization > 70%.
- **Routing**: Ingress routing `/` to Frontend and `/api` to Backend.

```bash
# Apply namespace
kubectl apply -f k8s/namespace.yaml

# Install with Helm
helm upgrade --install gym-portal helm/gym-portal -n gym-portal
```

---

## 8. Observability & Monitoring
 
- **Prometheus Metrics**: Exposed on `/metrics` with custom gauges and counters:
  - `gym_bookings_total` (Counter)
  - `gym_late_cancellations_total` (Counter)
  - `gym_active_streaks_total` (Gauge)
  - `gym_restricted_members_total` (Gauge)
  - `http_requests_total` and `http_request_duration_seconds` (HTTP traffic & latency)
- **Prometheus Server**: Scrapes the backend every 5 seconds (accessible at `http://localhost:9090`).
- **Grafana Dashboard**: Automatically provisioned on startup with pre-built panels at `http://localhost:3200`:
  - API Request Rate (`req/sec`)
  - API Latency (95th Percentile)
  - Active Member Streaks
  - Late Cancellations Total
- **Kubernetes / Helm Manifests**: Located in `monitoring/` including `service-monitor.yaml`, `values.yaml`, and `grafana-dashboard.json`.
