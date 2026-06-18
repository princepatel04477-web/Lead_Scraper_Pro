"""
app.py — Beautiful Streamlit UI for the Lead Scraper
Run:  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import time
import logging
import sys
import os
from io import BytesIO

# Ensure the script directory is in sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scrapers import GoogleMapsScraper, InstagramScraper, YellowPagesScraper, FacebookScraper
from utils.filters import filter_no_website, deduplicate
from utils.export import export_csv, export_excel

logging.basicConfig(level=logging.INFO)

# ── Page config ─────────────────────────────────────────
st.set_page_config(
    page_title="🎯 Lead Scraper Pro",
    page_icon="🎯",
    layout="wide",
)

# ── Custom CSS ──────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #666;
        margin-top: -10px;
        margin-bottom: 30px;
    }
    .metric-card {
        background: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
    }
    .stButton > button {
        width: 100%;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-size: 1.1rem;
        font-weight: 600;
        padding: 0.6rem 1rem;
        border: none;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ──────────────────────────────────────────────
st.markdown('<p class="main-header">🎯 Lead Scraper Pro</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="sub-header">'
    'Find businesses WITHOUT websites — your next clients are waiting.'
    '</p>',
    unsafe_allow_html=True,
)

# ── Sidebar inputs ──────────────────────────────────────
with st.sidebar:
    st.header("🔧 Scraper Settings")

    niche = st.text_input(
        "🏷️ Niche / Industry",
        placeholder="e.g. Interior Design",
        help="The type of business you're looking for",
    )
    city = st.text_input(
        "🏙️ City",
        placeholder="e.g. Toronto",
    )
    country = st.text_input(
        "🌍 Country",
        placeholder="e.g. Canada",
    )

    st.subheader("📡 Data Sources")
    use_gmaps = st.checkbox("🗺️  Google Maps", value=True)
    use_insta = st.checkbox("📸  Instagram", value=False)
    use_yp = st.checkbox("📒  Yellow Pages / Yelp", value=True)
    use_fb = st.checkbox("📘  Facebook", value=False)

    st.divider()
    max_results = st.slider(
        "Max leads per source",
        min_value=10,
        max_value=200,
        value=50,
        step=10,
    )

    broaden_search = st.checkbox("🔍 Auto-broaden Google Maps search", value=True, help="Try alternative query formats if initial search returns low results (< 5)")
    headless = st.checkbox("Run browser headless (hidden)", value=True)

    st.divider()
    start_btn = st.button("🚀 START SCRAPING", type="primary")

# ── Main area ───────────────────────────────────────────
if start_btn:
    if not niche or not city or not country:
        st.error("⚠️ Please fill in Niche, City, and Country.")
        st.stop()

    status_box = st.empty()
    progress_bar = st.progress(0)
    results_placeholder = st.empty()

    all_leads = []
    steps_done = 0
    total_steps = sum([use_gmaps, use_insta, use_yp, use_fb]) + 2  # +2 for dedup & filter

    def update_status(msg):
        status_box.info(f"⏳ {msg}")

    # ── Google Maps ────────────────────────────────────
    if use_gmaps:
        update_status("Scraping Google Maps…")
        try:
            gm = GoogleMapsScraper(headless=headless)
            leads = gm.scrape(niche, city, country, max_results, update_status, broaden=broaden_search)
            all_leads.extend(leads)
            st.success(f"✅ Google Maps: {len(leads)} leads found")
        except Exception as e:
            st.warning(f"⚠️ Google Maps error: {e}")
        steps_done += 1
        progress_bar.progress(steps_done / total_steps)

    # ── Instagram ──────────────────────────────────────
    if use_insta:
        update_status("Scraping Instagram…")
        try:
            ig = InstagramScraper()
            leads = ig.scrape(niche, city, country, max_results, update_status)
            all_leads.extend(leads)
            st.success(f"✅ Instagram: {len(leads)} leads found")
        except Exception as e:
            st.warning(f"⚠️ Instagram error: {e}")
        steps_done += 1
        progress_bar.progress(steps_done / total_steps)

    # ── Yellow Pages ───────────────────────────────────
    if use_yp:
        update_status("Scraping Yellow Pages / Yelp…")
        try:
            yp = YellowPagesScraper()
            leads = yp.scrape(niche, city, country, max_results, update_status)
            all_leads.extend(leads)
            st.success(f"✅ Yellow Pages/Yelp: {len(leads)} leads found")
        except Exception as e:
            st.warning(f"⚠️ Yellow Pages error: {e}")
        steps_done += 1
        progress_bar.progress(steps_done / total_steps)

    # ── Facebook ───────────────────────────────────────
    if use_fb:
        update_status("Scraping Facebook…")
        try:
            fb = FacebookScraper(headless=headless)
            leads = fb.scrape(niche, city, country, max_results, update_status)
            all_leads.extend(leads)
            st.success(f"✅ Facebook: {len(leads)} leads found")
        except Exception as e:
            st.warning(f"⚠️ Facebook error: {e}")
        steps_done += 1
        progress_bar.progress(steps_done / total_steps)

    # ── Deduplication ──────────────────────────────────
    update_status("Removing duplicates…")
    before = len(all_leads)
    all_leads = deduplicate(all_leads)
    steps_done += 1
    progress_bar.progress(steps_done / total_steps)

    # ── Classify and count website status ────────────────
    update_status("Analyzing website status…")
    from utils.filters import classify_website_url
    for lead in all_leads:
        if "website_status" not in lead:
            lead["website_status"] = classify_website_url(lead.get("website", ""))

    no_website_leads = [l for l in all_leads if l.get("website_status") == "No Website"]
    moderate_website_leads = [l for l in all_leads if l.get("website_status") == "Moderate Website"]
    good_website_leads = [l for l in all_leads if l.get("website_status") == "Good Website"]
    
    steps_done += 1
    progress_bar.progress(1.0)

    status_box.empty()

    # ── Display metrics ────────────────────────────────
    st.divider()
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("📊 Total Scraped", before)
    col2.metric("🔄 After Dedup", len(all_leads))
    col3.metric("🟢 No Website", len(no_website_leads))
    col4.metric("🟡 Moderate Website", len(moderate_website_leads))
    col5.metric("🔴 Good Website", len(good_website_leads))

    # ── Results table ──────────────────────────────────
    if all_leads:
        st.subheader("🎯 Scraped Leads & Website Status")
        
        df = pd.DataFrame(all_leads)

        # reorder columns nicely
        preferred_cols = [
            "name", "category", "phone", "email", "address",
            "website", "instagram", "website_status", "rating", "reviews",
            "maps_url", "source",
        ]
        cols = [c for c in preferred_cols if c in df.columns]
        cols += [c for c in df.columns if c not in cols]
        df = df[cols]

        # Interactive filter
        status_filter = st.multiselect(
            "Filter leads by Website Status:",
            options=["No Website", "Moderate Website", "Good Website"],
            default=["No Website", "Moderate Website", "Good Website"]
        )
        
        filtered_df = df[df["website_status"].isin(status_filter)]

        if not filtered_df.empty:
            # Style the dataframe using pandas styler
            def style_rows(data):
                styles = pd.DataFrame('', index=data.index, columns=data.columns)
                if 'website_status' in data.columns:
                    for idx, val in data['website_status'].items():
                        if val == "No Website":
                            styles.at[idx, 'website_status'] = 'background-color: #d4edda; color: #155724; font-weight: bold;'
                        elif val == "Moderate Website":
                            styles.at[idx, 'website_status'] = 'background-color: #fff3cd; color: #856404; font-weight: bold;'
                        elif val == "Good Website":
                            styles.at[idx, 'website_status'] = 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
                return styles

            styled_df = filtered_df.style.apply(style_rows, axis=None)
            st.dataframe(styled_df, use_container_width=True, height=500)

            # ── Download buttons ───────────────────────────
            st.divider()
            dl_col1, dl_col2, dl_col3 = st.columns(3)

            # CSV
            csv_data = filtered_df.to_csv(index=False).encode("utf-8-sig")
            dl_col1.download_button(
                "📥 Download CSV",
                data=csv_data,
                file_name=f"leads_{city}_{niche.replace(' ','_')}.csv",
                mime="text/csv",
            )

            # Excel
            buffer = BytesIO()
            filtered_df.to_excel(buffer, index=False, engine="openpyxl")
            dl_col2.download_button(
                "📥 Download Excel",
                data=buffer.getvalue(),
                file_name=f"leads_{city}_{niche.replace(' ','_')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

            # JSON
            json_data = filtered_df.to_json(orient="records", indent=2)
            dl_col3.download_button(
                "📥 Download JSON",
                data=json_data,
                file_name=f"leads_{city}_{niche.replace(' ','_')}.json",
                mime="application/json",
            )
        else:
            st.warning("No leads match the selected status filter.")

    else:
        st.warning("No leads found. Try broadening your search.")

else:
    # ── Landing state ──────────────────────────────────
    st.info(
        "👈 Enter your **niche**, **city**, and **country** in the sidebar, "
        "select your data sources, and hit **START SCRAPING**."
    )

    st.divider()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("### 🗺️ Google Maps")
        st.markdown(
            "Scrapes business names, phone numbers, addresses, ratings. "
            "Identifies which businesses have no website."
        )
    with col2:
        st.markdown("### 📸 Instagram")
        st.markdown(
            "Finds business accounts via niche + city hashtags. "
            "Extracts emails and phone numbers from bios."
        )
    with col3:
        st.markdown("### 📒 Yellow Pages")
        st.markdown(
            "Scrapes traditional business directories. "
            "Great for established local businesses."
        )
    with col4:
        st.markdown("### 📘 Facebook")
        st.markdown(
            "Searches Google for public Facebook pages. "
            "Extracts emails, phone numbers, and websites."
        )
