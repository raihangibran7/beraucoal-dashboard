import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pyproj import Transformer
import folium
from streamlit_folium import st_folium
import calendar, re, math

# ===============================
# CONFIG DASHBOARD
# ===============================
st.set_page_config(page_title="Dashboard GBST", page_icon="🌍", layout="wide")

# ===============================
# LOGO + HEADER
# ===============================
logo = "assets/4logo.png"
st.logo(logo, icon_image=logo, size="large")
st.markdown(
    "<h1 style='font-size:24px; color:#000000; font-weight:bold; margin-bottom:0.5px;'>📈 Dashboard Gerakan Buang Sampah Terpilah (GBST)</h1>",
    unsafe_allow_html=True,
)

# ===============================
# UTILITIES
# ===============================
def norm_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = df.columns.astype(str).str.strip().str.lower().str.replace(" ", "_")
    return df

def company_to_code(s: pd.Series) -> pd.Series:
    return (
        s.astype(str).str.upper().str.replace(r"[^A-Z ]", "", regex=True)
         .str.split().apply(lambda t: t[-1] if len(t) else "")
    )

def fmt_num(x: float) -> str:
    """Bulatkan cantik: kalau integer tampil 0 desimal, selain itu 2 desimal."""
    if pd.isna(x): return "0"
    return f"{x:,.0f}" if float(x).is_integer() else f"{x:,.2f}"

# ===============================
# PARSER KOORDINAT (UTM -> WGS84)
# ===============================
transformer = Transformer.from_crs("EPSG:32650", "EPSG:4326", always_xy=True)
def parse_coord(easting, northing):
    try:
        e = float(str(easting).replace("°E","").replace("E","").strip())
        n = float(str(northing).replace("°N","").replace("N","").strip())
    except:
        return None, None
    if e <= 180 and n <= 90:     # decimal degrees
        return e, n
    if e > 100000 and n > 100000:  # UTM
        lon, lat = transformer.transform(e, n)
        return lon, lat
    return None, None

# ===============================
# LOAD DATA GOOGLE SHEETS
# ===============================
sheet_url = "https://docs.google.com/spreadsheets/d/1cw3xMomuMOaprs8mkmj_qnib-Zp_9n68rYMgiRZZqBE/edit?usp=sharing"
sheet_id = sheet_url.split("/")[5]
sheet_names = ["Timbulan","Program","Ketidaksesuaian","Survei_Online","Survei_Offline","CCTV","Koordinat_UTM"]

all_df = {}
for sheet in sheet_names:
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet}"
        df = pd.read_csv(url)
        all_df[sheet] = df
    except Exception as e:
        st.error(f"Gagal load sheet {sheet}: {e}")
        all_df[sheet] = pd.DataFrame()

# Normalisasi
df_timbulan      = norm_cols(all_df.get("Timbulan", pd.DataFrame()))
df_program       = norm_cols(all_df.get("Program", pd.DataFrame()))
df_ketidaksesuaian = norm_cols(all_df.get("Ketidaksesuaian", pd.DataFrame()))
df_online        = norm_cols(all_df.get("Survei_Online", pd.DataFrame()))
df_offline       = norm_cols(all_df.get("Survei_Offline", pd.DataFrame()))
df_cctv          = norm_cols(all_df.get("CCTV", pd.DataFrame()))
df_koordinat     = norm_cols(all_df.get("Koordinat_UTM", pd.DataFrame()))

# Simpan di session_state (opsional dipakai halaman lain)
st.session_state["data"] = {
    "Timbulan": df_timbulan, "Program": df_program, "Ketidaksesuaian": df_ketidaksesuaian,
    "Survei_Online": df_online, "Survei_Offline": df_offline,
    "CCTV": df_cctv, "Koordinat_UTM": df_koordinat
}

# =============================
# FILTER SIDEBAR
# =============================
st.sidebar.subheader("Filter Data")

