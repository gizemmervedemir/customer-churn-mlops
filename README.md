# Customer Churn Prediction — End-to-End MLOps Pipeline

This repository contains an end-to-end **MLOps system** for customer churn prediction built on the IBM Telco Customer Churn dataset.
The focus of the project is **production-grade ML lifecycle management**, not just model training.

The system demonstrates:

* Containerized ML services with Docker
* CI/CD automation with Jenkins
* GitHub Webhook–based pipeline triggering
* Data drift detection (numeric & categorical)
* Automatic retraining and model reloading
* Model artifact versioning with MinIO
* Lightweight UI for live monitoring and demo

---

## High-Level Architecture

```
GitHub (Push)
   │
   ▼
GitHub Webhook
   │
   ▼
Jenkins Pipeline
   │
   ├─ Build & Deploy (Docker Compose)
   ├─ Drift Detection
   ├─ Conditional Retraining
   └─ API Model Reload
   │
   ▼
Dockerized Services
   ├─ FastAPI (Model Serving)
   ├─ Streamlit (UI)
   ├─ PostgreSQL (Metadata)
   └─ MinIO (Model Artifacts)
```

---

## Tech Stack

**Infrastructure & DevOps**

* Docker & Docker Compose
* Jenkins (CI/CD)
* GitHub Webhooks
* Rocky Linux (VM)

**Backend & ML**

* Python
* FastAPI
* scikit-learn (RandomForest)
* Pandas / NumPy

**MLOps**

* Drift detection:

  * PSI (numeric features)
  * L1 distance (categorical features)
* Automated retraining pipeline
* Model versioning & artifact storage (MinIO)

**UI**

* Streamlit (demo & monitoring UI)

---

## Dataset

* **IBM Telco Customer Churn Dataset**
* Binary classification: churn vs non-churn
* Mixed feature types:

  * Numeric (tenure, charges, etc.)
  * Categorical (contract type, payment method, services, etc.)

---

## Project Structure

```
customer-churn-mlops/
│
├─ apps/
│   ├─ api/            # FastAPI backend (prediction, drift, reload)
│   └─ ui/             # Streamlit UI
│
├─ infra/
│   └─ compose/        # Docker Compose & service definitions
│
├─ scripts/            # Utility / training scripts
│
├─ Jenkinsfile         # CI/CD pipeline definition
├─ .env.example        # Environment variable template
├─ README.md
```

---

## Services & Ports

| Service      | Port        |
| ------------ | ----------- |
| FastAPI API  | 8000        |
| Streamlit UI | 8501        |
| Jenkins      | 8080        |
| MinIO        | 9000 / 9001 |
| PostgreSQL   | 5432        |

---

## CI/CD Pipeline (Jenkins)

The Jenkins pipeline is fully automated and triggered by **GitHub push events**.

### Pipeline Steps

1. **Checkout**

   * Pull latest code from GitHub

2. **Environment Setup**

   * Generate `.env` from Jenkins credentials

3. **Service Startup**

   * Start PostgreSQL & MinIO
   * Initialize MinIO buckets
   * Start API & UI containers

4. **Smoke Tests**

   * `/health`
   * `/predict/schema`

5. **Drift Detection**

   * `/drift/check`
   * Numeric: PSI
   * Categorical: L1 distance

6. **Conditional Retraining**

   * Triggered only if drift is detected
   * New model version is trained and uploaded to MinIO

7. **Model Reload**

   * API reloads the latest model without downtime

8. **Final Prediction Test**

   * Ensures the new model is serving correctly

---

## Drift Detection Strategy

* **Numeric features**

  * Population Stability Index (PSI)
* **Categorical features**

  * L1 distance between distributions
* Configurable thresholds
* Drift results are persisted and visible in logs/UI

If drift is detected:

* Retraining is automatically triggered
* New model version is deployed

---

## Model Versioning

* Each training run generates a versioned model:

  ```
  vYYYYMMDD-HHMMSS
  ```
* Stored in MinIO (S3-compatible)
* API always exposes the active `model_version`

---

## Streamlit UI

The UI is intentionally lightweight and used for:

* Health & schema checks
* Manual prediction demo
* Drift monitoring visualization

> The core value of the project lies in the backend automation and CI/CD pipeline, not the UI layer.

---

## How to Run Locally

```bash
cd infra/compose
docker compose up -d
```

Access:

* API: [http://localhost:8000](http://localhost:8000)
* UI: [http://localhost:8501](http://localhost:8501)
* Jenkins: [http://localhost:8080](http://localhost:8080)

---

## Key Takeaways

* Demonstrates a **realistic MLOps workflow**
* Fully automated ML lifecycle
* Production-oriented design
* Drift-aware model management
* CI/CD-driven ML retraining

---

## Future Improvements

* Richer UI dashboards
* Model performance tracking over time
* Canary / A/B model deployments
* Integration with cloud-native services (EKS, GKE, S3)
