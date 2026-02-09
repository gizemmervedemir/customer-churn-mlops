import streamlit as st
from components.api_client import get, post

st.set_page_config(page_title="Predict — Customer Churn", layout="wide")
st.title("Predict")
st.caption("Goal: Send a feature payload to the FastAPI `/predict` endpoint and display prediction + probability + model_version.")

# --- Load schema ---
schema_resp, t = get("/predict/schema", timeout=15)
if schema_resp.status_code != 200:
    st.error(f"Schema fetch failed: {schema_resp.status_code} {schema_resp.text}")
    st.stop()

schema = schema_resp.json()
model_version = schema.get("model_version", "unknown")
num_cols = schema.get("num_cols", [])
cat_cols = schema.get("cat_cols", [])

st.info(f"Loaded schema in {t:.2f}s — model_version: {model_version}")

# --- Categorical options (Telco churn dataset typical values) ---
CAT_OPTIONS = {
    "gender": ["Female", "Male"],
    "Partner": ["Yes", "No"],
    "Dependents": ["Yes", "No"],
    "PhoneService": ["Yes", "No"],
    "MultipleLines": ["No", "Yes", "No phone service"],
    "InternetService": ["DSL", "Fiber optic", "No"],
    "OnlineSecurity": ["No", "Yes", "No internet service"],
    "OnlineBackup": ["No", "Yes", "No internet service"],
    "DeviceProtection": ["No", "Yes", "No internet service"],
    "TechSupport": ["No", "Yes", "No internet service"],
    "StreamingTV": ["No", "Yes", "No internet service"],
    "StreamingMovies": ["No", "Yes", "No internet service"],
    "Contract": ["Month-to-month", "One year", "Two year"],
    "PaperlessBilling": ["Yes", "No"],
    "PaymentMethod": [
        "Electronic check",
        "Mailed check",
        "Bank transfer (automatic)",
        "Credit card (automatic)",
    ],
}

# --- Presets for demo (WOW effect) ---
PRESETS = {
    "High churn risk (typical)": {
        "SeniorCitizen": 0,
        "tenure": 2,
        "MonthlyCharges": 95,
        "TotalCharges": 190,
        "gender": "Male",
        "Partner": "No",
        "Dependents": "No",
        "PhoneService": "Yes",
        "MultipleLines": "Yes",
        "InternetService": "Fiber optic",
        "OnlineSecurity": "No",
        "OnlineBackup": "No",
        "DeviceProtection": "No",
        "TechSupport": "No",
        "StreamingTV": "Yes",
        "StreamingMovies": "Yes",
        "Contract": "Month-to-month",
        "PaperlessBilling": "Yes",
        "PaymentMethod": "Electronic check",
    },
    "Low churn risk (typical)": {
        "SeniorCitizen": 0,
        "tenure": 48,
        "MonthlyCharges": 55,
        "TotalCharges": 2500,
        "gender": "Female",
        "Partner": "Yes",
        "Dependents": "Yes",
        "PhoneService": "Yes",
        "MultipleLines": "No",
        "InternetService": "DSL",
        "OnlineSecurity": "Yes",
        "OnlineBackup": "Yes",
        "DeviceProtection": "Yes",
        "TechSupport": "Yes",
        "StreamingTV": "No",
        "StreamingMovies": "No",
        "Contract": "Two year",
        "PaperlessBilling": "No",
        "PaymentMethod": "Bank transfer (automatic)",
    },
    "Blank (manual)": {},  # user fills
}

# Store state
if "preset_name" not in st.session_state:
    st.session_state.preset_name = "High churn risk (typical)"
if "features" not in st.session_state:
    st.session_state.features = {}

def apply_preset(preset_name: str):
    base = PRESETS.get(preset_name, {})
    st.session_state.features = dict(base)

# preset selector
left, right = st.columns([1, 2])
with left:
    preset = st.selectbox("Demo preset", list(PRESETS.keys()), index=list(PRESETS.keys()).index(st.session_state.preset_name))
    if st.button("Apply preset"):
        st.session_state.preset_name = preset
        apply_preset(preset)
        st.rerun()

with right:
    st.caption("Use presets to avoid typing 15 categorical fields live. Jury will love this because it demonstrates product thinking.")

# initialize features if empty
if not st.session_state.features:
    apply_preset(st.session_state.preset_name)

features = st.session_state.features

st.divider()

# --- Build form ---
with st.form("predict_form"):
    c1, c2 = st.columns([1, 1])

    with c1:
        st.subheader("Numeric")
        for c in num_cols:
            default = features.get(c, 0.0)
            # nicer defaults if missing
            if c == "tenure" and c not in features:
                default = 12
            if c == "MonthlyCharges" and c not in features:
                default = 70
            if c == "TotalCharges" and c not in features:
                default = 1000
            if c == "SeniorCitizen" and c not in features:
                default = 0

            # SeniorCitizen is int-like
            if c == "SeniorCitizen":
                features[c] = int(st.number_input(c, value=int(default), step=1))
            else:
                features[c] = float(st.number_input(c, value=float(default)))

    with c2:
        st.subheader("Categorical")
        for c in cat_cols:
            opts = CAT_OPTIONS.get(c)
            if opts:
                # choose default safely
                current = features.get(c, opts[0])
                if current not in opts:
                    current = opts[0]
                features[c] = st.selectbox(c, opts, index=opts.index(current))
            else:
                # fallback (should not happen if schema matches)
                features[c] = st.text_input(c, value=str(features.get(c, "")))

    submitted = st.form_submit_button("Predict")

# save back
st.session_state.features = features

# --- Predict action ---
if submitted:
    with st.spinner("Calling /predict ..."):
        resp, latency = post("/predict", {"features": features}, timeout=30)

    if resp.status_code != 200:
        st.error(f"Predict failed: {resp.status_code} {resp.text}")
    else:
        out = resp.json()
        prob = out.get("probability")
        pred = out.get("prediction")
        mv = out.get("model_version", "unknown")

        st.success(f"Prediction completed in {latency:.2f}s — model_version: {mv}")

        colA, colB, colC = st.columns(3)
        colA.metric("prediction", pred)
        colB.metric("probability", f"{prob:.3f}" if isinstance(prob, (int, float)) else str(prob))
        colC.metric("model_version", mv)

        st.subheader("Raw response")
        st.json(out)

        st.subheader("Payload sent")
        st.json({"features": features})
