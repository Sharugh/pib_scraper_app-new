import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import time
from transformers import pipeline
import torch
from pypdf import PdfReader

# ---------------------- LLM Summarizer ----------------------
@st.cache_resource
def load_summarizer():
    device = 0 if torch.cuda.is_available() else -1
    return pipeline("summarization", model="sshleifer/distilbart-cnn-12-6", device=device)

def summarize_pdf_text(text):
    summarizer = load_summarizer()
    text = text[:1024]  # limit for distilBART
    summary = summarizer(text, max_length=150, min_length=30, do_sample=False)
    return summary[0]['summary_text']

# ---------------------- PDF Downloader ----------------------
def download_pdf(pdf_url):
    try:
        response = requests.get(pdf_url, stream=True)
        if response.status_code == 200:
            filename = pdf_url.split("/")[-1]
            with open(filename, "wb") as pdf_file:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        pdf_file.write(chunk)
            return filename
    except Exception:
        return None
    return None

# ---------------------- PDF Text Extractor ----------------------
def extract_text_from_pdf(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages[:2]:  # Read first 2 pages for summary
            text += page.extract_text() or ""
        return text
    except Exception:
        return ""

# ---------------------- PIB Scraper ----------------------
def fetch_press_releases(ministry_id, from_date, to_date, max_results=50):
    collected_data = []
    base_url = "https://pib.gov.in/PressReleaseIframePage.aspx"

    payload = {
        "MinID": ministry_id,
        "CatID": 0,
        "DateFrom": from_date.strftime("%m/%d/%Y"),
        "DateTo": to_date.strftime("%m/%d/%Y"),
        "LangID": 1,
    }

    session = requests.Session()

    for start in range(0, max_results, 10):
        payload["start"] = start
        response = session.post(base_url, data=payload)

        if response.status_code != 200:
            break

        soup = BeautifulSoup(response.text, "html.parser")
        items = soup.select(".col-sm-9.col-xs-12.contentnew")

        if not items:
            break

        for item in items:
            title = item.find("a").text.strip()
            relative_link = item.find("a")["href"]
            full_link = "https://pib.gov.in/" + relative_link
            date = item.find("span", class_="contentdate").text.strip()
            collected_data.append((title, full_link, date))

        time.sleep(1)

    return collected_data

# ---------------------- Streamlit App ----------------------
st.title("📢 PIB Press Release PDF Downloader + AI Summarizer")

ministries = {
    "Ministry of Petroleum & Natural Gas": 33,
    "Ministry of Finance": 25,
    "Ministry of Health and Family Welfare": 26,
    "Ministry of Education": 27,
}

selected_ministry = st.selectbox("🔽 Select Ministry", list(ministries.keys()))
from_date = st.date_input("📅 Start Date")
to_date = st.date_input("📅 End Date")
max_count = st.number_input("🔢 Number of press releases to fetch", min_value=1, max_value=100, value=20)

if st.button("🔍 Fetch & Process"):
    with st.spinner("Fetching press releases..."):
        press_releases = fetch_press_releases(
            ministry_id=ministries[selected_ministry],
            from_date=from_date,
            to_date=to_date,
            max_results=max_count
        )

    if not press_releases:
        st.warning("No press releases found for selected ministry and date range.")
    else:
        results = []
        for title, link, date in press_releases:
            try:
                page = requests.get(link)
                soup = BeautifulSoup(page.text, "html.parser")
                pdf_link = None
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    if href.lower().endswith(".pdf"):
                        pdf_link = "https://pib.gov.in/" + href.lstrip("/")
                        break

                if pdf_link:
                    filename = download_pdf(pdf_link)
                    text = extract_text_from_pdf(filename)
                    summary = summarize_pdf_text(text) if text.strip() else "No readable text found in PDF"
                else:
                    pdf_link = "No PDF Found"
                    summary = "No PDF to summarize"

                results.append({
                    "Title": title,
                    "PIB Page Link": link,
                    "PDF Link": pdf_link,
                    "Date": date,
                    "Summary": summary
                })

            except Exception as e:
                results.append({
                    "Title": title,
                    "PIB Page Link": link,
                    "PDF Link": "Error",
                    "Date": date,
                    "Summary": str(e)
                })

        df = pd.DataFrame(results)
        st.success(f"✅ Fetched and processed {len(df)} press releases.")
        st.dataframe(df)

        # Excel download
        excel_file = "pib_press_releases.xlsx"
        df.to_excel(excel_file, index=False)
        with open(excel_file, "rb") as f:
            st.download_button(
                "📥 Download Excel File",
                f,
                file_name=excel_file,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
