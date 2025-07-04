import streamlit as st
import pandas as pd
import datetime
from bs4 import BeautifulSoup
import requests
from playwright.sync_api import sync_playwright

# -------------------------------
# Step 1: Get ministries using Playwright
# -------------------------------
@st.cache_data
def get_ministry_list():
    ministries = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://pib.gov.in/allRel.aspx", timeout=60000)
        try:
            page.wait_for_selector("#ddlMinistry", timeout=10000)
            options = page.query_selector_all("#ddlMinistry option")
            for option in options:
                text = option.inner_text().strip()
                if text and "Select" not in text:
                    ministries.append(text)
        except Exception as e:
            st.error(f"Error extracting ministries: {str(e)}")
        finally:
            browser.close()
    return ministries

# -------------------------------
# Step 2: Scrape press releases
# -------------------------------
def fetch_press_releases(ministry, start_date, end_date):
    url = "https://pib.gov.in/PressReleseAll.aspx"
    headers = {
        "User-Agent": "Mozilla/5.0",
    }

    payload = {
        "Min": ministry,
        "CatID": 0,
        "CatName": "All",
        "start": start_date.strftime("%d/%m/%Y"),
        "end": end_date.strftime("%d/%m/%Y"),
        "LangID": 1
    }

    response = requests.post(url, data=payload, headers=headers)

    soup = BeautifulSoup(response.content, "html.parser")
    press_data = []

    for item in soup.select("div.col-sm-9.col-xs-12.textJustify"):
        title = item.find("a")
        date = item.find_next("span", class_="date")

        if title and date:
            press_data.append({
                "Title": title.text.strip(),
                "Link": "https://pib.gov.in/" + title.get("href"),
                "Date": date.text.strip()
            })

    return press_data

# -------------------------------
# Step 3: Streamlit UI
# -------------------------------
st.title("📰 PIB Press Release Extractor")
st.write("Built for internal use @ S&P Global")

with st.spinner("Loading ministry list..."):
    ministries = get_ministry_list()

if ministries:
    selected_ministry = st.selectbox("Select Ministry", ministries)
    col1, col2 = st.columns(2)

    with col1:
        start_date = st.date_input("Start Date", datetime.date.today() - datetime.timedelta(days=30))
    with col2:
        end_date = st.date_input("End Date", datetime.date.today())

    if st.button("📥 Fetch Press Releases"):
        with st.spinner("Fetching press releases..."):
            results = fetch_press_releases(selected_ministry, start_date, end_date)

        if results:
            df = pd.DataFrame(results)
            st.success(f"✅ Fetched {len(df)} press releases.")
            st.dataframe(df)

            # Export to Excel
            file_name = f"{selected_ministry.replace(' ', '_')}_Press_Releases.xlsx"
            df.to_excel(file_name, index=False)

            with open(file_name, "rb") as f:
                st.download_button("⬇️ Download Excel", data=f, file_name=file_name)
        else:
            st.warning("No press releases found for this range.")
else:
    st.error("❗ Failed to load ministry list.")
