import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import date, timedelta

# -------- Static Ministry List (You can add more here) -------- #
MINISTRY_LIST = [
    "Ministry of Petroleum & Natural Gas"
]

# -------- Function to fetch press releases -------- #
def fetch_press_releases(ministry, start_date, end_date):
    base_url = "https://pib.gov.in/PressReleseDetail.aspx?PRID="
    all_data = []

    # Convert to PIB date format (e.g. 04 JUL 2025)
    def to_pib_date(dt):
        return dt.strftime("%d %b %Y").upper()

    for offset in range(0, 2000, 20):  # Scraping first 100 pages (~2000 articles)
        url = f"https://pib.gov.in/allRel.aspx?PageNo={(offset // 20) + 1}"
        res = requests.get(url)
        soup = BeautifulSoup(res.content, "html.parser")

        rows = soup.find_all("div", class_="col-sm-9 col-xs-12 contentarea")
        if not rows:
            break  # End of pages

        for rel in soup.select(".contentarea > ul > li"):
            try:
                title = rel.find("a").get_text(strip=True)
                link = "https://pib.gov.in/" + rel.find("a")["href"]
                raw_date = rel.find("span").get_text(strip=True)
                date_obj = pd.to_datetime(raw_date, format="%d %b %Y", errors='coerce')

                if date_obj is pd.NaT or not (start_date <= date_obj.date() <= end_date):
                    continue

                # Fetch article to extract ministry name
                detail_page = requests.get(link)
                detail_soup = BeautifulSoup(detail_page.content, "html.parser")
                ministry_tag = detail_soup.find("span", id="ContentPlaceHolder1_lblMinistry")

                if ministry_tag and ministry.strip().lower() in ministry_tag.text.strip().lower():
                    content_div = detail_soup.find("div", id="ContentPlaceHolder1_divContent")
                    content = content_div.get_text(separator="\n", strip=True) if content_div else "N/A"

                    all_data.append({
                        "Title": title,
                        "Date": date_obj.strftime("%d-%m-%Y"),
                        "Ministry": ministry_tag.text.strip(),
                        "Link": link,
                        "Description": content[:500] + "..." if content else "N/A"
                    })

            except Exception as e:
                continue

    return pd.DataFrame(all_data)

# ------------------- Streamlit UI ------------------- #
st.title("📢 PIB Press Release Scraper")

ministry = st.selectbox("🔽 Select Ministry", MINISTRY_LIST)

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("📅 Start Date", date.today() - timedelta(days=30))
with col2:
    end_date = st.date_input("📅 End Date", date.today())

if st.button("🚀 Fetch Press Releases"):
    with st.spinner("Fetching data..."):
        df = fetch_press_releases(ministry, start_date, end_date)

        if df.empty:
            st.warning("No press releases found for the selected ministry and date range.")
        else:
            st.success(f"Found {len(df)} press releases.")
            st.dataframe(df)

            # Download button
            st.download_button("📥 Download as Excel", df.to_excel(index=False, engine="openpyxl"), file_name="press_releases.xlsx")
