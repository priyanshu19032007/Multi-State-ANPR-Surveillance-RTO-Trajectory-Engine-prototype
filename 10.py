"""Indian Multi-State ANPR Trajectory & Autonomous Surveillance Engine.

Run with: streamlit run 10.py
"""
from __future__ import annotations

import hashlib
import json
import random
import re
import sqlite3
import sys
import warnings
from datetime import datetime, timedelta

warnings.filterwarnings("ignore")

import pandas as pd
import streamlit as st

DB_PATH = "anpr.sqlite3"

# Real Mapped Motorable Highway & Arterial Corridors
RTO_DATABASE = {
    ("MH", "34"): {
        "city": "Chandrapur, Maharashtra",
        "center": [19.9550, 79.2970],
        "corridors": [
            ("Padoli Bypass Toll Gate (MSH-6)", 19.9890, 79.2710),
            ("Ramnagar Traffic Chowk", 19.9670, 79.2900),
            ("Gandhi Chowk Metro Square", 19.9550, 79.2970),
            ("Babupeth Railway Crossing Flyover", 19.9390, 79.3010),
            ("Ballarpur Highway Road Post", 19.8650, 79.3380),
            ("MIDC Industrial Corridor Gate", 19.9480, 79.3190),
            ("Chandrapur Thermal Bypass Gate", 20.0080, 79.3020),
        ]
    },
    ("MH", "33"): {
        "city": "Gadchiroli, Maharashtra",
        "center": [20.1809, 79.9999],
        "corridors": [
            ("Armori Road Highway Post (NH-353C)", 20.2100, 79.9920),
            ("Chamorshi Naka Main Junction", 20.1820, 79.9950),
            ("Indira Square Central Hub", 20.1780, 80.0010),
            ("Dhanora T-Junction Checkpost", 20.1720, 80.0150),
            ("Aheri Highway Outpost", 20.1450, 80.0100),
            ("Potegaon Link Road Gate", 20.1600, 80.0250),
        ]
    },
    ("MH", "31"): {
        "city": "Nagpur Urban, Maharashtra",
        "center": [21.1458, 79.0882],
        "corridors": [
            ("Kamptee Road North Toll", 21.2050, 79.1450),
            ("Automotive Square (NH-44)", 21.1890, 79.1120),
            ("Zero Mile Central Interchange", 21.1488, 79.0890),
            ("Sitabuldi Metro Junction", 21.1466, 79.0825),
            ("Wardha Road Flyover Hub", 21.1020, 79.0620),
            ("Dharampeth West Plaza", 21.1440, 79.0600),
        ]
    },
    ("MH", "40"): {
        "city": "Nagpur Rural / Ramtek, Maharashtra",
        "center": [21.3966, 79.3282],
        "corridors": [
            ("Kanhan Bridge Toll Plaza", 21.2310, 79.2450),
            ("Mouda Industrial Bypass", 21.2750, 79.3200),
            ("Mansar Highway T-Point (NH-44)", 21.3930, 79.2620),
            ("Ramtek Town Main Entrance", 21.3980, 79.3250),
            ("Parseoni Link Junction", 21.3780, 79.1950),
        ]
    },
    ("MH", "12"): {
        "city": "Pune, Maharashtra",
        "center": [18.5204, 73.8567],
        "corridors": [
            ("Hinjawadi IT Highway Toll", 18.5913, 73.7389),
            ("Shivajinagar Central Hub", 18.5314, 73.8446),
            ("Swargate Flyover Corridor", 18.5018, 73.8636),
            ("Hadapsar Magarpatta Gate", 18.5120, 73.9280),
            ("Viman Nagar Bypass Post", 18.5670, 73.9140),
        ]
    },
    ("MH", "01"): {
        "city": "Mumbai South, Maharashtra",
        "center": [18.9400, 72.8350],
        "corridors": [
            ("Dadar TT Circle Hub", 19.0178, 72.8478),
            ("Worli Sea Face Entry", 19.0144, 72.8150),
            ("Marine Drive Coastal Road", 18.9430, 72.8230),
            ("CST Main Station Gate", 18.9401, 72.8354),
            ("Colaba Causeway Junction", 18.9150, 72.8250),
        ]
    },
    ("TN", "01"): {
        "city": "Chennai Central, Tamil Nadu",
        "center": [13.0827, 80.2707],
        "corridors": [
            ("Kathipara Grand Flyover", 13.0067, 80.2025),
            ("Anna Salai Mount Road", 13.0600, 80.2500),
            ("Central Station Arterial Gate", 13.0820, 80.2750),
            ("Marina Coastal Tollway", 13.0500, 80.2824),
        ]
    },
    ("KA", "01"): {
        "city": "Bengaluru Central, Karnataka",
        "center": [12.9716, 77.5946],
        "corridors": [
            ("Hebbal Flyover North Toll", 13.0358, 77.5970),
            ("MG Road Central Junction", 12.9750, 77.6080),
            ("Silk Board Interchange", 12.9176, 77.6238),
            ("Electronic City Tollway", 12.8450, 77.6600),
        ]
    },
    ("DL", "01"): {
        "city": "North Delhi, NCR",
        "center": [28.6139, 77.2090],
        "corridors": [
            ("Kashmere Gate ISBT Plaza", 28.6670, 77.2310),
            ("Connaught Place Radial Ring", 28.6315, 77.2167),
            ("India Gate Radial Corridor", 28.6129, 77.2295),
            ("Dhaula Kuan Central Junction", 28.5921, 77.1610),
        ]
    },
}

