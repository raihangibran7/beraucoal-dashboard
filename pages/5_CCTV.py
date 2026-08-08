# pages/5_CCTV.py
import streamlit as st
import pandas as pd
import re, unicodedata
import folium
from streamlit_folium import st_folium
from pyproj import Transformer

st.title("📹 CCTV Monitoring")

# ===============================
# LOAD DATA GOOGLE SHEETS
# ===============================
sheet_url = "https://docs.google.com/spreadsheets/d/1cw3xMomuMOaprs8mkmj_qnib-Zp_9n68rYMgiRZZqBE/edit?usp=sharing"
sheet_id = sheet_url.split("/")[5]
sheet_names = ["Timbulan", "Program", "Ketidaksesuaian",
               "Survei_Online", "Survei_Offline", "CCTV", "Koordinat_UTM"]

all_df = {}
for sheet in sheet_names:
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet}"
        df = pd.read_csv(url, dtype=str, keep_default_na=False, encoding="utf-8")
        all_df[sheet] = df
    except Exception as e:
        st.error(f"Gagal load sheet {sheet}: {e}")
        all_df[sheet] = pd.DataFrame()

df_cctv = all_df.get("CCTV", pd.DataFrame())

# ===============================
# PARSE KOORDINAT
# ===============================
transformer = Transformer.from_crs("EPSG:32650", "EPSG:4326", always_xy=True)  # UTM 50N -> WGS84

def parse_coord(easting, northing):
    try:
        e = float(str(easting).replace("°E","").replace("E","").strip())
        n = float(str(northing).replace("°N","").replace("N","").strip())
    except:
        return None, None

    # Kasus 1: decimal degrees (langsung dipakai)
    if e <= 180 and n <= 90:
        return e, n   # lon, lat

    # Kasus 2: UTM (angka besar, ribuan-jutaan)
    if e > 100000 and n > 100000:
        lon, lat = transformer.transform(e, n)
        return lon, lat

    return None, None

if not df_cctv.empty and "easting" in df_cctv.columns and "northing" in df_cctv.columns:
    lon_lat = df_cctv.apply(lambda r: pd.Series(parse_coord(r["easting"], r["northing"]),
                                                index=["lon","lat"]), axis=1)
    df_cctv = pd.concat([df_cctv, lon_lat], axis=1)

# ===============================
# FILTER DROPDOWN
# ===============================
if not df_cctv.empty:
    perusahaan_list = ["Semua"] + sorted(df_cctv["perusahaan"].dropna().unique().tolist())
    site_list = ["Semua"] + sorted(df_cctv["site"].dropna().unique().tolist())

    col1, col2 = st.columns(2)
    with col1:
        perusahaan_filter = st.selectbox("Filter Perusahaan:", perusahaan_list)
    with col2:
        site_filter = st.selectbox("Filter Site:", site_list)

    filtered = df_cctv.copy()
    if perusahaan_filter != "Semua":
        filtered = filtered[filtered["perusahaan"] == perusahaan_filter]
    if site_filter != "Semua":
        filtered = filtered[filtered["site"] == site_filter]

# ===============================
# PETA DENGAN WARNA
# ===============================
    COLOR_LIST = [
        "red", "blue", "green", "purple", "orange",
        "darkred", "lightred", "beige", "darkblue", "darkgreen",
        "cadetblue", "darkpurple", "white", "pink", "lightblue",
        "lightgreen", "gray", "black", "lightgray"
    ]

    def assign_color(value, unique_values):
        idx = unique_values.index(value) % len(COLOR_LIST)
        return COLOR_LIST[idx]

    valid = filtered.dropna(subset=["lat","lon"])
    if not valid.empty:
        st.subheader("🗺️ Peta Lokasi CCTV")

        unique_perusahaan = sorted(valid["perusahaan"].dropna().unique().tolist())
        m = folium.Map(location=[valid["lat"].astype(float).mean(),
                                 valid["lon"].astype(float).mean()],
                       zoom_start=11)

        for _, row in valid.iterrows():
            color = assign_color(row["perusahaan"], unique_perusahaan)
            popup_text = f"""
            <b>{row.get('nama_titik_penaatan_ts','')}</b><br>
            {row.get('perusahaan','')} - {row.get('site','')}<br>
            Coverage: {row.get('coverage_cctv','')}
            """
            folium.Marker(
                location=[float(row["lat"]), float(row["lon"])],
                popup=popup_text,
                tooltip=row.get("nama_titik_penaatan_ts",""),
                icon=folium.Icon(color=color, icon="camera", prefix="fa")
            ).add_to(m)

        st_folium(m, width=700, height=500)
    else:
        st.warning("Tidak ada data sesuai filter untuk ditampilkan.")
else:
    st.warning("❌ Sheet CCTV kosong atau gagal dimuat.")
