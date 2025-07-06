import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
from io import BytesIO
from pypdf import PdfReader
from transformers import pipeline

# Load the summarizer
summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

# Keywords to filter relevant PDFs
TARGET_KEYWORDS = [
    "petroleum", "natural gas", "energy", "policy", "refined products",
    "refineries", "refining", "downstream", "crude oil", "oil trade",
    "oil pricing", "shipping", "ONGC", "IOCL", "HPCL", "BPCL"
]

# Function to scrape PIB PDF links
@st.cache_data(show_spinner=False)
def scrape_pdfs(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        base_url = "https://www.pib.gov.in"
        pdf_data = []

        for link in soup.find_all("a", href=True):
            href = link['href']
            text = link.get_text(strip=True)
            if href.endswith(".pdf") and any(kw in text.lower() for kw in TARGET_KEYWORDS):
                full_link = href if href.startswith("http") else base_url + href
                date_tag = link.find_parent("td")
                pub_date = date_tag.get_text(strip=True) if date_tag else ""
                pdf_data.append({"date": pub_date, "text": text, "url": full_link})
        return pdf_data
    except Exception as e:
        return []

# Function to summarize PDF content
def summarize_pdf(pdf_url):
    try:
        response = requests.get(pdf_url)
        pdf = PdfReader(BytesIO(response.content))
        full_text = " ".join(page.extract_text() or "" for page in pdf.pages)
        if not full_text.strip():
            return "No text found."

        chunks = [full_text[i:i+1024] for i in range(0, len(full_text), 1024)]
        summaries = [summarizer(chunk, max_length=150, min_length=30, do_sample=False)[0]['summary_text'] for chunk in chunks]
        return " ".join(summaries)
    except Exception as e:
        return "Summary error."

# Streamlit UI
st.title("📑 PIB Ministry of Petroleum PDF Scraper & Summarizer")
st.write("Enter a PIB URL related to the Ministry of Petroleum and Natural Gas.")

url = st.text_input("Enter the PIB Ministry URL (e.g., https://pib.gov.in/allRel.aspx?reg=3&lang=1)")

if url:
    with st.spinner("🔍 Searching for PDFs related to petroleum and energy..."):
        pdf_info = scrape_pdfs(url)

    if pdf_info:
        st.success(f"✅ Found {len(pdf_info)} matching PDF(s). Generating summaries...")

        summary_data = []
        for entry in pdf_info:
            summary = summarize_pdf(entry['url'])
            summary_data.append({
                "Date": entry['date'],
                "PDF Title": entry['text'],
                "PDF URL": entry['url'],
                "Summary": summary
            })

        df = pd.DataFrame(summary_data)
        st.dataframe(df)

        # Excel Download Button
        excel_buffer = BytesIO()
        df.to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)
        st.download_button(
            label="📥 Download Summary Report (Excel)",
            data=excel_buffer,
            file_name="PIB_Energy_Summaries.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("⚠️ No relevant PDFs found with petroleum or energy-related keywords.")
