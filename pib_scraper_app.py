import streamlit as st
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
from transformers import pipeline
import pandas as pd
import tempfile
import datetime
import re

# Load summarization model
@st.cache_resource
def load_model():
    return pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

summarizer = load_model()

# Extract PDF text
def extract_pdf_text(url):
    try:
        response = requests.get(url)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(response.content)
            reader = PdfReader(tmp.name)
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text
        return text
    except:
        return ""

# Summarize large text
def summarize_text(text):
    if not text.strip():
        return "No extractable content."
    chunks = [text[i:i+1000] for i in range(0, len(text), 1000)]
    summaries = []
    for chunk in chunks[:3]:  # Limit to 3 chunks
        try:
            result = summarizer(chunk, max_length=150, min_length=30, do_sample=False)
            summaries.append(result[0]['summary_text'])
        except:
            continue
    return " ".join(summaries) if summaries else "Summary failed."

# Scrape PIB page for PDFs
def scrape_pib_page(base_url, start_date, end_date, keywords):
    res = requests.get(base_url)
    soup = BeautifulSoup(res.text, "html.parser")
    links = soup.find_all("a", href=True)

    data = []
    for tag in links:
        title = tag.get_text(strip=True)
        href = tag['href']
        if not href.endswith(".pdf"):
            continue
        full_link = href if href.startswith("http") else f"https://pib.gov.in/{href}"
        if any(k.lower() in title.lower() for k in keywords):
            match = re.search(r"(\d{1,2}/\d{1,2}/\d{4})", title)
            date = None
            if match:
                try:
                    date = datetime.datetime.strptime(match.group(1), "%d/%m/%Y").date()
                except:
                    pass
            if date is None or (start_date <= date <= end_date):
                data.append((title, full_link, date))
    return data

# UI
st.title("📢 PIB Press Release PDF Scraper + LLM Summary")

url = st.text_input("🔗 Enter PIB Press Release Page URL (e.g., https://pib.gov.in/allRel.aspx):", "https://pib.gov.in/allRel.aspx")

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("📅 Start Date", datetime.date.today() - datetime.timedelta(days=30))
with col2:
    end_date = st.date_input("📅 End Date", datetime.date.today())

keywords = [
    "energy", "policy", "petroleum", "refined products", "refineries", "refining companies",
    "downstream", "crude oil", "crude trade", "pricing", "shipping", "fuel", "gasoline", "diesel"
]

if st.button("🔍 Fetch PDFs & Summarize"):
    st.info("🔎 Searching for PDFs on page...")
    pdfs = scrape_pib_page(url, start_date, end_date, keywords)

    if not pdfs:
        st.warning("No matching PDFs found.")
    else:
        results = []
        for idx, (title, pdf_url, date) in enumerate(pdfs):
            st.write(f"📄 Processing PDF {idx+1}/{len(pdfs)}")
            raw_text = extract_pdf_text(pdf_url)
            summary = summarize_text(raw_text)
            results.append({
                "Title": title,
                "Date": date or "N/A",
                "PDF Link": pdf_url,
                "Summary": summary,
                "Source Page": url
            })

        df = pd.DataFrame(results)
        st.dataframe(df)
        st.download_button("📥 Download Summary as Excel", df.to_excel(index=False), "pib_summary.xlsx")
