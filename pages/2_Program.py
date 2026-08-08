# ==================================================
# STREAMLIT - Program Pengurangan & Pengolahan (FIX YEAR 2024 + UPDATED CLUSTER)
# ==================================================
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import calendar, re

st.markdown('<p style="text-align: left;font-weight: bold;">♻️ Program Pengurangan & Pengolahan</p>', unsafe_allow_html=True)

# =============================
# LOAD DATA GOOGLE SHEETS
# =============================
sheet_url = "https://docs.google.com/spreadsheets/d/1cw3xMomuMOaprs8mkmj_qnib-Zp_9n68rYMgiRZZqBE/edit?usp=sharing"
sheet_id = sheet_url.split("/")[5]
sheet_name = ["Timbulan","Program","Survei_Online","Ketidaksesuaian","Survei_Offline","CCTV","Koordinat_UTM"]

all_df = {}
for sheet in sheet_name:
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet}"
        df = pd.read_csv(url)
        all_df[sheet] = df
    except Exception as e:
        st.error(f"Gagal load sheet {sheet}: {e}")

# =============================
# AMBIL DATAFRAME
# =============================
df_timbulan = all_df.get("Timbulan", pd.DataFrame()).copy()
df_program = all_df.get("Program", pd.DataFrame()).copy()
df_ketidaksesuaian = all_df.get("Ketidaksesuaian", pd.DataFrame()).copy()

# =============================
# NORMALISASI NAMA KOLOM
# =============================
def norm_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = (df.columns.astype(str)
                  .str.strip()
                  .str.lower()
                  .str.replace(" ", "_")
                  .str.replace("/", "_"))
    return df

df_timbulan = norm_cols(df_timbulan)
df_program = norm_cols(df_program)
df_ketidaksesuaian = norm_cols(df_ketidaksesuaian)

# =============================
# NORMALISASI NAMA PROGRAM (dibesarkan cakupannya)
# =============================
def normalize_name(text: str):
    if pd.isna(text): 
        return ""
    txt = str(text).lower().strip()

    # ejaan/alias umum
    txt = txt.replace("magot", "maggot")
    txt = txt.replace("vermikomposting", "vermicomposting")
    txt = txt.replace("vermi compost", "vermicomposting")
    txt = txt.replace("meal box", "mealbox")
    txt = txt.replace("pack meal", "packmeal")
    txt = txt.replace("reuseable", "reusable")
    txt = txt.replace("bank sampah anorganik", "bank sampah anorganik")
    txt = txt.replace("bank sampah organik", "bank sampah organik")

    # penyamaan frasa
    txt = re.sub(r"\s+", " ", txt)

    return txt.title()

if "nama_program" in df_program.columns:
    df_program["nama_program"] = df_program["nama_program"].map(normalize_name)

# =============================
# CLUSTER PROGRAM (diperluas)
# =============================
def cluster_program(name: str):
    txt = str(name).lower()

    # Maggot / BSF / Hermetia / Budidaya larva
    if re.search(r"\bmaggot\b|\bhermetia\b|\bbsf\b|\blarva\b|\bbudidaya", txt):
        return "Maggot/BSF"

    # Kompos / Vermi / Komposting
    if re.search(r"\bkompos|\bkomposting|\bvermi", txt):
        return "Komposting"

    # Bank Sampah (kertas/kardus/botol/anorganik/organik)
    if "bank sampah" in txt:
        return "Bank Sampah"

    # Reduce Plastik: tumbler/mealbox/packmeal/prasmanan/diet plastik
    if re.search(r"\btumbler\b|\bmealbox\b|\bpackmeal\b|\bprasmanan\b|\bdiet plastik\b|\breduce\b", txt):
        return "Reduce Plastik"

    return "Lainnya"

df_program["cluster"] = df_program["nama_program"].map(cluster_program)

# =============================
# JENIS SAMPAH (AMBIL DARI DATA ASLI)
# =============================
# Hanya fallback ke cluster kalau kolom tidak tersedia
if "jenis_sampah" not in df_program.columns:
    def map_timbulan(cluster):
        if cluster in ["Maggot/BSF","Komposting"]:
            return "Organik"
        if cluster == "Bank Sampah":
            return "Anorganik"
        if cluster == "Reduce Plastik":
            return "Plastik"
        return "Campuran"
    df_program["jenis_sampah"] = df_program["cluster"].map(map_timbulan)

