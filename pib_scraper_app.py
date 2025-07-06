import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import BytesIO

# Target ministry name
TARGET_MINISTRY = "Ministry of Petroleum & Natural Gas"

# Function to extract PIB press release info for Petroleum Ministry
@st.cache_data(show_spinner=False)
def extract_pib_pdfs(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        base_url = "https://www.pib.gov.in"
        press_data = []

        table = soup.find("table", id="tablegrid")  # main press release table
        if not table:
            return []

        rows = table.find_all("tr")[1:]  # Skip header row
        for row in rows:
            columns = row.find_all("td")
            if len(columns) < 4:
                continue

            date = columns[0].get_text(strip=True)
            ministry = columns[1].get_text(strip=True)
            title_link = columns[2].find("a", href=True)
            title = title_link.get_text(strip=True) if title_link else ""
            press_release_url = base_url + title_link["href"] if title_link else ""

            if TARGET_MINISTRY.lower() in ministry.lower() and press_release_url:
                # Go inside press release page and find PDF
                pdf_url = ""
                press_page = requests.get(press_release_url)
                press_soup = BeautifulSoup(press_page.text, "html.parser")
                for a in press_soup.find_all("a", href=True):
                    href = a["href"]
                    if href.lower().endswith(".pdf"):
                        pdf_url = href if href.startswith("http") else base_url + href
                        break  # only first PDF

                if pdf_url:
                    press_data.append({
                        "Date": date,
                        "Title": title,
                        "PDF URL": pdf_url,
                        "Press Release Page": press_release_url
                    })
        return press_data
    except Exception as e:
        return []

# Streamlit UI
st.title("📄 PIB Petroleum Ministry Press Release PDF Collector")
st.write("Scrape PIB press releases that belong to the Ministry of Petroleum & Natural Gas and contain PDFs.")

url = st.text_input("🔗 Enter the PIB URL (e.g., https://pib.gov.in/allRel.aspx?reg=3&lang=1)")

if url:
    with st.spinner("⛏️ Scraping PIB..."):
        data = extract_pib_pdfs(url)

    if data:
        df = pd.DataFrame(data)
        st.success(f"✅ Found {len(df)} press release(s) with PDFs for Ministry of Petroleum & Natural Gas.")
        st.dataframe(df)

        # Download as Excel
        excel_buffer = BytesIO()
        df.to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)
        st.download_button(
            label="📥 Download Results (Excel)",
            data=excel_buffer,
            file_name="petroleum_press_releases.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("⚠️ No matching PDFs found for Ministry of Petroleum & Natural Gas.")

