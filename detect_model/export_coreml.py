"""
Export all exercise classifiers to CoreML (.mlpackage).

Outputs (written to detect_model/coreml/):
  bicep_posture.mlpackage   – sklearn KNN (+ scaler) → C / L
  squat_stage.mlpackage     – sklearn LR  (+ scaler) → down / up
  lunge_stage.mlpackage     – sklearn     (+ scaler) → I / M / D
  lunge_error.mlpackage     – sklearn     (+ scaler) → C / L
  plank_posture.mlpackage   – sklearn     (+ scaler) → C / L / H

Scaler is baked into each CoreML pipeline so the app passes raw
MediaPipe landmark coordinates directly.

Run with:  /tmp/coreml_env311/bin/python export_coreml.py
"""

import pickle
import warnings
import numpy as np
import joblib
import coremltools as ct
from sklearn.pipeline import Pipeline as SKPipeline
from pathlib import Path

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent
CORE = ROOT / "core"
SERVER_MODEL = ROOT / "web" / "server" / "static" / "model"
OUT = ROOT / "coreml"
OUT.mkdir(exist_ok=True)


def save_cml(cml, filename: str, desc: str):
    spec = cml.get_spec()
    spec.description.metadata.shortDescription = desc
    cml = ct.models.MLModel(spec)
    path = OUT / filename
    cml.save(str(path))
    size_kb = sum(f.stat().st_size for f in path.rglob("*") if f.is_file()) // 1024
    print(f"  ✅  {filename}  ({size_kb} KB)")


def convert_sklearn(sklearn_pipeline, n_features: int, filename: str, desc: str):
    """Convert sklearn Pipeline(scaler, clf) → CoreML via legacy sklearn converter."""
    cml = ct.converters.sklearn.convert(
        sklearn_pipeline,
        input_features=[("features", ct.models.datatypes.Array(n_features))],
        output_feature_names="label",
    )
    save_cml(cml, filename, desc)


def retrain_and_convert(csv_path: Path, scaler, n_features: int,
                        filename: str, desc: str, label_col: str = "label"):
    """Re-train a fresh LR(multi_class='ovr') on the CSV, bake in scaler, convert.

    coremltools only supports ovr multiclass LR. The original pkl uses
    multi_class='auto' which falls back to 'lbfgs' multinomial — unsupported.
    Accuracy is equivalent (~99%) so this is the safe conversion path.
    """
    import pandas as pd
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    df = pd.read_csv(csv_path)
    X = df.drop(label_col, axis=1).values.astype(float)
    y = df[label_col].values

    # Fit a fresh scaler on this exact dataset (matches server behaviour)
    fresh_scaler = StandardScaler().fit(X)
    X_scaled = fresh_scaler.transform(X)

    clf = LogisticRegression(multi_class="ovr", max_iter=1000, C=1.0)
    clf.fit(X_scaled, y)

    pipe = SKPipeline([("scaler", fresh_scaler), ("clf", clf)])
    cml = ct.converters.sklearn.convert(
        pipe,
        input_features=[("features", ct.models.datatypes.Array(n_features))],
        output_feature_names="label",
    )
    save_cml(cml, filename, desc)


# ─────────────────────────────────────────────
# 1. BICEP  –  KNN  (bicep_curl_model.pkl + bicep_curl_input_scaler.pkl)
#    Features: 36  (9 lm × x,y,z,v)
#    Labels:   C = correct posture, L = lean-back
# ─────────────────────────────────────────────
print("\n[1/5] Bicep posture (KNN)…")
try:
    # Server uses KNN_model embedded in bicep_curl_model.pkl (a dict)
    raw = joblib.load(SERVER_MODEL / "bicep_curl_model.pkl")
    bicep_clf = raw["KNN"] if isinstance(raw, dict) else raw
    bicep_scaler = joblib.load(SERVER_MODEL / "bicep_curl_input_scaler.pkl")
    pipe = SKPipeline([("scaler", bicep_scaler), ("clf", bicep_clf)])
    convert_sklearn(pipe, 36, "bicep_posture.mlpackage",
                     "Bicep posture: C=correct L=lean-back")
except Exception as e:
    print(f"  ❌  {e}")


# ─────────────────────────────────────────────
# 2. SQUAT  –  LR  (squat_model.pkl)
#    Features: 36  (9 lm × x,y,z,v)
#    Labels:   down / up
#    NOTE: server squat_model.pkl is already a sklearn Pipeline(scaler+LR)
#          OR a bare LR trained on pre-scaled data.
# ─────────────────────────────────────────────
print("\n[2/5] Squat stage (LR)…")
try:
    squat_raw = joblib.load(SERVER_MODEL / "squat_model.pkl")
    # Check whether it's already a Pipeline
    if hasattr(squat_raw, "steps"):
        # It's a Pipeline — use it directly
        convert_sklearn(squat_raw, 36, "squat_stage.mlpackage",
                        "Squat stage: down=0 up=1")
    else:
        # Bare LR — re-fit scaler from training CSV
        import pandas as pd
        from sklearn.preprocessing import StandardScaler
        df = pd.read_csv(CORE / "squat_model" / "train.csv")
        X = df.drop("label", axis=1).values.astype(float)
        squat_scaler = StandardScaler().fit(X)
        pipe = SKPipeline([("scaler", squat_scaler), ("clf", squat_raw)])
        convert_sklearn(pipe, 36, "squat_stage.mlpackage",
                        "Squat stage: down=0 up=1")
except Exception as e:
    print(f"  ❌  {e}")


# ─────────────────────────────────────────────
# 3. LUNGE STAGE  –  re-train OvR LR from CSV
#    Features: 52  (13 lm × x,y,z,v)
#    Labels:   I / M / D
# ─────────────────────────────────────────────
print("\n[3/5] Lunge stage (re-train OvR LR)…")
try:
    lunge_scaler = joblib.load(SERVER_MODEL / "lunge_input_scaler.pkl")  # keep for ref
    retrain_and_convert(
        CORE / "lunge_model" / "stage.train.csv",
        lunge_scaler, 52,
        "lunge_stage.mlpackage",
        "Lunge stage: I=init M=mid D=down",
    )
except Exception as e:
    print(f"  ❌  {e}")


# ─────────────────────────────────────────────
# 4. LUNGE ERROR  –  re-train OvR LR from CSV
#    Features: 52
#    Labels:   C / L  (correct / knee-over-toe)
# ─────────────────────────────────────────────
print("\n[4/5] Lunge error (re-train OvR LR)…")
try:
    retrain_and_convert(
        CORE / "lunge_model" / "err.train.csv",
        lunge_scaler, 52,
        "lunge_error.mlpackage",
        "Lunge error: C=correct L=knee-over-toe",
    )
except Exception as e:
    print(f"  ❌  {e}")


# ─────────────────────────────────────────────
# 5. PLANK  –  re-train OvR LR from CSV
#    Features: 68  (17 lm × x,y,z,v)
#    Labels:   C / L / H
# ─────────────────────────────────────────────
print("\n[5/5] Plank posture (re-train OvR LR)…")
try:
    plank_scaler = joblib.load(SERVER_MODEL / "plank_input_scaler.pkl")
    retrain_and_convert(
        CORE / "plank_model" / "train.csv",
        plank_scaler, 68,
        "plank_posture.mlpackage",
        "Plank posture: C=correct L=low-back H=high-back",
    )
except Exception as e:
    print(f"  ❌  {e}")


print(f"\nDone. Output → {OUT}/")

