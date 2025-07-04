import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd

st.set_page_config(page_title="PIB Press Release Scraper", layout="centered")

st.title("📢 PIB Press Release Scraper")

# ---------------------------------------------
# Static ministry list (you can expand this)
MINISTRY_LIST = [
    "Ministry of Petroleum & Natural Gas",
    "Ministry of Finance",
    "Ministry of Health and Family Welfare",
    "Ministry of Education",
    "Ministry of Defence",
    "Ministry of External Affairs",
    "Ministry of Home Affairs"
]
# ---------------------------------------------

# 🧠 Fetch ministry name from each detail page
def fetch_press_releases(ministry, start_date, end_date):
    base_url = "https://pib.gov.in/allrel.aspx"
    headers = {"User-Agent": "Mozilla/5.0"}
    all_data = []

    for page in range(1, 6):  # First 5 pages
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

                # Filter by date
                if not (start_date <= date_obj.date() <= end_date):
                    continue

                # Now go inside press release page
                detail_res = requests.get(link, headers=headers)
                detail_soup = BeautifulSoup(detail_res.text, "html.parser")
                ministry_tag = detail_soup.find("span", {"id": "ContentPlaceHolder1_Label6"})

                if ministry_tag and ministry.lower() in ministry_tag.text.strip().lower():
                    all_data.append({
                        "Date": date_obj.strftime("%Y-%m-%d"),
                        "Title": title,
                        "Ministry": ministry_tag.text.strip(),
                        "Link": link
                    })

            except Exception:
                continue

    return pd.DataFrame(all_data)

# UI Components
selected_ministry = st.selectbox("🔽 Select Ministry", MINISTRY_LIST)
start_date = st.date_input("📅 Start Date", datetime(2024, 1, 1))
end_date = st.date_input("📅 End Date", datetime(2024, 12, 31))

if st.button("🔍 Fetch Press Releases"):
    with st.spinner("Fetching press releases..."):
        df = fetch_press_releases(selected_ministry, start_date, end_date)

    if df.empty:
        st.warning("No press releases found for the selected ministry and date range.")
    else:
        st.success(f"Found {len(df)} press releases.")
        st.dataframe(df, use_container_width=True)

        # 📤 Download as Excel
        excel_bytes = df.to_excel(index=False, engine='openpyxl')
        st.download_button("⬇ Download Excel", data=excel_bytes, file_name="press_releases.xlsx")
