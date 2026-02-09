import streamlit as st
from components.api_client import get, post

st.set_page_config(page_title="Monitoring — Drift", layout="wide")
st.title("Monitoring")
st.caption("Goal: Run `/drift/check` and visualize summary + which features drifted. Optional: reload model after retrain.")

# Controls
c1, c2, c3 = st.columns([1, 1, 2])
with c1:
    n = st.slider("Current window size (N)", min_value=20, max_value=200, value=200, step=10)
with c2:
    timeout = st.number_input("Request timeout (s)", min_value=10, max_value=120, value=60, step=5)
with c3:
    st.caption("Tip: During demo, set N=200, click Run drift check, then show drifted_features + thresholds.")

st.divider()

if st.button("Run drift check"):
    with st.spinner("Running drift check..."):
        resp, latency = get(f"/drift/check?n={n}", timeout=int(timeout))

    if resp.status_code != 200:
        st.error(f"Drift check failed: {resp.status_code} {resp.text}")
        st.stop()

    out = resp.json()
    st.success(f"Drift check completed in {latency:.2f}s — saved id={out.get('id')}")

    summary = out.get("summary", {}) or {}
    details = out.get("details", {}) or {}
    numeric = details.get("numeric") or {}
    categorical = details.get("categorical") or {}

    # --- Summary ---
    st.subheader("Summary")
    drift_detected = summary.get("drift_detected", False)
    drifted_features = summary.get("drifted_features", []) or []

    colA, colB, colC = st.columns(3)
    colA.metric("drift_detected", str(drift_detected))
    colB.metric("n_reference", summary.get("n_reference", "-"))
    colC.metric("n_current", summary.get("n_current", "-"))

    if drifted_features:
        st.warning(f"Drifted features ({len(drifted_features)}): " + ", ".join(drifted_features))
    else:
        st.info("No drifted features reported.")

    st.json(summary)

    # --- Numeric table ---
    st.subheader("Numeric drift (PSI)")
    num_rows = []
    for feat, v in numeric.items():
        num_rows.append(
            {
                "feature": feat,
                "psi": v.get("psi"),
                "drift": v.get("drift"),
            }
        )
    if num_rows:
        st.dataframe(num_rows, use_container_width=True)
    else:
        st.info("No numeric drift results.")

    # --- Categorical table ---
    st.subheader("Categorical drift (L1)")
    cat_rows = []
    for feat, v in categorical.items():
        cat_rows.append(
            {
                "feature": feat,
                "l1": v.get("l1"),
                "drift": v.get("drift"),
            }
        )
    if cat_rows:
        st.dataframe(cat_rows, use_container_width=True)
    else:
        st.info("No categorical drift results.")

    st.subheader("Raw response")
    st.json(out)

st.divider()

st.subheader("Operational actions")
st.caption("If you retrain via Jenkins pipeline, you can reload the model here to pick up the newest artifact.")
if st.button("Reload model in API"):
    r, t = post("/model/reload", payload={}, timeout=30)
    if r.status_code != 200:
        st.error(f"Reload failed: {r.status_code} {r.text}")
    else:
        st.success(f"Reloaded in {t:.2f}s")
        st.json(r.json())