STATE_FALLBACKS = {
    "MH": {"city": "Maharashtra State", "center": [19.7515, 75.7139]},
    "TN": {"city": "Tamil Nadu State", "center": [11.1271, 78.6569]},
    "KA": {"city": "Karnataka State", "center": [15.3173, 75.7139]},
    "DL": {"city": "Delhi NCR", "center": [28.7041, 77.1025]},
    "MP": {"city": "Madhya Pradesh", "center": [22.9734, 78.6569]},
    "GJ": {"city": "Gujarat State", "center": [22.2587, 71.1924]},
    "UP": {"city": "Uttar Pradesh", "center": [26.8467, 80.9462]},
    "TS": {"city": "Telangana State", "center": [18.1124, 79.0193]},
    "AP": {"city": "Andhra Pradesh", "center": [15.9129, 79.7400]},
    "RJ": {"city": "Rajasthan State", "center": [27.0238, 74.2179]},
}


def auto_format_and_validate_plate(plate: str) -> tuple[bool, str, str, str, str, str]:
    clean_compact = re.sub(r"[^A-Z0-9]", "", plate.upper().strip())
    pattern = r"^([A-Z]{2})(\d{1,2})([A-Z]{0,3})(\d+)$"
    match = re.match(pattern, clean_compact)
    
    if not match:
        return False, "", "", "", "", "Format mismatch. Enter valid Indian plate (e.g. mh34ak3456 or MH 34 AK 3456)."
    
    state_code = match.group(1)
    rto_code = match.group(2).zfill(2)
    series_code = match.group(3)
    digits_part = match.group(4)
    
    if len(digits_part) != 4:
        return False, "", "", "", "", f"Last segment must contain EXACTLY 4 digits (Got {len(digits_part)}: '{digits_part}')."
    
    if series_code:
        formatted_plate = f"{state_code} {rto_code} {series_code} {digits_part}"
    else:
        formatted_plate = f"{state_code} {rto_code} {digits_part}"
        
    return True, state_code, rto_code, clean_compact, formatted_plate, ""


