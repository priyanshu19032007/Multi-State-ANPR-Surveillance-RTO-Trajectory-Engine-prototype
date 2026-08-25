# 🇮🇳 Indian Multi-State ANPR Surveillance & Autonomous Trajectory Engine

A high-performance vehicle surveillance, route trajectory tracking, and automated anomaly detection engine designed for Indian road networks and vehicle registration conventions.

---

## 📌 Project Overview
This application processes Automatic Number Plate Recognition (ANPR) sightings and reconstructs real-time vehicle movement history across multi-state checkpoints. It autonomously evaluates driving behaviors—such as linear transit, legitimate return journeys, and suspicious area looping/recce—and synchronizes dynamic alerts with a central security watchlist.

---

## 🚀 Key Features

* **Strict Indian Number Plate Parsing & Formatting:** Automatically normalizes arbitrary inputs (e.g., `mh34ak3456`) into official standard Indian formats (`MH 34 AK 3456`) with real-time UI auto-capitalization.
* **Deterministic Cryptographic Routing (SHA-256):** Every single character variation in the plate generates a distinct, unique route tied to actual regional highway corridors and arterial bypasses without artificial map drift.
* **Autonomous Behavioral Diagnosis:**
  * **➡️ Normal Forward Transit:** Linear movement across checkpoints.
  * **🔁 U-Turn / Return Journey:** Natural two-way trips along highway routes.
  * **🚨 Suspicious Looping / Recce:** Repeated circular movements across the same junctions within a short timeframe.
* **Dynamic Watchlist Synchronization:**
  * Automatically flags and blacklists vehicles exhibiting repetitive looping patterns.
  * Automatically unflags and clears vehicles when normal transit patterns are observed.
* **Ultra-Fast Interactive GIS Mapping:** Lightweight OpenStreetMap Leaflet.js canvas providing zero-lag rendering with color-coded hop markers and polyline routes.
* **Granular Analytics & Trip Corridors:** Real-time checkpoint detection frequencies and sequential hop matrices.
* **Central Database Storage:** SQLite-backed persistence for surveillance logs, blacklist records, and operator controls.

---

## 🛠️ Tech Stack

* **Language:** Python 3.10+
* **Frontend / UI Framework:** Streamlit
* **Geospatial Mapping:** Leaflet.js / OpenStreetMap
* **Data Processing:** Pandas
* **Database:** SQLite3
* **Security & Hashing:** Python `hashlib` (SHA-256)

---

## 📁 Project Structure

```text
├── 10.py               # Main Streamlit surveillance dashboard application
├── anpr.sqlite3        # SQLite database storing sightings & blacklist logs
├── README.md           # Project documentation
└── requirements.txt    # Project dependencies
