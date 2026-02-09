pipeline {
  agent any

  environment {
    COMPOSE_DIR = "infra/compose"
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
        sh '''
          set -e
          cd infra/compose

          test -f ../../.env

          docker compose --env-file ../../.env up -d postgres minio

          echo "Waiting postgres healthy..."
          for i in $(seq 1 60); do
            docker compose --env-file ../../.env ps postgres | grep -qi healthy && break || true
            sleep 2
          done
          docker compose --env-file ../../.env ps postgres | grep -qi healthy

          echo "Waiting minio ready..."
          for i in $(seq 1 60); do
            curl -sSf http://minio:9000/minio/health/ready >/dev/null 2>&1 && break || true
            sleep 2
          done
          curl -sSf http://minio:9000/minio/health/ready >/dev/null

          echo "Running minio_init..."
          docker compose --env-file ../../.env up -d minio_init || true

          echo "Waiting minio_init to finish..."
          for i in $(seq 1 30); do
            docker compose --env-file ../../.env ps -a minio_init | grep -Eqi '(Exit 0|exited \(0\))' && break || true
            sleep 2
          done

          docker compose --env-file ../../.env up -d api ui
          docker compose --env-file ../../.env ps
        '''
      }
    }

    stage("Proof: Model version (BEFORE)") {
      steps {
        withCredentials([string(credentialsId: 'CHURN_API_KEY', variable: 'CHURN_API_KEY')]) {
          sh '''
            set -e
            echo "=== MODEL VERSION (BEFORE) ==="
            curl -sS "$API_BASE/predict/schema" -H "X-API-Key: $CHURN_API_KEY" | tee schema_before.json >/dev/null

            # Extract model_version without python/jq
            ver=$(sed -n 's/.*"model_version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' schema_before.json | head -n 1)
            echo "$ver"
          '''
        }
      }
    }

    stage("Smoke: Health & Schema") {
      steps {
        withCredentials([string(credentialsId: 'CHURN_API_KEY', variable: 'CHURN_API_KEY')]) {
          sh '''
            set -e
            echo "--- health ---"
            curl -sS "$API_BASE/health"

            echo "\n--- schema ---"
            curl -sS "$API_BASE/predict/schema" -H "X-API-Key: $CHURN_API_KEY"
          '''
        }
      }
    }

    stage("Drift check") {
      steps {
        withCredentials([string(credentialsId: 'CHURN_API_KEY', variable: 'CHURN_API_KEY')]) {
          sh '''
            set -e
            curl -sS "$API_BASE/drift/check?n=200" -H "X-API-Key: $CHURN_API_KEY" | tee drift.json

            echo "\n=== DRIFT SUMMARY (one-line) ==="
            drift=$(sed -n 's/.*"drift_detected"[[:space:]]*:[[:space:]]*\(true\|false\).*/\1/p' drift.json | head -n 1)
            ncur=$(sed -n 's/.*"n_current"[[:space:]]*:[[:space:]]*\([0-9][0-9]*\).*/\1/p' drift.json | head -n 1)
            echo "drift_detected=$drift | n_current=$ncur"
          '''
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
          sh '''
            set -e
            cd infra/compose
            docker compose --env-file ../../.env --profile train run --rm trainer
          '''

          // Proof: show latest.json model_version from MinIO (no python/jq)
          sh '''
            set -e
            echo "=== LATEST AFTER RETRAIN (from MinIO latest.json) ==="

            MINIO_ROOT_USER=$(grep -E '^MINIO_ROOT_USER=' ../../.env | cut -d= -f2-)
            MINIO_ROOT_PASSWORD=$(grep -E '^MINIO_ROOT_PASSWORD=' ../../.env | cut -d= -f2-)
            MINIO_BUCKET=$(grep -E '^MINIO_BUCKET=' ../../.env | cut -d= -f2-)

            curl -sS -u "${MINIO_ROOT_USER}:${MINIO_ROOT_PASSWORD}" \
              "http://minio:9000/${MINIO_BUCKET}/churn_model/latest.json" | tee latest.json >/dev/null

            ver=$(sed -n 's/.*"model_version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' latest.json | head -n 1)
            echo "$ver"
          '''
        }
      }
    }

    stage("Reload model in API") {
      steps {
        withCredentials([string(credentialsId: 'CHURN_API_KEY', variable: 'CHURN_API_KEY')]) {
          sh '''
            set -e
            echo "=== RELOAD RESPONSE ==="
            curl -sS -X POST "$API_BASE/model/reload" -H "X-API-Key: $CHURN_API_KEY" | tee reload.json
          '''
        }
      }
    }

    stage("Proof: Model version (AFTER reload)") {
      steps {
        withCredentials([string(credentialsId: 'CHURN_API_KEY', variable: 'CHURN_API_KEY')]) {
          sh '''
            set -e
            echo "=== MODEL VERSION (AFTER reload) ==="
            curl -sS "$API_BASE/predict/schema" -H "X-API-Key: $CHURN_API_KEY" | tee schema_after.json >/dev/null
            ver=$(sed -n 's/.*"model_version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' schema_after.json | head -n 1)
            echo "$ver"
          '''
        }
      }
    }

    stage("Final smoke: Predict") {
      steps {
        withCredentials([string(credentialsId: 'CHURN_API_KEY', variable: 'CHURN_API_KEY')]) {
          sh '''
            set -e
            echo "=== PREDICT (smoke) ==="
            curl -sS -X POST "$API_BASE/predict" \
              -H "Content-Type: application/json" \
              -H "X-API-Key: $CHURN_API_KEY" \
              -d '{"features":{"SeniorCitizen":0,"tenure":10,"MonthlyCharges":80,"TotalCharges":500,"gender":"Female","Partner":"Yes","Dependents":"No","PhoneService":"Yes","MultipleLines":"No","InternetService":"DSL","OnlineSecurity":"No","OnlineBackup":"Yes","DeviceProtection":"No","TechSupport":"No","StreamingTV":"No","StreamingMovies":"No","Contract":"Month-to-month","PaperlessBilling":"Yes","PaymentMethod":"Electronic check"}}' | tee predict.json

            echo "\n=== PREDICT SUMMARY (one-line) ==="
            pred=$(sed -n 's/.*"prediction"[[:space:]]*:[[:space:]]*\([0-9]\+\).*/\1/p' predict.json | head -n 1)
            mver=$(sed -n 's/.*"model_version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' predict.json | head -n 1)
            echo "prediction=$pred | model_version=$mver"
          '''
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
      sh '''
        set +e
        cd infra/compose
        docker compose --env-file ../../.env ps || true
        docker compose --env-file ../../.env logs --tail=200 minio minio_init postgres api ui || true
      '''
    }
  }
}