def generate_unique_road_path_from_full_plate(clean_compact: str, state_code: str, rto_code: str) -> tuple[dict, list[tuple[str, float, float]]]:
    plate_hash_int = int(hashlib.sha256(clean_compact.encode()).hexdigest(), 16)
    vehicle_rng = random.Random(plate_hash_int)
    
    if (state_code, rto_code) in RTO_DATABASE:
        data = RTO_DATABASE[(state_code, rto_code)]
        city_name = data["city"]
        center = data["center"]
        corridor = list(data["corridors"])
    else:
        fallback = STATE_FALLBACKS.get(state_code, {"city": f"{state_code} State", "center": [20.5937, 78.9629]})
        city_name = f"{fallback['city']} (RTO: {state_code}-{rto_code})"
        center = fallback["center"]
        c_lat, c_lon = center
        corridor = [
            (f"Highway Toll Plaza {state_code}-{rto_code} A", c_lat + 0.030, c_lon - 0.020),
            (f"Outer Ring Junction {state_code}-{rto_code}", c_lat + 0.015, c_lon - 0.010),
            (f"City Center Metro Point {state_code}-{rto_code}", c_lat, c_lon),
            (f"State Highway Bypass {state_code}-{rto_code}", c_lat - 0.020, c_lon + 0.015),
            (f"Interstate Border Gate {state_code}-{rto_code}", c_lat - 0.035, c_lon + 0.025),
        ]
    
    mode_prob = vehicle_rng.random()
    if mode_prob < 0.45:
        route = corridor[:4]
    elif mode_prob < 0.78:
        outbound = corridor[:4]
        inbound = [corridor[2], corridor[1]]
        route = outbound + inbound
    else:
        route = [corridor[0], corridor[1], corridor[0], corridor[1], corridor[2]]

    return {"city": city_name, "center": center}, route


def connect() -> sqlite3.Connection:
    db = sqlite3.connect(DB_PATH)
    db.execute("""CREATE TABLE IF NOT EXISTS sightings (
        id INTEGER PRIMARY KEY AUTOINCREMENT, plate TEXT NOT NULL, camera_id TEXT NOT NULL,
        lat REAL, lon REAL, timestamp TEXT NOT NULL, confidence REAL DEFAULT 0.0)""")
    
    cur = db.execute("PRAGMA table_info(sightings)")
    cols = [r[1] for r in cur.fetchall()]
    if "lat" not in cols: db.execute("ALTER TABLE sightings ADD COLUMN lat REAL")
    if "lon" not in cols: db.execute("ALTER TABLE sightings ADD COLUMN lon REAL")

    db.execute("CREATE TABLE IF NOT EXISTS blacklist (plate TEXT PRIMARY KEY, added_on TEXT, note TEXT, auto_flagged INTEGER DEFAULT 0)")
    
    cur_b = db.execute("PRAGMA table_info(blacklist)")
    b_cols = [r[1] for r in cur_b.fetchall()]
    if "added_on" not in b_cols: db.execute("ALTER TABLE blacklist ADD COLUMN added_on TEXT")
    if "note" not in b_cols: db.execute("ALTER TABLE blacklist ADD COLUMN note TEXT")
    if "auto_flagged" not in b_cols: db.execute("ALTER TABLE blacklist ADD COLUMN auto_flagged INTEGER DEFAULT 0")

    db.execute("CREATE INDEX IF NOT EXISTS idx_plate ON sightings(plate)")
    db.commit()
    return db


def seed_vehicle_trajectory(formatted_plate: str, state_code: str, rto_code: str, clean_compact: str) -> None:
    _, route = generate_unique_road_path_from_full_plate(clean_compact, state_code, rto_code)
    
    plate_hash_int = int(hashlib.sha256(clean_compact.encode()).hexdigest(), 16)
    rng = random.Random(plate_hash_int)
    
    with connect() as db:
        db.execute("DELETE FROM sightings WHERE plate = ?", (formatted_plate,))
        rows = []
        base_time = datetime.now()
        
        for i, (cam_name, lat, lon) in enumerate(route):
            time_str = (base_time - timedelta(minutes=(len(route) - i) * 16)).strftime("%Y-%m-%d %H:%M:%S")
            conf = round(rng.uniform(0.93, 0.99), 2)
            rows.append((formatted_plate, cam_name, lat, lon, time_str, conf))
            
        db.executemany("INSERT INTO sightings(plate, camera_id, lat, lon, timestamp, confidence) VALUES (?, ?, ?, ?, ?, ?)", rows)
        db.commit()


