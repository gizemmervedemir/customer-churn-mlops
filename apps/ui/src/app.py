import os
import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "")

st.set_page_config(page_title="Customer Churn — MLOps UI", layout="centered")
st.title("Customer Churn — MLOps UI")
st.caption(f"API: {API_BASE_URL}")

if not API_KEY:
    st.warning("API_KEY env is empty. Requests to protected endpoints will fail (401).")

headers = {"X-API-Key": API_KEY} if API_KEY else {}


def api_get(path: str, timeout: int = 10):
    return requests.get(f"{API_BASE_URL}{path}", headers=headers, timeout=timeout)


def api_post(path: str, payload: dict | None = None, timeout: int = 20):
    return requests.post(
        f"{API_BASE_URL}{path}",
        headers={**headers, "Content-Type": "application/json"},
        json=payload if payload is not None else {},
        timeout=timeout,
    )


# --- Health ---
try:
    r = requests.get(f"{API_BASE_URL}/health", timeout=5)
    if r.status_code != 200:
        st.error(f"Health check failed: {r.status_code} {r.text}")
        st.stop()
    st.success(f"API Health: {r.json()}")
except Exception as e:
    st.error(f"API not reachable: {e}")
    st.stop()


# --- Schema fetch ---
def fetch_schema():
    s = api_get("/predict/schema", timeout=15)
    if s.status_code != 200:
        raise RuntimeError(f"Schema error: {s.status_code} {s.text}")
    return s.json()


st.subheader("Model & Schema")

colA, colB, colC = st.columns([1, 1, 1])
with colA:
    if st.button("Refresh schema / model version"):
        st.rerun()
with colB:
    if st.button("Reload model in API (/model/reload)"):
        try:
            rr = api_post("/model/reload", payload={}, timeout=20)
            if rr.status_code != 200:
                st.error(f"Reload error: {rr.status_code} {rr.text}")
            else:
                st.success(f"Reloaded: {rr.json()}")
        except Exception as e:
            st.error(f"Reload request failed: {e}")
with colC:
    st.caption("Use after retrain + latest.json update")

try:
    schema = fetch_schema()
except Exception as e:
    st.error(f"Schema fetch failed: {e}")
    st.stop()

model_version = schema.get("model_version")
num_cols = schema.get("num_cols", [])
cat_cols = schema.get("cat_cols", [])

st.write("**Model version:**", model_version)


# --- Predict ---
st.subheader("Predict")

with st.form("predict_form"):
    features = {}

    st.markdown("### Numeric features")
    for c in num_cols:
        default = 0.0
        if c == "tenure":
            default = 12.0
        elif c == "MonthlyCharges":
            default = 70.0
        elif c == "TotalCharges":
            default = 1000.0
        elif c == "SeniorCitizen":
            default = 0.0

        features[c] = st.number_input(c, value=float(default))

    st.markdown("### Categorical features")
    for c in cat_cols:
        features[c] = st.text_input(c, value="")

    submitted = st.form_submit_button("Predict")

if submitted:
    try:
        p = api_post("/predict", {"features": features}, timeout=30)
        if p.status_code != 200:
            st.error(f"Predict error: {p.status_code} {p.text}")
        else:
            out = p.json()
            st.success("Prediction success")
            st.json(out)
    except Exception as e:
        st.error(f"Predict request failed: {e}")


# --- Drift Monitoring ---
st.divider()
st.subheader("Drift Monitoring")

n = st.slider("Current window size (N)", min_value=20, max_value=200, value=200, step=10)

if st.button("Run drift check"):
    try:
        d = api_get(f"/drift/check?n={n}", timeout=40)
        if d.status_code != 200:
            st.error(f"Drift error: {d.status_code} {d.text}")
        else:
            out = d.json()
            st.success(f"Drift run saved (id={out.get('id')})")

            summary = out.get("summary", {})
            details = out.get("details", {})

            st.markdown("### Summary")
            st.json(summary)

            num = details.get("numeric") or {}
            cat = details.get("categorical") or {}

            st.markdown("### Numeric (PSI)")
            num_rows = [
                {"feature": k, "psi": v.get("psi"), "drift": v.get("drift")}
                for k, v in num.items()
            ]
            if num_rows:
                st.dataframe(num_rows, use_container_width=True)
            else:
                st.info("No numeric drift results.")

            st.markdown("### Categorical (L1)")
            cat_rows = [
                {"feature": k, "l1": v.get("l1"), "drift": v.get("drift")}
                for k, v in cat.items()
            ]
            if cat_rows:
                st.dataframe(cat_rows, use_container_width=True)
            else:
                st.info("No categorical drift results.")
    except Exception as e:
        st.error(f"Drift request failed: {e}")