site_list = sorted(df_timbulan["site"].dropna().unique()) if "site" in df_timbulan.columns else []
site_sel = st.sidebar.multiselect("Pilih Site", site_list, default=site_list)

perusahaan_list = sorted(df_timbulan["perusahaan"].dropna().unique()) if "perusahaan" in df_timbulan.columns else []
perusahaan_sel = st.sidebar.multiselect("Pilih Perusahaan", perusahaan_list, default=perusahaan_list)

# deteksi kolom bulan_tahun di df_program
pattern = r"^(januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember)_\d{4}$"
bulan_tahun_cols = [c for c in df_program.columns if re.match(pattern, c)]

# reshape wide -> long utk program
if bulan_tahun_cols:
    df_prog_long = df_program.melt(
        id_vars=[c for c in df_program.columns if c not in bulan_tahun_cols],
        value_vars=bulan_tahun_cols,
        var_name="bulan_tahun",
        value_name="Value"
    )
    df_prog_long["tahun"] = df_prog_long["bulan_tahun"].apply(lambda x: int(x.split("_")[1]))
    df_prog_long["bulan"] = df_prog_long["bulan_tahun"].apply(lambda x: x.split("_")[0].capitalize())
else:
    df_prog_long = df_program.copy()
    df_prog_long["tahun"] = None
    df_prog_long["bulan"] = None

bulan_map = {"Januari":1,"Februari":2,"Maret":3,"April":4,"Mei":5,"Juni":6,
             "Juli":7,"Agustus":8,"September":9,"Oktober":10,"November":11,"Desember":12}

# filter bulan & tahun (ambil dari data program agar range realistis)
tahun_tersedia = sorted(df_prog_long["tahun"].dropna().astype(int).unique().tolist())
if not tahun_tersedia:
    # fallback: kalau tidak ada, coba dari ketidaksesuaian
    if "TanggalLapor" in df_ketidaksesuaian.columns:
        tgl = pd.to_datetime(df_ketidaksesuaian["TanggalLapor"], dayfirst=True, errors="coerce")
        tahun_tersedia = sorted(tgl.dt.year.dropna().astype(int).unique().tolist())

bulan_tersedia = list(bulan_map.keys())
tahun_pilihan = st.sidebar.multiselect("Pilih Tahun:", tahun_tersedia, default=tahun_tersedia)
bulan_pilihan = st.sidebar.multiselect("Pilih Bulan:", bulan_tersedia, default=bulan_tersedia)

# =============================
# Helper filter global
# =============================
def apply_site_perusahaan_filter(df, site_col="site", perusahaan_col="perusahaan"):
    d = df.copy()
    if site_sel and site_col in d.columns:
        d = d[d[site_col].isin(site_sel)]
    if perusahaan_sel and perusahaan_col in d.columns:
        d = d[d[perusahaan_col].isin(perusahaan_sel)]
    return d


def apply_program_filter(df_prog_long, tahun_pilihan, bulan_pilihan):
    d = df_prog_long.copy()
    if "tahun" in d.columns and tahun_pilihan:
        d = d[d["tahun"].isin(tahun_pilihan)]
    if "bulan" in d.columns and bulan_pilihan:
        d = d[d["bulan"].isin(bulan_pilihan)]
    d = apply_site_perusahaan_filter(d)
    return d


def apply_ketidaksesuaian_filter(df_ket, tahun_pilihan, bulan_pilihan):
    d = df_ket.copy()
    if "TanggalLapor" in d.columns:
        d["TanggalLapor"] = pd.to_datetime(
            d["TanggalLapor"], dayfirst=True, errors="coerce"
        )
        d["tahun"] = d["TanggalLapor"].dt.year
        d["bulan"] = d["TanggalLapor"].dt.month
        if tahun_pilihan:
            d = d[d["tahun"].isin(tahun_pilihan)]
        if bulan_pilihan:
            bulan_num = [bulan_map[b] for b in bulan_pilihan]
            d = d[d["bulan"].isin(bulan_num)]
    if "status_temuan" in d.columns:
        d = d[d["status_temuan"].str.lower() == "valid"]
    d = apply_site_perusahaan_filter(d)
    return d


