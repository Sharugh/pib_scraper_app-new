import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
from io import BytesIO

st.title("📰 PIB News Scraper (Petroleum Ministry)")

MINISTRY_NAME = "Ministry of Petroleum & Natural Gas"

start_date = st.date_input("From Date", datetime(2024, 6, 1))
end_date = st.date_input("To Date", datetime.today())

if st.button("Fetch News"):
    with st.spinner("Getting press releases..."):

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        payload = {
            "Min": MINISTRY_NAME,
            "CatID": 0,
            "CatName": "All",
            "start": start_date.strftime("%d/%m/%Y"),
            "end": end_date.strftime("%d/%m/%Y"),
            "LangID": 1
        }

        try:
            res = requests.post("https://pib.gov.in/PressReleseAll.aspx", data=payload, headers=headers)
            soup = BeautifulSoup(res.content, "html.parser")
            items = soup.select("div.col-sm-9.panelContent")

            if not items:
                st.warning("No news found.")
            else:
                news = []
                for item in items:
                    a_tag = item.find("a")
                    if not a_tag:
                        continue
                    title = a_tag.text.strip()
                    link = "https://pib.gov.in/" + a_tag["href"]
                    date = item.find("span").text.strip()

                    # Get full description from detail page
                    detail = requests.get(link, headers=headers)
                    desc_soup = BeautifulSoup(detail.content, "html.parser")
                    desc_div = desc_soup.find("div", {"id": "divMainContent"})
                    desc = desc_div.text.strip() if desc_div else ""

                    news.append({
                        "Title": title,
                        "Date": date,
                        "Link": link,
                        "Description": desc
                    })

                df = pd.DataFrame(news)
                st.success(f"✅ Found {len(df)} releases")
                st.dataframe(df[["Date", "Title", "Link"]])

                buffer = BytesIO()
                df.to_excel(buffer, index=False, engine="openpyxl")
                st.download_button("⬇ Download Excel", buffer.getvalue(), file_name="petroleum_press.xlsx")

        except Exception as e:
            st.error(f"Error: {e}")
