pipeline {
  agent any

  environment {
    COMPOSE_DIR = "infra/compose"
    // Jenkins container içinden host üzerindeki API’ye erişim:
    API_BASE    = "http://host.docker.internal:8000"
    ENV_FILE    = "../../.env"
  }

  options {
    disableConcurrentBuilds()
    timestamps()
  }

  stages {

    stage("Checkout ok") {
      steps {
        sh 'pwd && ls -la'
      }
    }

    stage("Create .env at repo root") {
      steps {
        withCredentials([
          string(credentialsId: 'CHURN_API_KEY',       variable: 'API_KEY'),

          string(credentialsId: 'POSTGRES_DB',         variable: 'POSTGRES_DB'),
          string(credentialsId: 'POSTGRES_USER',       variable: 'POSTGRES_USER'),
          string(credentialsId: 'POSTGRES_PASSWORD',   variable: 'POSTGRES_PASSWORD'),

          string(credentialsId: 'MINIO_ROOT_USER',     variable: 'MINIO_ROOT_USER'),
          string(credentialsId: 'MINIO_ROOT_PASSWORD', variable: 'MINIO_ROOT_PASSWORD'),
          string(credentialsId: 'MINIO_BUCKET',        variable: 'MINIO_BUCKET')
        ]) {
          sh '''
            set -e

            # .env must live at repo root (workspace root)
            cat > .env << EOF
API_KEY=${API_KEY}
POSTGRES_DB=${POSTGRES_DB}
POSTGRES_USER=${POSTGRES_USER}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
MINIO_ROOT_USER=${MINIO_ROOT_USER}
MINIO_ROOT_PASSWORD=${MINIO_ROOT_PASSWORD}
MINIO_BUCKET=${MINIO_BUCKET}
MINIO_ENDPOINT=http://minio:9000
EOF

            echo ".env created at: $(pwd)/.env"
            ls -la .env
            grep -E "^(POSTGRES_DB|POSTGRES_USER|MINIO_ROOT_USER|MINIO_BUCKET|MINIO_ENDPOINT)=" .env || true
          '''
        }
      }
    }

    stage("Bring stack up (stable CI)") {
      steps {
        sh """
          set -e
          cd ${COMPOSE_DIR}

          # Compose MUST read repo-root .env
          test -f ${ENV_FILE}

          # Start deps first (avoid race)
          docker compose --env-file ${ENV_FILE} up -d postgres minio

          # Wait postgres healthy
          echo "Waiting postgres healthy..."
          for i in \$(seq 1 60); do
            docker compose --env-file ${ENV_FILE} ps postgres | grep -qi healthy && break || true
            sleep 2
          done
          docker compose --env-file ${ENV_FILE} ps postgres | grep -qi healthy

          # Wait minio ready (IMPORTANT: use service name, not localhost)
          echo "Waiting minio ready..."
          for i in \$(seq 1 60); do
            curl -sSf http://minio:9000/minio/health/ready >/dev/null 2>&1 && break || true
            sleep 2
          done
          curl -sSf http://minio:9000/minio/health/ready >/dev/null

          # Run minio_init as one-shot (don't let it hang)
          echo "Running minio_init..."
          docker compose --env-file ${ENV_FILE} up -d minio_init || true

          # Wait minio_init to exit (max 60s)
          echo "Waiting minio_init to finish..."
          for i in \$(seq 1 30); do
            docker compose --env-file ${ENV_FILE} ps -a minio_init | grep -Eqi '(Exit 0|exited \\(0\\))' && break || true
            sleep 2
          done

          # Start API + UI
          docker compose --env-file ${ENV_FILE} up -d api ui

          docker compose --env-file ${ENV_FILE} ps
        """
      }
    }

    // ✅ NEW: prove current running model version BEFORE anything
    stage("Proof: Model version (BEFORE)") {
      steps {
        withCredentials([string(credentialsId: 'CHURN_API_KEY', variable: 'CHURN_API_KEY')]) {
          sh """
            set -e
            echo "=== MODEL VERSION (BEFORE) ==="
            curl -sS ${API_BASE}/predict/schema -H "X-API-Key: ${CHURN_API_KEY}" | \
              python -c "import sys,json; print(json.load(sys.stdin).get('model_version'))"
          """
        }
      }
    }

    stage("Smoke: Health & Schema") {
      steps {
        withCredentials([string(credentialsId: 'CHURN_API_KEY', variable: 'CHURN_API_KEY')]) {
          sh """
            set -e
            echo "--- health ---"
            curl -sS ${API_BASE}/health

            echo "\\n--- schema ---"
            curl -sS ${API_BASE}/predict/schema -H "X-API-Key: ${CHURN_API_KEY}"
          """
        }
      }
    }

    stage("Drift check") {
      steps {
        withCredentials([string(credentialsId: 'CHURN_API_KEY', variable: 'CHURN_API_KEY')]) {
          sh """
            set -e
            curl -sS "${API_BASE}/drift/check?n=200" \
              -H "X-API-Key: ${CHURN_API_KEY}" | tee drift.json

            echo "\\n=== DRIFT SUMMARY (one-line) ==="
            python - << 'PY'
import json
d=json.load(open("drift.json"))
s=d.get("summary",{})
print("drift_detected=", s.get("drift_detected"), "| n_current=", s.get("n_current"), "| drifted_features=", len(s.get("drifted_features",[])))
PY
          """
        }
      }
    }

    stage("Retrain if drift detected") {
      steps {
        script {
          def out = sh(script: "cat drift.json", returnStdout: true).trim()
          if (!out.contains('"drift_detected":true')) {
            echo "No drift detected (or not enough data). Skipping retrain."
            return
          }

          echo "Drift detected → retraining model"
          sh """
            set -e
            cd ${COMPOSE_DIR}
            docker compose --env-file ${ENV_FILE} --profile train run --rm trainer
          """

          // ✅ NEW: after retrain, show what's written as latest in MinIO (latest.json)
          sh """
            set -e
            echo "=== LATEST AFTER RETRAIN (from MinIO latest.json) ==="

            # Read required vars from env_file without printing secrets
            MINIO_ROOT_USER=\$(grep -E '^MINIO_ROOT_USER=' ${ENV_FILE} | cut -d= -f2-)
            MINIO_ROOT_PASSWORD=\$(grep -E '^MINIO_ROOT_PASSWORD=' ${ENV_FILE} | cut -d= -f2-)
            MINIO_BUCKET=\$(grep -E '^MINIO_BUCKET=' ${ENV_FILE} | cut -d= -f2-)

            # Pull latest.json via MinIO S3-compatible API (needs no mc)
            curl -sS -u "\${MINIO_ROOT_USER}:\${MINIO_ROOT_PASSWORD}" \\
              "http://minio:9000/\${MINIO_BUCKET}/churn_model/latest.json" | \\
              python -c "import sys,json; print(json.load(sys.stdin).get('model_version'))"
          """
        }
      }
    }

    stage("Reload model in API") {
      steps {
        withCredentials([string(credentialsId: 'CHURN_API_KEY', variable: 'CHURN_API_KEY')]) {
          sh """
            set -e
            echo "=== RELOAD RESPONSE ==="
            curl -sS -X POST ${API_BASE}/model/reload \
              -H "X-API-Key: ${CHURN_API_KEY}" | tee reload.json
          """
        }
      }
    }

    // ✅ NEW: prove running model switched AFTER reload
    stage("Proof: Model version (AFTER reload)") {
      steps {
        withCredentials([string(credentialsId: 'CHURN_API_KEY', variable: 'CHURN_API_KEY')]) {
          sh """
            set -e
            echo "=== MODEL VERSION (AFTER reload) ==="
            curl -sS ${API_BASE}/predict/schema -H "X-API-Key: ${CHURN_API_KEY}" | \
              python -c "import sys,json; print(json.load(sys.stdin).get('model_version'))"
          """
        }
      }
    }

    stage("Final smoke: Predict") {
      steps {
        withCredentials([string(credentialsId: 'CHURN_API_KEY', variable: 'CHURN_API_KEY')]) {
          sh """
            set -e
            echo "=== PREDICT (smoke) ==="
            curl -sS -X POST ${API_BASE}/predict \
              -H "Content-Type: application/json" \
              -H "X-API-Key: ${CHURN_API_KEY}" \
              -d '{"features":{"SeniorCitizen":0,"tenure":10,"MonthlyCharges":80,"TotalCharges":500,"gender":"Female","Partner":"Yes","Dependents":"No","PhoneService":"Yes","MultipleLines":"No","InternetService":"DSL","OnlineSecurity":"No","OnlineBackup":"Yes","DeviceProtection":"No","TechSupport":"No","StreamingTV":"No","StreamingMovies":"No","Contract":"Month-to-month","PaperlessBilling":"Yes","PaymentMethod":"Electronic check"}}' | tee predict.json

            echo "\\n=== PREDICT SUMMARY (one-line) ==="
            python - << 'PY'
import json
p=json.load(open("predict.json"))
print("prediction=", p.get("prediction"), "| prob=", p.get("probability"), "| model_version=", p.get("model_version"))
PY
          """
        }
      }
    }
  }

  post {
    always {
      echo "Pipeline finished."
    }
    failure {
      echo "Pipeline failed; showing compose status/logs..."
      sh """
        set +e
        cd ${COMPOSE_DIR}
        docker compose --env-file ${ENV_FILE} ps || true
        docker compose --env-file ${ENV_FILE} logs --tail=200 minio minio_init postgres api ui || true
      """
    }
  }
}
