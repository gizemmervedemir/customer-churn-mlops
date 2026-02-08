FROM python:3.12-slim@sha256:9e01bf1ae5db7649a236da7be1e94ffbbbdd7a93f867dd0d8d5720d9e1f89fab

WORKDIR /app

# System deps (optional but useful)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
  && rm -rf /var/lib/apt/lists/*

COPY apps/api/pyproject.toml /app/pyproject.toml

RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir \
      "fastapi>=0.110" "uvicorn[standard]>=0.27" \
      "sqlmodel>=0.0.16" "psycopg2-binary>=2.9" \
      "boto3>=1.34" "joblib>=1.3" "pandas>=2.1" \
      "numpy>=1.26" "scikit-learn>=1.4" \
      "pyarrow>=15.0"


COPY apps/api/src /app/src

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
