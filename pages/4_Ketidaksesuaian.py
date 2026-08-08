# pages/4_Ketidaksesuaian.py
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from sklearn.preprocessing import MinMaxScaler
import calendar, re
from collections import Counter 

# ===============================
# LOGO + HEADER
# ===============================
logo = "assets/4logo.png"
st.logo(logo, icon_image=logo, size="large")

st.markdown(
    """
    <h1 style="font-size:24px; color:#000000; font-weight:bold; margin-bottom:0.5px;">
    📝 Ketidaksesuaian Pengelolaan Sampah
    </h1>
    """,
    unsafe_allow_html=True
)

# ===============================
# LOAD DATA GOOGLE SHEETS
# ===============================
sheet_url = "https://docs.google.com/spreadsheets/d/1cw3xMomuMOaprs8mkmj_qnib-Zp_9n68rYMgiRZZqBE/edit?usp=sharing"
sheet_id = sheet_url.split("/")[5]

def norm_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.replace(" ", "_")
        .str.replace("/", "_")
        .str.lower()
    )
    return df

if "data" not in st.session_state:
    sheet_names = ["Ketidaksesuaian", "Survei_Online", "Survei_Offline","Level_Jabatan"]
    data_dict = {}
    for sheet in sheet_names:
        try:
            url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet}"
            df = pd.read_csv(url)
            df = norm_cols(df)
            data_dict[sheet] = df
        except Exception as e:
            st.error(f"Gagal load sheet {sheet}: {e}")
            data_dict[sheet] = pd.DataFrame()
    st.session_state["data"] = data_dict

# ✅ perbaikan case-sensitive
df = st.session_state["data"].get("Ketidaksesuaian", pd.DataFrame())
df_online = st.session_state["data"].get("Survei_Online", pd.DataFrame())
df_offline = st.session_state["data"].get("Survei_Offline", pd.DataFrame())
df_level = st.session_state["data"].get("Level_Jabatan", pd.DataFrame())
df_survey = pd.concat([df_online, df_offline], ignore_index=True)

if not df_survey.empty and not df_level.empty:
    merge_keys = [
        k
        for k in ["perusahaan_area_kerja_tambang", "site___lokasi_kerja", "id"]
        if k in df_survey.columns and k in df_level.columns
    ]

    if merge_keys:
        cols_level = merge_keys + [
            c for c in ["Level_Jabatan"] if c in df_level.columns
        ]
        df_level_small = df_level[cols_level].drop_duplicates()

        df_survey = df_survey.merge(
            df_level_small,
            on=merge_keys,
            how="left",
        )
    else:
        st.warning(
            "Kolom kunci untuk menggabungkan Level Jabatan tidak lengkap. "
            "Filter level jabatan tidak akan aktif."
        )
# ===============================
# FILTER SIDEBAR
# ===============================
st.sidebar.subheader("Filter Ketidaksesuaian")

if not df.empty:
    # Pastikan kolom tanggal ada
    if "tanggallapor" in df.columns:
        df["tanggallapor"] = pd.to_datetime(df["tanggallapor"], errors="coerce")
        df["tahun"] = df["tanggallapor"].dt.year
        df["bulan"] = df["tanggallapor"].dt.month

    # Filter perusahaan
    perusahaan_list = sorted(df["perusahaan"].dropna().unique()) if "perusahaan" in df.columns else []
    perusahaan_sel = st.sidebar.multiselect("Pilih Perusahaan", perusahaan_list, default=perusahaan_list)

    # Filter site
    site_list = sorted(df["site"].dropna().unique()) if "site" in df.columns else []
    site_sel = st.sidebar.multiselect("Pilih Site", site_list, default=site_list)

    # mapping bulan
    bulan_map = {
        "Januari": 1, "Februari": 2, "Maret": 3, "April": 4, "Mei": 5, "Juni": 6,
        "Juli": 7, "Agustus": 8, "September": 9, "Oktober": 10, "November": 11, "Desember": 12
    }

    # tahun
    if "tahun" in df.columns:
        tahun_list = sorted(df["tahun"].dropna().unique())
        tahun_sel = st.sidebar.multiselect("Pilih Tahun", tahun_list, default=tahun_list)
    else:
        tahun_sel = []

    # bulan
    if "bulan" in df.columns:
        bulan_list = list(bulan_map.keys())
        bulan_sel = st.sidebar.multiselect("Pilih Bulan", bulan_list, default=bulan_list)
        bulan_sel_num = [bulan_map[b] for b in bulan_sel]  # ubah ke angka 1–12
    else:
        bulan_sel, bulan_sel_num = [], []

    # Terapkan filter
    if perusahaan_sel:
        df = df[df["perusahaan"].isin(perusahaan_sel)]
    if site_sel:
        df = df[df["site"].isin(site_sel)]
    if tahun_sel:
        df = df[df["tahun"].isin(tahun_sel)]
    if bulan_sel_num:
        df = df[df["bulan"].isin(bulan_sel_num)]

    if df.empty:
        st.warning("⚠️ Data ketidaksesuaian kosong setelah filter. Silakan ubah filter.")
        st.stop()
else:
    st.warning("❌ Data `Ketidaksesuaian` tidak ditemukan.")
    st.stop()

# ===============================
# NORMALISASI KOLOM KETIDAKSESUAIAN
# ===============================
if "status_temuan" in df.columns:
    df["status_temuan"] = df["status_temuan"].astype(str).str.strip().str.title()

if "kategori_subketidaksesuaian" in df.columns:
    df["kategori_subketidaksesuaian"] = (
        df["kategori_subketidaksesuaian"]
        .fillna("Unknown")
        .astype(str)
        .str.strip()
        .str.title()
    )
# ===============================
# METRICS
# ===============================
total_reports = len(df)
df_valid = df[df["status_temuan"] == "Valid"].copy() if "status_temuan" in df.columns else df.copy()
total_valid = len(df_valid)
pct_valid = (total_valid / total_reports * 100) if total_reports > 0 else 0

count_perilaku = (df_valid["kategori_subketidaksesuaian"] == "Perilaku").sum() if "kategori_subketidaksesuaian" in df_valid.columns else 0
count_nonperilaku = (df_valid["kategori_subketidaksesuaian"] == "Non Perilaku").sum() if "kategori_subketidaksesuaian" in df_valid.columns else 0

pct_perilaku = (count_perilaku / total_valid * 100) if total_valid > 0 else 0
pct_nonperilaku = (count_nonperilaku / total_valid * 100) if total_valid > 0 else 0

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Jumlah Laporan", total_reports)
with col2:
    st.metric("Laporan Valid", total_valid, f"{pct_valid:.1f}% dari total")
with col3:
    st.metric("Kategori Perilaku", count_perilaku, f"{pct_perilaku:.1f}% dari valid")
with col4:
    st.metric("Kategori Non Perilaku", count_nonperilaku, f"{pct_nonperilaku:.1f}% dari valid")

st.markdown("---")




# ===============================
# 📈 TREN JUMLAH LAPORAN PER BULAN (FRAUD + VALID)
# ===============================
st.subheader("📈 Tren Jumlah Laporan per Bulan (Fraud + Valid)")

if "tanggallapor" in df.columns:
    df_plot = df.copy()
    df_plot["tanggallapor"] = pd.to_datetime(df_plot["tanggallapor"], errors="coerce")
    df_plot = df_plot.dropna(subset=["tanggallapor"])

    # normalisasi status biar aman
    if "status_temuan" in df_plot.columns:
        df_plot["status_temuan"] = df_plot["status_temuan"].astype(str).str.strip().str.title()
    else:
        df_plot["status_temuan"] = "Unknown"

    df_plot["period_month"] = df_plot["tanggallapor"].dt.to_period("M").dt.to_timestamp()

    # agregasi jumlah laporan per bulan & status
    monthly = (
        df_plot.groupby(["period_month", "status_temuan"])
        .size()
        .reset_index(name="jumlah")
        .sort_values("period_month")
    )

    if monthly.empty:
        st.info("Tidak ada data untuk membuat tren bulanan.")
    else:
        # opsi tampilan
        mode_tren = st.radio(
            "Tampilan tren bulanan:",
            ["Total saja", "Komposisi Valid vs Fraud (stacked)"],
            horizontal=True,
            key="mode_tren_bulanan"
        )

        if mode_tren == "Total saja":
            monthly_total = (
                df_plot.groupby("period_month")
                .size()
                .reset_index(name="jumlah")
                .sort_values("period_month")
            )

            fig_total = px.line(
                monthly_total,
                x="period_month",
                y="jumlah",
                markers=True,
                template="plotly_white",
                labels={"period_month": "Bulan", "jumlah": "Jumlah Laporan"}
            )
            fig_total.update_layout(height=350)
            st.plotly_chart(fig_total, use_container_width=True)

        else:
            # stacked bar (valid+fraud per bulan)
            fig_stack = px.bar(
                monthly,
                x="period_month",
                y="jumlah",
                color="status_temuan",
                barmode="stack",
                text="jumlah",
                template="plotly_white",
                labels={"period_month": "Bulan", "jumlah": "Jumlah Laporan", "status_temuan": "Status"}
            )
            fig_stack.update_traces(textposition="outside")
            fig_stack.update_layout(height=420, xaxis_tickangle=-25)
            st.plotly_chart(fig_stack, use_container_width=True)
