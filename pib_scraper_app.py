import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import BytesIO

BASE_URL = "https://www.pib.gov.in/allRel.aspx"
TARGET_MINISTRY = "Ministry of"

# Scraper function
@st.cache_data(show_spinner=False)
def extract_petro_ministry_pdfs(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table", id="tablegrid")
        if not table:
            return []

        press_data = []
        rows = table.find_all("tr")[1:]  # Skip header row
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 3:
                continue
            date = cols[0].get_text(strip=True)
            title_link = cols[2].find("a", href=True)
            title = title_link.get_text(strip=True) if title_link else ""
            detail_url = BASE_URL + title_link["href"] if title_link else ""

            # Open press release detail page
            if detail_url:
                detail_resp = requests.get(detail_url)
                detail_soup = BeautifulSoup(detail_resp.text, "html.parser")

                # Check if ministry name appears anywhere
                if TARGET_MINISTRY.lower() in detail_soup.get_text(strip=True).lower():
                    # Look for PDF link
                    pdf_url = ""
                    for a in detail_soup.find_all("a", href=True):
                        href = a["href"]
                        if href.lower().endswith(".pdf"):
                            pdf_url = href if href.startswith("http") else BASE_URL + href
                            break
                    if pdf_url:
                        press_data.append({
                            "Date": date,
                            "Title": title,
                            "PDF URL": pdf_url,
                            "Press Release Page": detail_url
                        })
        return press_data
    except Exception as e:
        return []

# Streamlit UI
st.set_page_config(page_title="PIB Petroleum PDF Scraper", layout="wide")
st.title("📄 PIB Ministry of Petroleum PDF Scraper")
st.write("Scrape PDFs from PIB press releases belonging to **Ministry of Petroleum & Natural Gas**.")

url = st.text_input("🔗 Enter PIB Press Release URL (e.g., https://www.pib.gov.in/allRel.aspx)")

if url:
    with st.spinner("🔍 Searching press releases..."):
        results = extract_petro_ministry_pdfs(url)

    if results:
        df = pd.DataFrame(results)
        st.success(f"✅ Found {len(df)} PDF(s) from Ministry of")
        st.dataframe(df)

        # Excel download
        output = BytesIO()
        df.to_excel(output, index=False)
        output.seek(0)
        st.download_button(
            label="📥 Download Excel Report",
            data=output,
            file_name="petroleum_ministry_pdfs.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("⚠️ No matching PDFs found for Ministry of Petroleum & Natural Gas.")


