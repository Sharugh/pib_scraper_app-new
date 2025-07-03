import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import urllib.parse

# -------------------- Manual Ministry List --------------------
MINISTRY_LIST = [
    "Ministry of Petroleum & Natural Gas",
    "Ministry of Finance",
    "Ministry of Health and Family Welfare",
    "Ministry of Education",
    "Ministry of Environment, Forest and Climate Change",
    "Ministry of Defence",
    "Ministry of External Affairs",
    "Ministry of Home Affairs",
]

# -------------------- Scrape PIB News --------------------
def get_press_releases(ministry_name, start_date, end_date):
    encoded_min = urllib.parse.quote_plus(ministry_name)
    base_url = f"https://pib.gov.in/allRel.aspx?min={encoded_min}"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(base_url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    press_blocks = soup.select("div.span6 a")

    data = []

    for block in press_blocks:
        title = block.text.strip()
        link = "https://pib.gov.in/" + block.get('href')
        
        try:
            detail_resp = requests.get(link, headers=headers)
            detail_soup = BeautifulSoup(detail_resp.text, 'html.parser')

            date_el = detail_soup.select_one("#ContentPlaceHolder1_lblDate")
            desc_el = detail_soup.select_one("#ContentPlaceHolder1_divContent")

            if date_el and desc_el:
                pub_date = date_el.text.strip()
                pub_date_obj = datetime.strptime(pub_date, "%d %b %Y")

                if start_date <= pub_date_obj <= end_date:
                    data.append({
                        "Title": title,
                        "Date": pub_date_obj.strftime("%Y-%m-%d"),
                        "Description": desc_el.get_text(strip=True),
                        "Link": link
                    })
        except Exception as e:
            print(f"Error fetching {link}: {e}")
            continue

    return pd.DataFrame(data)


# -------------------- Streamlit App --------------------
st.set_page_config(page_title="PIB News Scraper", layout="wide")
st.title("📢 PIB News Scraper - S&P Global Tool")

with st.sidebar:
    st.header("🔍 Filter News")
    selected_ministry = st.selectbox("Select Ministry", MINISTRY_LIST)
    start_date = st.date_input("Start Date", datetime(2024, 1, 1))
    end_date = st.date_input("End Date", datetime.today())

if st.button("🔍 Fetch Press Releases"):
    st.info(f"Fetching news for: {selected_ministry}...")
    df = get_press_releases(selected_ministry, start_date, end_date)

    if not df.empty:
        st.success(f"✅ Found {len(df)} press releases.")
        st.dataframe(df, use_container_width=True)

        @st.cache_data
        def convert_df(df):
            return df.to_excel(index=False, engine='openpyxl')

        excel_data = convert_df(df)
        st.download_button("📥 Download Excel", excel_data, file_name="PIB_Press_Releases.xlsx")
    else:
        st.warning("⚠️ No press releases found for selected ministry and date range.")
