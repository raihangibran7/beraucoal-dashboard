import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import calendar
import re
import datetime

# =============================
# Load Data dari Google Sheets
# =============================
sheet_url = "https://docs.google.com/spreadsheets/d/1cw3xMomuMOaprs8mkmj_qnib-Zp_9n68rYMgiRZZqBE/edit?usp=sharing"
sheet_id = sheet_url.split("/")[5]
sheet_name = ["Timbulan", "Program", "Survei_Online",
              "Ketidaksesuaian", "Survei_Offline", "CCTV", "Jml_CCTV"]

all_df = {}
for sheet in sheet_name:
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet}"
        df = pd.read_csv(url)
        all_df[sheet] = df
    except Exception as e:
        st.error(f"Gagal load sheet {sheet}: {e}")
        all_df[sheet] = pd.DataFrame()

# Ambil sheet utama
dt_timbulan = all_df.get("Timbulan", pd.DataFrame())
dt_program = all_df.get("Program", pd.DataFrame())
df_program = dt_program.copy()
dt_online = all_df.get("Survei_Online", pd.DataFrame())
df_ketidaksesuaian = all_df.get("Ketidaksesuaian", pd.DataFrame())
df_cctv = all_df.get("Jml_CCTV", pd.DataFrame())

# Pastikan kolom numeric dasar
if "Timbulan" in dt_timbulan.columns:
    dt_timbulan["Timbulan"] = pd.to_numeric(
        dt_timbulan["Timbulan"], errors="coerce"
    ).fillna(0)

if "Total_calc" in dt_program.columns:
    dt_program["Total_calc"] = pd.to_numeric(
        dt_program["Total_calc"], errors="coerce"
    ).fillna(0)

# =============================
# FILTER SIDEBAR
# =============================
st.sidebar.subheader("Filter Data")

site_list = sorted(dt_timbulan["Site"].dropna().unique()) if "Site" in dt_timbulan.columns else []
site_sel = st.sidebar.multiselect("Pilih Site", site_list, default=site_list if site_list else [])

perusahaan_list = sorted(dt_timbulan["Perusahaan"].dropna().unique()) if "Perusahaan" in dt_timbulan.columns else []
perusahaan_sel = st.sidebar.multiselect("Pilih Perusahaan", perusahaan_list, default=perusahaan_list if perusahaan_list else [])

# ----- Deteksi kolom bulan-tahun di Program -----
pattern = r"^(Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|September|Oktober|November|Desember) \d{4}$"
bulan_tahun_cols = [col for col in df_program.columns if re.match(pattern, str(col))]

if bulan_tahun_cols:
    df_prog_long = df_program.melt(
        id_vars=[c for c in df_program.columns if c not in bulan_tahun_cols],
        value_vars=bulan_tahun_cols,
        var_name="Bulan-Tahun",
        value_name="Value"
    )
    df_prog_long["Tahun"] = df_prog_long["Bulan-Tahun"].apply(lambda x: int(x.split(" ")[1]))
    df_prog_long["Bulan"] = df_prog_long["Bulan-Tahun"].apply(lambda x: x.split(" ")[0])
else:
    df_prog_long = pd.DataFrame(columns=["Tahun", "Bulan", "Value"])

bulan_map = {
    "Januari": 1, "Februari": 2, "Maret": 3, "April": 4,
    "Mei": 5, "Juni": 6, "Juli": 7, "Agustus": 8,
    "September": 9, "Oktober": 10, "November": 11, "Desember": 12
}

if not df_prog_long.empty:
    df_prog_long["Periode"] = df_prog_long.apply(
        lambda row: datetime.datetime(row["Tahun"], bulan_map[row["Bulan"]], 1),
        axis=1
    )

# ----- Tambah Tahun di Ketidaksesuaian (kalau ada) -----
if not df_ketidaksesuaian.empty and "TanggalLapor" in df_ketidaksesuaian.columns:
    df_ketidaksesuaian["TanggalLapor"] = pd.to_datetime(
        df_ketidaksesuaian["TanggalLapor"], dayfirst=True, errors="coerce"
    )
    df_ketidaksesuaian["Tahun"] = df_ketidaksesuaian["TanggalLapor"].dt.year
    df_ketidaksesuaian["Bulan"] = df_ketidaksesuaian["TanggalLapor"].dt.month

# -------------------------
# 🔹 FILTER TAHUN
# -------------------------
tahun_tersedia = sorted(df_prog_long["Tahun"].dropna().astype(int).unique().tolist()) if "Tahun" in df_prog_long.columns else []
if "Tahun" in dt_timbulan.columns:
    tahun_tersedia = sorted(
        set(tahun_tersedia) | set(dt_timbulan["Tahun"].dropna().astype(int).unique().tolist())
    )

tahun_pilihan = st.sidebar.multiselect(
    "Pilih Tahun:", tahun_tersedia, default=tahun_tersedia
)

# Untuk hitung rata-rata per hari (approx.)
if tahun_pilihan:
    days_period = 365 * len(tahun_pilihan)
else:
    days_period = 365

# -------------------------
# 🔹 APPLY FILTER TAHUN KE SEMUA DF
# -------------------------
if tahun_pilihan:
    if "Tahun" in dt_timbulan.columns:
        dt_timbulan = dt_timbulan[dt_timbulan["Tahun"].isin(tahun_pilihan)]

    if "Tahun" in dt_program.columns:
        dt_program = dt_program[dt_program["Tahun"].isin(tahun_pilihan)]

    if not df_ketidaksesuaian.empty and "Tahun" in df_ketidaksesuaian.columns:
        df_ketidaksesuaian = df_ketidaksesuaian[df_ketidaksesuaian["Tahun"].isin(tahun_pilihan)]

    if not dt_online.empty and "Tanggal" in dt_online.columns:
        dt_online["Tanggal"] = pd.to_datetime(dt_online["Tanggal"], dayfirst=True, errors="coerce")
        dt_online["Tahun"] = dt_online["Tanggal"].dt.year
        dt_online = dt_online[dt_online["Tahun"].isin(tahun_pilihan)]

# -------------------------
# 🔹 FILTER SITE & PERUSAHAAN
# -------------------------
df_timbulan_filtered = dt_timbulan.copy()
if site_sel:
    df_timbulan_filtered = df_timbulan_filtered[df_timbulan_filtered["Site"].isin(site_sel)]
if perusahaan_sel:
    df_timbulan_filtered = df_timbulan_filtered[df_timbulan_filtered["Perusahaan"].isin(perusahaan_sel)]

df_program_filtered = dt_program.copy()
if site_sel and "Site" in df_program_filtered.columns:
    df_program_filtered = df_program_filtered[df_program_filtered["Site"].isin(site_sel)]
if perusahaan_sel and "Perusahaan" in df_program_filtered.columns:
    df_program_filtered = df_program_filtered[df_program_filtered["Perusahaan"].isin(perusahaan_sel)]

df_ket_filtered = df_ketidaksesuaian.copy()
if site_sel and "Site" in df_ket_filtered.columns:
    df_ket_filtered = df_ket_filtered[df_ket_filtered["Site"].isin(site_sel)]
if perusahaan_sel and "Perusahaan" in df_ket_filtered.columns:
    df_ket_filtered = df_ket_filtered[df_ket_filtered["Perusahaan"].isin(perusahaan_sel)]

