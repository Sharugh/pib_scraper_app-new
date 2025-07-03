import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import urllib.parse

# ----------------- Helper Functions -----------------
@st.cache_data
def get_ministry_list():
    url = "https://www.pib.gov.in/allRel.aspx"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    ministries = soup.select('select#ddlMinistry option')
    ministry_list = [m.text.strip() for m in ministries if m.get('value')]
    return ministry_list

def get_press_releases(ministry_name, start_date, end_date):
    encoded_min = urllib.parse.quote_plus(ministry_name)
    base_url = f"https://pib.gov.in/allRel.aspx?min={encoded_min}"
    response = requests.get(base_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    press_blocks = soup.select("div.span6 a")
    data = []

    for block in press_blocks:
        title = block.text.strip()
        link = "https://pib.gov.in/" + block.get('href')
        detail_resp = requests.get(link)
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

    return pd.DataFrame(data)

# ----------------- Streamlit UI -----------------
st.set_page_config(page_title="PIB News Scraper", layout="wide")
st.title("📢 PIB News Scraper - S&P Global Tool")

# Sidebar Inputs
with st.sidebar:
    st.header("Filter News")
    ministries = get_ministry_list()
    selected_ministry = st.selectbox("Select Ministry", ministries)
    start_date = st.date_input("Start Date", datetime(2024, 1, 1))
    end_date = st.date_input("End Date", datetime.today())

if st.button("🔍 Fetch Press Releases"):
    if selected_ministry:
        st.info(f"Fetching news for: {selected_ministry}...")
        df = get_press_releases(selected_ministry, start_date, end_date)
        if not df.empty:
            st.success(f"Fetched {len(df)} press releases.")
            st.dataframe(df, use_container_width=True)
            # Export button
            @st.cache_data
            def convert_df(df):
                return df.to_excel(index=False, engine='openpyxl')
            excel_data = convert_df(df)
            st.download_button("📥 Download Excel", excel_data, file_name="PIB_News.xlsx")
        else:
            st.warning("No press releases found for the selected period.")
