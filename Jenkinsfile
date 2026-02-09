pipeline {
  agent any

  environment {
    COMPOSE_DIR = "infra/compose"
    API_BASE    = "http://host.docker.internal:8000"
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
        sh """
          set -e
          cd ${COMPOSE_DIR}
          test -f ../../.env

          docker compose up -d postgres minio

          echo "Waiting postgres healthy..."
          for i in \$(seq 1 40); do
            docker compose ps postgres | grep -qi healthy && break || true
            sleep 2
          done

          echo "Waiting minio ready..."
          for i in \$(seq 1 40); do
            curl -sSf http://localhost:9000/minio/health/ready >/dev/null 2>&1 && break || true
            sleep 2
          done

          echo "Running minio_init..."
          docker compose up -d minio_init || true

          docker compose up -d api ui

          docker compose ps
        """
      }
    }

    stage("Snapshot: model version (BEFORE)") {
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
            docker compose --profile train run --rm trainer
          """

          // after retrain, show version from latest.json path indirectly (via schema after reload),
          // but schema won't change until reload. We'll still log "retrain finished".
          echo "Retrain finished. Next: /model/reload will switch the running API to latest model."
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

    stage("Snapshot: model version (AFTER reload)") {
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
            curl -sS -X POST ${API_BASE}/predict \
              -H "Content-Type: application/json" \
              -H "X-API-Key: ${CHURN_API_KEY}" \
              -d '{"features":{"SeniorCitizen":0,"tenure":10,"MonthlyCharges":80,"TotalCharges":500,"gender":"Female","Partner":"Yes","Dependents":"No","PhoneService":"Yes","MultipleLines":"No","InternetService":"DSL","OnlineSecurity":"No","OnlineBackup":"Yes","DeviceProtection":"No","TechSupport":"No","StreamingTV":"No","StreamingMovies":"No","Contract":"Month-to-month","PaperlessBilling":"Yes","PaymentMethod":"Electronic check"}}'
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
        docker compose ps || true
        docker compose logs --tail=120 minio minio_init postgres api ui || true
      """
    }
  }
}
