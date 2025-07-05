import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from pypdf import PdfReader
from transformers import pipeline
from datetime import datetime
import io
import re

# 🎯 Only filter Ministry of Petroleum
TARGET_MINISTRY = "Ministry of Petroleum & Natural Gas"

# 🧠 LLM summarizer
@st.cache_resource
def load_summarizer():
    return pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

summarizer = load_summarizer()

# ✅ Keywords
KEYWORDS = [
    "energy", "policy", "petroleum", "refinery", "refined products", "downstream",
    "crude oil", "shipping", "pricing", "oil trade", "refining companies"
]

# 🔍 Extract press release links from main page
def get_press_release_links(url):
    res = requests.get(url)
    soup = BeautifulSoup(res.content, "html.parser")
    links = soup.select("a[href*='PressReleseDetail.aspx?PRID=']")
    return ["https://www.pib.gov.in/" + link['href'] for link in links]

# 📄 Check if page belongs to Ministry of Petroleum
def is_petroleum_ministry(page_url):
    try:
        res = requests.get(page_url)
        soup = BeautifulSoup(res.content, "html.parser")
        ministry_tag = soup.find("span", id="ContentPlaceHolder1_lblMinistry")
        if ministry_tag:
            return TARGET_MINISTRY.lower() in ministry_tag.text.strip().lower()
    except:
        pass
    return False

# 📅 Extract date
def extract_date_from_page(url):
    try:
        res = requests.get(url)
        soup = BeautifulSoup(res.content, "html.parser")
        date_tag = soup.find("span", {"id": "ContentPlaceHolder1_lblDate"})
        return date_tag.text.strip() if date_tag else "N/A"
    except:
        return "N/A"

# 📥 Extract PDF URL
def extract_pdf_url_from_page(url):
    try:
        res = requests.get(url)
        soup = BeautifulSoup(res.content, "html.parser")
        pdf_link = soup.find("a", href=re.compile(r".*\.pdf"))
        if pdf_link:
            href = pdf_link["href"]
            return href if href.startswith("http") else "https://www.pib.gov.in/" + href
    except:
        pass
    return None

# 📖 Read PDF content
def extract_pdf_text(pdf_url):
    try:
        response = requests.get(pdf_url)
        if response.status_code == 200:
            reader = PdfReader(io.BytesIO(response.content))
            return "".join([page.extract_text() for page in reader.pages if page.extract_text()])
    except:
        return ""
    return ""

# 🧠 Summarize text
def summarize_text(text):
    chunks = [text[i:i+1024] for i in range(0, len(text), 1024)]
    summaries = []
    for chunk in chunks:
        summary = summarizer(chunk, max_length=150, min_length=30, do_sample=False)
        summaries.append(summary[0]["summary_text"])
    return " ".join(summaries)

# 🚀 Streamlit UI
st.set_page_config(page_title="PIB Petroleum Scraper + Summary", layout="wide")
st.title("📢 PIB Press Release PDF Scraper for Petroleum Ministry + LLM Summary")

base_url = st.text_input("🔗 Enter PIB URL (e.g., https://www.pib.gov.in/allRel.aspx):", "https://www.pib.gov.in/allRel.aspx")
start_date = st.date_input("📅 Start Date", datetime(2024, 1, 1))
end_date = st.date_input("📅 End Date", datetime(2025, 6, 30))

if st.button("🔍 Fetch PDFs"):
    st.info("🔍 Scraping press releases...")
    press_release_links = get_press_release_links(base_url)

    results = []

    for i, pr_link in enumerate(press_release_links):
        st.write(f"🔎 Checking press release {i+1}/{len(press_release_links)}")

        if not is_petroleum_ministry(pr_link):
            continue

        date_str = extract_date_from_page(pr_link)
        try:
            press_date = datetime.strptime(date_str, "%d %b %Y")
            if not (start_date <= press_date.date() <= end_date):
                continue
        except:
            continue

        pdf_url = extract_pdf_url_from_page(pr_link)
        if not pdf_url:
            continue

        pdf_text = extract_pdf_text(pdf_url)
        if not any(keyword.lower() in pdf_text.lower() for keyword in KEYWORDS):
            continue

        summary = summarize_text(pdf_text)

        results.append({
            "Date": date_str,
            "Press Release Page": pr_link,
            "PDF URL": pdf_url,
            "Summary": summary
        })

    if results:
        df = pd.DataFrame(results)

        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False, engine='openpyxl')
        excel_buffer.seek(0)

        st.success(f"✅ Found {len(df)} relevant press releases.")
        st.dataframe(df)

        st.download_button(
            label="📥 Download Summary as Excel",
            data=excel_buffer,
            file_name="PIB_Petroleum_Summary.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("⚠️ No relevant PDFs found for the Petroleum Ministry in the selected range.")
