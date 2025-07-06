import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import requests
import pandas as pd
import re
from io import BytesIO
from pypdf import PdfReader
from transformers import pipeline

# Set device to CPU explicitly
import torch
DEVICE = "cpu"

def initialize_summarizer():
    return pipeline("summarization", model="sshleifer/distilbart-cnn-12-6", device=0 if torch.cuda.is_available() else -1)

summarizer = initialize_summarizer()

st.set_page_config(page_title="📢 PIB Scraper with Summary", layout="wide")
st.title("📢 PIB Press Release PDF Scraper + LLM Summary")

# User Inputs
pib_url = st.text_input("🔗 Enter PIB Press Release Page URL (e.g., https://pib.gov.in/allRel.aspx?reg=3&lang=1):")
start_date = st.date_input("📅 Start Date")
end_date = st.date_input("📅 End Date")

keywords = ["energy", "petroleum", "refined products", "refineries", "refining companies",
            "downstream", "crude oil trade", "pricing", "shipping", "oil", "gas", "natural gas"]

@st.cache_data(show_spinner=False)
def extract_pdf_links(pib_url):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)
    driver.get(pib_url)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    pdf_links = []
    for link in soup.find_all("a", href=True):
        href = link["href"]
        text = link.text.strip().lower()
        if href.endswith(".pdf") and any(k in text for k in keywords):
            full_link = href if href.startswith("http") else "https://www.pib.gov.in/" + href.lstrip("/")
            pdf_links.append((link.text.strip(), full_link))
    return pdf_links

def extract_text_from_pdf(pdf_url):
    try:
        response = requests.get(pdf_url)
        if response.status_code == 200:
            pdf = PdfReader(BytesIO(response.content))
            text = " ".join(page.extract_text() or "" for page in pdf.pages)
            return text.strip()
        else:
            return ""
    except Exception as e:
        return ""

def summarize_text(text):
    chunks = [text[i:i + 1000] for i in range(0, len(text), 1000)]
    summaries = []
    for chunk in chunks:
        try:
            out = summarizer(chunk, max_length=150, min_length=30, do_sample=False)
            summaries.append(out[0]['summary_text'])
        except:
            continue
    return " ".join(summaries)

if st.button("🔎 Fetch & Summarize PDFs") and pib_url:
    with st.spinner("🔍 Searching for PDFs on page..."):
        links = extract_pdf_links(pib_url)

    if not links:
        st.warning("⚠️ No relevant PDFs found on this page with matching keywords.")
    else:
        summaries = []
        for i, (title, link) in enumerate(links, start=1):
            st.write(f"\n📄 Processing PDF {i}/{len(links)}")
            raw_text = extract_text_from_pdf(link)
            summary = summarize_text(raw_text)
            summaries.append({"Title": title, "URL": link, "Summary": summary})

        df = pd.DataFrame(summaries)
        st.dataframe(df)

        output = BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        st.download_button("📥 Download Summary as Excel", output.getvalue(), "pib_summary.xlsx")
