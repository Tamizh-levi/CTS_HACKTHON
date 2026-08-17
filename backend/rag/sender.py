import os
import requests
import json
import time

# ============================================================
# TARGET RECEIVER HOST / IP ADDRESS
# ============================================================
# If running on the SAME PC: keep "127.0.0.1"
# If running on a DIFFERENT PC in the same Wi-Fi/LAN:
# Replace with the Receiver PC's IPv4 address (e.g., "192.168.1.50")
RECEIVER_HOST = os.getenv("RECEIVER_IP", "127.0.0.1")

CANDIDATE_URLS = [
    f"http://{RECEIVER_HOST}:8000/api/predict-and-rca",  # Flask Main API
    f"http://{RECEIVER_HOST}:8000/predict-and-rca",      # Flask Root Alias
    f"http://{RECEIVER_HOST}:8001/predict-and-rca"       # Backup Port
]


# ============================================================
# TELECOM NETWORK DATA PAYLOAD
# ============================================================
network_data = {
    # --------------------------------------------------------
    # IDENTIFIERS & RCA ARRAYS
    # --------------------------------------------------------
    "id": 14122,
    "event_types": ["event_type 32"],
    "log_features": ["log_feature 234"],

    # --------------------------------------------------------
    # CATEGORICAL FEATURES
    # --------------------------------------------------------
    "location": "location 481",
    "severity_type": "severity_type 2",
    "resource_type": "resource_type 2",

    # --------------------------------------------------------
    # NUMERICAL FEATURES
    # --------------------------------------------------------
    "event_count_x": 2.0,
    "unique_event_count": 2.0,
    "log_feature_count": 4.0,
    "unique_log_features": 4.0,
    "total_log_volume": 98.0,
    "mean_log_volume": 24.5,
    "max_log_volume": 28.0,
    "min_log_volume": 20.0,

    # --------------------------------------------------------
    # EVENT FEATURES
    # --------------------------------------------------------
    "event_count_y": 2.0,
    "event_event_type_unique": 2.0,

    # --------------------------------------------------------
    # LOG FEATURES
    # --------------------------------------------------------
    "log_count": 2.0,
    "log_log_feature_unique": 2.0,
    "log_volume_unique": 2.0,

    # --------------------------------------------------------
    # RESOURCE FEATURES
    # --------------------------------------------------------
    "resource_count": 2.0,
    "resource_resource_type_unique": 2.0,

    # --------------------------------------------------------
    # RATIO FEATURES
    # --------------------------------------------------------
    "log_count_ratio": 2.0,
    "resource_count_ratio": 2.0,

    # --------------------------------------------------------
    # CATEGORICAL INTERACTION FEATURES
    # --------------------------------------------------------
    "severity_resource": "severity_type 2_resource_type 2",
    "severity_location": "severity_type 2_location 481",
    "resource_location": "resource_type 2_location 481"
}

# ============================================================
# EXECUTE DISPATCH WITH MULTI-URL RESOLUTION
# ============================================================
print("\n" + "=" * 60)
print("SYSTEM 1 - TELECOM DATA SENDER")
print("=" * 60)
print("Payload:")
print(json.dumps(network_data, indent=4))
print("=" * 60)

sent_successfully = False

for url in CANDIDATE_URLS:
    print(f"Attempting destination: {url}...")
    start_time = time.time()

    try:
        response = requests.post(url, json=network_data, timeout=120)
        elapsed_time = time.time() - start_time

        if response.status_code == 200:
            print("=" * 60)
            print(f"SUCCESS! HTTP Status: 200 (in {elapsed_time:.2f} seconds)")
            print(f"Connected to: {url}")
            print("=" * 60)
            print("RESPONSE FROM SYSTEM 2:")
            print(json.dumps(response.json(), indent=4))
            print("=" * 60)
            sent_successfully = True
            break
        elif response.status_code == 404:
            print(f"Endpoint {url} returned 404. Trying next candidate endpoint...\n")
            continue
        else:
            print(f"HTTP Status: {response.status_code}")
            print(response.text)
            break

    except requests.exceptions.ConnectionError:
        print(f"Could not connect to {url}. Server might be offline on that port.")
    except requests.exceptions.Timeout:
        print(f"Timeout connecting to {url}. Local Ollama inference may be taking longer.")
    except Exception as e:
        print(f"Request Error on {url}: {e}")

if not sent_successfully:
    print("\n" + "=" * 60)
    print("CONNECTION SUMMARY:")
    print("Could not deliver payload to any candidate endpoint.")
    print("Ensure the Flask backend is running on port 8000: 'python backend/app.py'")
    print("=" * 60)