else:
    st.warning("Kolom 'tanggallapor' tidak ditemukan, tren bulanan tidak bisa dibuat.")


st.markdown("---")


# ======================================================
# 🏢 PERUSAHAAN–SITE: PERBANDINGAN FRAUD vs VALID PER BULAN
# ======================================================
st.subheader("🏢 Perbandingan Fraud vs Valid per Bulan (Perusahaan - Site)")

needed_cols = {"tanggallapor", "perusahaan", "site", "status_temuan"}
if not needed_cols.issubset(df.columns):
    st.warning("Kolom wajib tidak lengkap (butuh: tanggallapor, perusahaan, site, status_temuan).")
else:
    df_comp = df.copy()
    df_comp["tanggallapor"] = pd.to_datetime(df_comp["tanggallapor"], errors="coerce")
    df_comp = df_comp.dropna(subset=["tanggallapor"])

    df_comp["status_temuan"] = df_comp["status_temuan"].astype(str).str.strip().str.title()
    df_comp = df_comp[df_comp["status_temuan"].isin(["Valid", "Fraud"])]

    if df_comp.empty:
        st.info("Tidak ada data Valid/Fraud untuk dibandingkan.")
    else:
        # buat label perusahaan-site
        df_comp["company_site"] = (
            df_comp["perusahaan"].astype(str).str.strip() + " - " +
            df_comp["site"].astype(str).str.strip()
        )
        df_comp["period_month"] = df_comp["tanggallapor"].dt.to_period("M").dt.to_timestamp()

        # agregasi jumlah laporan per company_site per bulan per status
        agg = (
            df_comp.groupby(["company_site", "period_month", "status_temuan"])
            .size()
            .reset_index(name="jumlah")
            .sort_values(["company_site", "period_month"])
        )

        # selector: All atau salah satu dari 9 company-site
        cs_opsi = sorted(df_comp["company_site"].dropna().unique().tolist())
        cs_pilih = st.selectbox(
            "Pilih Perusahaan - Site:",
            ["All"] + cs_opsi,
            index=0,
            key="company_site_pilih_tren"
        )

        # ===== MODE ALL: 2 grafik berdampingan =====
        if cs_pilih == "All":
            c1, c2 = st.columns([0.5, 0.5])

            # kiri: Fraud vs Valid per bulan (gabungan semua perusahaan-site)
            with c1:
                st.markdown(
                    '<p style="text-align:center;font-weight:bold;">📊 Semua Perusahaan-Site (per Bulan)</p>',
                    unsafe_allow_html=True
                )

                agg_all = (
                    df_comp.groupby(["period_month", "status_temuan"])
                    .size()
                    .reset_index(name="jumlah")
                    .sort_values("period_month")
                )

                fig_all = px.bar(
                    agg_all,
                    x="period_month",
                    y="jumlah",
                    color="status_temuan",
                    barmode="group",
                    text="jumlah",
                    template="plotly_white",
                    labels={"period_month": "Bulan", "jumlah": "Jumlah Laporan", "status_temuan": "Status"}
                )
                fig_all.update_traces(textposition="outside")
                fig_all.update_layout(height=420, xaxis_tickangle=-25)
                st.plotly_chart(fig_all, use_container_width=True)

            # kanan: Fraud vs Valid per perusahaan-site (total semua bulan)
            with c2:
                st.markdown(
                    '<p style="text-align:center;font-weight:bold;">📊 Semua Bulan (per Perusahaan-Site)</p>',
                    unsafe_allow_html=True
                )

                agg_cs = (
                    df_comp.groupby(["company_site", "status_temuan"])
                    .size()
                    .reset_index(name="jumlah")
                    .sort_values("jumlah", ascending=False)
                )

                fig_cs = px.bar(
                    agg_cs,
                    y="company_site",
                    x="jumlah",
                    color="status_temuan",
                    barmode="group",
                    text="jumlah",
                    template="plotly_white",
                    orientation="h",
                    labels={"company_site": "Perusahaan - Site", "jumlah": "Jumlah Laporan", "status_temuan": "Status"}
                )
                fig_cs.update_traces(textposition="outside")
                fig_cs.update_layout(height=420, yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig_cs, use_container_width=True)

        # ===== MODE 1 COMPANY-SITE: Fraud vs Valid per bulan =====
        else:
            df_one = agg[agg["company_site"] == cs_pilih].copy()

            pivot = (
                df_one.pivot_table(
                    index="period_month",
                    columns="status_temuan",
                    values="jumlah",
                    aggfunc="sum",
                    fill_value=0
                )
                .reset_index()
                .sort_values("period_month")
            )

            fig_one = go.Figure()
            for stat in ["Valid", "Fraud"]:
                if stat in pivot.columns:
                    fig_one.add_trace(go.Bar(
                        name=stat,
                        x=pivot["period_month"],
                        y=pivot[stat],
                        text=pivot[stat],
                        textposition="outside"
                    ))

            fig_one.update_layout(
                barmode="group",
                template="plotly_white",
                height=450,
                xaxis_title="Bulan",
                yaxis_title="Jumlah Laporan",
                title=f"Fraud vs Valid per Bulan — {cs_pilih}",
            )
            st.plotly_chart(fig_one, use_container_width=True)


# ===============================
# TREN WAKTU
# ===============================
st.subheader("📈 Tren: Perilaku vs Non-Perilaku (Valid)")
if "tanggallapor" in df_valid.columns:
    df_valid["period_month"] = df_valid["tanggallapor"].dt.to_period("M")
    trend = df_valid.groupby(["period_month", "kategori_subketidaksesuaian"]).size().reset_index(name="count")
    if not trend.empty:
        pivot = trend.pivot(index="period_month", columns="kategori_subketidaksesuaian", values="count").fillna(0)
        pivot.index = pivot.index.to_timestamp()
        fig = go.Figure()
        for col in pivot.columns:
            fig.add_trace(go.Scatter(x=pivot.index, y=pivot[col], mode="lines+markers", name=col))
        fig.update_layout(height=350, xaxis_title="Bulan", yaxis_title="Jumlah Laporan (Valid)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Tidak ada data tanggal valid untuk tren.")
else:
    st.warning("Kolom 'tanggallapor' tidak ditemukan.")

st.markdown("---")

# ===============================
# PROPORSI SUB-KETIDAKSESUAIAN
# ===============================
# ===============================
# PROPORSI SUB-KETIDAKSESUAIAN (Valid)
# Donut — paksa SEMUA label tampil (outside + leader line)
# ===============================
st.subheader("📊 Proporsi berdasarkan Sub-Ketidaksesuaian (Valid)")

