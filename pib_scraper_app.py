import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime

st.set_page_config(page_title="📢 PIB Press Release Scraper", layout="centered")

st.title("📢 PIB Press Release Scraper")

# Manually define known ministries (you can expand this list)
MINISTRY_LIST = [
    "Ministry of Petroleum & Natural Gas",
    "Ministry of Finance",
    "Ministry of Education",
    "Ministry of Defence",
    "Ministry of Health and Family Welfare",
    "Ministry of External Affairs",
    "Ministry of Environment, Forest and Climate Change"
]

selected_ministry = st.selectbox("🔽 Select Ministry", MINISTRY_LIST)

start_date = st.date_input("📅 Start Date", datetime(2024, 1, 1))
end_date = st.date_input("📅 End Date", datetime(2024, 1, 31))

def fetch_press_releases(ministry, start_date, end_date):
    base_url = "https://pib.gov.in/allrel.aspx"
    headers = {"User-Agent": "Mozilla/5.0"}
    all_data = []

    for page in range(1, 6):  # Scrape first 5 pages
        url = f"{base_url}?PageId={page}"
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")

        items = soup.select("div.content-area div.col-sm-12")

        for item in items:
            try:
                title_tag = item.select_one("a")
                if not title_tag or not title_tag.get("href"):
                    continue

                title = title_tag.text.strip()
                link = "https://pib.gov.in/" + title_tag["href"]

                date_tag = item.select_one("span")
                if date_tag:
                    date_text = date_tag.text.strip()
                    date_obj = datetime.strptime(date_text, "%d %b %Y")
                else:
                    continue

                # Filter by ministry name (in title)
                if ministry.lower() not in title.lower():
                    continue

                # Filter by date range
                if not (start_date <= date_obj.date() <= end_date):
                    continue

                all_data.append({
                    "Date": date_obj.strftime("%Y-%m-%d"),
                    "Title": title,
                    "Link": link
                })

            except Exception as e:
                continue

    return pd.DataFrame(all_data)

if st.button("🔍 Fetch Press Releases"):
    with st.spinner("Fetching data... please wait"):
        df = fetch_press_releases(selected_ministry, start_date, end_date)

    if df.empty:
        st.warning("No press releases found for the selected ministry and date range.")
    else:
        st.success(f"✅ Found {len(df)} press releases.")
        st.dataframe(df, use_container_width=True)

        # Download button
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download CSV", data=csv, file_name="press_releases.csv", mime="text/csv")
