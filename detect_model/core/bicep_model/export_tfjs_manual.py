"""
Export the bicep-curl posture model to TensorFlow.js format WITHOUT
using the tensorflowjs Python package (which has broken dependencies on macOS).

Output files (drop into frontend/assets/models/bicep_posture/):
  - model.json          <- topology + weight manifest
  - group1-shard1of1.bin <- raw Float32 weights (little-endian)
  - scaler.json          <- StandardScaler mean + scale
"""

import json, os, struct
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.preprocessing import StandardScaler

# ─── Paths ───────────────────────────────────────────────────────────────────
HERE      = os.path.dirname(os.path.abspath(__file__))
TRAIN_CSV = os.path.join(HERE, "train.csv")
OUT_DIR   = os.path.join(HERE, "tfjs_bicep_model")
os.makedirs(OUT_DIR, exist_ok=True)

# ─── 1. Load data ─────────────────────────────────────────────────────────────
print("Loading data...")
df = pd.read_csv(TRAIN_CSV)
df.loc[df["label"] == "C", "label"] = 0  # Gập  (correct)
df.loc[df["label"] == "L", "label"] = 1  # Duỗi (lean-back error)

X = df.drop("label", axis=1).values
y = df["label"].astype("int").values
print(f"  {len(X)} samples, {X.shape[1]} features")

# ─── 2. Scaler ────────────────────────────────────────────────────────────────
print("Fitting scaler...")
sc = StandardScaler()
X_scaled = sc.fit_transform(X)

scaler_data = {"mean": sc.mean_.tolist(), "scale": sc.scale_.tolist()}
with open(os.path.join(OUT_DIR, "scaler.json"), "w") as f:
    json.dump(scaler_data, f)
print("  scaler.json saved.")

# ─── 3. Build & train model ───────────────────────────────────────────────────
print("Training model...")
model = tf.keras.Sequential([
    tf.keras.layers.Dense(32, activation="relu", input_shape=(X.shape[1],)),
    tf.keras.layers.Dense(16, activation="relu"),
    tf.keras.layers.Dense(1,  activation="sigmoid"),
])
model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
model.fit(X_scaled, y, epochs=50, batch_size=32, verbose=0)

loss, acc = model.evaluate(X_scaled, y, verbose=0)
print(f"  Train accuracy: {acc:.4f}")

# ─── 4. Manual TF.js export ───────────────────────────────────────────────────
# TF.js LayersModel format:
#   model.json  → { modelTopology, weightsManifest, format, generatedBy, convertedBy }
#   *.bin       → Float32 little-endian concatenation of all weight tensors

print("Exporting to TF.js format manually...")

# 4a. Collect all weights in the standard order
all_weights = []
weight_specs = []
byte_offset  = 0

for weight in model.weights:
    arr   = weight.numpy().astype(np.float32)
    shape = list(arr.shape)
    nbytes = arr.nbytes

    weight_specs.append({
        "name":   weight.name,
        "shape":  shape,
        "dtype":  "float32",
    })
    all_weights.append(arr.flatten())
    byte_offset += nbytes

# 4b. Write binary weights file
bin_filename = "group1-shard1of1.bin"
bin_path = os.path.join(OUT_DIR, bin_filename)
with open(bin_path, "wb") as f:
    for w in all_weights:
        f.write(w.tobytes())
total_bytes = sum(w.nbytes for w in all_weights)
print(f"  {bin_filename} written ({total_bytes} bytes).")

# 4c. Build weightsManifest
weights_manifest = [{
    "paths":   [bin_filename],
    "weights": weight_specs,
}]

# 4d. Get Keras topology JSON (model.to_json() gives a string)
topology = json.loads(model.to_json())

# 4e. Assemble model.json
model_json = {
    "format":      "layers-model",
    "generatedBy": "manual-export-script",
    "convertedBy": None,
    "modelTopology": topology,
    "weightsManifest": weights_manifest,
}

with open(os.path.join(OUT_DIR, "model.json"), "w") as f:
    json.dump(model_json, f, indent=2)
print("  model.json written.")

print(f"\n✅ Done! Copy the contents of:\n   {OUT_DIR}\ninto:\n   frontend/assets/models/bicep_posture/")
