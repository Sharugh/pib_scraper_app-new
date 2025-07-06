from pypdf import PdfReader
import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import re
from io import BytesIO
from pypdf import PdfReader
from transformers import pipeline

# ------------------ SETUP ------------------
# Load summarization pipeline
summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

# Ministry name to filter
TARGET_MINISTRY = "Ministry of Petroleum and Natural Gas"
KEYWORDS = [
    "energy", "petroleum", "crude", "refinery", "refined products", "downstream",
    "shipping", "gas", "oil", "pricing", "policy", "natural gas"
]

# ------------------ FUNCTIONS ------------------

def extract_press_releases(base_url):
    try:
        response = requests.get(base_url, timeout=10)
        soup = BeautifulSoup(response.content, "html.parser")

        pdf_links = []
        articles = soup.find_all("div", class_="col-sm-12 col-md-8 col-lg-8 content")

        for article in articles:
            title_tag = article.find("a")
            if not title_tag or not title_tag.has_attr("href"):
                continue

            title_text = title_tag.text.strip().lower()
            href = title_tag["href"]
            full_link = requests.compat.urljoin(base_url, href)

            # Only go into Ministry of Petroleum pages
            if any(keyword in title_text for keyword in KEYWORDS):
                pdf_links.append((title_tag.text.strip(), full_link))

        return pdf_links
    except Exception as e:
        st.error(f"Error extracting press releases: {e}")
        return []

def extract_pdf_link(press_release_url):
    try:
        res = requests.get(press_release_url, timeout=10)
        soup = BeautifulSoup(res.content, "html.parser")
        pdf_link_tag = soup.find("a", href=re.compile(r"\.pdf$"))
        if pdf_link_tag:
            return requests.compat.urljoin(press_release_url, pdf_link_tag["href"])
    except:
        return None
    return None

def download_and_extract_text(pdf_url):
    try:
        response = requests.get(pdf_url)
        reader = PdfReader(BytesIO(response.content))
        full_text = ""
        for page in reader.pages:
            full_text += page.extract_text() or ""
        return full_text
    except:
        return ""

def summarize_text(text):
    chunks = [text[i:i+1000] for i in range(0, len(text), 1000)]
    summary = ""
    for chunk in chunks:
        try:
            s = summarizer(chunk, max_length=150, min_length=40, do_sample=False)[0]['summary_text']
            summary += s + "\n"
        except:
            continue
    return summary

# ------------------ STREAMLIT UI ------------------
st.set_page_config(layout="wide")
st.title("📢 PIB Ministry of Petroleum PDF Extractor + Summarizer")

pib_url = st.text_input("🔗 Enter PIB Ministry Press Release URL", "https://pib.gov.in/allRel.aspx?reg=3&lang=1")

if st.button("🔍 Fetch and Process PDFs"):
    with st.spinner("Searching for relevant press releases..."):
        releases = extract_press_releases(pib_url)

    if not releases:
        st.warning("⚠️ No relevant press releases found.")
    else:
        st.success(f"✅ Found {len(releases)} relevant press releases.")

        results = []
        for title, link in releases:
            pdf_link = extract_pdf_link(link)
            if not pdf_link:
                continue

            text = download_and_extract_text(pdf_link)
            if not text:
                continue

            summary = summarize_text(text)
            results.append({
                "Title": title,
                "Press Release URL": link,
                "PDF URL": pdf_link,
                "Summary": summary
            })

        if results:
            df = pd.DataFrame(results)
            st.dataframe(df[["Title", "Press Release URL", "PDF URL", "Summary"]])

            excel_data = BytesIO()
            df.to_excel(excel_data, index=False)
            st.download_button(
                label="📥 Download Summary Excel",
                data=excel_data.getvalue(),
                file_name="pib_petroleum_press_summaries.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("No summaries generated. Please try with a broader timeline or keywords.")