if "sub_ketidaksesuaian" in df_valid.columns:
    import numpy as np

    sub_counts = (
        df_valid["sub_ketidaksesuaian"]
        .fillna("Unknown")
        .value_counts()
        .reset_index()
    )
    sub_counts.columns = ["Sub Ketidaksesuaian", "Jumlah"]
    total = sub_counts["Jumlah"].sum()
    sub_counts["Persen"] = sub_counts["Jumlah"] / total * 100

    # Urutkan biar konsisten
    sub_counts = sub_counts.sort_values("Jumlah", ascending=False).reset_index(drop=True)

    # --- fungsi pendekin label biar gak tabrakan ---
    def shorten(s, n=28):
        s = str(s)
        return s if len(s) <= n else s[:n-1] + "…"

    # Label yang tampil (ringkas) -> semua outside
    sub_counts["LabelShort"] = sub_counts["Sub Ketidaksesuaian"].map(lambda x: shorten(x, 30))
    sub_counts["LabelText"] = (
        sub_counts["LabelShort"] + "<br>" +
        sub_counts["Persen"].round(2).astype(str) + "%"
    )

    # warna viridis konsisten
    viridis = px.colors.sequential.Viridis
    colors = (viridis * ((len(sub_counts) // len(viridis)) + 1))[:len(sub_counts)]
    color_map = dict(zip(sub_counts["Sub Ketidaksesuaian"], colors))

    fig = px.pie(
        sub_counts,
        names="Sub Ketidaksesuaian",
        values="Jumlah",
        hole=0.45,
        color="Sub Ketidaksesuaian",
        color_discrete_map=color_map
    )

    fig.update_traces(
        # ✅ paksa semua label tampil di luar
        text=sub_counts["LabelText"],
        textinfo="text",
        textposition="outside",
        outsidetextfont=dict(size=12),
        # bantu garis leader lebih jelas
        pull=[0.02]*len(sub_counts),
        # hover tetap lengkap (pakai nama asli)
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Jumlah: %{value} laporan<br>"
            "Proporsi: %{percent}<extra></extra>"
        )
    )

    fig.update_layout(
        template="plotly_white",
        height=750,  # ✅ tinggiin biar label tidak tabrakan
        margin=dict(t=10, b=10, l=40, r=200),  # ✅ kasih ruang kanan untuk label
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)

    # Bonus: tabel full label supaya tidak ada info yang hilang
    with st.expander("📋 Daftar lengkap (nama penuh + jumlah + proporsi)"):
        show_tbl = sub_counts[["Sub Ketidaksesuaian", "Jumlah", "Persen"]].copy()
        show_tbl["Persen"] = show_tbl["Persen"].round(3)
        st.dataframe(show_tbl, hide_index=True, use_container_width=True)

else:
    st.warning("Kolom 'sub_ketidaksesuaian' tidak ditemukan.")

st.markdown("---")


# ===============================
# JUMLAH PER SITE
# ===============================
st.subheader("🔍 Jumlah Sub-Ketidaksesuaian per Site - Perusahaan (Valid)")
if "perusahaan" in df_valid.columns and "site" in df_valid.columns and "sub_ketidaksesuaian" in df_valid.columns:
    df_valid["company_site"] = df_valid["perusahaan"].astype(str).str.strip() + " - " + df_valid["site"].astype(str).str.strip()
    grp = df_valid.groupby(["company_site", "sub_ketidaksesuaian"]).size().reset_index(name="count")
    pivot_cs = grp.pivot(index="company_site", columns="sub_ketidaksesuaian", values="count").fillna(0)

    fig = go.Figure()
    for col in pivot_cs.columns:
        fig.add_trace(go.Bar(y=pivot_cs.index, x=pivot_cs[col], name=col, orientation="h"))
    fig.update_layout(barmode="stack", height=600, xaxis_title="Jumlah Temuan (Valid)", yaxis_title="Perusahaan - Site")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(grp)
else:
    st.warning("Kolom perusahaan/site/sub_ketidaksesuaian tidak ditemukan.")

st.markdown("---")

# ===============================
# TOP 3 SITE
# ===============================
st.subheader("🏆 Top 3 Site dengan Ketidaksesuaian Valid")
if "perusahaan" in df_valid.columns and "site" in df_valid.columns:
    top3 = df_valid.groupby(["perusahaan", "site"]).size().reset_index(name="count").sort_values("count", ascending=False).head(3)
    for _, row in top3.iterrows():
        st.markdown(f"**{row['count']}** — {row['perusahaan']} · {row['site']}")
    st.dataframe(top3)
else:
    st.warning("Kolom perusahaan/site tidak ditemukan.")

st.markdown("---")

# ===========================================================
# === ANALISIS LENGKAP FRAUD: DUPLIKAT, KEMIRIPAN, ANOMALI ===
# ===========================================================
st.header("🚩 Analisis Menyeluruh Fraud & Validasi Bukti")

import numpy as np
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ---------- 0) Kolom penting & normalisasi ----------
COL_DESC = "deskripsi" if "deskripsi" in df.columns else None
COL_TGL  = "tanggallapor" if "tanggallapor" in df.columns else None
COL_PERU = "perusahaan" if "perusahaan" in df.columns else None
COL_SITE = "site" if "site" in df.columns else None
COL_SUB  = "sub_ketidaksesuaian" if "sub_ketidaksesuaian" in df.columns else None
COL_STAT = "status_temuan" if "status_temuan" in df.columns else None
COL_USER = "pelapor" if "pelapor" in df.columns else None
COL_FOTO = "foto_url" if "foto_url" in df.columns else None  # opsional

needed = [COL_DESC, COL_TGL, COL_PERU, COL_SITE, COL_SUB, COL_STAT]
if any(c is None for c in needed):
    st.warning("Beberapa kolom kunci hilang. Pastikan ada: deskripsi, tanggallapor, perusahaan, site, sub_ketidaksesuaian, status_temuan.")
else:
    # jamankan tanggal ke date saja (agar duplicate harian akurat)
    df["_tanggal"] = pd.to_datetime(df[COL_TGL], errors="coerce").dt.date

    def norm_text(s: str) -> str:
        s = str(s).lower().strip()
        # standarkan istilah umum yang sering salah ketik
        rep = {
            "sampaj":"sampah", "sampag":"sampah", "sm":"sampah",
            "limba":"limbah", "majung":"majun", "greas":"grease",
            "trush":"trash", "temapt":"tempat", "temaptnya":"tempatnya",
            "belom":"belum", "tdk":"tidak", "tkn":"tidak",
        }
        for k,v in rep.items(): s = re.sub(rf"\b{k}\b", v, s)
        s = re.sub(r"[^\w\s]", " ", s)   # buang tanda baca
        s = re.sub(r"\s+", " ", s)
        return s

    df["desc_clean"] = df[COL_DESC].fillna("").map(norm_text)
    df["sub_clean"]  = df[COL_SUB].fillna("").map(norm_text)
    df["status_lc"]  = df[COL_STAT].astype(str).str.lower().str.strip()
    df["pelapor_lc"] = df[COL_USER].astype(str).str.lower().str.strip() if COL_USER else ""

    # ---------- 1) Deteksi duplikat eksak ----------
    exact_key_cols = [COL_PERU, COL_SITE, "_tanggal", "sub_clean", "desc_clean"]
    df["dup_exact_key"] = df[exact_key_cols].astype(str).agg("|".join, axis=1)
    cnt_exact = df["dup_exact_key"].value_counts()
    df["is_dup_exact"] = df["dup_exact_key"].map(cnt_exact).fillna(0).astype(int).gt(1)

    # ---------- 2) Deteksi duplikat hampir sama (teks mirip) ----------
    # batasi per perusahaan-site-tanggal agar komputasi efisien
    df["dup_group"] = df[[COL_PERU, COL_SITE, "_tanggal"]].astype(str).agg("|".join, axis=1)

    near_flags = np.zeros(len(df), dtype=bool)
    near_scores = np.zeros(len(df), dtype=float)
    SIM_TH = 0.90  # ambang kemiripan TF-IDF

    for grp, idx in df.groupby("dup_group").indices.items():
        sub_df = df.iloc[list(idx)]
        texts = (sub_df["desc_clean"] + " " + sub_df["sub_clean"]).fillna("").tolist()
        if len(texts) <= 1:
            continue
        try:
            tfidf = TfidfVectorizer(min_df=1, ngram_range=(1,2)).fit_transform(texts)
            sim = cosine_similarity(tfidf)
            # tandai pasangan i≠j dengan similarity >= TH
            for i in range(sim.shape[0]):
                # skor maksimum selain diagonal
                sim[i,i] = 0.0
                smax = sim[i].max()
                if smax >= SIM_TH:
                    near_flags[sub_df.index[i]] = True
                    near_scores[sub_df.index[i]] = smax
        except Exception:
            # fallback aman bila vocab kosong
            pass

    df["is_dup_near"] = near_flags
    df["near_sim"]    = near_scores

    # ---------- 3) Anomali waktu (spam/double submit) ----------
    # urutkan per pelapor & lokasi; flag jika jeda antar input sangat singkat & konten sangat mirip
    df = df.sort_values([COL_PERU, COL_SITE, COL_TGL], na_position="last")
    df["_ts"] = pd.to_datetime(df[COL_TGL], errors="coerce")
    df["dt_prev"] = df.groupby(["pelapor_lc", COL_PERU, COL_SITE])["_ts"].shift(1)
    df["delta_min"] = (df["_ts"] - df["dt_prev"]).dt.total_seconds() / 60
    # spam bila < 10 menit DAN near-duplicate
    df["is_time_spam"] = df["delta_min"].le(10) & df["is_dup_near"].fillna(False)

    # ---------- 4) Ketidakselarasan status (status mismatch) ----------
    def has_real_issue(t):
        t = str(t).lower()
        # kata kunci “benar-benar masalah”
        return bool(re.search(
            r"penuh|menumpuk|meluap|overflow|tercampur|tidak\s*terpilah|b3|kontaminasi|berceceran|bau|lalat|tidak\s*dibuang|belum\s*(di)?angkut|tidak\s*pada\s*tempatnya|housekeep",
            t
        ))

    df["indikasi_masalah"] = df["desc_clean"].map(has_real_issue)
    # status_temuan = fraud tapi tanpa indikator masalah → mismatch
    df["is_status_mismatch"] = (df["status_lc"] == "fraud") & (~df["indikasi_masalah"])

    # ---------- 5) Pola pelapor (copy–paste n-gram) ----------
    def repetitive_score(t):
        tokens = str(t).split()
        if len(tokens) < 6: return 0.0
        # hitung rasio token unik
        uniq_ratio = len(set(tokens)) / max(len(tokens),1)
        return 1.0 - uniq_ratio  # makin tinggi → makin repetitif

    df["repet_score"] = (df["desc_clean"] + " " + df["sub_clean"]).map(repetitive_score)
    # anomali bila repetitif & sering muncul oleh pelapor sama dalam 1 hari-lokasi
    df["is_reporter_pattern"] = (df["repet_score"] >= 0.5) & df["is_dup_near"]

    # ---------- 6) Konsistensi foto (placeholder; aktif jika ada kolom foto_url) ----------
    if COL_FOTO and COL_FOTO in df.columns:
        # tanpa memuat gambar, kita tetap bisa cek “string URL yang sama”
        df["_foto_norm"] = df[COL_FOTO].astype(str).str.strip().str.lower()
        url_cnt = df["_foto_norm"].value_counts(dropna=True)
        df["is_same_photo_url"] = df["_foto_norm"].map(url_cnt).fillna(0).astype(int).gt(1)
    else:
        df["is_same_photo_url"] = False

    # ---------- 7) Label akhir & alasan ----------
    def final_label(row):
        reasons = []
        if row["is_dup_exact"]:       reasons.append("Duplikat Eksak")
        if row["is_dup_near"]:        reasons.append(f"Duplikat Mirip (sim={row['near_sim']:.2f})")
        if row["is_time_spam"]:       reasons.append("Rentang Waktu Sangat Dekat (indikasi double submit)")
        if row["is_reporter_pattern"]:reasons.append("Pola Pelapor Repetitif")
        if row["is_status_mismatch"]: reasons.append("Status Fraud tanpa indikator masalah (mismatch)")
        if row["is_same_photo_url"]:  reasons.append("Foto Sama Dipakai Ulang")

        # Keputusan akhir:
        if any([row["is_dup_exact"], row["is_dup_near"], row["is_time_spam"], row["is_reporter_pattern"], row["is_same_photo_url"]]):
            cat = "Fraud: Duplikasi/Anomali"
        elif row["is_status_mismatch"]:
            cat = "Fraud: Status Tidak Didukung Bukti"
        else:
            cat = "Non-Fraud (Temuan Sah)" if row["indikasi_masalah"] else "Butuh Tinjau (Bukti Lemah)"

        return pd.Series({"fraud_decision": cat, "fraud_reasons": "; ".join(reasons)})

    out = df.apply(final_label, axis=1)
    df["fraud_decision"] = out["fraud_decision"]
    df["fraud_reasons"]  = out["fraud_reasons"]

    # ---------- 8) Ringkasan & visual ----------
    # ======================================
    # 🔎 RINGKASAN KEPUTUSAN FRAUD - VERSI REVISI
    # ======================================
    import plotly.express as px
    import plotly.graph_objects as go

    st.subheader("📊 Ringkasan Keputusan Fraud (Versi Revisi)")

    # --- 1️⃣ Agregasi ulang data untuk grafik batang ---
    # pastikan kolom fraud_decision dan status_lc sudah ada
    summary = (
        df.groupby(["fraud_decision", "status_lc"])
        .size()
        .reset_index(name="jumlah")
        .sort_values("jumlah", ascending=False)
    )

    # --- 2️⃣ Label kategori agar lebih deskriptif ---
    label_map = {
        "Fraud: Duplikasi/Anomali": "Fraud: Duplikasi/Anomali (Laporan Ganda)",
        "Fraud: Status Tidak Didukung Bukti": "Fraud: Tidak Didukung Bukti (Mislabeling)",
        "Non-Fraud (Temuan Sah)": "Non-Fraud (Temuan Valid)",
        "Butuh Tinjau (Bukti Lemah)": "Perlu Verifikasi Ulang (Bukti Lemah)"
    }
    summary["fraud_decision_label"] = summary["fraud_decision"].map(label_map).fillna(summary["fraud_decision"])

    # --- 3️⃣ Grafik batang dengan label baru ---
    fig_sum = px.bar(
        summary,
        x="fraud_decision_label",
        y="jumlah",
        color="status_lc",
        barmode="group",
        text="jumlah",
        color_discrete_sequence=["#6FCF97", "#F2994A"],  # hijau valid, oranye fraud
    )

    fig_sum.update_traces(textposition="outside")

    fig_sum.update_layout(
        title="<b>Ringkasan Keputusan Fraud</b>",
        xaxis_title="Kategori Keputusan Fraud (dengan konteks lebih jelas)",
        yaxis_title="Jumlah Laporan",
        xaxis_tickangle=-25,
        legend_title="Status Laporan Lapangan",
        height=520,
        template="simple_white"
    )

    st.plotly_chart(fig_sum, use_container_width=True)

    # Top 15 baris yang paling kuat indikasi duplikat (skor similarity tertinggi)
    st.markdown("### 🔎 Kandidat Duplikat Terkuat (Top 15)")
    cand = df[(df["is_dup_exact"] | df["is_dup_near"])].copy()
    cand = cand.sort_values(["is_dup_exact","near_sim"], ascending=[False, False])
    show_cols = [COL_PERU, COL_SITE, COL_TGL, COL_SUB, COL_DESC,
                 "is_dup_exact","near_sim","delta_min","pelapor_lc","fraud_decision","fraud_reasons"]
    st.dataframe(cand[show_cols].head(15), use_container_width=True)

    # Tabel lengkap (opsional, toggle)
    with st.expander("📋 Lihat tabel lengkap dengan penjelasan"):
        st.dataframe(df[show_cols], use_container_width=True)

    # ---------- 9) Metrik cepat ----------
    total = len(df)
    n_dup_fraud = int(((df["is_dup_exact"] | df["is_dup_near"]) & (df["status_lc"] == "fraud")).sum())
    n_mis  = int(df["is_status_mismatch"].sum())
    n_time = int(df["is_time_spam"].sum())
    n_url  = int(df["is_same_photo_url"].sum())
    colm1, colm2, colm3, colm4 = st.columns(4)
    colm1.metric("Fraud Duplikasi (laporan ganda)", n_dup_fraud, f"{n_dup_fraud/total:.1%}" if total else "0%")
    colm2.metric("Status Mismatch", n_mis, f"{n_mis/total:.1%}" if total else "0%")
    colm3.metric("Time-Spam (<10 menit)", n_time, f"{n_time/total:.1%}" if total else "0%")
    colm4.metric("Foto URL Sama", n_url, f"{n_url/total:.1%}" if total else "0%")

    # Simpan ke session_state bila ingin dipakai plot lain
    st.session_state["ketidaksesuaian_scored"] = df

# ===========================================================
# === HEATMAP: Distribusi Fraud per Pelapor & Site/Perusahaan ===
# ===========================================================
st.markdown("### 🧩 Heatmap Pelapor vs Lokasi (Frekuensi Fraud)")

# Filter hanya baris dengan keputusan Fraud (apapun tipenya)
df_fraud = df[df["fraud_decision"].str.contains("Fraud", case=False, na=False)].copy()

if not df_fraud.empty:
    # Tentukan apakah mau pakai kolom Site atau Perusahaan
    level_opt = st.radio(
        "Tampilkan berdasarkan:", ["Site", "Perusahaan"], horizontal=True
    )
    level_col = COL_SITE if level_opt == "Site" else COL_PERU

    # Ringkas jumlah fraud per pelapor per lokasi
    fraud_matrix = (
        df_fraud.groupby(["pelapor_lc", level_col])
        .size()
        .reset_index(name="jumlah")
    )

    # Pivot tabel untuk heatmap
    pivot_fraud = fraud_matrix.pivot_table(
        index="pelapor_lc", columns=level_col, values="jumlah", fill_value=0
    )

    # Plotly heatmap
    fig_heat = px.imshow(
        pivot_fraud,
        color_continuous_scale="Greens",
        aspect="auto",
        title=f"Distribusi Fraud berdasarkan Pelapor dan {level_opt}",
        labels=dict(x=level_opt, y="Pelapor", color="Jumlah Fraud"),
    )
    fig_heat.update_layout(
        height=600,
        margin=dict(l=60, r=60, t=60, b=60),
        xaxis_title=level_opt,
        yaxis_title="Pelapor",
        xaxis_tickangle=-25,
    )
    st.plotly_chart(fig_heat, use_container_width=True)

    # Highlight pelapor top
    top_fraud = (
        fraud_matrix.groupby("pelapor_lc")["jumlah"]
        .sum()
        .reset_index()
        .sort_values("jumlah", ascending=False)
        .head(10)
    )
    st.markdown("#### 🔝 Top 10 Pelapor dengan Laporan Fraud Terbanyak")
    st.dataframe(top_fraud, hide_index=True, use_container_width=True)
else:
    st.info("Tidak ada data Fraud untuk divisualisasikan pada heatmap.")


# =========================================================
# =========================================================
# 📋 PERSIAPAN DATA SURVEI
# =========================================================
# === BASELINE Q2 YANG BENAR (hindari average of averages) ===
import numpy as np
from numpy.random import default_rng
rng = default_rng(42)

# Pastikan kolom ada
col_site = "site___lokasi_kerja"
col_corp = "perusahaan_area_kerja_tambang"
col_q2   = "2._seberapa_optimal_program_gbst_berjalan_selama_ini_di_perusahaan_anda?"

df_ind = df_survey[[col_corp, col_site, col_q2]].copy() if not df_survey.empty else pd.DataFrame()
if not df_ind.empty and all(c in df_ind.columns for c in [col_corp, col_site, col_q2]):
    df_ind[col_q2] = pd.to_numeric(df_ind[col_q2], errors="coerce")
    df_ind = df_ind.dropna(subset=[col_q2])

    
# =========================================================
# 📈 ANALISIS Survei dan Ketidaksesuaian
# =========================================================
st.header("📈 Analisis Survei dan Ketidaksesuaian")

if not df_survey.empty and not df.empty:
    if all(c in df_survey.columns for c in [col_site, col_corp, col_q2]):

        df_survey[col_q2] = pd.to_numeric(df_survey[col_q2], errors="coerce")

        # Rata-rata per perusahaan-site
        df_feedback = (
            df_survey.groupby([col_corp, col_site])[col_q2]
            .mean()
            .reset_index()
            .rename(columns={col_corp: "perusahaan", col_site: "site", col_q2: "feedback_q2"})
        )

        # Hitung total ketidaksesuaian valid
        df_valid = df[df["status_temuan"] == "Valid"].copy()
        df_count = df_valid.groupby(["perusahaan", "site"]).size().reset_index(name="jumlah_ketidaksesuaian")

        # Hitung kategori perilaku dan non-perilaku
        perilaku_count = (
            df_valid[df_valid["kategori_subketidaksesuaian"] == "Perilaku"]
            .groupby(["perusahaan", "site"])
            .size()
            .reset_index(name="jumlah_perilaku")
        )
        nonperilaku_count = (
            df_valid[df_valid["kategori_subketidaksesuaian"] == "Non Perilaku"]
            .groupby(["perusahaan", "site"])
            .size()
            .reset_index(name="jumlah_nonperilaku")
        )

        # Gabungkan seluruh data
        df_corr = (
            df_feedback
            .merge(df_count, on=["perusahaan", "site"], how="left")
            .merge(perilaku_count, on=["perusahaan", "site"], how="left")
            .merge(nonperilaku_count, on=["perusahaan", "site"], how="left")
            .fillna(0)
        )

        # =========================================================
        # 🧪 UJI NORMALITAS (Smirnov, Lilliefors, Shapiro, dll)
        # =========================================================
        import numpy as np
        import pandas as pd
        import scipy.stats as stats
        import seaborn as sns
        import matplotlib.pyplot as plt
        from statsmodels.stats.diagnostic import lilliefors

        def run_normality_tests(series, label=""):
            s = pd.Series(series).dropna().astype(float)
            n = len(s)
            out = {"label": label, "n": n}
            if n == 0:
                return out, s
            mean, std = np.mean(s), np.std(s, ddof=1)
            out.update({"mean": mean, "std": std})

            # Kolmogorov-Smirnov (Smirnov Test)
            try:
                D, p_ks = stats.kstest(s, 'norm', args=(mean, std))
                out.update({"Smirnov stat": D, "Smirnov p": p_ks})
            except Exception:
                out.update({"Smirnov stat": np.nan, "Smirnov p": np.nan})

            # Lilliefors
            try:
                lillie_stat, lillie_p = lilliefors(s, dist='norm')
                out.update({"Lilliefors stat": lillie_stat, "Lilliefors p": lillie_p})
            except Exception:
                out.update({"Lilliefors stat": np.nan, "Lilliefors p": np.nan})

            # Shapiro–Wilk
            try:
                sh_stat, sh_p = stats.shapiro(s)
                out.update({"Shapiro stat": sh_stat, "Shapiro p": sh_p})
            except Exception:
                out.update({"Shapiro stat": np.nan, "Shapiro p": np.nan})

            # D’Agostino
            try:
                dag_stat, dag_p = stats.normaltest(s)
                out.update({"D’Agostino stat": dag_stat, "D’Agostino p": dag_p})
            except Exception:
                out.update({"D’Agostino stat": np.nan, "D’Agostino p": np.nan})

            return out, s

        res_base, s_base = run_normality_tests(df_corr["feedback_q2"], "Baseline (Perusahaan–Site)")
        res_ind, s_ind = run_normality_tests(df_survey[col_q2], "Responden Individu (Online+Offline)")
        res_df = pd.DataFrame([res_base, res_ind])
        
        # =========================================================
        # 📈 VISUALISASI DISTRIBUSI Survei Feedback Q2
        # =========================================================
        def plot_distribution(data, title):
            fig, ax = plt.subplots(1, 3, figsize=(16, 4))
            sns.histplot(data, kde=True, stat="density", color="#4C84FF", ax=ax[0])
            x = np.linspace(min(data), max(data), 200)
            y = stats.norm.pdf(x, np.mean(data), np.std(data))
            ax[0].plot(x, y, "r--", label="Kurva Normal")
            ax[0].legend()
            ax[0].set_title(f"{title}\n(Histogram + Kurva Normal)")

            stats.probplot(data, dist="norm", plot=ax[1])
            ax[1].set_title("QQ Plot")

            sorted_data = np.sort(data)
            theoretical = stats.norm.cdf(sorted_data, np.mean(data), np.std(data))
            empirical = np.arange(1, len(sorted_data)+1) / len(sorted_data)
            ax[2].plot(theoretical, empirical, "o", color="#4C84FF")
            ax[2].plot([0, 1], [0, 1], "r--")
            ax[2].set_title("PP Plot")
            plt.tight_layout()
            return fig

        st.markdown("### 📈 Visualisasi Distribusi Survei Feedback Q2")
        st.pyplot(plot_distribution(s_base, "Distribusi Feedback Q2 – Baseline"))
        st.pyplot(plot_distribution(s_ind, "Distribusi Feedback Q2 – Individu"))
        # =========================================================
        # 📊 ANALISIS KESTABILAN & REPRESENTATIVITAS BASELINE
        # =========================================================
        st.subheader("📏 Analisis Kestabilan Baseline (Feedback Q2)")

        # Hitung statistik deskriptif baseline & individu
        desc_stats = pd.DataFrame({
            "Statistik": ["Mean", "Median", "Std Dev", "Min", "Max", "IQR"],
            "Baseline (Perusahaan–Site)": [
                s_base.mean(), s_base.median(), s_base.std(), s_base.min(), s_base.max(),
                np.percentile(s_base, 75) - np.percentile(s_base, 25)
            ],
            "Individu (Online+Offline)": [
                s_ind.mean(), s_ind.median(), s_ind.std(), s_ind.min(), s_ind.max(),
                np.percentile(s_ind, 75) - np.percentile(s_ind, 25)
            ]
        }).set_index("Statistik")

        st.dataframe(desc_stats.style.format(precision=3), use_container_width=True)

        # Visualisasi perbandingan boxplot
        fig, ax = plt.subplots(figsize=(8,4))
        sns.boxplot(data=[s_base, s_ind], orient="v", palette=["#4C84FF","#50C878"])
        ax.set_xticklabels(["Baseline (Perusahaan–Site)", "Individu"])
        ax.set_ylabel("Skor Feedback Q2")
        ax.set_title("Perbandingan Distribusi Baseline vs Individu")
        st.pyplot(fig)

        # Uji kesamaan distribusi antara baseline dan individu (Mann–Whitney / KS)
        try:
            stat_mw, p_mw = stats.mannwhitneyu(s_base, s_ind, alternative="two-sided")
            stat_ks, p_ks = stats.ks_2samp(s_base, s_ind)
            st.markdown(f"**Mann–Whitney U test:** p = {p_mw:.4f}")
            st.markdown(f"**Kolmogorov–Smirnov 2-sample test:** p = {p_ks:.4f}")

            if p_mw > 0.05 and p_ks > 0.05:
                st.success("✅ Tidak ada perbedaan signifikan → baseline representatif terhadap populasi individu.")
            else:
                st.warning("⚠️ Ada perbedaan signifikan antara baseline dan individu → baseline mungkin belum stabil sebagai acuan.")
        except Exception as e:
            st.error(f"Gagal menjalankan uji kesamaan distribusi: {e}")

        st.caption("""
        **Interpretasi:**
        - Jika kedua p-value > 0.05 → distribusi baseline ≈ distribusi individu → baseline valid sebagai ukuran umum.
        - Jika salah satu p < 0.05 → baseline mungkin bias (misalnya hanya mewakili site tertentu).
        - IQR dan Std Dev membantu melihat seberapa homogen persepsi antar-site.
        """)

        # =========================================================
        # 🔗 UJI KORELASI ANTAR-VARIABEL
        # =========================================================
        st.markdown("## 🔗 Korelasi Antar-Variabel ")
        from sklearn.preprocessing import MinMaxScaler, StandardScaler

        # =========================================================
        # 🔧 FUNGSI: PLOT TREN KORELASI
        # =========================================================
        def plot_tren_korelasi(df_plot_in, var_x, var_y, mode="Baseline", scale_method="minmax"):
            import matplotlib.pyplot as plt
            import seaborn as sns

            df_plot = df_plot_in.copy()

            corp_col = next((c for c in df_plot.columns if "perusahaan" in c.lower() or "company" in c.lower()), None)
            site_col = next((c for c in df_plot.columns if "site" in c.lower() or "lokasi" in c.lower()), None)

            if corp_col is None and "perusahaan" in df_plot.columns:
                corp_col = "perusahaan"
            if site_col is None and "site" in df_plot.columns:
                site_col = "site"

            if corp_col in df_plot.columns and site_col in df_plot.columns:
                df_plot["corp_site_label"] = df_plot[corp_col].astype(str) + " - " + df_plot[site_col].astype(str)
            else:
                df_plot["corp_site_label"] = df_plot.index.astype(str)

            if scale_method == "minmax":
                range_min, range_max = (1, 5) if mode.lower() == "baseline" else (1, 4)
                scaler = MinMaxScaler((range_min, range_max))
            else:
                scaler = StandardScaler()

            df_scaled = df_plot[[var_x, var_y]].dropna()
            scaled = scaler.fit_transform(df_scaled)
            df_plot.loc[df_scaled.index, [f"{var_x}_scaled", f"{var_y}_scaled"]] = scaled

            baseline_val = df_plot[f"{var_x}_scaled"].mean()

            df_plot = df_plot.sort_values(f"{var_y}_scaled", ascending=False)
            fig, ax = plt.subplots(figsize=(20, 10))
            ax.plot(df_plot["corp_site_label"], df_plot[f"{var_y}_scaled"],
                    color="blue", marker="o", linestyle="-", linewidth=2, label=f"{var_y} (scaled)")
            ax.plot(df_plot["corp_site_label"], df_plot[f"{var_x}_scaled"],
                    color="red", marker="o", linestyle="dotted", linewidth=2, label=f"{var_x} (scaled)")

            ax.axhline(y=baseline_val, color="green", linestyle="dotted", linewidth=1.5)
            ax.text(len(df_plot)-1, baseline_val + 0.1,
                    f"Baseline (mean X): {baseline_val:.2f}",
                    color="green", fontsize=9, ha="right")

            ax.set_xticks(range(len(df_plot)))
            ax.set_xticklabels(df_plot["corp_site_label"], rotation=45, ha="right", fontsize=12)
            ax.set_ylabel("Skala (distandarisasi)")
            ax.set_xlabel("Perusahaan - Site", labelpad=10)
            ax.set_title(f"📈 Tren {var_y} vs {var_x} ({mode})", fontsize=11, fontweight="bold")
            ax.grid(True, linestyle="--", alpha=0.5)

            ax.legend(
                loc="center left",
                bbox_to_anchor=(1.02, 0.5),
                borderaxespad=0,
                fancybox=True,
                shadow=False,
                frameon=False,
                fontsize=8
            )

            plt.subplots_adjust(right=0.78, bottom=0.25)
            st.pyplot(fig)

            st.caption("""
            🔍 Interpretasi:
            - Garis **biru**: pola nilai variabel dependen setelah distandarisasi.
            - Garis **merah**: nilai variabel independen.
            - Garis **hijau putus-putus**: baseline (rata-rata variabel X terstandarisasi).
            - Jika trennya berlawanan arah, indikasi korelasi negatif.
            """)

        # ==============================
        # PILIH SUMBER VARIABEL
        # ==============================
        corr_source = st.radio(
            "Pilih sumber variabel untuk korelasi:",
            ("Baseline (df_corr + fraud metrics)", "Individu (df_survey + fraud context)"),
            horizontal=True
        )

        # ==============================
        # 🔽 FILTER LEVEL JABATAN (BARU, SETELAH RADIO)
        # ==============================
        df_survey_kor = df_survey.copy()
        level_col = "level_jabatan"

        if level_col in df_survey_kor.columns:
            level_opts = sorted(df_survey_kor[level_col].dropna().unique().tolist())
            level_sel = st.multiselect(
                "Filter Level Jabatan (berlaku untuk analisis korelasi):",
                level_opts,
                default=level_opts,
                key="filter_level_jabatan"
            )
            if level_sel:
                df_survey_kor = df_survey_kor[df_survey_kor[level_col].isin(level_sel)]
        else:
            st.info("Kolom **Level Jabatan** tidak ditemukan di data survei, jadi filter ini tidak aktif.")

        if df_survey_kor.empty:
            st.warning("Data survei kosong setelah filter level jabatan. Ubah pilihan level jabatan.")
            st.stop()

        # ==============================
        # === SUMBER 1: BASELINE ===
        # ==============================
        if "Baseline" in corr_source:
            # bangun ulang baseline dari df_survey_kor (bukan df_survey penuh)
            df_survey_kor[col_q2] = pd.to_numeric(df_survey_kor[col_q2], errors="coerce")

            df_feedback_kor = (
                df_survey_kor.groupby([col_corp, col_site])[col_q2]
                .mean()
                .reset_index()
                .rename(columns={col_corp: "perusahaan", col_site: "site", col_q2: "feedback_q2"})
            )

            df_corr = (
                df_feedback_kor
                .merge(df_count, on=["perusahaan", "site"], how="left")
                .merge(perilaku_count, on=["perusahaan", "site"], how="left")
                .merge(nonperilaku_count, on=["perusahaan", "site"], how="left")
                .fillna(0)
            )

            df_for_corr = df_corr.copy()

            # tambahkan ringkasan fraud
            if "ketidaksesuaian_scored" in st.session_state:
                df_fraud_all = st.session_state["ketidaksesuaian_scored"]
                fraud_summary = (
                    df_fraud_all.groupby(["perusahaan", "site"])
                    .agg(
                        jumlah_valid=('status_temuan', lambda x: (x=="Valid").sum()),
                        jumlah_fraud=('status_temuan', lambda x: (x=="Fraud").sum()),
                        fraud_decision_mode=('fraud_decision', lambda x: x.mode()[0] if not x.mode().empty else None)
                    ).reset_index()
                )
                df_for_corr = df_for_corr.merge(fraud_summary, on=["perusahaan", "site"], how="left")

                fraud_map = {
                    "Fraud: Duplikasi/Anomali": 3,
                    "Fraud: Status Tidak Didukung Bukti": 2,
                    "Non-Fraud (Temuan Sah)": 1,
                    "Butuh Tinjau (Bukti Lemah)": 0
                }
                df_for_corr["fraud_decision_code"] = df_for_corr["fraud_decision_mode"].map(fraud_map).fillna(0)
            else:
                st.warning("⚠️ Data fraud belum tersedia di session_state.")
                df_for_corr["jumlah_valid"] = df_for_corr["jumlah_fraud"] = df_for_corr["fraud_decision_code"] = 0

            # rasio tambahan
            if all(col in df_for_corr.columns for col in ["jumlah_valid", "jumlah_fraud", "jumlah_ketidaksesuaian"]):
                df_for_corr["total_laporan"] = df_for_corr["jumlah_valid"] + df_for_corr["jumlah_fraud"]
                df_for_corr["rasio_fraud"] = df_for_corr.apply(
                    lambda r: r["jumlah_fraud"] / r["total_laporan"] if r["total_laporan"] > 0 else 0,
                    axis=1
                )
                df_for_corr["rasio_valid"] = df_for_corr.apply(
                    lambda r: r["jumlah_valid"] / r["total_laporan"] if r["total_laporan"] > 0 else 0,
                    axis=1
                )
                if "jumlah_perilaku" in df_for_corr.columns:
                    df_for_corr["rasio_fraud_perilaku"] = df_for_corr.apply(
                        lambda r: r["jumlah_fraud"] / r["jumlah_perilaku"] if r["jumlah_perilaku"] > 0 else 0,
                        axis=1
                    )
                else:
                    df_for_corr["rasio_fraud_perilaku"] = 0

            numeric_cols_corr = [
                "feedback_q2",
                "jumlah_ketidaksesuaian",
                "jumlah_perilaku",
                "jumlah_nonperilaku",
                "jumlah_valid",
                "jumlah_fraud",
                "fraud_decision_code",
                "rasio_fraud",
                "rasio_valid",
                "rasio_fraud_perilaku"
            ]
            numeric_cols_corr = [c for c in numeric_cols_corr if c in df_for_corr.columns]

            st.markdown("### ⚙️ Pilihan Variabel (Baseline)")
            var_x = st.selectbox("Variabel X (independen):", numeric_cols_corr, key="base_x")
            var_y = st.selectbox("Variabel Y (dependen):", [v for v in numeric_cols_corr if v != var_x], key="base_y")
            force_method = st.selectbox(
                "Metode korelasi:",
                ("Otomatis (berdasarkan normalitas)", "Spearman", "Pearson"),
                key="baseline_method"
            )

            x = pd.to_numeric(df_for_corr[var_x], errors="coerce").dropna()
            y = pd.to_numeric(df_for_corr[var_y], errors="coerce").dropna()
            common_idx = x.index.intersection(y.index)
            x, y = x.loc[common_idx], y.loc[common_idx]

            normal_x = stats.shapiro(x)[1] > 0.05 if len(x) >= 3 else False
            normal_y = stats.shapiro(y)[1] > 0.05 if len(y) >= 3 else False
            if force_method == "Spearman":
                method = "spearman"
            elif force_method == "Pearson":
                method = "pearson"
            else:
                method = "pearson" if (normal_x and normal_y) else "spearman"

            corr_val, p_val = (
                stats.spearmanr(x, y) if method == "spearman" else stats.pearsonr(x, y)
            )

            st.markdown(f"### 🔢 Hasil Korelasi ({method.title()}) — Baseline")
            st.write(f"Koefisien: **{corr_val:.4f}**, p-value: **{p_val:.4f}**, n = {len(x)}")

            if p_val < 0.05:
                st.success("Hubungan signifikan (p < 0.05).")
            else:
                st.info("Tidak ada hubungan signifikan (p ≥ 0.05).")
            
            st.markdown("""
            - Motode Korelasi **Pearson** digunakan pada data yang berdistribusi normal.
            - Metode Korelasi **Spearman** digunakan pada data yang **tidak** berdistribusi normal. 
            """)

            fig, ax = plt.subplots(figsize=(6, 4))
            sns.scatterplot(x=x, y=y, ax=ax, color="#4C84FF")
            if method == "pearson":
                sns.regplot(x=x, y=y, ax=ax, scatter=False, line_kws={"color": "red"})
            else:
                sns.regplot(x=x, y=y, ax=ax, scatter=False, lowess=True, line_kws={"color": "red"})
            ax.set_title(f"{method.title()} Correlation (Baseline): {var_x} vs {var_y}")
            st.pyplot(fig)

            st.markdown("### 📊 Tren Variabel per Site/Perusahaan")
            plot_tren_korelasi(df_for_corr, var_x, var_y, mode="Baseline", scale_method="minmax")

        # ==============================
        # === SUMBER 2: INDIVIDU ===
        # ==============================
        else:
            import regex as re_rx
            from sklearn.preprocessing import MinMaxScaler, StandardScaler

            df_for_corr = df_survey_kor.copy()
            # (lanjutan blok INDIVIDU kamu yang lama, tapi ganti df_survey -> df_survey_kor,
            # dan df_for_corr = df_survey_kor.copy() seperti di sini

            # ----------------------------------------------------------
            # 1️⃣ PILIH INDIKATOR
            # ----------------------------------------------------------
            indicator_choice = st.radio(
                "Pilih indikator yang ingin dianalisis:",
                ("Knowledge", "Attitude", "Behaviour"),
                horizontal=True
            )

            # Daftar kata kunci unik untuk tiap indikator
            indicator_keywords = {
                "Knowledge": [
                    "memahami tujuan dari program", "memahami sampah sesuai dengan jenisnya", "jenis tempat sampah yang tersedia", "sosialisasi atau edukasi tentang GBST",
                    "dampak jika sampah tidak dikelola", "mengetahui PIC atau penanggung jawab", "lokasi tempat sampah khusus", "sanksi jika tidak mengikut aturan"
                ],
                "Attitude": [
                    "berpendapat bahwa GBST penting untuk dilaksanakan", "terganggu jika sampah tidak terpilah", "mendukung adanya pengawasan yang ketat", "lebih lanjut tentang pemilahan sampah", "perusahaan sudah serius",
                    "partisipasi aktif individu dapat mempengaruhi keberhasilan", "penting adanya sanksi jika ada pekerja", "target kinerja penilaian PROPER", "bagian dari budaya kerja", "kewajiban seluruh pekerja", "platform Beats dengan benar"
                ],
                "Behaviour": [
                    "terbiasa memilah dan membuang", "mengingatkan rekan kerja jika salah", "mengurangi penggunaan plastik sekali",
                    "konsisten mematuhi aturan memilah", "menggunakan APD", "terbiasa menggunakan tumbler"
                ]
            }

            # ----------------------------------------------------------
            # 2️⃣ OTOMATISASI PENCARIAN KOLOM
            # ----------------------------------------------------------
            def find_columns_by_keywords(keywords, df_cols):
                """Temukan kolom df_survey yang paling relevan dengan daftar kata kunci"""
                matched = []
                for kw in keywords:
                    pattern = re.escape(kw.lower()).replace("\\ ", ".*")
                    for col in df_cols:
                        if re.search(pattern, col.lower()):
                            matched.append(col)
                return sorted(set(matched))

            all_cols = df_for_corr.columns.tolist()
            selected_items = find_columns_by_keywords(indicator_keywords[indicator_choice], all_cols)

            if not selected_items:
                st.warning("⚠️ Tidak ada kolom yang cocok dengan indikator ini. Periksa nama kolom di df_survey.")
            else:
                st.markdown(f"### 🧠 Item yang Ditemukan untuk {indicator_choice}")
                st.write(selected_items)

            # Konversi ke numerik dan buat composite
            for col in selected_items:
                df_for_corr[col] = pd.to_numeric(df_for_corr[col], errors="coerce")
            composite_col = f"{indicator_choice.lower()}_composite"
            if selected_items:
                df_for_corr[composite_col] = df_for_corr[selected_items].mean(axis=1, skipna=True)

            # ----------------------------------------------------------
            # 3️⃣ GABUNGKAN METRIK KETIDAKSESUAIAN, PERILAKU, DAN FRAUD/VALID DARI SITE
            # ----------------------------------------------------------
            if "ketidaksesuaian_scored" in st.session_state:
                df_fraud = st.session_state["ketidaksesuaian_scored"]

                # normalisasi dulu label agar gak error ejaan
                if "kategori_subketidaksesuaian" in df_fraud.columns:
                    df_fraud["kategori_subketidaksesuaian"] = (
                        df_fraud["kategori_subketidaksesuaian"]
                        .astype(str).str.strip().str.lower()
                        .replace({
                            "non-perilaku": "non perilaku",
                            "non_perilaku": "non perilaku",
                            "non  perilaku": "non perilaku"
                        })
                    )
                if "status_temuan" in df_fraud.columns:
                    df_fraud["status_temuan"] = df_fraud["status_temuan"].astype(str).str.strip().str.title()

                fraud_summary = (
                    df_fraud.groupby(["perusahaan","site"])
                    .agg(
                        jumlah_ketidaksesuaian_site=('status_temuan', 'size'),
                        jumlah_perilaku_site=('kategori_subketidaksesuaian', lambda x: (x=="perilaku").sum()),
                        jumlah_nonperilaku_site=('kategori_subketidaksesuaian', lambda x: (x=="non perilaku").sum()),
                        jumlah_valid_site=('status_temuan', lambda x: (x=="Valid").sum()),
                        jumlah_fraud_site=('status_temuan', lambda x: (x=="Fraud").sum())
                    )
                    .reset_index()
                )

                # hitung rasio
                fraud_summary["total_site"] = fraud_summary["jumlah_valid_site"] + fraud_summary["jumlah_fraud_site"]
                fraud_summary["rasio_valid_site"] = fraud_summary.apply(
                    lambda r: r["jumlah_valid_site"]/r["total_site"] if r["total_site"]>0 else 0, axis=1)
                fraud_summary["rasio_fraud_site"] = fraud_summary.apply(
                    lambda r: r["jumlah_fraud_site"]/r["total_site"] if r["total_site"]>0 else 0, axis=1)
                fraud_summary["rasio_ketidaksesuaian_site"] = fraud_summary.apply(
                    lambda r: r["jumlah_fraud_site"]/r["jumlah_ketidaksesuaian_site"]
                    if r["jumlah_ketidaksesuaian_site"]>0 else 0, axis=1
                )

                # gabungkan ke df_for_corr
                df_for_corr = df_for_corr.merge(
                    fraud_summary,
                    left_on=[col_corp, col_site],
                    right_on=["perusahaan","site"],
                    how="left"
                ).drop(columns=["perusahaan","site"], errors="ignore")

            else:
                st.warning("⚠️ Data ketidaksesuaian belum dimuat di session_state.")
                for c in [
                    "jumlah_ketidaksesuaian_site","jumlah_perilaku_site","jumlah_nonperilaku_site",
                    "jumlah_valid_site","jumlah_fraud_site",
                    "rasio_valid_site","rasio_fraud_site","rasio_ketidaksesuaian_site"
                ]:
                    df_for_corr[c] = 0

            # ----------------------------------------------------------
            # 4️⃣ GROUPING & STANDARISASI
            # ----------------------------------------------------------
            st.markdown("### 🧩 Opsi Pengelompokan & Standarisasi (Individu)")
            group_mode = st.selectbox(
                "Level agregasi:",
                ("Per Responden","Per Site (mean)","Per Perusahaan–Site (mean)","Per Perusahaan (mean)")
            )
            keys = None
            if group_mode == "Per Site (mean)": keys = [col_site]
            elif group_mode == "Per Perusahaan–Site (mean)": keys = [col_corp, col_site]
            elif group_mode == "Per Perusahaan (mean)": keys = [col_corp]
            if keys:
                num_cols = [c for c in df_for_corr.columns if pd.api.types.is_numeric_dtype(df_for_corr[c])]
                df_for_corr = df_for_corr.groupby(keys, as_index=False)[num_cols].mean()

            scaling_method = st.radio("Metode standarisasi:",("Tanpa","MinMax (1–4)","MinMax (0–1)","Z-score"),horizontal=True)
            df_for_corr_scaled = df_for_corr.copy()
            num_cols_all = [c for c in df_for_corr.columns if pd.api.types.is_numeric_dtype(df_for_corr[c])]
            if scaling_method != "Tanpa" and num_cols_all:
                if scaling_method == "MinMax (1–4)":
                    sc = MinMaxScaler((1,4))
                elif scaling_method == "MinMax (0–1)":
                    sc = MinMaxScaler((0,1))
                else:
                    sc = StandardScaler()
                df_for_corr_scaled[num_cols_all] = sc.fit_transform(df_for_corr[num_cols_all])

            # ----------------------------------------------------------
            # 5️⃣ PILIH VARIABEL X & Y
            # ----------------------------------------------------------
            st.markdown("### 🔗 Pilih Variabel untuk Korelasi")
            extra_vars = [
                "jumlah_ketidaksesuaian_site","jumlah_perilaku_site","jumlah_nonperilaku_site",
                "jumlah_valid_site","jumlah_fraud_site",
                "rasio_ketidaksesuaian_site","rasio_valid_site","rasio_fraud_site"
            ]
            numeric_cols_corr = [c for c in selected_items + [composite_col] + extra_vars
                                if c in df_for_corr_scaled.columns]
            var_x = st.selectbox("Variabel X (independen):", sorted(numeric_cols_corr))
            var_y = st.selectbox("Variabel Y (dependen):", sorted([c for c in numeric_cols_corr if c != var_x]))

            # ----------------------------------------------------------
            # 6️⃣ HITUNG KORELASI + VISUALISASI
            # ----------------------------------------------------------
            x = pd.to_numeric(df_for_corr_scaled[var_x], errors="coerce").dropna()
            y = pd.to_numeric(df_for_corr_scaled[var_y], errors="coerce").dropna()
            common_idx = x.index.intersection(y.index)
            x, y = x.loc[common_idx], y.loc[common_idx]

            normal_x = stats.shapiro(x)[1] > 0.05 if len(x) >= 3 else False
            normal_y = stats.shapiro(y)[1] > 0.05 if len(y) >= 3 else False
            method = "pearson" if (normal_x and normal_y) else "spearman"
            corr_val, p_val = (stats.pearsonr(x, y) if method == "pearson" else stats.spearmanr(x, y))

            st.markdown(f"### 🔢 Hasil Korelasi ({method.title()}) — {indicator_choice}")
            st.write(f"Koefisien: **{corr_val:.4f}**, p-value: **{p_val:.4f}** • n = {len(x)}")
            if p_val < 0.05:
                st.success("Hubungan signifikan (p < 0.05).")
            else:
                st.info("Tidak ada hubungan signifikan (p ≥ 0.05).")
            
            st.markdown("""
                        - Motode Korelasi **Pearson** digunakan pada data yang berdistribusi normal. 
                        - Metode Korelasi **Spearman** digunakan pada data yang **tidak** berdistribusi normal. """)
            # Scatter
            fig, ax = plt.subplots(figsize=(6, 4))
            sns.scatterplot(x=x, y=y, ax=ax, color="#4C84FF")
            sns.regplot(x=x, y=y, ax=ax, scatter=False, lowess=(method=="spearman"), line_kws={"color":"red"})
            ax.set_title(f"{method.title()} Correlation (Individu): {var_x} vs {var_y}")
            st.pyplot(fig)

            # Tren
            st.markdown("### 📊 Tren Variabel per Site/Perusahaan")
            plot_tren_korelasi(df_for_corr, var_x, var_y, mode="Individu", scale_method="minmax")
                
        # =========================================================
        # 🔥 HEATMAP KORELASI ANTAR SEMUA VARIABEL (otomatis) – VERSI UMUM
        # =========================================================
        st.markdown("### 🧩 Heatmap Korelasi Antar Variabel (Versi Umum)")

        num_data_global = df_for_corr.select_dtypes(include=[np.number]).dropna()
        if num_data_global.shape[1] >= 2:
            corr_matrix_global = num_data_global.corr(method=method)
            fig_corr_g, ax_g = plt.subplots(figsize=(8, 5))
            sns.heatmap(
                corr_matrix_global,
                annot=True, fmt=".2f", cmap="coolwarm",
                square=True, cbar_kws={"label": f"{method.title()} Coefficient"},
                linewidths=0.5, ax=ax_g
            )
            ax_g.set_title(f"Heatmap Korelasi ({method.title()}) untuk Semua Variabel", fontweight="bold", pad=10)
            st.pyplot(fig_corr_g)

            st.markdown("#### 🧠 Interpretasi Cepat")
            st.markdown("""
            - Warna **merah** menunjukkan korelasi positif, **biru** menunjukkan korelasi negatif.  
            - Nilai di atas **0.5** atau di bawah **–0.5** umumnya dianggap kuat.  
            - Gunakan hasil ini untuk mengidentifikasi variabel yang paling berkaitan dengan *Feedback Q2*, *attitude*, atau indikator *fraud/valid*.
            """)
        else:
            st.info("Tidak cukup variabel numerik untuk menampilkan heatmap.")


# ===============================
# EKSPOR DATA
# ===============================
st.subheader("📥 Ekspor Data (opsional)")
if not df_valid.empty:
    csv = df_valid.to_csv(index=False).encode('utf-8')
    st.download_button("Download CSV Laporan Valid", data=csv, file_name="ketidaksesuaian_valid.csv", mime="text/csv")
else:
    st.info("Tidak ada laporan valid untuk diunduh.")