# =============================
# METRIC UTAMA (atas)
# =============================
try:
    df_timbulan = df_timbulan_filtered.copy()
    df_program = df_program_filtered.copy()
    df_ket = df_ket_filtered.copy()

    # --- Total Timbulan ---
    if "Timbulan" in df_timbulan.columns:
        df_timbulan["Timbulan"] = pd.to_numeric(
            df_timbulan["Timbulan"].astype(str).str.replace(",", "."),
            errors="coerce"
        )

        total_timbulan = df_timbulan["Timbulan"].sum()

        # kalau ada kolom data_input_total dipakai, kalau tidak pakai total_timbulan
        if "data_input_total" in df_timbulan.columns:
            total_timbulan_all = pd.to_numeric(
                df_timbulan["data_input_total"], errors="coerce"
            ).sum()
        else:
            total_timbulan_all = total_timbulan
    else:
        total_timbulan = 0
        total_timbulan_all = 0

    # --- Man Power unik & jumlah unit perusahaan-site (LOGIKA SAMA DENGAN SNI) ---
    if not df_timbulan.empty and {"Site", "Perusahaan", "Man Power"}.issubset(df_timbulan.columns):
        subset_cols = ["Site", "Perusahaan"]
        if "Tahun" in df_timbulan.columns:
            subset_cols.append("Tahun")

        df_mp_unik_metric = (
            df_timbulan
            .drop_duplicates(subset=subset_cols, keep="last")
            [subset_cols + ["Man Power"]]
            .copy()
        )

        df_mp_unik_metric["Man Power"] = pd.to_numeric(
            df_mp_unik_metric["Man Power"], errors="coerce"
        ).fillna(0)

        total_manpower = df_mp_unik_metric["Man Power"].sum()
        jumlah_unit = (
                df_mp_unik_metric[["Site", "Perusahaan"]]
                .drop_duplicates()
                .shape[0]
        )
    else:
        total_manpower = 0
        jumlah_unit = 0

    rasio_manpower = total_timbulan / total_manpower if total_manpower > 0 else 0

    # --- Jumlah Program ---
    if "Nama program" in df_program.columns:
        df_program["Total_calc"] = pd.to_numeric(
            df_program["Total_calc"].astype(str).str.replace(",", "."),
            errors="coerce"
        )
        jumlah_program = df_program["Nama program"].dropna().shape[0]
        total_program = df_program["Total_calc"].sum()
    else:
        jumlah_program = 0
        total_program = 0

    # --- Ketidaksesuaian Valid ---
    if "status_temuan" in df_ket.columns:
        total_ketidaksesuaian = df_ket.query("status_temuan == 'Valid'").shape[0]
        temuan_masuk = df_ket["status_temuan"].count()
    else:
        total_ketidaksesuaian = 0
        temuan_masuk = 0

    # --- Persentase program terkelola (approx) ---
    if total_timbulan > 0 and total_program > 0 and days_period > 0:
        avg_timbulan_perhari = total_timbulan
        avg_program_perhari = total_program / days_period
        persentase_terkelola = (avg_program_perhari / avg_timbulan_perhari) * 100
    else:
        persentase_terkelola = 0

    # ---------- STYLE CARD ----------
    card_style = """
        background-color:#ffffff;
        border-radius:10px;
        padding:14px 16px;
        box-shadow:0 2px 4px rgba(15,15,15,0.08);
    """

    # ---------- TAMPILKAN 3 CARD METRIK ----------
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
            <div style="{card_style}">
                <h6 style="margin-bottom:4px;margin-top:0;font-weight:normal;">Total Timbulan (kg)</h6>
                <p style="font-size:40px; margin:0;">{total_timbulan_all:,.0f}</p>
                <p style="font-size:13px; margin-top:4px; color:#3BB143;">
                    per {jumlah_unit} perusahaan-site dari <strong>{total_manpower:,.0f}</strong> manpower unik
                </p>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
            <div style="{card_style}">
                <h6 style="margin-bottom:4px;margin-top:0;font-weight:normal;">Rata-rata Timbulan (kg/hari)</h6>
                <p style="font-size:40px; margin:0;">{total_timbulan:.2f}</p>
                <p style="font-size:13px; margin-top:4px; color:#3BB143;">
                    dengan <strong>{rasio_manpower:.2f}</strong> kg/hari/manpower
                </p>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
            <div style="{card_style}">
                <h6 style="margin-bottom:4px;margin-top:0;font-weight:normal;">Jumlah Man Power (Unik)</h6>
                <p style="font-size:40px; margin:0;">{total_manpower:,.0f}</p>
                <p style="font-size:13px; margin-top:4px; color:#3BB143;">
                    pada {jumlah_unit} perusahaan-site terpilih
                </p>
            </div>
        """, unsafe_allow_html=True)

except Exception as e:
    st.error("Gagal menghitung metric.")
    st.exception(e)


 # ======================================================
# 🔢 RATA-RATA TIMBULAN SESUAI SNI (kg/hari/orang)
# ======================================================
st.markdown("### ♻️ Rata-rata Timbulan Sesuai SNI (kg/hari/orang)")

if not df_timbulan.empty and {"Site", "Perusahaan", "Timbulan", "Man Power"}.issubset(df_timbulan.columns):
    df_timbulan_sni = df_timbulan.copy()
    df_timbulan_sni["Timbulan"] = pd.to_numeric(df_timbulan_sni["Timbulan"], errors="coerce").fillna(0)
    df_timbulan_sni["Man Power"] = pd.to_numeric(df_timbulan_sni["Man Power"], errors="coerce").fillna(0)

    # kombinasi unik site-perusahaan-tahun (kalau kolom Tahun ada)
    subset_cols_sni = ["Site", "Perusahaan"]
    if "Tahun" in df_timbulan_sni.columns:
        subset_cols_sni.append("Tahun")

    df_mp_unik_sni = (
        df_timbulan_sni
        .drop_duplicates(subset=subset_cols_sni, keep="last")
        [subset_cols_sni + ["Man Power"]]
        .copy()
    )

    df_mp_unik_sni["Man Power"] = pd.to_numeric(
        df_mp_unik_sni["Man Power"], errors="coerce"
    ).fillna(0)

    total_timbulan_all_sni = df_timbulan_sni["Timbulan"].sum()
    total_mp_unik = df_mp_unik_sni["Man Power"].sum()   # → harusnya jadi 3.498


    rata_sni = total_timbulan_all_sni / total_mp_unik if total_mp_unik > 0 else 0

    st.markdown(f"""
    <div style="background:#f8fff5;border:1px solid #a5d6a7;border-radius:8px;padding:15px;margin-bottom:10px;">
        <h5 style="margin:0;color:#2e7d32;">Rata-rata Timbulan (SNI)</h5>
        <p style="font-size:32px;margin:0;color:#1b5e20;"><strong>{rata_sni:.3f}</strong> kg/hari/orang</p>
        <p style="font-size:13px;margin-top:4px;color:#388e3c;">
            Total Timbulan: {total_timbulan_all_sni:,.0f} kg | Total Man Power Unik: {total_mp_unik:,.0f}
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("#### 📋 Rincian per Site")
    df_site_sni = (
        df_timbulan_sni.groupby("Site", as_index=False)
        .agg(total_timbulan=("Timbulan", "sum"))
        .merge(
            df_mp_unik_sni.groupby("Site", as_index=False)["Man Power"].sum(),
            on="Site", how="left"
        )
    )
    df_site_sni["kg/hari/orang"] = (
        df_site_sni["total_timbulan"] / df_site_sni["Man Power"]
    ).round(3)
    df_site_sni = df_site_sni.sort_values("kg/hari/orang", ascending=False)
    st.dataframe(df_site_sni, hide_index=True)
else:
    st.warning("Kolom 'Timbulan', 'Man Power', 'Site', atau 'Perusahaan' belum lengkap untuk perhitungan SNI.")


# ======================================================
# 📊 GRAFIK TIMBULAN: data_input_total (kg) vs Timbulan (kg/hari) vs kg/hari/manpower
# ======================================================
st.markdown("## 📊 Visualisasi Timbulan (3 metrik)")

needed_cols = {"Site", "Perusahaan", "Timbulan", "Man Power", "Tahun"}
if df_timbulan_filtered.empty or not needed_cols.issubset(df_timbulan_filtered.columns):
    st.warning(
        "Data timbulan kosong atau kolom belum lengkap.\n"
        "Kolom wajib: Site, Perusahaan, Tahun, Timbulan, Man Power."
    )
