import os
import time
import requests

API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000")
API_KEY = os.getenv("API_KEY", "")

def _headers():
    headers = {}
    if API_KEY:
        headers["X-API-Key"] = API_KEY
    return headers

def get(path: str, timeout: int = 15):
    start = time.time()
    resp = requests.get(f"{API_BASE_URL}{path}", headers=_headers(), timeout=timeout)
    return resp, (time.time() - start)

def post(path: str, payload: dict | None = None, timeout: int = 30):
    start = time.time()
    resp = requests.post(
        f"{API_BASE_URL}{path}",
        headers={**_headers(), "Content-Type": "application/json"},
        json=payload if payload is not None else {},
        timeout=timeout,
    )
    return resp, (time.time() - start)
