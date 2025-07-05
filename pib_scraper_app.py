import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from PyPDF2 import PdfReader
from transformers import pipeline
from datetime import datetime
import io
import re

# 📌 Set keywords to filter relevant PDFs
KEYWORDS = [
    "energy", "policy", "petroleum", "refinery", "refined products", "downstream",
    "crude oil", "shipping", "pricing", "oil trade", "refining companies"
]

# 💡 Load LLM summarizer
@st.cache_resource
def load_summarizer():
    return pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

summarizer = load_summarizer()

# 🔍 Extract all press release links from PIB main page
def get_press_release_links(base_url):
    res = requests.get(base_url)
    soup = BeautifulSoup(res.content, "html.parser")
    links = soup.select("a[href*='PressReleseDetail.aspx?PRID=']")
    full_links = ["https://www.pib.gov.in/" + link['href'] for link in links]
    return full_links

# 📥 Extract PDF URL from individual press release page
def extract_pdf_url_from_page(url):
    try:
        res = requests.get(url)
        soup = BeautifulSoup(res.content, "html.parser")
        pdf_link = soup.find("a", href=re.compile(r".*\.pdf"))
        if pdf_link:
            return pdf_link['href'] if pdf_link['href'].startswith("http") else "https://www.pib.gov.in/" + pdf_link['href']
    except:
        return None

# 📖 Extract and clean text from PDF
def extract_pdf_text(pdf_url):
    try:
        response = requests.get(pdf_url)
        if response.status_code == 200:
            reader = PdfReader(io.BytesIO(response.content))
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            return text.strip()
    except:
        return ""
    return ""

# 🧠 Summarize text using LLM
def summarize_text(text):
    chunks = [text[i:i+1024] for i in range(0, len(text), 1024)]
    summaries = []
    for chunk in chunks:
        summary = summarizer(chunk, max_length=150, min_length=30, do_sample=False)
        summaries.append(summary[0]['summary_text'])
    return " ".join(summaries)

# 📅 Extract date from PIB page content
def extract_date_from_page(url):
    try:
        res = requests.get(url)
        soup = BeautifulSoup(res.content, "html.parser")
        date_tag = soup.find("span", {"id": "ContentPlaceHolder1_lblDate"})
        return date_tag.text.strip() if date_tag else "N/A"
    except:
        return "N/A"

# 🚀 Streamlit UI
st.set_page_config(page_title="PIB PDF Scraper + LLM Summary", layout="wide")
st.title("📢 PIB Press Release PDF Scraper + LLM Summary")

base_url = st.text_input(
    "🔗 Enter PIB Press Release Page URL (e.g., https://www.pib.gov.in/allRel.aspx):",
    value="https://www.pib.gov.in/allRel.aspx"
)

start_date = st.date_input("📅 Start Date", datetime(2025, 1, 1))
end_date = st.date_input("📅 End Date", datetime(2025, 6, 30))

if st.button("🔎 Search and Summarize"):
    st.info("🔍 Searching for PDFs on page...")
    press_release_links = get_press_release_links(base_url)

    results = []
    for i, link in enumerate(press_release_links):
        st.write(f"📄 Processing PDF {i+1}/{len(press_release_links)}")

        date_str = extract_date_from_page(link)
        try:
            release_date = datetime.strptime(date_str, "%d %b %Y")
        except:
            release_date = None

        if release_date and not (start_date <= release_date.date() <= end_date):
            continue  # Skip out-of-range dates

        pdf_url = extract_pdf_url_from_page(link)
        if not pdf_url:
            continue

        pdf_text = extract_pdf_text(pdf_url)
        if not pdf_text or not any(keyword.lower() in pdf_text.lower() for keyword in KEYWORDS):
            continue  # Skip irrelevant PDFs

        summary = summarize_text(pdf_text)
        results.append({
            "Date": date_str,
            "PDF URL": pdf_url,
            "Press Release Page": link,
            "Summary": summary
        })

    if results:
        df = pd.DataFrame(results)

        # Save to Excel using BytesIO
        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False, engine='openpyxl')
        excel_buffer.seek(0)

        st.success(f"✅ Done! Found {len(df)} relevant PDFs.")
        st.dataframe(df)
        st.download_button(
            label="📥 Download Summary as Excel",
            data=excel_buffer,
            file_name="pib_summary.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("⚠️ No relevant PDFs found in this date range with matching keywords.")