else:
    # ----------------------------
    # UI pilihan metrik
    # ----------------------------
    metric_mode = st.radio(
        "Pilih metrik yang ditampilkan:",
        ["data_input_total (kg)", "Timbulan (kg/hari)", "kg/hari/manpower"],
        horizontal=True
    )

    df_base = df_timbulan_filtered.copy()

    # Pastikan numeric
    df_base["Tahun"] = pd.to_numeric(df_base["Tahun"], errors="coerce").astype("Int64")
    df_base["Timbulan"] = pd.to_numeric(df_base["Timbulan"], errors="coerce").fillna(0)
    df_base["Man Power"] = pd.to_numeric(df_base["Man Power"], errors="coerce").fillna(0)

    # data_input_total optional (kalau ada)
    has_totalcol = "data_input_total" in df_base.columns
    if has_totalcol:
        df_base["data_input_total"] = pd.to_numeric(df_base["data_input_total"], errors="coerce").fillna(0)

    import plotly.graph_objects as go

    # =========================
    # Tahun dropdown + opsi All
    # =========================
    tahun_opsi = sorted([int(x) for x in df_base["Tahun"].dropna().unique().tolist()])
    if not tahun_opsi:
        st.warning("Tidak ada nilai Tahun yang valid.")
    else:
        opsi_tahun_ui = ["All"] + tahun_opsi
        tahun_pilihan_ui = st.selectbox("Pilih Tahun untuk grafik:", opsi_tahun_ui, index=0)

        # ======================================================
        # MODE ALL -> tampilkan perbandingan 2024 vs 2025 (grouped horizontal)
        # ======================================================
        if tahun_pilihan_ui == "All":
            years_available = sorted([int(x) for x in df_base["Tahun"].dropna().unique().tolist()])
            years_target = [y for y in [2024, 2025] if y in years_available]

            if len(years_target) < 2:
                st.warning("Mode All membutuhkan data minimal tahun 2024 dan 2025.")
            else:
                import plotly.graph_objects as go

                year_colors = {2024: "red", 2025: "green"}

                # ambil data 2024 & 2025
                df_c = df_base[df_base["Tahun"].isin(years_target)].copy()
                df_c["Tahun"] = pd.to_numeric(df_c["Tahun"], errors="coerce").astype(int)
                df_c["Timbulan"] = pd.to_numeric(df_c["Timbulan"], errors="coerce").fillna(0)
                df_c["Man Power"] = pd.to_numeric(df_c["Man Power"], errors="coerce").fillna(0)

                # data_input_total optional
                if has_totalcol:
                    df_c["data_input_total"] = pd.to_numeric(df_c["data_input_total"], errors="coerce").fillna(0)

                # tentukan metrik sesuai metric_mode
                if metric_mode == "data_input_total (kg)":
                    if not has_totalcol:
                        st.warning("Kolom 'data_input_total' tidak ditemukan, jadi mode ini tidak bisa dibandingkan.")
                        st.stop()
                    value_kind = "KG"
                    x_title = "data_input_total (kg)"
                    decimals = 0
                elif metric_mode == "Timbulan (kg/hari)":
                    value_kind = "KGDAY"
                    x_title = "Timbulan (kg/hari)"
                    decimals = 2
                else:
                    value_kind = "KGDAY_per_MP"
                    x_title = "kg/hari/manpower"
                    decimals = 4

                uniq_cols = ["Site", "Perusahaan", "Tahun"]

                # =========================
                # A) PERBANDINGAN PER SITE
                # =========================
                site_kgday_y = (
                    df_c.groupby(["Site", "Tahun"], as_index=False)["Timbulan"]
                    .sum().rename(columns={"Timbulan": "KGDAY"})
                )
                site_mp_y = (
                    df_c[uniq_cols + ["Man Power"]]
                    .drop_duplicates(subset=uniq_cols, keep="last")
                    .groupby(["Site", "Tahun"], as_index=False)["Man Power"]
                    .sum().rename(columns={"Man Power": "MP"})
                )

                site_comp = site_kgday_y.merge(site_mp_y, on=["Site", "Tahun"], how="left")
                site_comp["MP"] = site_comp["MP"].fillna(0)

                if has_totalcol:
                    site_kg_y = (
                        df_c.groupby(["Site", "Tahun"], as_index=False)["data_input_total"]
                        .sum().rename(columns={"data_input_total": "KG"})
                    )
                    site_comp = site_comp.merge(site_kg_y, on=["Site", "Tahun"], how="left")
                else:
                    site_comp["KG"] = 0

                site_comp["KGDAY_per_MP"] = np.where(site_comp["MP"] > 0, site_comp["KGDAY"] / site_comp["MP"], 0)
                site_comp["Value"] = site_comp[value_kind]

                cat_order_site = (
                    site_comp.groupby("Site")["Value"].sum()
                    .sort_values(ascending=True)
                    .index.tolist()
                )

                fig_site_cmp = go.Figure()
                for yr in years_target:
                    df_y = site_comp[site_comp["Tahun"] == yr].set_index("Site").reindex(cat_order_site).reset_index()
                    df_y["Value"] = df_y["Value"].fillna(0)

                    fig_site_cmp.add_trace(go.Bar(
                        name=str(yr),
                        y=df_y["Site"],
                        x=df_y["Value"],
                        orientation="h",
                        marker_color=year_colors.get(yr, "gray"),
                        text=[f"{v:,.{decimals}f}" for v in df_y["Value"]],
                        textposition="outside",
                        cliponaxis=False
                    ))

                fig_site_cmp.update_layout(
                    barmode="group",
                    template="plotly_white",
                    height=520,
                    xaxis_title=x_title,
                    yaxis_title="Site",
                    legend_title="Tahun",
                    margin=dict(t=40, b=40, l=90, r=20),
                )
                fig_site_cmp.update_yaxes(categoryorder="array", categoryarray=cat_order_site)

                # ======================================
                # B) PERBANDINGAN PER PERUSAHAAN - SITE
                # ======================================
                ps_kgday_y = (
                    df_c.groupby(["Perusahaan", "Site", "Tahun"], as_index=False)["Timbulan"]
                    .sum().rename(columns={"Timbulan": "KGDAY"})
                )
                ps_mp_y = (
                    df_c[uniq_cols + ["Man Power"]]
                    .drop_duplicates(subset=uniq_cols, keep="last")
                    .groupby(["Perusahaan", "Site", "Tahun"], as_index=False)["Man Power"]
                    .sum().rename(columns={"Man Power": "MP"})
                )

                ps_comp = ps_kgday_y.merge(ps_mp_y, on=["Perusahaan", "Site", "Tahun"], how="left")
                ps_comp["MP"] = ps_comp["MP"].fillna(0)

                if has_totalcol:
                    ps_kg_y = (
                        df_c.groupby(["Perusahaan", "Site", "Tahun"], as_index=False)["data_input_total"]
                        .sum().rename(columns={"data_input_total": "KG"})
                    )
                    ps_comp = ps_comp.merge(ps_kg_y, on=["Perusahaan", "Site", "Tahun"], how="left")
                else:
                    ps_comp["KG"] = 0

                ps_comp["KGDAY_per_MP"] = np.where(ps_comp["MP"] > 0, ps_comp["KGDAY"] / ps_comp["MP"], 0)
                ps_comp["Value"] = ps_comp[value_kind]
                ps_comp["Perusahaan_Site"] = ps_comp["Perusahaan"].astype(str) + " - " + ps_comp["Site"].astype(str)

                cat_order_ps = (
                    ps_comp.groupby("Perusahaan_Site")["Value"].sum()
                    .sort_values(ascending=True)
                    .index.tolist()
                )

                fig_ps_cmp = go.Figure()
                for yr in years_target:
                    df_y = ps_comp[ps_comp["Tahun"] == yr].set_index("Perusahaan_Site").reindex(cat_order_ps).reset_index()
                    df_y["Value"] = df_y["Value"].fillna(0)

                    fig_ps_cmp.add_trace(go.Bar(
                        name=str(yr),
                        y=df_y["Perusahaan_Site"],
                        x=df_y["Value"],
                        orientation="h",
                        marker_color=year_colors.get(yr, "gray"),
                        text=[f"{v:,.{decimals}f}" for v in df_y["Value"]],
                        textposition="outside",
                        cliponaxis=False
                    ))

                fig_ps_cmp.update_layout(
                    barmode="group",
                    template="plotly_white",
                    height=520,
                    xaxis_title=x_title,
                    yaxis_title="Perusahaan - Site",
                    legend_title="Tahun",
                    margin=dict(t=40, b=40, l=140, r=20),
                )
                fig_ps_cmp.update_yaxes(categoryorder="array", categoryarray=cat_order_ps)

                # =========================
                # TAMPILKAN BERDAMPINGAN
                # =========================
                c1, c2 = st.columns([0.5, 0.5])

                with c1:
                    st.markdown('<p style="text-align:center;font-weight:bold;">📊 Perbandingan per Site (2024 vs 2025)</p>',
                                unsafe_allow_html=True)
                    st.plotly_chart(fig_site_cmp, use_container_width=True)

                with c2:
                    st.markdown('<p style="text-align:center;font-weight:bold;">📊 Perbandingan per Perusahaan - Site (2024 vs 2025)</p>',
                                unsafe_allow_html=True)
                    st.plotly_chart(fig_ps_cmp, use_container_width=True)


        # ======================================================
        # MODE 1 TAHUN -> tampilkan grafik lama (2 kolom) seperti yang sudah berhasil
        # ======================================================
        else:
            tahun_chart = int(tahun_pilihan_ui)
            df_y = df_base[df_base["Tahun"] == tahun_chart].copy()

            # ======================================================
            # 1) Manpower UNIK (anti double count)
            # ======================================================
            uniq_cols = ["Site", "Perusahaan", "Tahun"]
            mp_uniq = (
                df_y[uniq_cols + ["Man Power"]]
                .drop_duplicates(subset=uniq_cols, keep="last")
                .groupby(["Site"], as_index=False)["Man Power"].sum()
                .rename(columns={"Man Power": "MP_Site"})
            )

            mp_uniq_ps = (
                df_y[uniq_cols + ["Man Power"]]
                .drop_duplicates(subset=uniq_cols, keep="last")
                .groupby(["Perusahaan", "Site"], as_index=False)["Man Power"].sum()
                .rename(columns={"Man Power": "MP_PS"})
            )

            # ======================================================
            # 2) Agregasi metrik dasar
            # ======================================================
            site_kgday = df_y.groupby("Site", as_index=False)["Timbulan"].sum().rename(columns={"Timbulan": "KGDAY_Site"})
            ps_kgday = df_y.groupby(["Perusahaan", "Site"], as_index=False)["Timbulan"].sum().rename(columns={"Timbulan": "KGDAY_PS"})

            if has_totalcol:
                site_kg = df_y.groupby("Site", as_index=False)["data_input_total"].sum().rename(columns={"data_input_total": "KG_Site"})
                ps_kg = df_y.groupby(["Perusahaan", "Site"], as_index=False)["data_input_total"].sum().rename(columns={"data_input_total": "KG_PS"})
            else:
                site_kg = site_kgday[["Site"]].copy()
                site_kg["KG_Site"] = 0
                ps_kg = ps_kgday[["Perusahaan", "Site"]].copy()
                ps_kg["KG_PS"] = 0

            site_plot = site_kgday.merge(site_kg, on="Site", how="left").merge(mp_uniq, on="Site", how="left")
            site_plot["MP_Site"] = site_plot["MP_Site"].fillna(0)
            site_plot["KGDAY_per_MP"] = np.where(site_plot["MP_Site"] > 0, site_plot["KGDAY_Site"] / site_plot["MP_Site"], 0)

            ps_plot = ps_kgday.merge(ps_kg, on=["Perusahaan", "Site"], how="left").merge(mp_uniq_ps, on=["Perusahaan", "Site"], how="left")
            ps_plot["MP_PS"] = ps_plot["MP_PS"].fillna(0)
            ps_plot["Perusahaan_Site"] = ps_plot["Perusahaan"].astype(str) + " - " + ps_plot["Site"].astype(str)
            ps_plot["KGDAY_per_MP"] = np.where(ps_plot["MP_PS"] > 0, ps_plot["KGDAY_PS"] / ps_plot["MP_PS"], 0)

            # ======================================================
            # 3) Pilih Y sesuai metric_mode
            # ======================================================
            if metric_mode == "data_input_total (kg)":
                y_site = "KG_Site"
                y_ps = "KG_PS"
                y_title = "data_input_total (kg)"
                text_fmt = "%{text:,.0f}"
            elif metric_mode == "Timbulan (kg/hari)":
                y_site = "KGDAY_Site"
                y_ps = "KGDAY_PS"
                y_title = "Timbulan (kg/hari)"
                text_fmt = "%{text:,.2f}"
            else:
                y_site = "KGDAY_per_MP"
                y_ps = "KGDAY_per_MP"
                y_title = "kg/hari/manpower"
                text_fmt = "%{text:,.4f}"

            # ======================================================
            # 4) Plot dua grafik (versi lama kamu)
            # ======================================================
            c1, c2 = st.columns([0.5, 0.5])

            with c1:
                st.markdown(f'<p style="text-align:center;font-weight:bold;">📊 Per Site ({tahun_chart})</p>',
                            unsafe_allow_html=True)
                site_plot = site_plot.sort_values(y_site, ascending=False)

                fig_site = px.bar(
                    site_plot,
                    x="Site",
                    y=y_site,
                    text=y_site,
                    color=y_site,
                    labels={y_site: y_title},
                    template="plotly_white"
                )
                fig_site.update_traces(texttemplate=text_fmt, textposition="outside")
                fig_site.update_layout(height=420, margin=dict(t=40, b=90))
                st.plotly_chart(fig_site, use_container_width=True)

            with c2:
                st.markdown(f'<p style="text-align:center;font-weight:bold;">📊 Per Perusahaan - Site ({tahun_chart})</p>',
                            unsafe_allow_html=True)
                ps_plot = ps_plot.sort_values(y_ps, ascending=True)

                fig_ps = px.bar(
                    ps_plot,
                    y="Perusahaan_Site",
                    x=y_ps,
                    text=y_ps,
                    color=y_ps,
                    labels={y_ps: y_title, "Perusahaan_Site": "Perusahaan - Site"},
                    template="plotly_white",
                    orientation="h"
                )
                fig_ps.update_traces(texttemplate=text_fmt, textposition="outside")
                fig_ps.update_layout(height=420, margin=dict(t=40, b=40), yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig_ps, use_container_width=True)



