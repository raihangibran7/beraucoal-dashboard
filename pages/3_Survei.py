# pages/3_Survei.py
import math
import io, base64

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import plotly.subplots as sp

from wordcloud import WordCloud
from sklearn.feature_extraction.text import CountVectorizer

st.title("📝 Survei GBST (Offline & Online)")

# ===============================
# UTILITIES
# ===============================
def norm_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = df.columns.astype(str).str.strip().str.replace(" ", "_").str.lower()
    return df

STOPWORDS_ID = {
    "yang","yg","dan","dengan","untuk","atau","serta","pada","dari","di","ke",
    "agar","karena","juga","adalah","akan","dalam","itu","sudah","belum",
    "sebagai","oleh","tidak","ada","ya","saya","kami","kita"
}

def show_wordcloud(texts: pd.Series, title: str, cmap: str = "viridis"):
    if texts is None or texts.empty or texts.isna().all():
        st.warning(f"Tidak ada jawaban untuk: {title}")
        return
    all_text = " ".join(texts.astype(str)).lower().strip()
    if not all_text:
        st.warning(f"Tidak ada kata yang bisa ditampilkan untuk: {title}")
        return
    try:
        wc = WordCloud(
            width=800, height=400,
            background_color="white",
            colormap=cmap,
            stopwords=STOPWORDS_ID
        ).generate(all_text)
    except ValueError:
        st.warning(f"⚠️ WordCloud gagal dibuat: {title}")
        return

    buf = io.BytesIO()
    wc.to_image().save(buf, format="PNG")
    img_b64 = base64.b64encode(buf.getvalue()).decode()

    st.subheader(title)
    st.markdown(f'<img src="data:image/png;base64,{img_b64}" width="100%">', unsafe_allow_html=True)

def get_top_phrases(texts: pd.Series, ngram_range=(2,2), top_n=10) -> pd.DataFrame:
    if texts is None:
        return pd.DataFrame(columns=["Frasa", "Frekuensi"])
    texts = texts.dropna().astype(str)
    if texts.empty:
        return pd.DataFrame(columns=["Frasa", "Frekuensi"])
    try:
        vec = CountVectorizer(ngram_range=ngram_range, stop_words=list(STOPWORDS_ID)).fit(texts)
        bag = vec.transform(texts)
        sum_words = bag.sum(axis=0)
        words_freq = [(word, sum_words[0, idx]) for word, idx in vec.vocabulary_.items()]
        sorted_words = sorted(words_freq, key=lambda x: x[1], reverse=True)
        return pd.DataFrame(sorted_words[:top_n], columns=["Frasa", "Frekuensi"])
    except ValueError:
        return pd.DataFrame(columns=["Frasa", "Frekuensi"])

def make_insight(bi: pd.DataFrame, tri: pd.DataFrame) -> str:
    insights = []
    if not bi.empty:
        insights.append(f"Responden banyak menyinggung **'{bi.iloc[0]['Frasa']}'**.")
    if not tri.empty:
        insights.append(f"Selain itu, frasa **'{tri.iloc[0]['Frasa']}'** juga cukup dominan.")
    return " ".join(insights) if insights else "Tidak ada pola dominan yang muncul."

def gauge_figure(value: float, title: str, color_bar: str = "teal", w=350, h=320):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=float(value),
        title={"text": title},
        gauge={
            "axis": {"range": [1, 5]},
            "bar": {"color": color_bar},
            "steps": [
                {"range": [1,2], "color": "#ff9999"},
                {"range": [2,3], "color": "#ffcc99"},
                {"range": [3,4], "color": "#99ff99"},
                {"range": [4,5], "color": "#66ccff"},
            ],
        },
    ))
    fig.update_layout(height=h, width=w, margin=dict(t=80, r=40, b=40, l=40), showlegend=False)
    return fig

# ===============================
# LOAD DATA GOOGLE SHEETS
# ===============================
sheet_url = "https://docs.google.com/spreadsheets/d/1cw3xMomuMOaprs8mkmj_qnib-Zp_9n68rYMgiRZZqBE/edit?usp=sharing"
sheet_id = sheet_url.split("/")[5]
sheet_names = ["Survei_Online", "Survei_Offline"]

