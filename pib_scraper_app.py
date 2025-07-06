import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
import os
import re
import tempfile
from io import BytesIO
from pypdf import PdfReader
from transformers import pipeline

# Load summarizer
summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

# Helper function to extract press release links from a PIB ministry page
def extract_press_release_links(pib_url):
    response = requests.get(pib_url)
    soup = BeautifulSoup(response.content, "html.parser")
    links = []
    for a in soup.select("a.news_content a"):
        href = a.get("href")
        if href and "PressReleasePage.aspx" in href:
            links.append("https://www.pib.gov.in/" + href)
    return links

# Helper function to extract date from press release page
def extract_date_from_page(soup):
    date_tag = soup.find("span", id="ContentPlaceHolder1_lblDate")
    if date_tag:
        return date_tag.text.strip()
    return "Unknown"

# Extract PDFs from a press release page
def extract_pdf_links_from_release(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    date = extract_date_from_page(soup)
    pdf_links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.endswith(".pdf"):
            full_url = href if href.startswith("http") else "https://www.pib.gov.in" + href
            pdf_links.append((full_url, date))
    return pdf_links, url

# Download PDF and extract text
def download_and_extract_text(pdf_url):
    try:
        response = requests.get(pdf_url)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(response.content)
            tmp_file_path = tmp_file.name
        reader = PdfReader(tmp_file_path)
        text = " ".join([page.extract_text() or "" for page in reader.pages])
        os.remove(tmp_file_path)
        return text.strip()
    except:
        return ""

# Summarize text
def summarize_text(text):
    if not text:
        return "No content found."
    if len(text) > 4000:
        text = text[:4000]  # Trim to fit model limits
    summary = summarizer(text, max_length=150, min_length=30, do_sample=False)
    return summary[0]['summary_text']

# Streamlit UI
st.set_page_config(page_title="PIB Scraper & Summarizer", layout="wide")
st.title("📢 PIB Press Release PDF Scraper + LLM Summary")

url = st.text_input("🔗 Enter PIB Press Release Page URL (e.g., https://www.pib.gov.in/allRel.aspx?reg=3&lang=1):")
start_date = st.date_input("📅 Start Date", value=datetime(2025, 1, 1))
end_date = st.date_input("📅 End Date", value=datetime(2025, 6, 30))

if st.button("🔎 Search and Summarize"):
    if not url:
        st.error("Please enter a PIB press release page URL.")
    else:
        st.info("🔍 Scraping the page for PDF links...")
        release_links = extract_press_release_links(url)
        all_data = []

        for idx, link in enumerate(release_links):
            st.write(f"\n📄 Processing PDF {idx + 1}/{len(release_links)}")
            pdfs, release_page = extract_pdf_links_from_release(link)
            for pdf_url, date_str in pdfs:
                try:
                    date_obj = datetime.strptime(date_str, "%d %B %Y")
                    if start_date <= date_obj.date() <= end_date:
                        raw_text = download_and_extract_text(pdf_url)
                        summary = summarize_text(raw_text)
                        all_data.append({
                            "Date": date_str,
                            "PDF URL": pdf_url,
                            "Summary": summary,
                            "Press Release Page": release_page
                        })
                except Exception as e:
                    continue

        if all_data:
            df = pd.DataFrame(all_data)
            output = BytesIO()
            df.to_excel(output, index=False, engine='openpyxl')
            st.success(f"✅ Scraped and summarized {len(df)} relevant PDFs!")
            st.download_button("📥 Download Summary as Excel", data=output.getvalue(), file_name="pib_summary.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.warning("⚠️ No relevant PDFs found in this date range.")