# ===========================
# FILTER ORGANIK / ANORGANIK
# ===========================
st.markdown('<p style="text-align:center;font-weight: bold;">🗑️ Filter Jenis Sampah</p>', unsafe_allow_html=True)

jenis_pilihan = (
    df_timbulan_filtered["jenis_sampah"].dropna().unique().tolist()
    if "jenis_sampah" in df_timbulan_filtered.columns else []
)

cl1, cl2 = st.columns(2)
with cl1:
    pilih_organik = st.checkbox("Organik", value=True)
with cl2:
    pilih_anorganik = st.checkbox("Anorganik", value=True)

df_filterjensampah = df_timbulan_filtered[df_timbulan_filtered["jenis_sampah"].isin(jenis_pilihan)]

if pilih_organik and not pilih_anorganik:
    df_filterjensampah = df_timbulan_filtered[df_timbulan_filtered["jenis_sampah"] == "Organik"]
elif pilih_anorganik and not pilih_organik:
    df_filterjensampah = df_timbulan_filtered[df_timbulan_filtered["jenis_sampah"] == "Anorganik"]
elif not (pilih_organik or pilih_anorganik):
    df_filterjensampah = pd.DataFrame(columns=df_timbulan_filtered.columns)
else:
    df_filterjensampah = df_timbulan_filtered