# Normalisasi ejaan
df_program["jenis_sampah"] = (
    df_program["jenis_sampah"]
    .astype(str).str.strip().str.lower()
    .replace({
        "organik lainnya": "organik",
        "sisa makanan & sayur": "organik",
        "non organik": "anorganik",
        "non-organik": "anorganik",
        "an-organik": "anorganik",
        "plastik": "plastik",
        "campuran": "campuran"
    })
    .map({"organik":"Organik","anorganik":"Anorganik","plastik":"Plastik","campuran":"Campuran"})
)

# =============================
# PALET WARNA ECO
# =============================
color_map = {
    "Maggot/BSF": "#1b7837",
    "Komposting": "#4daf4a",
    "Bank Sampah": "#ffff99",
    "Reduce Plastik": "#b2df8a",
    "Lainnya": "#d9f0a3",
    "Organik": "#238443",
    "Anorganik": "#ffffbf",
    "Plastik": "#addd8e",
    "Campuran": "#f7fcb9"
}

# =============================
# HELPER: DEDUP PROGRAM UNIK
# =============================
UNIQ_KEYS = [c for c in ["perusahaan","site","nama_program","kategori","cluster","jenis_sampah"] if c in df_program.columns]

def unique_program_df(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    if "nama_program" in d.columns:
        d = d.dropna(subset=["nama_program"])
    return d.drop_duplicates(subset=UNIQ_KEYS)

# =============================
# FILTER SIDEBAR
# =============================
st.sidebar.subheader("Filter Data")

site_list = sorted(df_program["site"].dropna().unique()) if "site" in df_program.columns else []
site_sel = st.sidebar.multiselect("Pilih Site", site_list, default=site_list)

perusahaan_list = sorted(df_program["perusahaan"].dropna().unique()) if "perusahaan" in df_program.columns else []
perusahaan_sel = st.sidebar.multiselect("Pilih Perusahaan", perusahaan_list, default=perusahaan_list)

# --- FILTER TAMBAHAN: Jenis Sampah (asli dari data) ---
jenis_list = sorted(df_program["jenis_sampah"].dropna().unique()) if "jenis_sampah" in df_program.columns else []
jenis_sel = st.sidebar.multiselect("Pilih Jenis Sampah", jenis_list, default=jenis_list)

# ==== Tahun & Bulan dari HEADER kolom (agar 2024 selalu muncul bila ada kolomnya) ====
pattern = r"^(januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember)_\d{4}$"
bulan_tahun_cols = [col for col in df_program.columns if re.match(pattern, str(col))]

# Peta bulan Indonesia
bulan_map = {
    "Januari":1,"Februari":2,"Maret":3,"April":4,"Mei":5,"Juni":6,
    "Juli":7,"Agustus":8,"September":9,"Oktober":10,"November":11,"Desember":12
}
bulan_list_ui = list(bulan_map.keys())

if bulan_tahun_cols:
    # Tahun dari header kolom -> memastikan 2024 muncul apabila ada "xxx_2024"
    tahun_from_header = sorted({int(str(c).split("_")[1]) for c in bulan_tahun_cols})

    # Bentuk long table
    df_prog_long = df_program.melt(
        id_vars=[c for c in df_program.columns if c not in bulan_tahun_cols],
        value_vars=bulan_tahun_cols,
        var_name="bulan_tahun",
        value_name="value"
    )

    # Ekstrak tahun-bulan dari nama kolom
    df_prog_long["tahun"] = df_prog_long["bulan_tahun"].apply(lambda x: int(str(x).split("_")[1]))
    df_prog_long["bulan"] = df_prog_long["bulan_tahun"].apply(lambda x: str(x).split("_")[0].capitalize())
    df_prog_long["periode"] = pd.to_datetime(
        df_prog_long["tahun"].astype(str) + "-" + df_prog_long["bulan"].map(bulan_map).astype(str) + "-01",
        errors="coerce"
    )

    # === Sidebar pilihan (pakai tahun_from_header supaya 2024 ada) ===
    tahun_pilihan = st.sidebar.multiselect("Pilih Tahun:", tahun_from_header, default=tahun_from_header)
    bulan_pilihan = st.sidebar.multiselect("Pilih Bulan:", bulan_list_ui, default=bulan_list_ui)

    # Terapkan filter Tahun/Bulan
    df_prog_filtered = df_prog_long[
        (df_prog_long["tahun"].isin(tahun_pilihan)) &
        (df_prog_long["bulan"].isin(bulan_pilihan))
    ].copy()
else:
    df_prog_filtered = df_program.copy()
    tahun_pilihan, bulan_pilihan = [], []

# =============================
# APPLY FILTERS
# =============================
if site_sel and "site" in df_prog_filtered.columns:
    df_prog_filtered = df_prog_filtered[df_prog_filtered["site"].isin(site_sel)]
if perusahaan_sel and "perusahaan" in df_prog_filtered.columns:
    df_prog_filtered = df_prog_filtered[df_prog_filtered["perusahaan"].isin(perusahaan_sel)]
if jenis_sel and "jenis_sampah" in df_prog_filtered.columns:
    df_prog_filtered = df_prog_filtered[df_prog_filtered["jenis_sampah"].isin(jenis_sel)]

aktif = ", ".join(jenis_sel) if jenis_sel else "Semua"
st.caption(f"🗑️ Filter Jenis Sampah aktif: **{aktif}**")

# =============================
# HITUNG JUMLAH HARI (berdasar pilihan sidebar)
# =============================
days_period = 0
if bulan_tahun_cols and tahun_pilihan and bulan_pilihan:
    for y in tahun_pilihan:
        for b in bulan_pilihan:
            days_period += calendar.monthrange(y, bulan_map[b])[1]
else:
    # fallback default (sesuai sebelumnya)
    days_period = 609

st.info(f"📅 Total jumlah hari periode filter: **{days_period} hari**")

# ====== DATA UNIK (SETELAH FILTER) UNTUK SEMUA METRIC JUMLAH PROGRAM ======
df_prog_unique = unique_program_df(df_prog_filtered)

# =============================
# METRICS (dedup, stabil)
# =============================
jumlah_program = df_prog_unique.shape[0]
if "kategori" in df_prog_unique.columns:
    jmlprog_pengurangan = df_prog_unique[df_prog_unique["kategori"]=="Program Pengurangan"].shape[0]
    jmlprog_pengelolaan = df_prog_unique[df_prog_unique["kategori"]=="Program Pengelolaan"].shape[0]
else:
    jmlprog_pengurangan = jmlprog_pengelolaan = 0


# ==================================================
# 💠 METRIC CARD SECTION (dua baris kotak)
# ==================================================
st.markdown("""
<style>
.metric-card {
    border-radius: 12px;
    padding: 15px;
    text-align: center;
    color: #fff;
    font-family: 'Segoe UI', sans-serif;
    box-shadow: 3px 3px 10px rgba(0,0,0,0.2);
}
.metric-card h3 {
    font-size: 16px;
    margin-bottom: 4px;
}
.metric-card h2 {
    font-size: 32px;
    margin: 0;
    font-weight: bold;
}
.metric-sub {
    font-size: 14px;
    color: #f1f1f1;
    margin-top: 4px;
}
</style>
""", unsafe_allow_html=True)

# --- Baris pertama: total program & kategori besar
colA, colB, colC, colD = st.columns(4)
with colA:
    st.markdown(f"""
    <div class="metric-card" style="background:#0077b6">
        <h3>Total Program</h3>
        <h2>{jumlah_program}</h2>
        <div class="metric-sub">📅 per Agustus 2025</div>
    </div>""", unsafe_allow_html=True)
with colB:
    st.markdown(f"""
    <div class="metric-card" style="background:#2b9348">
        <h3>Program Pengurangan</h3>
        <h2>{jmlprog_pengurangan}</h2>
        <div class="metric-sub">♻️ Reduce</div>
    </div>""", unsafe_allow_html=True)
with colC:
    st.markdown(f"""
    <div class="metric-card" style="background:#40916c">
        <h3>Program Pengelolaan</h3>
        <h2>{jmlprog_pengelolaan}</h2>
        <div class="metric-sub">🔁 Reuse & Recycle</div>
    </div>""", unsafe_allow_html=True)
with colD:
    st.markdown(f"""
    <div class="metric-card" style="background:#ffb703">
        <h3>Periode Hari</h3>
        <h2>{days_period}</h2>
        <div class="metric-sub">📆 hari aktif</div>
    </div>""", unsafe_allow_html=True)

# --- Baris kedua: cluster breakdown
col1, col2, col3, col4, col5 = st.columns(5)
cluster_colors = {
    "Maggot/BSF": "#184e77",
    "Komposting": "#52b788",
    "Bank Sampah": "#76c893",
    "Reduce Plastik": "#95d5b2",
    "Lainnya": "#adb5bd"
}
for col, cluster in zip([col1, col2, col3, col4, col5], cluster_colors.keys()):
    jumlah = (
        df_prog_unique[df_prog_unique["cluster"]==cluster].shape[0]
        if "cluster" in df_prog_unique.columns else 0
    )
    st_color = cluster_colors[cluster]
    col.markdown(f"""
    <div class="metric-card" style="background:{st_color}">
        <h3>{cluster}</h3>
        <h2>{jumlah}</h2>
    </div>""", unsafe_allow_html=True)

# =============================
# VISUALISASI
# =============================

# Pie (program unik)
st.markdown("### 🥧 Proporsi Program (Kategori & Jenis Sampah)")
if not df_prog_unique.empty and {"kategori","jenis_sampah"}.issubset(df_prog_unique.columns):
    df_prop = df_prog_unique.groupby(["kategori","jenis_sampah"], as_index=False).size()
    df_prop.rename(columns={"size":"jumlah_program"}, inplace=True)
    fig_prop = px.pie(
        df_prop, values="jumlah_program", names="jenis_sampah",
        color="jenis_sampah", color_discrete_map=color_map, hole=0.3
    )
    st.plotly_chart(fig_prop, use_container_width=True)

# =============================
# 🧩 SUB-JENIS SAMPAH 
# =============================
st.markdown("### 🧩 Analisis Sub-Jenis Sampah ")

# Pastikan kolom sub_jenis_sampah ada, kalau tidak buat deteksi sederhana
if "sub_jenis_sampah" not in df_prog_unique.columns:
    def detect_subjenis(name):
        name = str(name).lower()
        if "plastik" in name: return "Plastik"
        if "kardus" in name or "kertas" in name: return "Kertas/Kardus"
        if "logam" in name or "besi" in name: return "Logam"
        if "kaca" in name: return "Kaca"
        if "daun" in name or "ranting" in name: return "Daun & Ranting"
        if "sisa makanan" in name or "sayur" in name: return "Sisa Makanan"
        return "Lainnya"
    df_prog_unique["sub_jenis_sampah"] = df_prog_unique["nama_program"].map(detect_subjenis)

# Buat agregasi jumlah program per jenis_sampah dan sub_jenis_sampah
if {"jenis_sampah","sub_jenis_sampah"}.issubset(df_prog_unique.columns):
    df_sub = (
        df_prog_unique.groupby(["jenis_sampah","sub_jenis_sampah"], as_index=False)
        .agg(jumlah_program=("nama_program","count"))
    )

    col1, col2 = st.columns([0.5,0.5])
    with col1:
        st.markdown("#### 📊 Proporsi Sub-Jenis per Jenis Sampah")
        fig_subpie = px.sunburst(
            df_sub,
            path=["jenis_sampah","sub_jenis_sampah"],
            values="jumlah_program",
            color="jenis_sampah",
            color_discrete_map=color_map
        )
        st.plotly_chart(fig_subpie, use_container_width=True)

    with col2:
        st.markdown("#### 📈 Jumlah Program per Sub-Jenis")
        fig_subbar = px.bar(
            df_sub,
            x="sub_jenis_sampah",
            y="jumlah_program",
            color="jenis_sampah",
            text="jumlah_program",
            color_discrete_map=color_map,
            barmode="group"
        )
        fig_subbar.update_traces(textposition="outside")
        fig_subbar.update_layout(xaxis_title="", yaxis_title="Jumlah Program")
        st.plotly_chart(fig_subbar, use_container_width=True)
else:
    st.warning("Kolom sub_jenis_sampah belum tersedia di dataset.")

# ==================================================
# ♻️ SUB-JENIS × KATEGORI PROGRAM (PENGURANGAN / PENGELOLAAN) — SIDE-BY-SIDE + GREEN THEME
# ==================================================
st.markdown("### ♻️ Sub-Jenis Sampah per Kategori Program (kg)")

# pastikan kolom 'sub_jenis_sampah'
if "sub_jenis_sampah" not in df_prog_filtered.columns:
    def detect_subjenis(name):
        name = str(name).lower()
        if "plastik" in name: return "Plastik"
        if "kardus" in name or "kertas" in name: return "Kertas/Kardus"
        if "logam" in name or "besi" in name: return "Logam"
        if "kaca" in name: return "Kaca"
        if "daun" in name or "ranting" in name: return "Daun & Ranting"
        if "sisa makanan" in name or "sayur" in name: return "Sisa Makanan"
        return "Lainnya"
    df_prog_filtered["sub_jenis_sampah"] = df_prog_filtered["nama_program"].map(detect_subjenis)

# pastikan numeric
if "total_calc" in df_prog_filtered.columns:
    df_prog_filtered["total_calc"] = pd.to_numeric(df_prog_filtered["total_calc"], errors="coerce").fillna(0)
else:
    df_prog_filtered["total_calc"] = 0

# agregasi Kategori × Sub-Jenis
need_cols = {"kategori", "sub_jenis_sampah", "total_calc"}
if need_cols.issubset(df_prog_filtered.columns):
    df_kat_sub = (
        df_prog_filtered
        .groupby(["kategori", "sub_jenis_sampah"], as_index=False)["total_calc"]
        .sum()
        .rename(columns={"total_calc": "total_kg"})
    ).sort_values(["kategori", "total_kg"], ascending=[True, False])

    # ====== PALET HIJAU (bisa selaras tema / custom) ======
    # gunakan 2 shade hijau berbeda untuk kategori
    kategori_colors = {
        "Program Pengurangan": "#2b9348",   # hijau sedang
        "Program Pengelolaan": "#1b4332"    # hijau gelap
    }
    # fallback jika label kategori berbeda-beda casing
    kategori_colors = {k.lower(): v for k, v in kategori_colors.items()}

    # ====== LAYOUT BERSAMPINGAN ======
    col_left, col_right = st.columns([0.56, 0.44])

    # ---- BAR CHART (grouped) → perbandingan kategori di tiap Sub-Jenis
    with col_left:
        st.markdown("#### 📊 Perbandingan per Sub-Jenis")
        # pastikan urutan sub-jenis descending by total
        order_sub = (
            df_kat_sub.groupby("sub_jenis_sampah", as_index=False)["total_kg"].sum()
            .sort_values("total_kg", ascending=False)["sub_jenis_sampah"]
            .tolist()
        )
        df_plot = df_kat_sub.copy()
        df_plot["kategori_lc"] = df_plot["kategori"].astype(str).str.lower()

        fig_bar = px.bar(
            df_plot,
            x="sub_jenis_sampah", y="total_kg",
            color="kategori_lc", barmode="group", text="total_kg",
            category_orders={"sub_jenis_sampah": order_sub},
            color_discrete_map=kategori_colors,
            labels={"sub_jenis_sampah":"Sub-Jenis Sampah", "total_kg":"Total Timbulan (kg)", "kategori_lc":"Kategori"}
        )
        fig_bar.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
        fig_bar.update_layout(
            xaxis_title="",
            yaxis_title="Total Timbulan (kg)",
            margin=dict(t=40, b=90, l=40, r=20),
            legend_title_text="Kategori Program",
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # ---- SUNBURST (Kategori → Sub-Jenis) → distribusi komposisi
    with col_right:
        st.markdown("#### 🌞 Komposisi (Kategori → Sub-Jenis)")
        # gunakan warna kategori; node sub-jenis akan mengikuti
        df_sun = df_kat_sub.rename(columns={"kategori": "Kategori", "sub_jenis_sampah": "Sub-Jenis"})
        df_sun["Kategori_lc"] = df_sun["Kategori"].astype(str).str.lower()

        # plotly sunburst pakai color=Kategori_lc agar warna konsisten
        fig_sun = px.sunburst(
            df_sun,
            path=["Kategori", "Sub-Jenis"],
            values="total_kg",
            color="Kategori_lc",
            color_discrete_map=kategori_colors,
        )
        fig_sun.update_layout(margin=dict(t=30, b=10, l=10, r=10))
        st.plotly_chart(fig_sun, use_container_width=True)

    # ---- TABEL RINGKASAN
    with st.expander("📋 Tabel Ringkasan Kategori × Sub-Jenis (kg)"):
        st.dataframe(
            df_kat_sub.pivot_table(index="sub_jenis_sampah", columns="kategori", values="total_kg", aggfunc="sum")
            .fillna(0)
            .sort_values(by=list(df_kat_sub["kategori"].unique()), ascending=False)
            .style.format("{:,.2f}"),
            use_container_width=True
        )

else:
    st.warning("⚠️ Kolom 'kategori' / 'sub_jenis_sampah' / 'total_calc' belum lengkap di dataset Program.")

# Sunburst (program unik)
st.markdown("### 📊 Proporsi Program & Jenis Sampah (Cluster)")
if not df_prog_unique.empty and {"cluster","jenis_sampah"}.issubset(df_prog_unique.columns):
    df_sun = df_prog_unique.groupby(["cluster","jenis_sampah"], as_index=False).size()
    df_sun.rename(columns={"size":"jumlah_program"}, inplace=True)
    fig_sunburst = px.sunburst(
        df_sun, path=["cluster","jenis_sampah"], values="jumlah_program",
        color="cluster", color_discrete_map=color_map
    )
    st.plotly_chart(fig_sunburst, use_container_width=True)

# Line Trend Cluster (pakai nilai bulanan)
st.markdown("### 📈 Tren Sampah per Cluster")
if {"periode","value","cluster"}.issubset(df_prog_filtered.columns):
    trend_cluster = df_prog_filtered.groupby(["periode","cluster"], as_index=False)["value"].sum()
    fig_line = px.line(trend_cluster, x="periode", y="value", color="cluster", markers=True,
                       color_discrete_map=color_map)
    st.plotly_chart(fig_line, use_container_width=True)

# Sankey (program unik)
st.markdown("### 🔗 Sankey Diagram: Timbulan → Cluster")
if not df_prog_unique.empty and {"jenis_sampah","cluster"}.issubset(df_prog_unique.columns):
    df_sankey = df_prog_unique.groupby(["jenis_sampah","cluster"], as_index=False).size()
    df_sankey.rename(columns={"size":"jumlah_program"}, inplace=True)
    sources = list(df_sankey["jenis_sampah"].unique()) + list(df_sankey["cluster"].unique())
    mapping = {name:i for i,name in enumerate(sources)}
    link = {
        "source":[mapping[s] for s in df_sankey["jenis_sampah"]],
        "target":[mapping[t] for t in df_sankey["cluster"]],
        "value":df_sankey["jumlah_program"]
    }
    node = {"label":sources, "pad":20, "thickness":20,
            "color":[color_map.get(l,"#66c2a5") for l in sources]}
    fig_sankey = go.Figure(go.Sankey(node=node, link=link))
    st.plotly_chart(fig_sankey, use_container_width=True)


# Bar Distribusi Cluster (program unik)
st.markdown("### 🏢 Distribusi Cluster Program per Perusahaan & Site")
if not df_prog_unique.empty and {"perusahaan","site","cluster","nama_program"}.issubset(df_prog_unique.columns):
    df_dist = (df_prog_unique
               .groupby(["perusahaan","site","cluster"])["nama_program"]
               .nunique()
               .reset_index(name="jumlah_program"))
    fig_bar = px.bar(
        df_dist, x="perusahaan", y="jumlah_program", color="cluster", facet_col="site",
        barmode="stack", text="jumlah_program", color_discrete_map=color_map
    )
    st.plotly_chart(fig_bar, use_container_width=True)

# Line Trend Kategori (nilai bulanan)
st.markdown("### 📈 Tren Sampah Terkelola & Ter Kurangi (Kategori)")
if {"periode","kategori","value"}.issubset(df_prog_filtered.columns):
    trend_kat = df_prog_filtered.groupby(["periode","kategori"], as_index=False)["value"].sum()
    fig_trend = px.line(trend_kat, x="periode", y="value", color="kategori", markers=True,
                        color_discrete_map=color_map)
    st.plotly_chart(fig_trend, use_container_width=True)


# ===============================
# 🏢 Timbulan vs Terkelola vs Reduce (Perusahaan-Site) — konsisten dgn peta
# ===============================
st.markdown("### 🏢 Timbulan vs Terkelola vs Reduce (Perusahaan-Site)")

def company_to_code(s: pd.Series) -> pd.Series:
    return (
        s.astype(str)
         .str.upper()
         .str.replace(r"[^A-Z ]", "", regex=True)
         .str.split()
         .apply(lambda t: t[-1] if len(t) else "")
    )

# --- 1) TIMBULAN
if not df_timbulan.empty:
    df_tim = df_timbulan.copy()
    df_tim["timbulan"] = pd.to_numeric(df_tim["timbulan"], errors="coerce")
    df_tim["company_code"] = company_to_code(df_tim.get("perusahaan", ""))

    if site_sel:
        df_tim = df_tim[df_tim["site"].isin(site_sel)]
    if perusahaan_sel:
        df_tim = df_tim[df_tim["perusahaan"].isin(perusahaan_sel)]

    agg_timbulan = (df_tim.groupby(["site","company_code"], as_index=False)
                         .agg(total_timbulan=("timbulan","sum")))
else:
    agg_timbulan = pd.DataFrame(columns=["site","company_code","total_timbulan"])

# --- 2 & 3) TERKELOLA & REDUCE dari df_prog_filtered (long format hasil melt)
agg_pengolahan = pd.DataFrame(columns=["site","perusahaan","company_code","sampah_terkelola"])
agg_reduce     = pd.DataFrame(columns=["site","perusahaan","company_code","reduce_perhari"])

if {"value","kategori","perusahaan","site"}.issubset(df_prog_filtered.columns) and not df_prog_filtered.empty:
    base = df_prog_filtered.copy()
    base["value"] = pd.to_numeric(base["value"], errors="coerce").fillna(0)

    if site_sel:
        base = base[base["site"].isin(site_sel)]
    if perusahaan_sel:
        base = base[base["perusahaan"].isin(perusahaan_sel)]

    # TERKELOLA
    peng = base[base["kategori"] == "Program Pengelolaan"].copy()
    if not peng.empty:
        agg_pengolahan = (peng.groupby(["site","perusahaan"], as_index=False)
                               .agg(total_pengolahan=("value","sum")))
        agg_pengolahan["company_code"] = company_to_code(agg_pengolahan["perusahaan"])
        agg_pengolahan["sampah_terkelola"] = agg_pengolahan["total_pengolahan"] / max(days_period, 1)

    # REDUCE
    red = base[base["kategori"] == "Program Pengurangan"].copy()
    if not red.empty:
        agg_reduce = (red.groupby(["site","perusahaan"], as_index=False)
                          .agg(total_reduce=("value","sum")))
        agg_reduce["company_code"] = company_to_code(agg_reduce["perusahaan"])
        agg_reduce["reduce_perhari"] = agg_reduce["total_reduce"] / max(days_period, 1)

# --- 4) MERGE ala peta
df_bar = agg_timbulan.merge(
    agg_pengolahan[["site","company_code","sampah_terkelola"]],
    on=["site","company_code"], how="left"
).merge(
    agg_reduce[["site","company_code","reduce_perhari"]],
    on=["site","company_code"], how="left"
)

df_bar[["sampah_terkelola","reduce_perhari"]] = df_bar[["sampah_terkelola","reduce_perhari"]].fillna(0)
df_bar["sampah_tidak_terkelola"] = (df_bar["total_timbulan"] - df_bar["sampah_terkelola"]).clip(lower=0)
df_bar["label"] = df_bar["company_code"].astype(str) + " - " + df_bar["site"].astype(str)

# ===============================
# CARD METRICS dari Timbulan vs Terkelola vs Reduce
# ===============================
st.markdown("### 📊 Ringkasan Timbulan & Pengelolaan")

# Total agregat
total_timbulan_all = df_bar["total_timbulan"].sum()
total_terkelola_all = df_bar["sampah_terkelola"].sum()
total_reduce_all = df_bar["reduce_perhari"].sum()
total_tidak_terkelola_all = df_bar["sampah_tidak_terkelola"].sum()

# Persentase
persen_terkelola = (total_terkelola_all / total_timbulan_all * 100) if total_timbulan_all > 0 else 0
persen_reduce = (total_reduce_all / total_timbulan_all * 100) if total_timbulan_all > 0 else 0
persen_tidak_terkelola = (total_tidak_terkelola_all / total_timbulan_all * 100) if total_timbulan_all > 0 else 0

# CSS styling card
st.markdown("""
    <style>
    .card {border: 1px solid #e0e0e0; border-radius: 12px; padding: 20px; background-color: #fff;
           box-shadow: 3px 3px 12px rgba(0,0,0,0.1); text-align: center; margin-bottom: 5px;}
    .card h3 {font-size: 20px; color: #333; margin-bottom: 5px;}
    .card h2 {font-size: 32px; color: #257d0a; margin: 0;}
    .card p {font-size: 16px; color: #666; margin: 0;}
    </style>
""", unsafe_allow_html=True)

colA, colB, colC, colD = st.columns(4)
with colA:
    st.markdown(f"<div class='card'><h3>Timbulan</h3><h2>{total_timbulan_all:,.2f}</h2><p>kg total</p></div>", unsafe_allow_html=True)
with colB:
    st.markdown(f"<div class='card'><h3>Termanfaatkan</h3><h2>{persen_terkelola:.1f}%</h2><p>{total_terkelola_all:,.2f} kg</p></div>", unsafe_allow_html=True)
with colC:
    st.markdown(f"<div class='card'><h3>Tidak Termanfaatkan</h3>"f"<h2 style='color:#d00000;'>{persen_tidak_terkelola:.1f}%</h2>"f"<p>{total_tidak_terkelola_all:,.2f} kg</p></div>",unsafe_allow_html=True)
with colD:
    st.markdown(f"<div class='card'><h3>Reduce</h3><h2>{persen_reduce:.1f}%</h2><p>{total_reduce_all:,.2f} kg</p></div>", unsafe_allow_html=True)

# ===============================
# PLOT
# ===============================
fig_bar2 = go.Figure()

fig_bar2.add_bar(
    x=df_bar["label"], y=df_bar["total_timbulan"],
    name="Timbulan", marker_color="#d7d7d9",
    text=df_bar["total_timbulan"].round(2),
    textposition="outside"
)

fig_bar2.add_bar(
    x=df_bar["label"], y=df_bar["sampah_terkelola"],
    name="Termanfaatkan (per hari)", marker_color="#2ded67",
    text=df_bar["sampah_terkelola"].round(2),
    textposition="auto"
)

fig_bar2.add_bar(
    x=df_bar["label"], y=df_bar["sampah_tidak_terkelola"],
    name="Tidak Termanfaatkan (per hari)", marker_color="#f72525",
    text=df_bar["sampah_tidak_terkelola"].round(2),
    textposition="outside"
)

fig_bar2.add_bar(
    x=df_bar["label"], y=df_bar["reduce_perhari"],
    name="Reduce (per hari)", marker_color="#033801",
    text=df_bar["reduce_perhari"].round(2),
    textposition="auto"
)

fig_bar2.update_traces(textfont_size=10)  # biar font angka tidak terlalu besar
fig_bar2.update_layout(
    barmode="group",
    xaxis_tickangle=-45,
    yaxis_title="kg/hari"
)

st.plotly_chart(fig_bar2, use_container_width=True)



# ===============================
# TABEL CEK
# ===============================
st.dataframe(
    df_bar[["label","total_timbulan","sampah_terkelola","sampah_tidak_terkelola","reduce_perhari"]]
    .sort_values("label"),
    use_container_width=True
)


# =============================
# INSIGHT (pakai data unik)
# =============================
st.markdown("### 📌 Insight Otomatis")
if not df_prog_unique.empty and "cluster" in df_prog_unique.columns:
    df_dist_u = df_prog_unique.groupby(["perusahaan","site","cluster"], as_index=False).size()
    top_cluster = df_dist_u.groupby("cluster")["size"].sum().idxmax()
    top_company = df_dist_u.groupby("perusahaan")["size"].sum().idxmax()
    top_site = df_dist_u.groupby("site")["size"].sum().idxmax()
    st.info(f"📍 Program dominan: **{top_cluster}** | Perusahaan terbanyak: **{top_company}** | Site paling aktif: **{top_site}**")
else:
    st.warning("Tidak ada data yang sesuai dengan filter.")