all_df = {}
for sheet in sheet_names:
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet}"
        df = pd.read_csv(url)
        all_df[sheet] = df
    except Exception as e:
        st.warning(f"Gagal load sheet {sheet}: {e}")
        all_df[sheet] = pd.DataFrame()

df_online = norm_cols(all_df.get("Survei_Online", pd.DataFrame()).copy())
df_offline = norm_cols(all_df.get("Survei_Offline", pd.DataFrame()).copy())

# ===============================
# PILIH TAB
# ===============================
tab_choice = st.radio("Pilih Survei:", ["📋 Survei Offline", "🌐 Survei Online"], key="tab_choice", horizontal=True)

# ===============================
# FUNCTION ANALISIS
# ===============================
def analisis_survei(df: pd.DataFrame, label: str, key_prefix: str):
    if df.empty:
        st.warning(f"Tidak ada data untuk {label}")
        return

    st.subheader(f"Hasil {label}")
    st.dataframe(df, use_container_width=True)

    id_cols = [
        "kode_sid","perusahaan_area_kerja_tambang","site_/_lokasi_kerja",
        "jabatan","kategori_jabatan","level_jabatan","masa_kerja","masa_kerja_(bulan)"
    ]
    site_col, corp_col = "site_/_lokasi_kerja", "perusahaan_area_kerja_tambang"

    question_cols = [c for c in df.columns if c not in id_cols]
    if len(question_cols) == 0:
        st.warning("Tidak ada kolom pertanyaan ditemukan.")
        return

    question_cols_general = question_cols[:-5] if len(question_cols) > 5 else question_cols

    # Filter
    fcol = st.columns(2)
    with fcol[0]:
        sites = sorted(df[site_col].dropna().unique()) if site_col in df.columns else []
        sel_sites = st.multiselect("Filter Site", sites, default=sites[:3] if sites else [], key=f"{key_prefix}_sites")
    with fcol[1]:
        corps = sorted(df[corp_col].dropna().unique()) if corp_col in df.columns else []
        sel_corps = st.multiselect("Filter Perusahaan", corps, default=[], key=f"{key_prefix}_corps")

    df_f = df.copy()
    if sel_sites and site_col in df_f.columns:
        df_f = df_f[df_f[site_col].isin(sel_sites)]
    if sel_corps and corp_col in df_f.columns:
        df_f = df_f[df_f[corp_col].isin(sel_corps)]
    st.caption(f"Total respon (setelah filter): **{len(df_f)}**")

    # Distribusi umum
    c1, c2, c3 = st.columns(3)
    with c1: per_page = st.slider("Pertanyaan per halaman", 1, 8, 4, key=f"{key_prefix}_per_page")
    with c2: ncols = st.radio("Grafik per baris", [1, 2, 3], index=1, key=f"{key_prefix}_ncols")
    with c3:
        total = len(question_cols_general)
        pages = max(1, math.ceil(total / per_page))
        page = st.number_input("Halaman", min_value=1, max_value=pages, value=1, step=1, key=f"{key_prefix}_page")

    start, end = (page - 1) * per_page, min(page * per_page, total)
    questions = question_cols_general[start:end]

    nrows = max(1, math.ceil(len(questions) / ncols))
    fig = sp.make_subplots(rows=nrows, cols=ncols,
        subplot_titles=[q[:60] + ("..." if len(q) > 60 else "") for q in questions])

    for i, q in enumerate(questions):
        row, col = i // ncols + 1, i % ncols + 1
        counts = df_f[q].dropna().astype(str).value_counts()
        fig.add_trace(go.Bar(
            x=list(counts.index), y=list(counts.values),
            marker_color=px.colors.qualitative.Set2,
            hovertemplate="Pilihan = %{x}<br>Respon = %{y}<extra></extra>",
            showlegend=False
        ), row=row, col=col)

    fig.update_layout(barmode="group", height=max(350, 320*nrows),
                      title_text=f"Distribusi Jawaban (Hal {page}/{pages})", title_x=0.5)
    st.plotly_chart(fig, use_container_width=True, key=f"{key_prefix}_dist")

    # Multi-jawaban
    for col_multi in [
        "jika_pernah,_membuang_sampah_sembarangan,_alasannya?",
        "jika_pernah_tidak_memilah_sampah_,_alasannya?"
    ]:
        if col_multi in df_f.columns:
            multi = df_f[col_multi].dropna().astype(str).str.split(",").explode().str.strip()
            alasan_counts = multi.value_counts().reset_index()
            alasan_counts.columns = ["Alasan", "Jumlah"]
            st.subheader(f"📌 {col_multi}")
            st.dataframe(alasan_counts, use_container_width=True)
            fig2 = px.bar(alasan_counts, x="Jumlah", y="Alasan", orientation="h", color="Jumlah",
                          color_continuous_scale="orrd", text="Jumlah")
            fig2.update_layout(yaxis=dict(categoryorder="total ascending"), showlegend=False)
            st.plotly_chart(fig2, use_container_width=True, key=f"{key_prefix}_{col_multi}")

    # Analisis Q2
    q2_col = "2._seberapa_optimal_program_gbst_berjalan_selama_ini_di_perusahaan_anda?"
    if q2_col in df_f.columns:
        st.markdown("---"); st.header(f"⭐ Analisis Khusus Q2 — {label}")
        q2_vals = pd.to_numeric(df_f[q2_col], errors="coerce").dropna()
        if q2_vals.empty: 
            st.warning("Belum ada data numerik untuk Q2")
        else:
            c1,c2,c3,c4,c5 = st.columns(5)
            c1.metric("Mean", f"{q2_vals.mean():.2f}")
            c2.metric("Median", f"{q2_vals.median():.2f}")
            mode_val = q2_vals.mode().iat[0] if not q2_vals.mode().empty else "-"
            c3.metric("Modus", f"{mode_val}")
            c4.metric("Std. Dev", f"{q2_vals.std():.2f}")
            c5.metric("n", f"{len(q2_vals)}")
            st.plotly_chart(gauge_figure(q2_vals.mean(), "Rata-rata Optimalitas GBST"), use_container_width=True, key=f"{key_prefix}_gauge")

    # Open-ended
    st.markdown("---"); st.header(f"📊 Analisis Pertanyaan Terbuka ({label})")
    OPEN_QS = {
        "1._apa_hambatan_yang_dialami_dalam_melaksanakan_program_gbst?": "viridis",
        "3._menurut_anda,_bagaimana_cara_membuat_pekerja_lebih_disiplin_dalam_menjalankan_gbst?": "cividis",
        "4._bagaimana_fasilitas_pengelolaan_sampah_di_area_anda?": "inferno",
        "5._menurut_anda,_apa_bentuk_dukungan_tambahan_yang_anda_perlukan_untuk_menjalankan_atau_mendukung_program_gbst?": "magma"
    }
    for q_col, cmap in OPEN_QS.items():
        if q_col in df_f.columns:
            q_text = df_f[q_col].dropna().astype(str)
            if q_text.empty: continue
            show_wordcloud(q_text, f"WordCloud - {q_col}", cmap=cmap)
            top_bi, top_tri = get_top_phrases(q_text,(2,2)), get_top_phrases(q_text,(3,3))
            c1,c2 = st.columns(2)
            with c1: st.plotly_chart(px.bar(top_bi, x="Frekuensi", y="Frasa", orientation="h",
                                            color="Frekuensi", color_continuous_scale="blues", text="Frekuensi"),
                                     use_container_width=True, key=f"{key_prefix}_{q_col}_bi")
            with c2: st.plotly_chart(px.bar(top_tri, x="Frekuensi", y="Frasa", orientation="h",
                                            color="Frekuensi", color_continuous_scale="greens", text="Frekuensi"),
                                     use_container_width=True, key=f"{key_prefix}_{q_col}_tri")
            st.info(make_insight(top_bi, top_tri))

# ===============================
# CALL
# ===============================
if tab_choice == "📋 Survei Offline":
    analisis_survei(df_offline, "Survei Offline", "offline")
elif tab_choice == "🌐 Survei Online":
    analisis_survei(df_online, "Survei Online", "online")
