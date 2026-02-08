pipeline {
  agent any

  environment {
    COMPOSE_DIR = "infra/compose"
    API_BASE = "http://localhost:8000"
  }

  options {
    disableConcurrentBuilds()
  }

  stages {
    stage("Workspace ready") {
      steps {
        echo "Workspace ready"
        sh "pwd && ls -la"
      }
    }

    stage("Bring stack up") {
      steps {
        sh """
          set -e
          cd ${COMPOSE_DIR}
          docker compose up -d postgres minio api ui
        """
      }
    }

    stage("Smoke: Health & Schema") {
      steps {
        withCredentials([
          string(credentialsId: 'CHURN_API_KEY', variable: 'CHURN_API_KEY')
        ]) {
          sh """
            set -e
            curl -sS ${API_BASE}/health
            curl -sS ${API_BASE}/predict/schema -H "X-API-Key: ${CHURN_API_KEY}"
          """
        }
      }
    }

    stage("Drift check") {
      steps {
        withCredentials([
          string(credentialsId: 'CHURN_API_KEY', variable: 'CHURN_API_KEY')
        ]) {
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
            echo "No drift detected. Skipping retrain."
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
        withCredentials([
          string(credentialsId: 'CHURN_API_KEY', variable: 'CHURN_API_KEY')
        ]) {
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
        withCredentials([
          string(credentialsId: 'CHURN_API_KEY', variable: 'CHURN_API_KEY')
        ]) {
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
  }
}