if not df_timbulan_filtered.empty and "jenis_timbulan" in df_timbulan_filtered.columns:
    jenis_unique = df_timbulan_filtered["jenis_timbulan"].unique()
    colors = px.colors.sequential.Viridis[:len(jenis_unique)]
    color_map = {j: c for j, c in zip(jenis_unique, colors)}

    col1, col2 = st.columns([0.35, 0.65])

    # Pie Organik vs Anorganik
    with col1:
        st.markdown('<p style="text-align: left;font-weight: bold;">📊 Proporsi Sampah Organik vs Anorganik</p>',
                    unsafe_allow_html=True)
        proporsi = df_filterjensampah.groupby("jenis_sampah", as_index=False)["Timbulan"].sum()
        fig1 = px.pie(
            proporsi,
            names="jenis_sampah",
            values="Timbulan",
            hole=0.4,
            color="jenis_sampah",
            color_discrete_map={"Organik": "#1a5b1d", "Anorganik": "#d3d30e"}
        )
        fig1.update_traces(textinfo="percent+label", pull=[0.01] * len(proporsi))
        fig1.update_layout(showlegend=False)
        st.plotly_chart(fig1, use_container_width=True)

    # Bar per Perusahaan-Site (Organik/Anorganik)
    with col2:
        st.markdown('<p style="text-align: left;font-weight: bold;">📊 Proporsi Timbulan per Perusahaan - Site</p>',
                    unsafe_allow_html=True)
        if not df_filterjensampah.empty and "Perusahaan" in df_filterjensampah.columns:
            total_perusahaan = df_filterjensampah.groupby(
                ["Perusahaan", "Site", "jenis_sampah"], as_index=False
            )["Timbulan"].sum()
            total_perusahaan["Perusahaan_Site"] = total_perusahaan["Perusahaan"] + " - " + total_perusahaan["Site"]

            fig3 = px.bar(
                total_perusahaan,
                y="Perusahaan_Site",
                x="Timbulan",
                text="Timbulan",
                color="jenis_sampah",
                color_discrete_map={"Organik": "#1a5b1d", "Anorganik": "#d3d30e"},
                labels={"Timbulan": "Total Timbulan (kg)", "Perusahaan_Site": "Perusahaan - Site"},
                template="plotly_white",
                orientation="h"
            )
            fig3.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
            fig3.update_layout(
                height=500, width=800,
                margin=dict(t=50, b=50),
                xaxis_title="Total Timbulan (kg)",
                yaxis_title="Perusahaan - Site",
                barmode="stack",
                bargap=0.2,
                legend=dict(
                    orientation="h", font=dict(size=8),
                    yanchor="top", y=1.2,
                    x=0.2, xanchor="center",
                    traceorder="normal", valign="top"
                )
            )
            st.plotly_chart(fig3, use_container_width=True)

    # Detail jenis timbulan
    col1, col2 = st.columns([0.4, 0.6])
    with col1:
        st.markdown('<p style="text-align: left;font-weight: bold;">🔎 Proporsi Detail per Jenis Timbulan</p>',
                    unsafe_allow_html=True)
        jenis_detail = df_filterjensampah.groupby("jenis_timbulan", as_index=False)["Timbulan"].sum()
        fig2 = px.pie(
            jenis_detail,
            names="jenis_timbulan",
            values="Timbulan",
            color="jenis_timbulan",
            hole=0.3,
            color_discrete_sequence=px.colors.sequential.Viridis
        )
        fig2.update_traces(textinfo="percent+label", pull=[0.01] * len(jenis_detail))
        fig2.update_layout(showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    with col2:
        st.markdown('<p style="text-align: left;font-weight: bold;">📊 Proporsi Detail Timbulan per Perusahaan - Site</p>',
                    unsafe_allow_html=True)
        if not df_filterjensampah.empty and "Perusahaan" in df_filterjensampah.columns:
            total_perusahaan_detail = df_filterjensampah.groupby(
                ["Perusahaan", "Site", "jenis_timbulan"], as_index=False
            )["Timbulan"].sum()
            total_perusahaan_detail["Perusahaan_Site"] = (
                total_perusahaan_detail["Perusahaan"] + " - " + total_perusahaan_detail["Site"]
            )

            fig4 = px.bar(
                total_perusahaan_detail,
                x="Perusahaan_Site",
                y="Timbulan",
                text="Timbulan",
                color="jenis_timbulan",
                color_discrete_map=color_map,
                labels={
                    "Timbulan": "Total Timbulan (kg)",
                    "Perusahaan_Site": "Perusahaan - Site",
                    "jenis_timbulan": "Jenis Timbulan"
                },
                template="plotly_white"
            )
            fig4.update_traces(texttemplate="%{text:,.0f}", textposition="inside")
            y_max = total_perusahaan_detail["Timbulan"].max()
            y_dtick = max(int(y_max / 5), 1)
            fig4.update_layout(
                height=500, width=800,
                barmode="stack",
                margin=dict(t=30, b=50, l=100, r=20),
                yaxis=dict(tickmode="linear", dtick=y_dtick),
                xaxis=dict(tickangle=-45, tickfont=dict(size=8)),
                bargap=0.2,
                legend=dict(
                    orientation="h", font=dict(size=8),
                    yanchor="top", y=1.2,
                    x=0.8, xanchor="center",
                    traceorder="normal", valign="top"
                )
            )
            st.plotly_chart(fig4, use_container_width=True)

st.markdown("### 📈 Tren Timbulan per Jenis Timbulan (Tahunan)")

df_tren = df_filterjensampah.copy()

if "Tahun" not in df_tren.columns:
    st.warning("Kolom 'Tahun' tidak ditemukan di data timbulan, jadi tren tahunan tidak bisa dibuat.")
else:
    df_tren["Timbulan"] = pd.to_numeric(df_tren["Timbulan"], errors="coerce").fillna(0)

    # pilih semua jenis by default
    jenis_opsi = sorted(df_tren["jenis_timbulan"].dropna().unique().tolist())
    jenis_pilih = st.multiselect(
        "Pilih jenis timbulan yang ditampilkan",
        options=jenis_opsi,
        default=jenis_opsi
    )

    df_tren = df_tren[df_tren["jenis_timbulan"].isin(jenis_pilih)]

    tren_agg = (
        df_tren.groupby(["Tahun", "jenis_timbulan"], as_index=False)["Timbulan"]
        .sum()
        .sort_values("Tahun")
    )

    fig_tren = px.line(
        tren_agg,
        x="Tahun",
        y="Timbulan",
        color="jenis_timbulan",
        markers=True,
        template="plotly_white",
        labels={"Tahun": "Tahun", "Timbulan": "Total Timbulan (kg)"}
    )
    fig_tren.update_layout(
        height=450,
        legend=dict(orientation="h", y=1.15, x=0)
    )
    st.plotly_chart(fig_tren, use_container_width=True)

# ======================================================
# 📊 TIMBULAN BERDASARKAN JENIS TIMBULAN (ALL vs per Tahun)
# ======================================================
st.markdown("## 📊 Timbulan Berdasarkan Jenis Timbulan")

needed_cols = {"jenis_timbulan", "Timbulan", "Man Power", "Tahun", "Site", "Perusahaan"}
if df_timbulan_filtered.empty or not needed_cols.issubset(df_timbulan_filtered.columns):
    st.warning(
        "Data belum lengkap untuk grafik jenis timbulan.\n"
        "Kolom wajib: jenis_timbulan, Timbulan (kg/hari), Man Power, Tahun, Site, Perusahaan."
    )
else:
    import numpy as np

    metric_mode = st.radio(
        "Pilih metrik:",
        ["Timbulan (kg/hari)", "Timbulan (kg/hari/orang)"],
        horizontal=True,
        key="jenis_metric_v2"
    )

    dfj = df_timbulan_filtered.copy()
    dfj["Tahun"] = pd.to_numeric(dfj["Tahun"], errors="coerce").astype("Int64")
    dfj["Timbulan"] = pd.to_numeric(dfj["Timbulan"], errors="coerce").fillna(0)
    dfj["Man Power"] = pd.to_numeric(dfj["Man Power"], errors="coerce").fillna(0)

    tahun_opsi = sorted([int(x) for x in dfj["Tahun"].dropna().unique().tolist()])
    tahun_pilih = st.selectbox(
        "Pilih Tahun:",
        ["All"] + tahun_opsi,
        key="jenis_tahun_v2"
    )

    # -----------------------------------------
    # Helper: hitung agregat per Tahun x Jenis
    # -----------------------------------------
    def build_jenis_by_year(dfin: pd.DataFrame) -> pd.DataFrame:
        # manpower unik: Site-Perusahaan-Tahun (agar tidak double count)
        mp_uniq = (
            dfin[["Site", "Perusahaan", "Tahun", "Man Power"]]
            .drop_duplicates(subset=["Site", "Perusahaan", "Tahun"], keep="last")
            .groupby("Tahun", as_index=False)["Man Power"].sum()
            .rename(columns={"Man Power": "MP_Tahun"})
        )

        jenis_kgday = (
            dfin.groupby(["Tahun", "jenis_timbulan"], as_index=False)["Timbulan"]
            .sum()
            .rename(columns={"Timbulan": "KGDAY"})
        )

        out = jenis_kgday.merge(mp_uniq, on="Tahun", how="left")
        out["MP_Tahun"] = out["MP_Tahun"].fillna(0)
        out["KGDAY_per_MP"] = np.where(out["MP_Tahun"] > 0, out["KGDAY"] / out["MP_Tahun"], 0)
        return out

    # -----------------------------------------
    # Data sesuai pilihan tahun
    # -----------------------------------------
    if tahun_pilih != "All":
        df_plot = dfj[dfj["Tahun"] == int(tahun_pilih)].copy()
        agg = build_jenis_by_year(df_plot)
        agg = agg[agg["Tahun"] == int(tahun_pilih)].copy()
    else:
        agg = build_jenis_by_year(dfj)

    # pilih metrik
    if metric_mode == "Timbulan (kg/hari)":
        ycol = "KGDAY"
        ylab = "Timbulan (kg/hari)"
        tfmt = "%{text:,.2f}"
    else:
        ycol = "KGDAY_per_MP"
        ylab = "Timbulan (kg/hari/orang)"
        tfmt = "%{text:,.4f}"

    # urutan jenis konsisten
    order_jenis = (
        agg.groupby("jenis_timbulan")[ycol].sum()
        .sort_values(ascending=False)
        .index.tolist()
    )

    # -----------------------------------------
    # Plot
    # - jika All: grouped bar 2024 vs 2025
    # -----------------------------------------
    if tahun_pilih == "All":
        # Warna fixed
        color_map_year = {2024: "#E74C3C", 2025: "#2ECC71"}  # merah, hijau

        # Pastikan cuma tahun yang ada
        tahun_ada = sorted([int(x) for x in agg["Tahun"].dropna().unique().tolist()])
        agg_all = agg[agg["Tahun"].isin(tahun_ada)].copy()

        # Urutan jenis (besar di atas/bawah sesuai kebutuhan)
        order_jenis_h = (
            agg_all.groupby("jenis_timbulan")[ycol].sum()
            .sort_values(ascending=True)   # yg besar di bawah (enak untuk horizontal)
            .index.tolist()
        )

        fig = px.bar(
            agg_all,
            y="jenis_timbulan",
            x=ycol,
            color="Tahun",
            barmode="group",
            orientation="h",
            category_orders={"jenis_timbulan": order_jenis_h},
            labels={ycol: ylab, "jenis_timbulan": "Jenis Timbulan"},
            template="plotly_white",
            color_discrete_map=color_map_year
        )

        # Label angka di ujung bar
        fig.update_traces(
            text=agg_all[ycol],
            texttemplate=tfmt,
            textposition="outside",
            cliponaxis=False
        )

        # Supaya angka tidak kepotong
        mx = float(agg_all[ycol].max()) if len(agg_all) else 0
        fig.update_xaxes(range=[0, mx * 1.25] if mx > 0 else None)

        fig.update_layout(
            title="Perbandingan 2024 vs 2025 (All)",
            height=520,
            margin=dict(t=60, b=40, l=170, r=80),
            legend=dict(orientation="h", y=1.12, x=0),
            yaxis=dict(autorange="reversed")
        )

        st.plotly_chart(fig, use_container_width=True)



    else:
        # Single year
        agg = agg.sort_values(ycol, ascending=False)

        fig = px.bar(
            agg,
            x="jenis_timbulan",
            y=ycol,
            text=ycol,
            color=ycol,
            category_orders={"jenis_timbulan": order_jenis},
            labels={ycol: ylab, "jenis_timbulan": "Jenis Timbulan"},
            template="plotly_white"
        )
        fig.update_traces(texttemplate=tfmt, textposition="outside", cliponaxis=False)
        fig.update_layout(height=520, margin=dict(t=40, b=120))
        fig.update_xaxes(tickangle=-30)

        st.plotly_chart(fig, use_container_width=True)

    with st.expander("🔍 Audit perhitungan (Jenis x Tahun)"):
        st.dataframe(
            agg[["Tahun", "jenis_timbulan", "KGDAY", "MP_Tahun", "KGDAY_per_MP"]],
            hide_index=True,
            use_container_width=True
        )

# ======================================================
# 🧩 JENIS TIMBULAN per PERUSAHAAN–SITE (All / per PS) + Tahun (All / per Tahun)
# ======================================================
st.markdown("## 🧩 Jenis Timbulan per Perusahaan – Site")

needed_cols2 = {"jenis_timbulan", "Timbulan", "Man Power", "Tahun", "Site", "Perusahaan"}
if df_timbulan_filtered.empty or not needed_cols2.issubset(df_timbulan_filtered.columns):
    st.warning("Kolom belum lengkap untuk analisis Perusahaan–Site.")
else:
    import numpy as np

    dfps = df_timbulan_filtered.copy()
    dfps["Tahun"] = pd.to_numeric(dfps["Tahun"], errors="coerce").astype("Int64")
    dfps["Timbulan"] = pd.to_numeric(dfps["Timbulan"], errors="coerce").fillna(0)
    dfps["Man Power"] = pd.to_numeric(dfps["Man Power"], errors="coerce").fillna(0)
    dfps["Perusahaan_Site"] = dfps["Perusahaan"].astype(str) + " - " + dfps["Site"].astype(str)

    metric_mode_ps = st.radio(
        "Metrik:",
        ["Timbulan (kg/hari)", "Timbulan (kg/hari/orang)"],
        horizontal=True,
        key="ps_metric"
    )

    tahun_opsi_ps = sorted([int(x) for x in dfps["Tahun"].dropna().unique().tolist()])
    tahun_ps = st.selectbox("Tahun:", ["All"] + tahun_opsi_ps, key="ps_year")

    ps_list = sorted(dfps["Perusahaan_Site"].dropna().unique().tolist())
    ps_pick = st.selectbox("Perusahaan–Site:", ["All"] + ps_list, key="ps_pick")

    # -------- helper: agregasi per PS x Tahun x Jenis ----------
    def build_ps_agg(dfin: pd.DataFrame) -> pd.DataFrame:
        # manpower unik per Perusahaan-Site-Tahun (penting!)
        mp_uniq = (
            dfin[["Perusahaan_Site", "Site", "Perusahaan", "Tahun", "Man Power"]]
            .drop_duplicates(subset=["Perusahaan_Site", "Tahun"], keep="last")
            .groupby(["Perusahaan_Site", "Tahun"], as_index=False)["Man Power"].sum()
            .rename(columns={"Man Power": "MP_PS"})
        )

        kgday = (
            dfin.groupby(["Perusahaan_Site", "Tahun", "jenis_timbulan"], as_index=False)["Timbulan"]
            .sum()
            .rename(columns={"Timbulan": "KGDAY"})
        )

        out = kgday.merge(mp_uniq, on=["Perusahaan_Site", "Tahun"], how="left")
        out["MP_PS"] = out["MP_PS"].fillna(0)
        out["KGDAY_per_MP"] = np.where(out["MP_PS"] > 0, out["KGDAY"] / out["MP_PS"], 0)
        return out

    base = dfps.copy()
    if tahun_ps != "All":
        base = base[base["Tahun"] == int(tahun_ps)]
    if ps_pick != "All":
        base = base[base["Perusahaan_Site"] == ps_pick]

    agg_ps = build_ps_agg(base)

    # pilih metrik
    if metric_mode_ps == "Timbulan (kg/hari)":
        vcol = "KGDAY"
        vlab = "Timbulan (kg/hari)"
        tfmt = "%{z:,.2f}"
        barfmt = "%{text:,.2f}"
    else:
        vcol = "KGDAY_per_MP"
        vlab = "Timbulan (kg/hari/orang)"
        tfmt = "%{z:,.4f}"
        barfmt = "%{text:,.4f}"

    # -----------------------------------------
    # MODE 1: All perusahaan-site -> Heatmap
    # -----------------------------------------
    if ps_pick == "All":
        # Karena dimensinya 3 (PS x Tahun x Jenis),
        # agar grafik seperti contoh (rapih & kebaca), kita pilih 1 jenis timbulan dulu.
        jenis_opsi = sorted(dfps["jenis_timbulan"].dropna().unique().tolist())
        jenis_focus = st.selectbox(
            "Pilih Jenis Timbulan (untuk mode All Perusahaan–Site):",
            options=jenis_opsi,
            index=0,
            key="ps_all_jenis_focus"
        )

        tmp = agg_ps[agg_ps["jenis_timbulan"] == jenis_focus].copy()

        # Kalau user pilih Tahun tertentu
        if tahun_ps != "All":
            yy = int(tahun_ps)
            tmp = tmp[tmp["Tahun"] == yy].copy()

            tmp = tmp.groupby("Perusahaan_Site", as_index=False)[vcol].sum()
            tmp = tmp.sort_values(vcol, ascending=True)

            fig = px.bar(
                tmp,
                y="Perusahaan_Site",
                x=vcol,
                orientation="h",
                text=vcol,
                labels={vcol: vlab, "Perusahaan_Site": "Perusahaan - Site"},
                template="plotly_white"
            )
            fig.update_traces(texttemplate=barfmt, textposition="outside", cliponaxis=False)

            mx = float(tmp[vcol].max()) if len(tmp) else 0
            fig.update_xaxes(range=[0, mx * 1.25] if mx > 0 else None)

            fig.update_layout(
                title=f"{jenis_focus} — Perusahaan–Site (Tahun {yy})",
                height=520,
                margin=dict(t=60, b=40, l=170, r=80),
                yaxis=dict(autorange="reversed")
            )
            st.plotly_chart(fig, use_container_width=True)

        # Kalau Tahun = All (bandingkan 2024 vs 2025) → seperti contoh kamu
        else:
            color_map_year = {2024: "#E74C3C", 2025: "#2ECC71"}  # merah, hijau

            # Agregasi: total per PS per Tahun untuk jenis terpilih
            tmp = (
                tmp.groupby(["Perusahaan_Site", "Tahun"], as_index=False)[vcol]
                .sum()
            )

            # Urut PS berdasarkan total (biar rapih)
            order_ps = (
                tmp.groupby("Perusahaan_Site")[vcol].sum()
                .sort_values(ascending=True)
                .index.tolist()
            )

            fig = px.bar(
                tmp,
                y="Perusahaan_Site",
                x=vcol,
                color="Tahun",
                barmode="group",
                orientation="h",
                category_orders={"Perusahaan_Site": order_ps},
                labels={vcol: vlab, "Perusahaan_Site": "Perusahaan - Site"},
                template="plotly_white",
                color_discrete_map=color_map_year
            )

            fig.update_traces(
                text=tmp[vcol],
                texttemplate=barfmt,
                textposition="outside",
                cliponaxis=False
            )

            mx = float(tmp[vcol].max()) if len(tmp) else 0
            fig.update_xaxes(range=[0, mx * 1.25] if mx > 0 else None)

            fig.update_layout(
                title=f"{jenis_focus} — Perbandingan 2024 vs 2025 (All Perusahaan–Site)",
                height=560,
                margin=dict(t=60, b=40, l=170, r=80),
                legend=dict(orientation="h", y=1.12, x=0),
                yaxis=dict(autorange="reversed")
            )

            st.plotly_chart(fig, use_container_width=True)


    # -----------------------------------------
    # MODE 2: satu perusahaan-site -> Bar detail
    # -----------------------------------------
    else:
        # jika tahun All -> grouped per tahun (2024 merah, 2025 hijau)
        if tahun_ps == "All":
            color_map_year = {2024: "red", 2025: "green"}
            # urut jenis
            order_jenis = (
                agg_ps.groupby("jenis_timbulan")[vcol].sum()
                .sort_values(ascending=False).index.tolist()
            )

            fig = px.bar(
                agg_ps,
                x="jenis_timbulan",
                y=vcol,
                color="Tahun",
                barmode="group",
                category_orders={"jenis_timbulan": order_jenis},
                template="plotly_white",
                color_discrete_map=color_map_year,
                labels={vcol: vlab, "jenis_timbulan": "Jenis Timbulan"}
            )
            fig.update_traces(text=agg_ps[vcol], texttemplate=barfmt, textposition="outside", cliponaxis=False)
            fig.update_layout(
                title=f"{ps_pick} — Perbandingan 2024 vs 2025",
                height=520, margin=dict(t=60, b=120),
                legend=dict(orientation="h", y=1.12, x=0)
            )
            fig.update_xaxes(tickangle=-30)
            st.plotly_chart(fig, use_container_width=True)

        else:
            tmp = agg_ps.copy()
            tmp = tmp.sort_values(vcol, ascending=False)

            fig = px.bar(
                tmp,
                x="jenis_timbulan",
                y=vcol,
                text=vcol,
                color=vcol,
                template="plotly_white",
                labels={vcol: vlab, "jenis_timbulan": "Jenis Timbulan"}
            )
            fig.update_traces(texttemplate=barfmt, textposition="outside", cliponaxis=False)
            fig.update_layout(
                title=f"{ps_pick} — Tahun {tahun_ps}",
                height=520, margin=dict(t=60, b=120)
            )
            fig.update_xaxes(tickangle=-30)
            st.plotly_chart(fig, use_container_width=True)

    with st.expander("🔍 Audit perhitungan (Perusahaan–Site x Tahun x Jenis)"):
        st.dataframe(
            agg_ps[["Perusahaan_Site", "Tahun", "jenis_timbulan", "KGDAY", "MP_PS", "KGDAY_per_MP"]],
            hide_index=True,
            use_container_width=True
        )


# ===========================
# RASIO TIMBULAN vs MANPOWER
# ===========================
if not df_timbulan_filtered.empty:
    manpower_unique = df_timbulan_filtered[["Site", "Perusahaan", "Man Power"]].drop_duplicates()
    timbulan_agg = manpower_unique.groupby(["Site", "Perusahaan"], as_index=False)["Man Power"].sum()
    timbulan_site_perusahaan = df_timbulan_filtered.groupby(
        ["Site", "Perusahaan"], as_index=False
    )["Timbulan"].sum()

    df_agg = timbulan_site_perusahaan.merge(
        timbulan_agg, on=["Perusahaan", "Site"], how="left"
    )
    df_agg["Rasio_Timbulan"] = df_agg["Timbulan"] / df_agg["Man Power"]

    mean_ratio = df_agg["Rasio_Timbulan"].mean()
    std_ratio = df_agg["Rasio_Timbulan"].std()
    df_agg["Zscore"] = (df_agg["Rasio_Timbulan"] - mean_ratio) / std_ratio

    def kategori_iqr(r):
        Q1 = df_agg["Rasio_Timbulan"].quantile(0.25)
        Q3 = df_agg["Rasio_Timbulan"].quantile(0.75)
        IQR = Q3 - Q1
        if r <= Q3:
            return "Normal"
        elif Q1 - 1.5 * IQR <= r < Q1 or Q3 < r <= Q3 + 1.5 * IQR:
            return "Siaga"
        else:
            return "Tidak Normal"

    df_agg["Kategori"] = df_agg["Rasio_Timbulan"].apply(kategori_iqr)
    df_agg["Perusahaan_Site"] = df_agg["Perusahaan"] + " - " + df_agg["Site"]

    color_map_ratio = {
        "Normal": "#1a9850",
        "Siaga": "#fee08b",
        "Tidak Normal": "#d73027"
    }

    Q1 = df_agg["Rasio_Timbulan"].quantile(0.25)
    Q3 = df_agg["Rasio_Timbulan"].quantile(0.75)
    IQR = Q3 - Q1

    col1, col2 = st.columns([0.65, 0.35])
    with col1:
        st.markdown('<p style="text-align: left;font-weight: bold;">⚖️ Rasio Timbulan/Manpower</p>',
                    unsafe_allow_html=True)
        fig = px.bar(
            df_agg,
            x="Perusahaan_Site",
            y="Rasio_Timbulan",
            color="Kategori",
            color_discrete_map=color_map_ratio,
            text=df_agg["Rasio_Timbulan"].round(2),
            labels={"Rasio_Timbulan": "Rasio Timbulan per Manpower (kg/orang)"},
            template="plotly_white"
        )
        fig.add_hline(y=Q1, line_dash="dot", line_color="green",
                      annotation_text=f"Q1 = {Q1:.2f}", annotation_position="bottom left")
        fig.add_hline(y=Q3, line_dash="dot", line_color="green",
                      annotation_text=f"Q3 = {Q3:.2f}", annotation_position="top left")
        fig.add_hline(y=Q3 + 1.5 * IQR, line_dash="dash", line_color="orange",
                      annotation_text=f"Batas Siaga = {Q3 + 1.5 * IQR:.2f}", annotation_position="top right")

        fig.update_traces(textposition="outside")
        fig.update_layout(
            xaxis=dict(tickangle=-30),
            margin=dict(t=40, b=120, l=50, r=50),
            legend=dict(orientation="h", y=-0.3, x=0.5, xanchor="center")
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown('<p style="text-align: left;font-weight: bold;">📦 Distribusi Z-score Rasio Timbulan/Manpower</p>',
                    unsafe_allow_html=True)
        fig_box = px.box(
            df_agg,
            y="Zscore",
            points="all",
            hover_data=["Perusahaan_Site", "Rasio_Timbulan"],
            labels={"Zscore": "Z-score Rasio Timbulan"},
            template="plotly_white"
        )
        fig_box.update_traces(
            jitter=0.3,
            marker=dict(size=8, color="darkblue", line=dict(width=1, color="white"))
        )
        fig_box.update_layout(
            margin=dict(t=40, b=40, l=50, r=50),
            yaxis=dict(zeroline=True, zerolinewidth=2, zerolinecolor="red")
        )
        st.plotly_chart(fig_box, use_container_width=True)

    with st.expander("Detail Data Rasio Timbulan per Manpower"):
        st.dataframe(df_agg[["Perusahaan_Site", "Timbulan", "Man Power",
                             "Rasio_Timbulan", "Zscore", "Kategori"]])

# ===========================
# VOLUME vs KAPASITAS & CCTV
# ===========================
df_filtered = df_filterjensampah.copy()

rho_map = {
    "Kardus": 0.02,
    "Botol Plastik": 0.01,
    "Organik Lainnya": 0.12,
    "Lainnya": 0.01,
    "Sisa Makanan & Sayur": 0.12,
    "Kertas": 0.02,
    "Plastik": 0.01,
    "Organik": 0.12
}

if not df_filtered.empty:
    df_filtered["rho"] = df_filtered["jenis_timbulan"].map(rho_map)
    df_filtered["Timbulan_Volume"] = df_filtered["Timbulan"] / df_filtered["rho"]

    organik_list = ["Organik", "Organik Lainnya", "Sisa Makanan & Sayur"]
    anorganik_list = ["Kardus", "Botol Plastik", "Plastik", "Kertas", "Lainnya"]

    df_grouped = df_filtered.groupby(
        ["Site", "Perusahaan", "jenis_timbulan", "jenis_sampah", "Kapasitas", "Kapasitas.1"],
        as_index=False
    ).agg({"Timbulan_Volume": "sum"})

    df_grouped["Timbulan_Organik_Volume"] = np.where(
        df_grouped["jenis_timbulan"].isin(organik_list),
        df_grouped["Timbulan_Volume"], 0
    )
    df_grouped["Timbulan_Anorganik_Volume"] = np.where(
        df_grouped["jenis_timbulan"].isin(anorganik_list),
        df_grouped["Timbulan_Volume"], 0
    )

    df_pivot = df_grouped.groupby(["Site", "Perusahaan"], as_index=False).agg({
        "Timbulan_Organik_Volume": "sum",
        "Timbulan_Anorganik_Volume": "sum",
        "Kapasitas": "max",
        "Kapasitas.1": "max"
    }).rename(columns={"Kapasitas": "Kapasitas_Organik", "Kapasitas.1": "Kapasitas_Anorganik"})

    def kategori_icon(timbulan, kapasitas):
        if kapasitas == 0 or pd.isna(kapasitas):
            return "❓"
        if timbulan < 0.7 * kapasitas:
            return "✅"
        elif timbulan <= kapasitas:
            return "⚠️"
        else:
            return "❌"

    df_pivot["Status_Organik"] = df_pivot.apply(
        lambda r: kategori_icon(r["Timbulan_Organik_Volume"], r["Kapasitas_Organik"]), axis=1
    )
    df_pivot["Status_Anorganik"] = df_pivot.apply(
        lambda r: kategori_icon(r["Timbulan_Anorganik_Volume"], r["Kapasitas_Anorganik"]), axis=1
    )

    text_organik = df_pivot["Timbulan_Organik_Volume"].round(1).astype(str) + " L | " + df_pivot["Status_Organik"]
    text_anorganik = df_pivot["Timbulan_Anorganik_Volume"].round(1).astype(str) + " L | " + df_pivot["Status_Anorganik"]

    df_pivot["Perusahaan_Site"] = df_pivot["Perusahaan"] + "-" + df_pivot["Site"]
    perusahaan_list = df_pivot["Perusahaan_Site"]

    col1, col2 = st.columns([0.65, 0.35])
    with col1:
        st.markdown('<p style="text-align: left;font-weight: bold;">⚖️ Timbulan vs Kapasitas Tempat Sampah</p>',
                    unsafe_allow_html=True)
        color_map_vs = {"Organik": "#1a5b1d", "Anorganik": "#d3d30e"}

        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=perusahaan_list,
            x=df_pivot["Kapasitas_Anorganik"],
            name="Kapasitas Anorganik",
            orientation="h",
            marker_color=color_map_vs["Anorganik"],
            opacity=0.2,
            text=text_anorganik,
            textposition="outside",
            width=0.4,
            offset=-0.2
        ))
        fig.add_trace(go.Bar(
            y=perusahaan_list,
            x=df_pivot["Kapasitas_Organik"],
            name="Kapasitas Organik",
            orientation="h",
            marker_color=color_map_vs["Organik"],
            opacity=0.2,
            text=text_organik,
            textposition="outside",
            width=0.4,
            offset=0.2
        ))
        fig.add_trace(go.Bar(
            y=perusahaan_list,
            x=df_pivot["Timbulan_Anorganik_Volume"],
            name="Timbulan Anorganik",
            orientation="h",
            marker_color=color_map_vs["Anorganik"],
            width=0.4,
            offset=-0.2
        ))
        fig.add_trace(go.Bar(
            y=perusahaan_list,
            x=df_pivot["Timbulan_Organik_Volume"],
            name="Timbulan Organik",
            orientation="h",
            marker_color=color_map_vs["Organik"],
            width=0.4,
            offset=0.2
        ))

        fig.update_layout(
            barmode="overlay",
            xaxis_title="Volume Timbulan / Kapasitas (liter)",
            yaxis_title="Perusahaan-Site (dengan Status)",
            legend_title="Jenis / Kategori",
            yaxis=dict(autorange="reversed"),
            legend=dict(
                orientation="h",
                font=dict(size=9),
                yanchor="top",
                y=1.2,
                x=0.2,
                xanchor="center",
                traceorder="normal"
            )
        )
        st.plotly_chart(fig, use_container_width=True)

    # ----- CCTV per Perusahaan-Site -----
    if not df_cctv.empty and {"Site", "Perusahaan", "Coverage 24jam",
                              "Coverage non 24jam", "Tidak tercover", "Total CCTV"}.issubset(df_cctv.columns):
        df_cctv_filtered = df_cctv.copy()
        if site_sel:
            df_cctv_filtered = df_cctv_filtered[df_cctv_filtered["Site"].isin(site_sel)]
        if perusahaan_sel:
            df_cctv_filtered = df_cctv_filtered[df_cctv_filtered["Perusahaan"].isin(perusahaan_sel)]

        df_cctv_filtered["Perusahaan_Site"] = df_cctv_filtered["Perusahaan"] + "-" + df_cctv_filtered["Site"]

        with col2:
            st.markdown('<p style="text-align: left;font-weight: bold;">📊 Visualisasi CCTV per Perusahaan-Site</p>',
                        unsafe_allow_html=True)
            fig_c = go.Figure()
            for _, row in df_cctv_filtered.iterrows():
                fig_c.add_trace(go.Bar(
                    x=[row["Coverage 24jam"], row["Coverage non 24jam"], row["Tidak tercover"]],
                    y=[row["Perusahaan_Site"], row["Perusahaan_Site"], row["Perusahaan_Site"]],
                    orientation="h",
                    text=[row["Coverage 24jam"], row["Coverage non 24jam"], row["Tidak tercover"]],
                    showlegend=False,
                    marker=dict(color=["#1a9850", "#fee08b", "#d73027"])
                ))

            fig_c.update_layout(
                barmode="stack",
                xaxis_title="Jumlah CCTV",
                yaxis_title="Perusahaan-Site",
                showlegend=False
            )
            st.plotly_chart(fig_c, use_container_width=True)

    with st.expander("Detail Timbulan & Kapasitas per Perusahaan-Site"):
        st.dataframe(df_pivot)
