import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
from io import BytesIO

st.set_page_config(page_title="PIB News Scraper", layout="centered")
st.title("📰 PIB News Scraper")
st.subheader("Ministry of Petroleum & Natural Gas")

# Fixed ministry
MINISTRY_NAME = "Ministry of Petroleum & Natural Gas"

# Date input
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("📅 From Date", datetime.today())
with col2:
    end_date = st.date_input("📅 To Date", datetime.today())

if st.button("🚀 Fetch Press Releases"):
    st.info("Fetching news... please wait...")

    payload = {
        "MinID": 0,
        "Min": MINISTRY_NAME,
        "CatID": 0,
        "CatName": "All",
        "start": start_date.strftime("%d/%m/%Y"),
        "end": end_date.strftime("%d/%m/%Y"),
        "LangID": 1
    }

    try:
        url = "https://pib.gov.in/PressReleseAll.aspx"
        response = requests.post(url, data=payload, timeout=20)

        soup = BeautifulSoup(response.content, "html.parser")
        divs = soup.find_all("div", class_="col-sm-9 panelContent")

        if not divs:
            st.warning("No press releases found for selected dates.")
        else:
            news_data = []

            for div in divs:
                title_tag = div.find("a")
                date_tag = div.find("span")

                title = title_tag.text.strip()
                link = "https://pib.gov.in/" + title_tag["href"]
                date = date_tag.text.strip() if date_tag else "N/A"

                # Optional: Extract description from detail page
                detail_resp = requests.get(link)
                detail_soup = BeautifulSoup(detail_resp.content, "html.parser")
                desc_div = detail_soup.find("div", {"id": "divMainContent"})
                description = desc_div.text.strip() if desc_div else ""

                news_data.append({
                    "Title": title,
                    "Date": date,
                    "Link": link,
                    "Description": description
                })

            df = pd.DataFrame(news_data)

            st.success(f"✅ Found {len(df)} press releases.")
            st.dataframe(df[["Date", "Title", "Link"]])

            # Download
            buffer = BytesIO()
            df.to_excel(buffer, index=False, engine='openpyxl')
            st.download_button("⬇️ Download Excel", buffer.getvalue(), file_name="pib_petroleum_news.xlsx")

    except Exception as e:
        st.error(f"❗ Error: {e}")
