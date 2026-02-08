pipeline {
  agent any

  environment {
    COMPOSE_DIR = "infra/compose"
    API_BASE = "http://host.docker.internal:8000"
  }

  options {
    disableConcurrentBuilds()
    timestamps()
  }

  stages {
    stage("Workspace ready") {
      steps {
        echo "Workspace ready"
        sh 'pwd && ls -la'
      }
    }

    stage("Create .env for compose") {
      steps {
        withCredentials([
          string(credentialsId: 'CHURN_API_KEY', variable: 'API_KEY'),

          string(credentialsId: 'POSTGRES_DB', variable: 'POSTGRES_DB'),
          string(credentialsId: 'POSTGRES_USER', variable: 'POSTGRES_USER'),
          string(credentialsId: 'POSTGRES_PASSWORD', variable: 'POSTGRES_PASSWORD'),

          string(credentialsId: 'MINIO_ROOT_USER', variable: 'MINIO_ROOT_USER'),
          string(credentialsId: 'MINIO_ROOT_PASSWORD', variable: 'MINIO_ROOT_PASSWORD'),
          string(credentialsId: 'MINIO_BUCKET', variable: 'MINIO_BUCKET')
        ]) {
          sh '''
            set -e
            # .env MUST be at repo root because compose uses env_file: ../../.env from infra/compose
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

            echo ".env created."
            # Quick sanity (no secrets printed)
            ls -la .env
            grep -E "^(POSTGRES_DB|POSTGRES_USER|MINIO_ROOT_USER|MINIO_BUCKET|MINIO_ENDPOINT)=" .env || true
          '''
        }
      }
    }

    stage("Bring stack up (stable)") {
      steps {
        sh """
          set -e
          cd ${COMPOSE_DIR}

          # Verify compose can see env_file
          test -f ../../.env

          # Start core deps first
          docker compose up -d postgres minio

          # Wait postgres healthy (up to ~60s)
          for i in \$(seq 1 30); do
            docker compose ps postgres | grep -qi healthy && break || true
            sleep 2
          done

          # Run minio_init (one-shot). If it flakes, don't kill the build.
          docker compose up -d minio_init || true

          # Start app services
          docker compose up -d api ui

          # Show status
          docker compose ps
        """
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
        }
      }
    }

    stage("Reload model in API") {
      steps {
        withCredentials([string(credentialsId: 'CHURN_API_KEY', variable: 'CHURN_API_KEY')]) {
          sh """
            set -e
            curl -sS -X POST ${API_BASE}/model/reload \
              -H "X-API-Key: ${CHURN_API_KEY}"
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
      // Optional: show compose logs on failure
      // sh "cd ${COMPOSE_DIR} && docker compose logs --tail=120 || true"
    }
  }
}
