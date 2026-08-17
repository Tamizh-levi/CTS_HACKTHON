import pandas as pd
import numpy as np
import joblib
import json


# ============================================================
# LOAD MODEL
# ============================================================

model = joblib.load(
    "model/date_fault_severity_model.joblib"
)


# ============================================================
# LOAD CONFIG
# ============================================================

with open(
    "config/date_fault_config.json",
    "r"
) as f:
    config = json.load(f)


# ============================================================
# SLA CONFIGURATION
# ============================================================

SLA_TARGETS = config["sla_targets"]

SEVERITY_MAPPING = config["severity_mapping"]


# ============================================================
# GET DATE RANGE
# ============================================================

start_input = input(
    "Enter start date (DD-MM-YYYY): "
)

end_input = input(
    "Enter end date (DD-MM-YYYY): "
)


# ============================================================
# VALIDATE DATE
# ============================================================

try:

    start_date = pd.to_datetime(
        start_input,
        format="%d-%m-%Y"
    )

    end_date = pd.to_datetime(
        end_input,
        format="%d-%m-%Y"
    )

except ValueError:

    print("\nInvalid date format.")
    print("Please enter date as DD-MM-YYYY")
    exit()


if start_date > end_date:

    print("\nStart date cannot be after end date.")
    exit()


# ============================================================
# CREATE DATE RANGE
# ============================================================

dates = pd.date_range(
    start=start_date,
    end=end_date,
    freq="D"
)


# ============================================================
# CREATE DATE FEATURES
# ============================================================

data = pd.DataFrame({

    "year": dates.year,

    "month": dates.month,

    "day": dates.day,

    "day_of_week": dates.dayofweek,

    "day_of_year": dates.dayofyear
})


# ============================================================
# PREDICT FAULT COUNTS
# ============================================================

predictions = model.predict(data)


predictions = np.maximum(
    np.round(predictions),
    0
).astype(int)


# ============================================================
# GET TOTAL SEVERITY COUNTS
# ============================================================

severity_0_total = int(
    predictions[:, 0].sum()
)

severity_1_total = int(
    predictions[:, 1].sum()
)

severity_2_total = int(
    predictions[:, 2].sum()
)


# ============================================================
# MAP TO HIGH / MEDIUM / LOW
# ============================================================

severity_counts = {

    "HIGH": severity_0_total,

    "MEDIUM": severity_1_total,

    "LOW": severity_2_total
}


# ============================================================
# TOTAL FAULTS
# ============================================================

total_faults = sum(
    severity_counts.values()
)


# ============================================================
# SLA WORKLOAD
# ============================================================

high_workload = severity_counts["HIGH"]

medium_workload = severity_counts["MEDIUM"]

low_workload = severity_counts["LOW"]


# ============================================================
# DISPLAY RESULT
# ============================================================

print("\n")
print("=" * 60)

print(
    "          SLA PRIORITY & WORKLOAD ANALYSIS"
)

print("=" * 60)

print(
    f"Date Range : {start_input} → {end_input}"
)

print("-" * 60)


print(
    f"Total Faults : {total_faults}"
)

print(
    f"HIGH         : {high_workload}"
)

print(
    f"MEDIUM       : {medium_workload}"
)

print(
    f"LOW          : {low_workload}"
)


print("\n")
print("SLA TARGETS")

print("-" * 60)


print(
    f"HIGH         : {SLA_TARGETS['HIGH']} hours"
)

print(
    f"MEDIUM       : {SLA_TARGETS['MEDIUM']} hours"
)

print(
    f"LOW          : {SLA_TARGETS['LOW']} hours"
)


print("\n")
print("WORKLOAD PRIORITY")

print("-" * 60)


print(
    f"Urgent Workload      : {high_workload} faults"
)

print(
    f"Normal Workload      : {medium_workload} faults"
)

print(
    f"Low-Priority Workload: {low_workload} faults"
)


# ============================================================
# OVERALL PRIORITY
# ============================================================

if high_workload > 0:

    overall_priority = "URGENT"

elif medium_workload > 0:

    overall_priority = "NORMAL"

else:

    overall_priority = "LOW"


print("\n")
print(
    f"Overall Priority : {overall_priority}"
)


print("=" * 60)


# ============================================================
# DAILY BREAKDOWN
# ============================================================

show_daily = input(
    "\nDo you want daily SLA breakdown? (y/n): "
).lower()


if show_daily == "y":

    print("\n")
    print("=" * 75)

    print(
        "                       DAILY BREAKDOWN"
    )

    print("=" * 75)

    print(
        f"{'DATE':<15}"
        f"{'HIGH':<12}"
        f"{'MEDIUM':<12}"
        f"{'LOW':<12}"
        f"{'TOTAL':<12}"
    )

    print("-" * 75)


    for i, date in enumerate(dates):

        high = int(
            predictions[i, 0]
        )

        medium = int(
            predictions[i, 1]
        )

        low = int(
            predictions[i, 2]
        )

        total = (
            high +
            medium +
            low
        )


        print(
            f"{date.strftime('%d-%m-%Y'):<15}"
            f"{high:<12}"
            f"{medium:<12}"
            f"{low:<12}"
            f"{total:<12}"
        )


    print("=" * 75)