def apply_timbulan_filter(df_timbulan, tahun_pilihan):
    d = df_timbulan.copy()
    d = apply_site_perusahaan_filter(d)
    if "tahun" in d.columns and tahun_pilihan:
        d["tahun"] = pd.to_numeric(d["tahun"], errors="coerce")
        d = d[d["tahun"].isin(tahun_pilihan)]
    return d


# === Helper: hitung Man Power unik ===
def total_manpower_unik(df):
    if "man_power" not in df.columns:
        return 0, pd.DataFrame(), 0

    d = df.copy()
    d["man_power"] = pd.to_numeric(d["man_power"], errors="coerce").fillna(0)

    # Kunci deduplikasi yang BENAR (harus sama dengan perhitungan SNI)
    keys = ["site", "perusahaan"]
    if "tahun" in d.columns:
        keys.append("tahun")

    # TOTAL manpower unik berdasarkan kombinasi site-perusahaan-tahun
    d_uniq = d.drop_duplicates(subset=keys, keep="last")

    total_mp = d_uniq["man_power"].sum()

    # JUMLAH perusahaan-site unik (abaikan tahun)
    if {"site", "perusahaan"}.issubset(d.columns):
        jumlah_unit = (
            d_uniq[["site", "perusahaan"]]
            .drop_duplicates()
            .shape[0]
        )
    else:
        jumlah_unit = 0

    # AGREGASI per site
    if "site" in d_uniq.columns:
        mp_site = (
            d_uniq.groupby("site", as_index=False)["man_power"].sum()
            .rename(columns={"man_power": "mp_unik"})
        )
    else:
        mp_site = pd.DataFrame()

    return total_mp, mp_site, jumlah_unit


# apply semua filter
df_timbulan_f   = apply_timbulan_filter(df_timbulan, tahun_pilihan)
df_prog_f       = apply_program_filter(df_prog_long, tahun_pilihan, bulan_pilihan)
df_ket_f        = apply_ketidaksesuaian_filter(df_ketidaksesuaian, tahun_pilihan, bulan_pilihan)
df_online_f     = apply_site_perusahaan_filter(df_online)
df_offline_f    = apply_site_perusahaan_filter(df_offline)
df_cctv_f       = apply_site_perusahaan_filter(df_cctv)
df_koordinat_f  = apply_site_perusahaan_filter(df_koordinat)

# total manpower unik SESUDAH df_timbulan_f ada
total_mp_unik, mp_site_df, jumlah_unit = total_manpower_unik(df_timbulan_f)

# =============================
# DAYS PERIOD (ikut filter)
# =============================
days_period = 0
for y in tahun_pilihan:
    for b in bulan_pilihan:
        days_period += calendar.monthrange(y, bulan_map[b])[1]
if days_period == 0:
    days_period = 1
st.info(f"📅 Total jumlah hari periode filter: **{days_period} hari**")

# =============================
# TAB
# =============================
tab1, tab2 = st.tabs(["Overview", "Data Quality Check"])

