import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import os
from pypdf import PdfReader
from transformers import pipeline

# Set up summarizer
summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

# Title
st.title("📢 PIB Press Release PDF Scraper with LLM Summary")

# Input URL
url = st.text_input("Enter PIB Press Release Page URL (e.g., https://pib.gov.in/...):")

def scrape_pdfs_and_links(page_url):
    try:
        response = requests.get(page_url)
        soup = BeautifulSoup(response.text, "html.parser")

        pdf_links = []
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if ".pdf" in href:
                full_pdf_url = href if href.startswith("http") else "https://pib.gov.in" + href
                pdf_links.append(full_pdf_url)
        return pdf_links
    except Exception as e:
        st.error(f"Failed to scrape PDFs: {e}")
        return []

def download_pdf(pdf_url):
    try:
        response = requests.get(pdf_url, stream=True)
        filename = pdf_url.split("/")[-1]
        with open(filename, "wb") as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        return filename
    except Exception as e:
        st.error(f"Error downloading {pdf_url}: {e}")
        return None

def extract_text_from_pdf(file_path):
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text.strip()
    except Exception as e:
        st.error(f"Failed to extract text: {e}")
        return ""

def summarize_text(text):
    try:
        if len(text) < 100:
            return "Text too short for summary."
        summary = summarizer(text[:1024], max_length=150, min_length=30, do_sample=False)
        return summary[0]["summary_text"]
    except Exception as e:
        return f"Summarization failed: {e}"

if url:
    st.info("🔍 Scraping the page for PDF links...")
    pdf_links = scrape_pdfs_and_links(url)

    if not pdf_links:
        st.warning("No PDFs found on this page.")
    else:
        st.success(f"Found {len(pdf_links)} PDFs!")

        summary_data = []
        for i, pdf_url in enumerate(pdf_links[:50]):  # Limit to 50
            st.write(f"📄 Processing PDF {i + 1}/{len(pdf_links)}")
            filename = download_pdf(pdf_url)
            if not filename:
                continue

            raw_text = extract_text_from_pdf(filename)
            summary = summarize_text(raw_text)

            summary_data.append({
                "Date": datetime.now().strftime("%Y-%m-%d"),
                "PDF Link": pdf_url,
                "Press Release Page": url,
                "Summary": summary
            })

            # Cleanup
            os.remove(filename)

        if summary_data:
            df = pd.DataFrame(summary_data)
            st.dataframe(df)

            # Save Excel
            excel_name = "PIB_Press_Release_Summary.xlsx"
            df.to_excel(excel_name, index=False)

            with open(excel_name, "rb") as file:
                st.download_button("📥 Download Excel Report", file, file_name=excel_name)
