FROM python:3.12-slim@sha256:9e01bf1ae5db7649a236da7be1e94ffbbbdd7a93f867dd0d8d5720d9e1f89fab

WORKDIR /app

RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir \
      "pandas>=2.1" "numpy>=1.26" "scikit-learn>=1.4" \
      "joblib>=1.3" "pyarrow>=15.0" \
      "boto3>=1.34"

COPY apps/trainer/src /app/src
COPY data /app/data

ENV PYTHONPATH=/app

CMD ["python", "src/train.py"]
