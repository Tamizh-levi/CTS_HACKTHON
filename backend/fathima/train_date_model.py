import pandas as pd
import numpy as np
import joblib
import json
from pathlib import Path

from sklearn.ensemble import RandomForestRegressor
from sklearn.multioutput import MultiOutputRegressor
from sklearn.metrics import mean_absolute_error


# ==============================
# PATHS
# ==============================

DATA_PATH = "train_merged_with_date.csv"

MODEL_DIR = Path("model")
CONFIG_DIR = Path("config")

MODEL_DIR.mkdir(exist_ok=True)
CONFIG_DIR.mkdir(exist_ok=True)


# ==============================
# LOAD DATA
# ==============================

df = pd.read_csv(DATA_PATH)

df["date"] = pd.to_datetime(df["date"])


# ==============================
# DAILY FAULT COUNTS
# ==============================

daily = (
    df.groupby(["date", "fault_severity"])
    .size()
    .unstack(fill_value=0)
    .reset_index()
)

# Ensure all severity columns exist
for s in [0, 1, 2]:
    if s not in daily.columns:
        daily[s] = 0

daily = daily[["date", 0, 1, 2]]

daily.columns = [
    "date",
    "severity_0",
    "severity_1",
    "severity_2"
]


# ==============================
# DATE FEATURES
# ==============================

daily["year"] = daily["date"].dt.year
daily["month"] = daily["date"].dt.month
daily["day"] = daily["date"].dt.day
daily["day_of_week"] = daily["date"].dt.dayofweek
daily["day_of_year"] = daily["date"].dt.dayofyear


FEATURES = [
    "year",
    "month",
    "day",
    "day_of_week",
    "day_of_year"
]

TARGETS = [
    "severity_0",
    "severity_1",
    "severity_2"
]


X = daily[FEATURES]
y = daily[TARGETS]


# ==============================
# TRAIN MODEL
# ==============================

model = MultiOutputRegressor(
    RandomForestRegressor(
        n_estimators=200,
        random_state=42,
        n_jobs=-1
    )
)

model.fit(X, y)


# ==============================
# TRAINING ERROR
# ==============================

pred = model.predict(X)
pred = np.maximum(np.round(pred), 0)

print("\nTraining MAE:")

for i, target in enumerate(TARGETS):
    mae = mean_absolute_error(
        y.iloc[:, i],
        pred[:, i]
    )

    print(f"{target}: {mae:.2f}")


# ==============================
# SAVE MODEL
# ==============================

joblib.dump(
    model,
    MODEL_DIR / "date_fault_severity_model.joblib"
)


# ==============================
# SAVE CONFIG
# ==============================

config = {
    "features": FEATURES,
    "targets": TARGETS,
    "severity_mapping": {
        "0": "Severity 0",
        "1": "Severity 1",
        "2": "Severity 2"
    }
}

with open(
    CONFIG_DIR / "date_fault_config.json",
    "w"
) as f:
    json.dump(config, f, indent=4)


print("\nModel saved:")
print("model/date_fault_severity_model.joblib")

print("\nConfig saved:")
print("config/date_fault_config.json")