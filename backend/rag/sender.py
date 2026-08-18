import os
import requests
import json
import time

# ============================================================
# TARGET RECEIVER HOST / IP ADDRESS
# ============================================================
RECEIVER_HOST = os.getenv("RECEIVER_IP", "127.0.0.1")

CANDIDATE_URLS = [
    f"http://{RECEIVER_HOST}:8000/api/predict-and-rca",
    f"http://{RECEIVER_HOST}:8000/predict-and-rca",
    f"http://{RECEIVER_HOST}:8001/predict-and-rca"
]


# ============================================================
# TELECOM NETWORK DATA - 3 SEPARATE RECORDS
# ============================================================

network_data_list = [

    # ========================================================
    # DATA 1
    # ========================================================
    {
        "id": 14122,
        "event_types": ["event_type 32"],
        "log_features": ["log_feature 234"],

        "location": "location 481",
        "severity_type": "severity_type 2",
        "resource_type": "resource_type 2",

        "event_count_x": 2.0,
        "unique_event_count": 2.0,
        "log_feature_count": 4.0,
        "unique_log_features": 4.0,
        "total_log_volume": 98.0,
        "mean_log_volume": 24.5,
        "max_log_volume": 28.0,
        "min_log_volume": 20.0,

        "event_count_y": 2.0,
        "event_event_type_unique": 2.0,

        "log_count": 2.0,
        "log_log_feature_unique": 2.0,
        "log_volume_unique": 2.0,

        "resource_count": 2.0,
        "resource_resource_type_unique": 2.0,

        "log_count_ratio": 2.0,
        "resource_count_ratio": 2.0,

        "severity_resource": "severity_type 2_resource_type 2",
        "severity_location": "severity_type 2_location 481",
        "resource_location": "resource_type 2_location 481"
    },


    # ========================================================
    # DATA 2
    # ========================================================
    {
        "id": 14123,
        "event_types": ["event_type 45"],
        "log_features": ["log_feature 310"],

        "location": "location 275",
        "severity_type": "severity_type 1",
        "resource_type": "resource_type 3",

        "event_count_x": 4.0,
        "unique_event_count": 3.0,
        "log_feature_count": 5.0,
        "unique_log_features": 3.0,
        "total_log_volume": 145.0,
        "mean_log_volume": 29.0,
        "max_log_volume": 40.0,
        "min_log_volume": 18.0,

        "event_count_y": 4.0,
        "event_event_type_unique": 3.0,

        "log_count": 4.0,
        "log_log_feature_unique": 3.0,
        "log_volume_unique": 4.0,

        "resource_count": 3.0,
        "resource_resource_type_unique": 2.0,

        "log_count_ratio": 1.33,
        "resource_count_ratio": 1.5,

        "severity_resource": "severity_type 1_resource_type 3",
        "severity_location": "severity_type 1_location 275",
        "resource_location": "resource_type 3_location 275"
    },


    # ========================================================
    # DATA 3
    # ========================================================
    {
        "id": 14124,
        "event_types": ["event_type 17"],
        "log_features": ["log_feature 156"],

        "location": "location 620",
        "severity_type": "severity_type 3",
        "resource_type": "resource_type 1",

        "event_count_x": 6.0,
        "unique_event_count": 4.0,
        "log_feature_count": 7.0,
        "unique_log_features": 5.0,
        "total_log_volume": 210.0,
        "mean_log_volume": 30.0,
        "max_log_volume": 45.0,
        "min_log_volume": 15.0,

        "event_count_y": 6.0,
        "event_event_type_unique": 4.0,

        "log_count": 6.0,
        "log_log_feature_unique": 5.0,
        "log_volume_unique": 6.0,

        "resource_count": 4.0,
        "resource_resource_type_unique": 2.0,

        "log_count_ratio": 1.5,
        "resource_count_ratio": 2.0,

        "severity_resource": "severity_type 3_resource_type 1",
        "severity_location": "severity_type 3_location 620",
        "resource_location": "resource_type 1_location 620"
    }
]


# ============================================================
# SEND DATA ONE BY ONE
# ============================================================

print("\n" + "=" * 70)
print("SYSTEM 1 - TELECOM DATA SENDER")
print("MODE: ONE DATASET AT A TIME")
print("=" * 70)

for index, network_data in enumerate(network_data_list, start=1):

    print("\n" + "#" * 70)
    print(f"SENDING DATA {index} OF {len(network_data_list)}")
    print(f"Record ID: {network_data['id']}")
    print("#" * 70)

    print("\nPayload:")
    print(json.dumps(network_data, indent=4))

    sent_successfully = False

    # --------------------------------------------------------
    # Try each candidate URL
    # --------------------------------------------------------
    for url in CANDIDATE_URLS:

        print(f"\nAttempting destination: {url}...")

        start_time = time.time()

        try:

            response = requests.post(
                url,
                json=network_data,
                timeout=120
            )

            elapsed_time = time.time() - start_time

            # ------------------------------------------------
            # SUCCESS
            # ------------------------------------------------
            if response.status_code == 200:

                print("\n" + "=" * 70)
                print(
                    f"DATA {index} SUCCESSFUL"
                )
                print(
                    f"Record ID: {network_data['id']}"
                )
                print(
                    f"HTTP Status: 200 "
                    f"(in {elapsed_time:.2f} seconds)"
                )
                print(f"Connected to: {url}")
                print("=" * 70)

                print("RESPONSE FROM SYSTEM 2:")

                try:
                    print(
                        json.dumps(
                            response.json(),
                            indent=4
                        )
                    )

                except ValueError:
                    print(response.text)

                sent_successfully = True
                break

            # ------------------------------------------------
            # 404 - TRY NEXT URL
            # ------------------------------------------------
            elif response.status_code == 404:

                print(
                    f"Endpoint {url} returned 404."
                )
                print(
                    "Trying next candidate endpoint..."
                )

                continue

            # ------------------------------------------------
            # OTHER HTTP ERROR
            # ------------------------------------------------
            else:

                print(
                    f"DATA {index} FAILED"
                )
                print(
                    f"HTTP Status: {response.status_code}"
                )
                print(response.text)

                break

        # ----------------------------------------------------
        # CONNECTION ERROR
        # ----------------------------------------------------
        except requests.exceptions.ConnectionError:

            print(
                f"Could not connect to {url}."
            )

            continue

        # ----------------------------------------------------
        # TIMEOUT
        # ----------------------------------------------------
        except requests.exceptions.Timeout:

            print(
                f"Timeout connecting to {url}."
            )

            break

        # ----------------------------------------------------
        # OTHER ERROR
        # ----------------------------------------------------
        except Exception as e:

            print(
                f"Request Error: {e}"
            )

            break


    # ========================================================
    # DATA RESULT
    # ========================================================

    if sent_successfully:

        print(
            f"\nData {index} "
            f"(ID: {network_data['id']}) "
            f"sent successfully."
        )

    else:

        print(
            f"\nData {index} "
            f"(ID: {network_data['id']}) "
            f"could NOT be sent."
        )

        # Stop sending remaining records if this one fails
        print(
            "Stopping transmission because this record failed."
        )

        break


    # ========================================================
    # SMALL DELAY BEFORE NEXT DATASET
    # ========================================================

    if index < len(network_data_list):

        print(
            "\nWaiting 2 seconds before sending next dataset..."
        )

        time.sleep(2)


# ============================================================
# FINAL SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("TRANSMISSION COMPLETE")
print("=" * 70)