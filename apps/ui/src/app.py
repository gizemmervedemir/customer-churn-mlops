import streamlit as st
from components.api_client import get, post, API_BASE_URL, API_KEY

st.set_page_config(page_title="Customer Churn — MLOps UI", layout="wide")

st.title("Customer Churn — MLOps UI")
st.caption(f"API: {API_BASE_URL}")

if not API_KEY:
    st.warning("API_KEY env is empty. Protected endpoints may fail (401).")

# --- Health ---
health, t = get("/health", timeout=6)
if health.status_code != 200:
    st.error(f"API not reachable: {health.status_code} {health.text}")
    st.stop()

st.success(f"API healthy — latency {t:.2f}s")

# --- Schema / Model info ---
schema, t2 = get("/predict/schema", timeout=15)
if schema.status_code != 200:
    st.error(f"Schema fetch failed: {schema.status_code} {schema.text}")
    st.stop()

schema_json = schema.json()
model_version = schema_json.get("model_version", "unknown")

st.subheader("Model Status")
col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    st.metric("Model version", model_version)

with col2:
    st.metric("Schema fetch", f"{t2:.2f}s")

with col3:
    st.caption("Use the left menu for Predict & Monitoring pages. This home page is a quick system status view.")

st.divider()

st.subheader("Quick Actions")
a, b, c = st.columns([1, 1, 2])

with a:
    if st.button("Reload model in API"):
        r, tr = post("/model/reload", payload={}, timeout=20)
        if r.status_code != 200:
            st.error(f"Reload failed: {r.status_code} {r.text}")
        else:
            st.success(f"Reloaded in {tr:.2f}s")
            st.json(r.json())

with b:
    if st.button("Run drift check (N=200)"):
        d, td = get("/drift/check?n=200", timeout=60)
        if d.status_code != 200:
            st.error(f"Drift failed: {d.status_code} {d.text}")
        else:
            out = d.json()
            st.success(f"Drift checked in {td:.2f}s — saved id={out.get('id')}")
            st.json(out.get("summary", out))