def get_trajectory(formatted_plate: str) -> pd.DataFrame:
    with connect() as db:
        return pd.read_sql_query(
            "SELECT id, plate, camera_id, lat, lon, timestamp, confidence FROM sightings WHERE plate=? ORDER BY id ASC",
            db, params=(formatted_plate,)
        )


def evaluate_and_sync_surveillance(formatted_plate: str, trajectory: pd.DataFrame) -> tuple[str, str, str, str]:
    cams = trajectory["camera_id"].tolist()
    unique_cams = list(dict.fromkeys(cams))
    total_hops = len(cams)
    unique_count = len(unique_cams)
    
    is_excessive_looping = (total_hops >= 4 and cams[0] == cams[2] and cams[1] == cams[3])
    is_normal_return = (unique_count >= 3 and total_hops > unique_count and not is_excessive_looping)

    with connect() as db:
        existing_blacklist = db.execute("SELECT plate, auto_flagged FROM blacklist WHERE plate=?", (formatted_plate,)).fetchone()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if is_excessive_looping:
            db.execute("INSERT OR REPLACE INTO blacklist VALUES (?,?,?,?)", 
                       (formatted_plate, now_str, "Auto-Flagged: Excessive Junction Looping / Suspicious Movement", 1))
            db.commit()
            return "🚨 Auto-Flagged: Suspicious Looping", "#EF4444", "Vehicle detected looping repeatedly across the same junctions. <b>Added to Surveillance Watchlist.</b>", "SUSPICIOUS"

        if existing_blacklist and existing_blacklist[1] == 1 and not is_excessive_looping:
            db.execute("DELETE FROM blacklist WHERE plate=?", (formatted_plate,))
            db.commit()
            return "🟢 Normal Transit (Cleared)", "#10B981", "Normal road movement verified. <b>Removed from auto-flagged watchlist.</b>", "CLEARED"

        if is_normal_return:
            return "🔁 Standard Return / U-Turn", "#F59E0B", "Two-way return journey detected along highway corridor.", "RETURN"

        return "➡️ Normal Forward Transit", "#10B981", "One-way continuous transit along arterial road network.", "NORMAL"