with tab1:
    try:
        # ---------- METRIC DASAR ----------
        # Timbulan (kg/hari)
        if "timbulan" in df_timbulan_f.columns:
            df_timbulan_f["timbulan"] = pd.to_numeric(df_timbulan_f["timbulan"].astype(str).str.replace(",", "."), errors="coerce")
            total_timbulan_hari = df_timbulan_f["timbulan"].sum()
            total_timbulan_all  = pd.to_numeric(df_timbulan_f.get("data_input_total", 0), errors="coerce").sum()
        else:
            total_timbulan_hari = total_timbulan_all = 0
        # ============================
        # METRIC PEMBANDING (TAHUN SEBELUMNYA)
        # ============================
        # Kita pakai logika: jika user pilih 1 tahun, bandingkan dengan tahun sebelumnya.
        prev_total_timbulan_all = None
        prev_total_timbulan_hari = None
        prev_rata_timbulan_per_orang = None

        if len(tahun_pilihan) == 1:
            current_year = tahun_pilihan[0]
            prev_year = current_year - 1

            # data timbulan tahun sebelumnya dengan filter site & perusahaan yang sama
            df_timbulan_prev = apply_timbulan_filter(df_timbulan, [prev_year])
            if "timbulan" in df_timbulan_prev.columns:
                df_timbulan_prev["timbulan"] = pd.to_numeric(
                    df_timbulan_prev["timbulan"].astype(str).str.replace(",", "."),
                    errors="coerce"
                )
                prev_total_timbulan_hari = df_timbulan_prev["timbulan"].sum()
                prev_total_timbulan_all = pd.to_numeric(
                    df_timbulan_prev.get("data_input_total", 0),
                    errors="coerce"
                ).sum()

                # hitung man power unik tahun sebelumnya (pakai helper yang sama)
                total_mp_prev, mp_site_prev, jumlah_unit_prev = total_manpower_unik(df_timbulan_prev)
                prev_rata_timbulan_per_orang = (
                    prev_total_timbulan_hari / total_mp_prev if total_mp_prev > 0 else None
                )

        # Jumlah program unik (bukan baris melt)
        if "nama_program" in df_prog_f.columns:
            jumlah_program = (
                df_prog_f["nama_program"].astype(str).str.strip().replace({"": None}).dropna().nunique()
            )
        else:
            jumlah_program = 0

        # ===============================
        # KETIDAKSESUAIAN (Valid / Total)
        # ===============================
        # Total laporan (semua status) pakai filter site, perusahaan, tahun, bulan
        dk_all = apply_site_perusahaan_filter(df_ketidaksesuaian.copy())
        if "TanggalLapor" in dk_all.columns:
            dk_all["TanggalLapor"] = pd.to_datetime(dk_all["TanggalLapor"], dayfirst=True, errors="coerce")
            dk_all["tahun"] = dk_all["TanggalLapor"].dt.year
            dk_all["bulan"] = dk_all["TanggalLapor"].dt.month
            if tahun_pilihan:
                dk_all = dk_all[dk_all["tahun"].isin(tahun_pilihan)]
            if bulan_pilihan:
                bulan_num = [bulan_map[b] for b in bulan_pilihan]
                dk_all = dk_all[dk_all["bulan"].isin(bulan_num)]

        total_reports = len(dk_all)

        # Jumlah valid sudah otomatis ada di df_ket_f
        total_valid = len(df_ket_f) if not df_ket_f.empty else 0

        # kg/hari/orang (sesuai SNI)
        rata_timbulan_per_orang = (total_timbulan_hari / total_mp_unik) if total_mp_unik > 0 else 0.0
        
        c1, c2, c3, c4, c5 = st.columns(5)

        # --- Total Timbulan (kg) ---
        if prev_total_timbulan_all is not None:
            delta_total = total_timbulan_all - prev_total_timbulan_all
            delta_text_total = f"{'+' if delta_total >= 0 else ''}{fmt_num(delta_total)} kg vs {prev_year}"
        else:
            delta_text_total = None

        c1.metric(
            "Total Timbulan (kg)",
            fmt_num(total_timbulan_all),
            delta=delta_text_total
        )

        # --- Rata-rata Timbulan (kg/hari) ---
        if prev_total_timbulan_hari is not None:
            # di sini aku pakai selisih total kg/hari nya, bukan dibagi hari lagi
            delta_hari = total_timbulan_hari - prev_total_timbulan_hari
            delta_text_hari = f"{'+' if delta_hari >= 0 else ''}{fmt_num(delta_hari)} kg/hari vs {prev_year}"
        else:
            delta_text_hari = None

        c2.metric(
            "Rata-rata Timbulan (kg/hari)",
            fmt_num(total_timbulan_hari),
            delta=delta_text_hari
        )

        # --- Rata-rata Timbulan (kg/hari/orang) ---
        if prev_rata_timbulan_per_orang is not None:
            delta_rata_orang = rata_timbulan_per_orang - prev_rata_timbulan_per_orang
            delta_text_orang = f"{'+' if delta_rata_orang >= 0 else ''}{delta_rata_orang:.3f} kg/hari/orang vs {prev_year}"
        else:
            delta_text_orang = None

        c3.metric(
            "Rata-rata Timbulan (kg/hari/orang)",
            f"{rata_timbulan_per_orang:.3f}",
            delta=delta_text_orang
        )

        # --- Jumlah Program ---
        # logika: kalau mau, bisa juga bandingkan jumlah program tahun ini vs prev_year
        if len(tahun_pilihan) == 1:
            df_prog_prev = apply_program_filter(df_prog_long, [prev_year], bulan_pilihan)
            if "nama_program" in df_prog_prev.columns:
                prev_jumlah_program = (
                    df_prog_prev["nama_program"].astype(str).str.strip().replace({"": None}).dropna().nunique()
                )
            else:
                prev_jumlah_program = None
        else:
            prev_jumlah_program = None

        if prev_jumlah_program is not None:
            delta_prog = jumlah_program - prev_jumlah_program
            delta_text_prog = f"{'+' if delta_prog >= 0 else ''}{delta_prog} program vs {prev_year}"
        else:
            delta_text_prog = None

        c4.metric("Jumlah Program", jumlah_program, delta=delta_text_prog)

        # --- Ketidaksesuaian Valid ---
        # Di sini lebih tricky: mau dibandingkan apa? total_valid, atau rasio valid/total?
        # Untuk contoh, aku cuma tulis teks kecil tanpa hitung delta numerik.
        ratio_valid = (total_valid / total_reports * 100) if total_reports > 0 else 0
        c5.metric(
            "Ketidaksesuaian Valid",
            f"{total_valid} / {total_reports}",
            delta=f"{ratio_valid:.1f}% valid"
        )

        # =====================================================
        # KARTU (Reduce, Pengolahan, Sisa) — PAKAI df_prog_f (melt) SESUAI FILTER
        # =====================================================
        # Sum per kategori dari kolom Value (angka bulanan), lalu / days_period
        prog_pengolahan_per_hari = 0.0
        prog_pengurangan_per_hari = 0.0
        if not df_prog_f.empty and {"kategori","Value"}.issubset(df_prog_f.columns):
            df_prog_f["Value"] = pd.to_numeric(df_prog_f["Value"], errors="coerce").fillna(0)
            prog_pengolahan_per_hari = df_prog_f.loc[df_prog_f["kategori"]=="Program Pengelolaan","Value"].sum() / days_period
            prog_pengurangan_per_hari = df_prog_f.loc[df_prog_f["kategori"]=="Program Pengurangan","Value"].sum() / days_period
            # --- tambahkan persentase reduce (tanpa mengubah logika lain) ---
            persen_pengurangan = (
                prog_pengurangan_per_hari / total_timbulan_hari * 100
                if total_timbulan_hari > 0 else 0
            )

        sisa_per_hari = max(total_timbulan_hari - prog_pengolahan_per_hari, 0)
        persen_pengolahan = (prog_pengolahan_per_hari/total_timbulan_hari*100) if total_timbulan_hari>0 else 0
        persen_sisa       = (sisa_per_hari/total_timbulan_hari*100) if total_timbulan_hari>0 else 0

        # CSS card
        st.markdown("""
            <style>
            .card {border:1px solid #e0e0e0; border-radius:12px; padding:20px; background:#fff;
                   box-shadow:3px 3px 12px rgba(0,0,0,0.1); text-align:center; margin-bottom:6px;}
            .card h3 {font-size:20px; color:#333; margin-bottom:6px;}
            .card h2 {font-size:32px; color:#257d0a; margin:0;}
            .card p  {font-size:16px; color:#666; margin:0;}
            </style>
        """, unsafe_allow_html=True)

        ca, cb, cc = st.columns(3)
        with ca:
            st.markdown(
                f"<div class='card'><h3>Pengurangan Sampah (Reduce)</h3>"
                f"<h2>{persen_pengurangan:.2f}%</h2>"
                f"<p>{fmt_num(prog_pengurangan_per_hari)} kg/hari dari timbulan</p></div>",
                unsafe_allow_html=True
            )

        with cb:
            st.markdown(f"<div class='card'><h3>Pengolahan Sampah</h3><h2>{persen_pengolahan:.2f}%</h2><p>{fmt_num(prog_pengolahan_per_hari)} kg/hari dari timbulan</p></div>", unsafe_allow_html=True)
        with cc:
            st.markdown(f"<div class='card'><h3>Timbulan Tidak Terkelola</h3><h2>{persen_sisa:.2f}%</h2><p>{fmt_num(sisa_per_hari)} kg/hari</p></div>", unsafe_allow_html=True)

        # =====================================================
        # PETA SITE & CCTV (logika peta tetap pakai total_calc/days_period)
        # =====================================================
        st.subheader("🗺️ Peta Lokasi Site & CCTV")
        filter_map = st.radio("Pilih data:", ["Timbulan + Site", "CCTV", "Keduanya"], horizontal=True)
        fmap = folium.Map(location=[-2.0,117.0], zoom_start=6)

        # --- Site Timbulan ---
        if not df_timbulan.empty and not df_koordinat.empty and filter_map in ["Timbulan + Site","Keduanya"]:
            df_timbulan["company_code"] = company_to_code(df_timbulan.get("perusahaan",""))
            agg_timbulan = df_timbulan.groupby(["site","company_code"], as_index=False).agg(total_timbulan=("timbulan","sum"))

            if not df_program.empty and "kategori" in df_program.columns:
                df_pengolahan = df_program[df_program["kategori"]=="Program Pengelolaan"].copy()
                df_pengolahan["total_calc"] = pd.to_numeric(df_pengolahan.get("total_calc",0), errors="coerce").fillna(0)
                agg_pengolahan = df_pengolahan.groupby(["site","perusahaan"], as_index=False).agg(total_pengolahan=("total_calc","sum"))
                agg_pengolahan["company_code"] = company_to_code(agg_pengolahan["perusahaan"])
                agg_pengolahan["sampah_terkelola"] = agg_pengolahan["total_pengolahan"] / days_period
            else:
                agg_pengolahan = pd.DataFrame(columns=["site","company_code","sampah_terkelola"])

            agg = agg_timbulan.merge(agg_pengolahan[["site","company_code","sampah_terkelola"]],
                                     on=["site","company_code"], how="left")
            agg["sampah_terkelola"] = agg["sampah_terkelola"].fillna(0)
            agg["sampah_tidak_terkelola"] = agg["total_timbulan"] - agg["sampah_terkelola"]

            if {"x","y"}.issubset(df_koordinat.columns):
                dko = df_koordinat.copy()
                dko["x"] = pd.to_numeric(dko["x"], errors="coerce")
                dko["y"] = pd.to_numeric(dko["y"], errors="coerce")
                dko = dko.dropna(subset=["x","y"])
                dko["company_code"] = company_to_code(dko.get("company",""))
                df_map = dko.merge(agg, on=["site","company_code"], how="left")
                if not df_map.empty:
                    lon, lat = transformer.transform(df_map["x"].astype(float).values, df_map["y"].astype(float).values)
                    df_map["lon"], df_map["lat"] = lon, lat
                    for _, r in df_map.iterrows():
                        popup_html = (
                            f"<b>Site:</b> {r.get('site','-')}<br>"
                            f"<b>Perusahaan:</b> {r.get('company_code','-')}<br>"
                            f"<b>Total Timbulan:</b> {fmt_num(r.get('total_timbulan',0))} kg<br>"
                            f"<b>Sampah Terkelola:</b> {fmt_num(r.get('sampah_terkelola',0))} kg<br>"
                            f"<b>Sampah Tidak Terkelola:</b> {fmt_num(r.get('sampah_tidak_terkelola',0))} kg"
                        )
                        folium.Marker(
                            location=[r["lat"], r["lon"]],
                            tooltip=f"{r['site']} - {r['company_code']}",
                            popup=popup_html,
                            icon=folium.Icon(color="green", icon="trash", prefix="fa"),
                        ).add_to(fmap)

        # --- CCTV ---
        if not df_cctv.empty and {"easting","northing"}.issubset(df_cctv.columns) and filter_map in ["CCTV","Keduanya"]:
            dcc = df_cctv.copy()
            lonlat = dcc.apply(lambda r: pd.Series(parse_coord(r["easting"], r["northing"]), index=["lon","lat"]), axis=1)
            dcc = pd.concat([dcc, lonlat], axis=1).dropna(subset=["lat","lon"])
            uniq_comp = sorted(dcc["perusahaan"].dropna().unique().tolist())
            color_list = ["red","blue","green","purple","orange","darkred","lightred","beige","darkblue","darkgreen",
                          "cadetblue","darkpurple","white","pink","lightblue","lightgreen","gray","black","lightgray"]
            def assign_color(val):
                if not uniq_comp: return "blue"
                return color_list[uniq_comp.index(val) % len(color_list)]
            for _, row in dcc.iterrows():
                popup_text = (
                    f"<b>{row.get('nama_titik_penaatan_ts','')}</b><br>"
                    f"{row.get('perusahaan','')} - {row.get('site','')}<br>"
                    f"Coverage: {row.get('coverage_cctv','')}"
                )
                folium.Marker(
                    location=[float(row["lat"]), float(row["lon"])],
                    popup=popup_text,
                    tooltip=row.get("nama_titik_penaatan_ts",""),
                    icon=folium.Icon(color=assign_color(row.get("perusahaan","")), icon="camera", prefix="fa")
                ).add_to(fmap)

        st_folium(fmap, height=600, use_container_width=True)

        # =====================================================
        # GRAFIK TIMBULAN – tidak diubah
        # =====================================================
        col1, col2 = st.columns([0.5,0.5])
        if not df_timbulan.empty and "jenis_timbulan" in df_timbulan.columns:
            jenis_unique = df_timbulan["jenis_timbulan"].unique()
            colors = px.colors.sequential.Viridis[:len(jenis_unique)]
            cmap = {j:c for j,c in zip(jenis_unique, colors)}

            with col1:
                st.markdown('<p style="text-align:center;font-weight:bold;">🥧 Proporsi Timbulan Berdasarkan Jenis</p>', unsafe_allow_html=True)
                jenis_sum = df_timbulan.groupby("jenis_timbulan")["timbulan"].sum()
                fig2 = px.pie(names=jenis_sum.index, values=jenis_sum.values,
                              hole=0.4, color=jenis_sum.index, color_discrete_map=cmap, template="plotly_white")
                fig2.update_traces(textinfo="percent+label", showlegend=True)
                st.plotly_chart(fig2, use_container_width=True)

            with col2:
                st.markdown('<p style="text-align:center;font-weight:bold;">Proporsi Timbulan Per Site</p>', unsafe_allow_html=True)
                total_site = df_timbulan.groupby(["site","jenis_timbulan"], as_index=False)["timbulan"].sum()
                total_site = total_site.sort_values(by=["site","timbulan"], ascending=[True,False])
                fig1 = px.bar(total_site, y="site", x="timbulan", color="jenis_timbulan",
                              orientation="h", text="timbulan", template="plotly_white",
                              labels={"timbulan":"Total Timbulan (kg)", "jenis_timbulan":"Jenis Timbulan"},
                              color_discrete_map=cmap, height=400)
                fig1.update_traces(texttemplate='%{text:,.0f}', textposition="outside")
                st.plotly_chart(fig1, use_container_width=True)

        # =====================================================
        # Survei & Ketidaksesuaian (ringkas)
        # =====================================================
        st.subheader("📊 Survei & Ketidaksesuaian")
        if not df_ketidaksesuaian.empty and "kategori_subketidaksesuaian" in df_ketidaksesuaian.columns:
            df_valid = df_ketidaksesuaian[df_ketidaksesuaian["status_temuan"].str.lower()=="valid"]
            if not df_valid.empty:
                prop = df_valid["kategori_subketidaksesuaian"].value_counts()
                fig_ket = px.pie(names=prop.index, values=prop.values, hole=0.4,
                                 color=prop.index, template="plotly_white",
                                 color_discrete_map={"Perilaku":"#347829","Non Perilaku":"#78b00a"})
                fig_ket.update_traces(textinfo="percent+label")
                st.markdown("<p style='font-weight:bold;text-align:center;'>⚠️ Proporsi Ketidaksesuaian</p>", unsafe_allow_html=True)
                st.plotly_chart(fig_ket, use_container_width=True)

        # Gauge survei Q2
        df_survey = pd.concat([df_online, df_offline], ignore_index=True)
        col_q = "2. Seberapa optimal program GBST berjalan selama ini di perusahaan Anda?"
        if not df_survey.empty and col_q not in df_survey.columns:
            cand = [c for c in df_survey.columns if ("optimal" in c.lower() and "gbst" in c.lower())]
            if cand: col_q = cand[0]
        if col_q in df_survey.columns:
            df_survey[col_q] = pd.to_numeric(df_survey[col_q], errors="coerce")
            df_survey = df_survey.dropna(subset=[col_q])
            if not df_survey.empty:
                avg_score = df_survey[col_q].mean()
                max_score = max(df_survey[col_q].max(), 1)
                gauge_fig = go.Figure(go.Indicator(
                    mode="gauge+number", value=avg_score,
                    title={"text":"Rata-rata Skor Optimalitas Program"},
                    gauge={'axis':{'range':[0,max_score]}, 'bar':{'color':"green"},
                           'steps':[{'range':[0,max_score*0.5],'color':"#F58C62"},
                                    {'range':[max_score*0.5,max_score*0.8],'color':"#E1EF47"},
                                    {'range':[max_score*0.8,max_score],'color':"#4CB817"}]}
                ))
                st.plotly_chart(gauge_fig, use_container_width=True)
        else:
            st.warning(f"Kolom '{col_q}' tidak ditemukan dalam data survei.")

    except Exception as e:
        st.error("Terjadi error di Overview")
        st.exception(e)

with tab2:
    st.subheader("📋 Preview Data Timbulan")
    st.dataframe(df_timbulan.head(100) if not df_timbulan.empty else "Data Timbulan kosong.")
    st.subheader("📋 Preview Data Program")
    st.dataframe(df_program.head(100) if not df_program.empty else "Data Program kosong.")
    st.subheader("📋 Preview Data Ketidaksesuaian")
    st.dataframe(df_ketidaksesuaian.head(100) if not df_ketidaksesuaian.empty else "Data Ketidaksesuaian kosong.")
    st.subheader("📋 Preview Data Survei (Online + Offline)")
    st.dataframe(pd.concat([df_online, df_offline], ignore_index=True).head(100) if not df_online.empty or not df_offline.empty else "Data Survei kosong.")
    st.subheader("📋 Preview Data Koordinat UTM & CCTV")
    st.dataframe(df_koordinat.head(50) if not df_koordinat.empty else "Data Koordinat kosong.")
    st.dataframe(df_cctv.head(50) if not df_cctv.empty else "Data CCTV kosong.")
