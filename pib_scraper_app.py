import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import time
from PyPDF2 import PdfReader
from transformers import pipeline

# 📁 Setup
PDF_DIR = "pib_pdfs"
os.makedirs(PDF_DIR, exist_ok=True)
summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

# 🔗 Scrape press release links
def scrape_press_releases(pages=3):
    base_url = "https://pib.gov.in/allRel.aspx"
    headers = {"User-Agent": "Mozilla/5.0"}
    press_data = []

    for page in range(1, pages + 1):
        url = f"{base_url}?PageId={page}"
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")
        articles = soup.select("div.content-area div.col-sm-12 a")

        for a in articles:
            title = a.text.strip()
            href = a.get("href")
            if href:
                full_url = "https://pib.gov.in/" + href
                press_data.append({"title": title, "url": full_url})
        time.sleep(1)

    return press_data

# 📎 Find PDF link
def extract_pdf_link(detail_url):
    res = requests.get(detail_url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(res.text, "html.parser")
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if href.endswith(".pdf"):
            return href if href.startswith("http") else "https://pib.gov.in/" + href.lstrip("/")
    return None

# ⬇️ Download PDF
def download_pdf(pdf_url):
    try:
        res = requests.get(pdf_url)
        filename = os.path.join(PDF_DIR, pdf_url.split("/")[-1])
        with open(filename, "wb") as f:
            f.write(res.content)
        return filename
    except:
        return None

# 📄 Extract text from PDF
def extract_text_from_pdf(filepath):
    try:
        reader = PdfReader(filepath)
        text = ""
        for page in reader.pages[:3]:
            text += page.extract_text() or ""
        return text
    except:
        return ""

# 🧠 Summarize text
def summarize_text(text):
    try:
        if len(text.strip()) < 100:
            return "Too short to summarize."
        chunks = [text[i:i+1000] for i in range(0, len(text), 1000)]
        summary = ""
        for chunk in chunks[:3]:
            summary += summarizer(chunk, max_length=150, min_length=40, do_sample=False)[0]['summary_text'] + " "
        return summary.strip()
    except:
        return "Summary failed."

# 🟢 STREAMLIT UI
st.title("📢 PIB Press Release Summarizer")
pages_to_fetch = st.slider("How many PIB pages to scrape?", 1, 5, 2)
fetch_btn = st.button("🔍 Start Scraping")

if fetch_btn:
    with st.spinner("Fetching Press Releases..."):
        press_releases = scrape_press_releases(pages=pages_to_fetch)

    st.success(f"Found {len(press_releases)} press releases.")
    records = []
    progress_bar = st.progress(0)

    for i, press in enumerate(press_releases[:50]):
        st.write(f"📄 Processing: {press['title']}")
        pdf_url = extract_pdf_link(press['url'])

        if not pdf_url:
            st.warning("No PDF found.")
            progress_bar.progress((i + 1) / len(press_releases[:50]))
            continue

        filename = download_pdf(pdf_url)
        if not filename:
            st.error("Failed to download PDF.")
            progress_bar.progress((i + 1) / len(press_releases[:50]))
            continue

        text = extract_text_from_pdf(filename)
        summary = summarize_text(text)

        records.append({
            "Date": time.strftime("%Y-%m-%d"),
            "Title": press['title'],
            "Press Release Page": press['url'],
            "PDF Link": pdf_url,
            "Summary": summary
        })

        progress_bar.progress((i + 1) / len(press_releases[:50]))

    df = pd.DataFrame(records)
    st.success("✅ Done! Download Excel below.")
    st.dataframe(df)

    # Excel export
    excel_filename = "PIB_Press_Summary.xlsx"
    df.to_excel(excel_filename, index=False)
    with open(excel_filename, "rb") as f:
        st.download_button("⬇️ Download Excel", f, file_name=excel_filename, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