def get_vehicle_analytics(formatted_plate: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    with connect() as db:
        density = pd.read_sql_query(
            "SELECT camera_id, COUNT(*) AS detections FROM sightings WHERE plate=? GROUP BY camera_id ORDER BY detections DESC",
            db, params=(formatted_plate,)
        )
        
        sightings_df = pd.read_sql_query(
            "SELECT camera_id, timestamp FROM sightings WHERE plate=? ORDER BY id ASC",
            db, params=(formatted_plate,)
        )
        
        corridors = []
        if len(sightings_df) > 1:
            for i in range(len(sightings_df) - 1):
                from_cam = sightings_df.iloc[i]["camera_id"]
                to_cam = sightings_df.iloc[i+1]["camera_id"]
                corridors.append({"from_checkpoint": from_cam, "to_checkpoint": to_cam})
            
            routes = pd.DataFrame(corridors).groupby(["from_checkpoint", "to_checkpoint"]).size().reset_index(name="trips")
            routes = routes.sort_values(by="trips", ascending=False)
        else:
            routes = pd.DataFrame(columns=["from_checkpoint", "to_checkpoint", "trips"])
            
    return density, routes


def get_all_blacklisted() -> pd.DataFrame:
    with connect() as db:
        return pd.read_sql_query("SELECT plate, added_on, note FROM blacklist ORDER BY added_on DESC", db)


def render_centered_table(df: pd.DataFrame):
    if df.empty:
        st.markdown("<p style='text-align: center; color: #9CA3AF;'>No records available</p>", unsafe_allow_html=True)
        return

    html_table = f"""
    <div style="width: 100%; overflow-x: auto; margin-top: 10px; margin-bottom: 20px; border-radius: 8px; border: 1px solid #1F2937;">
        <table style="width: 100%; border-collapse: collapse; text-align: center; background-color: #0E1117; font-family: sans-serif;">
            <thead>
                <tr style="background-color: #1F2937; color: #F9FAFB; border-bottom: 2px solid #374151;">
                    {''.join([f'<th style="padding: 12px; text-align: center !important; font-weight: 600; font-size: 14px;">{col}</th>' for col in df.columns])}
                </tr>
            </thead>
            <tbody>
                {''.join([
                    f'<tr style="border-bottom: 1px solid #1F2937;">' + 
                    ''.join([f'<td style="padding: 10px; text-align: center !important; color: #E5E7EB; font-size: 14px;">{val}</td>' for val in row]) + 
                    '</tr>'
                    for row in df.values
                ])}
            </tbody>
        </table>
    </div>
    """
    st.markdown(html_table, unsafe_allow_html=True)


def app() -> None:
    st.set_page_config(page_title="India ANPR Surveillance", layout="wide")
    
    st.markdown("""
        <style>
            .block-container {
                padding-top: 2rem;
                padding-bottom: 5rem;
                max-width: 1200px;
                margin: auto;
            }
            input[type="text"] {
                text-transform: uppercase !important;
                letter-spacing: 2px;
                font-weight: 700;
            }
            .metric-card-container {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 16px;
                margin-top: 24px;
                margin-bottom: 24px;
            }
            .metric-card {
                background-color: #111827;
                border: 1px solid #1F2937;
                border-radius: 10px;
                padding: 16px 12px;
                text-align: center;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                min-width: 0;
            }
            .metric-card .label {
                color: #9CA3AF;
                font-size: 13px;
                font-weight: 500;
                margin-bottom: 6px;
                white-space: nowrap;
            }
            .metric-card .val {
                color: #F9FAFB;
                font-size: 19px;
                font-weight: 700;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                max-width: 100%;
            }
            .section-spacer {
                margin-top: 36px;
                margin-bottom: 12px;
            }
            .retrace-tag {
                background-color: #D97706;
                color: #FEF3C7;
                padding: 4px 8px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
            }
            .suspicious-tag {
                background-color: #DC2626;
                color: #FEE2E2;
                padding: 4px 8px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
            }
            .normal-tag {
                background-color: #1E3A8A;
                color: #DBEAFE;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
            }
            .alert-box {
                padding: 14px 18px;
                border-radius: 8px;
                margin-top: 15px;
                margin-bottom: 15px;
                font-size: 15px;
            }
        </style>
    """, unsafe_allow_html=True)

    st.title("🇮🇳 Multi-State ANPR Surveillance & RTO Trajectory Engine")
    connect()

    with st.sidebar:
        st.header("🔍 Vehicle Registration")
        raw_plate = st.text_input(
            "Enter Number Plate",
            value="MH 34 AK 3456",
            help="Type without space or in lowercase (e.g. mh34ak3456) — system formats automatically"
        )

        is_valid, state_code, rto_code, clean_compact, formatted_plate, err_msg = auto_format_and_validate_plate(raw_plate)

        if is_valid and formatted_plate != raw_plate.strip():
            st.caption(f"Formatted: `{formatted_plate}`")

        st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)
        if is_valid:
            if st.button("🔄 Re-simulate Movement", use_container_width=True):
                seed_vehicle_trajectory(formatted_plate, state_code, rto_code, clean_compact)
                st.success(f"Route re-evaluated for {formatted_plate}")

        st.markdown("---")
        st.subheader("🛡️ Watchlist Controls")

        if is_valid:
            b_col1, b_col2 = st.columns(2)
            with b_col1:
                if st.button("➕ Manual Flag", use_container_width=True):
                    with connect() as db:
                        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        db.execute("INSERT OR REPLACE INTO blacklist VALUES (?,?,?,?)", (formatted_plate, now_str, "Manual Flag by Operator", 0))
                        db.commit()
                    st.rerun()

            with b_col2:
                if st.button("➖ Clear Flag", use_container_width=True):
                    with connect() as db:
                        db.execute("DELETE FROM blacklist WHERE plate=?", (formatted_plate,))
                        db.commit()
                    st.rerun()

    if not is_valid:
        st.markdown("<div class='section-spacer'></div>", unsafe_allow_html=True)
        st.error(f"❌ INVALID NUMBER PLATE: {err_msg}")
        st.info("💡 **Format Examples (Space optional):**\n* `mh34ak3456` ➔ `MH 34 AK 3456`\n* `mh33ga1001` ➔ `MH 33 GA 1001`\n* `dl01c9999` ➔ `DL 01 C 9999`\n* `tn01ab1234` ➔ `TN 01 AB 1234`\n\n*(Must end with exactly **4 numeric digits**)*")
        return

    trajectory = get_trajectory(formatted_plate)
    if trajectory.empty:
        seed_vehicle_trajectory(formatted_plate, state_code, rto_code, clean_compact)
        trajectory = get_trajectory(formatted_plate)

    regional_data, _ = generate_unique_road_path_from_full_plate(clean_compact, state_code, rto_code)

    # Autonomous Surveillance Sync Engine
    behavior_title, behavior_color, behavior_desc, behavior_type = evaluate_and_sync_surveillance(formatted_plate, trajectory)

    # Notification Alert Box
    box_bg = "#78350F" if behavior_type in ["RETURN"] else ("#064E3B" if behavior_type in ["NORMAL", "CLEARED"] else "#7F1D1D")
    box_border = "#D97706" if behavior_type in ["RETURN"] else ("#10B981" if behavior_type in ["NORMAL", "CLEARED"] else "#EF4444")
    
    st.markdown(f"""
        <div class="alert-box" style="background-color: {box_bg}; border: 1px solid {box_border}; color: #FEF3C7;">
            <b>{behavior_title}:</b> {behavior_desc}
        </div>
    """, unsafe_allow_html=True)

    # Top Metrics Grid
    metrics_html = f"""
    <div class="metric-card-container">
        <div class="metric-card">
            <div class="label">Standard Formatted Plate</div>
            <div class="val">{formatted_plate}</div>
        </div>
        <div class="metric-card">
            <div class="label">State / RTO Code</div>
            <div class="val">{state_code}-{rto_code}</div>
        </div>
        <div class="metric-card">
            <div class="label">Jurisdiction</div>
            <div class="val">{regional_data['city'].split(',')[0]}</div>
        </div>
        <div class="metric-card">
            <div class="label">Surveillance Status</div>
            <div class="val" style="color: {behavior_color};">{behavior_title.split(':')[0]}</div>
        </div>
    </div>
    """
    st.markdown(metrics_html, unsafe_allow_html=True)

    # Trajectory Data Table
    st.markdown("<div class='section-spacer'></div>", unsafe_allow_html=True)
    st.subheader(f"📍 Active Surveillance Feed: {regional_data['city']}")
    
    seen_so_far = {}
    status_tags = []
    for cam in trajectory["camera_id"]:
        seen_so_far[cam] = seen_so_far.get(cam, 0) + 1
        if seen_so_far[cam] > 1:
            if behavior_type == "SUSPICIOUS":
                status_tags.append(f'<span class="suspicious-tag">🚨 RECCE PASS #{seen_so_far[cam]}</span>')
            else:
                status_tags.append(f'<span class="retrace-tag">🔁 REPEAT PASS #{seen_so_far[cam]}</span>')
        else:
            status_tags.append('<span class="normal-tag">1st Detection</span>')

    display_trajectory = pd.DataFrame({
        "Sequence": [f"Hop #{i+1}" for i in range(len(trajectory))],
        "Plate": trajectory["plate"],
        "Camera Checkpoint": trajectory["camera_id"],
        "Timestamp": trajectory["timestamp"],
        "Confidence": trajectory["confidence"],
        "Diagnosis": status_tags
    })
    render_centered_table(display_trajectory)

    # Instant Zero-Lag OpenStreetMap Canvas
    st.markdown("<div class='section-spacer'></div>", unsafe_allow_html=True)
    st.subheader("🗺️ Live Trajectory Tracking Map (Road-Optimized)")
    if not trajectory.empty:
        avg_lat = float(trajectory["lat"].mean())
        avg_lon = float(trajectory["lon"].mean())
        
        path_points = trajectory[["lat", "lon"]].values.tolist()
        
        markers_data = []
        cam_visit_counts = {}
        for idx, row in trajectory.iterrows():
            cam = row["camera_id"]
            cam_visit_counts[cam] = cam_visit_counts.get(cam, 0) + 1
            visit_num = cam_visit_counts[cam]
            
            is_latest = (idx == len(trajectory) - 1)
            is_revisit = visit_num > 1
            
            marker_color = "#EF4444" if is_latest else ("#F59E0B" if is_revisit else "#2563EB")
            radius = 10 if (is_latest or is_revisit) else 7
            
            popup = f"<b>Hop #{idx + 1}: {cam}</b><br>{'🔁 REPEAT PASS #' + str(visit_num) if is_revisit else '1st Detection'}<br>Time: {row['timestamp']}"
            
            markers_data.append({
                "lat": float(row["lat"]),
                "lon": float(row["lon"]),
                "color": marker_color,
                "radius": radius,
                "popup": popup
            })

        # Pure Canvas Embed (Zero overhead, instant load)
        raw_map_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8" />
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <style>
                html, body {{ margin: 0; padding: 0; width: 100%; height: 100%; }}
                #map {{ width: 100%; height: 460px; border-radius: 8px; }}
            </style>
        </head>
        <body>
            <div id="map"></div>
            <script>
                var map = L.map('map').setView([{avg_lat}, {avg_lon}], 12);
                L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                    maxZoom: 19,
                    attribution: '© OpenStreetMap'
                }}).addTo(map);

                var polyline = L.polyline({json.dumps(path_points)}, {{
                    color: '#2563EB',
                    weight: 4,
                    opacity: 0.85
                }}).addTo(map);

                var markers = {json.dumps(markers_data)};
                markers.forEach(function(m) {{
                    L.circleMarker([m.lat, m.lon], {{
                        radius: m.radius,
                        color: '#FFFFFF',
                        weight: 2,
                        fillColor: m.color,
                        fillOpacity: 0.95
                    }}).bindPopup(m.popup).addTo(map);
                }});

                map.fitBounds(polyline.getBounds(), {{ padding: [30, 30] }});
            </script>
        </body>
        </html>
        """
        st.components.v1.html(raw_map_html, height=470)

    # 1 by 1 Vertical Analytics Layout
    density, routes = get_vehicle_analytics(formatted_plate)
    
    st.markdown("<div class='section-spacer'></div>", unsafe_allow_html=True)
    st.markdown("---")
    st.subheader("📊 Checkpoint Hit Frequency (Chart)")
    st.bar_chart(data=density.set_index("camera_id"))

    st.markdown("<div class='section-spacer'></div>", unsafe_allow_html=True)
    st.subheader("📋 Checkpoint Detection Summary")
    render_centered_table(density)

    st.markdown("<div class='section-spacer'></div>", unsafe_allow_html=True)
    st.subheader("🛣️ Sequential Travel Corridors")
    render_centered_table(routes)

    # Global Watchlist Database
    st.markdown("<div class='section-spacer'></div>", unsafe_allow_html=True)
    st.markdown("---")
    st.subheader("📋 Central Watchlist / Blacklisted Vehicles Database")
    st.caption("Active surveillance records and automatically flagged repetitive loopers.")
    
    all_blacklisted = get_all_blacklisted()
    if not all_blacklisted.empty:
        render_centered_table(all_blacklisted)
        
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        del_col1, del_col2 = st.columns([3, 1])
        with del_col1:
            plate_to_del = st.selectbox("Select plate to remove from watchlist", all_blacklisted["plate"].tolist())
        with del_col2:
            st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
            if st.button("🗑️ Remove Selected", use_container_width=True):
                with connect() as db:
                    db.execute("DELETE FROM blacklist WHERE plate=?", (plate_to_del,))
                    db.commit()
                st.rerun()
    else:
        st.success("✅ No vehicles currently flagged on the Central Watchlist.")


if __name__ == "__main__":
    from streamlit.web import cli as stcli

    if not st.runtime.exists():
        sys.argv = ["streamlit", "run", sys.argv[0]]
        sys.exit(stcli.main())
    else:
        app()