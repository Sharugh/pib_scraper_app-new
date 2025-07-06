import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime
from io import BytesIO
from transformers import pipeline
import torch
from pypdf import PdfReader
# Set device for summarizer
device = 0 if torch.cuda.is_available() else -1
summarizer = pipeline("summarization", model="facebook/bart-large-cnn", device=device)

st.title("📢 PIB Press Release PDF Scraper + LLM Summary")

pib_url = st.text_input("🔗 Enter PIB Press Release Page URL (e.g., https://pib.gov.in/allRel.aspx):")
start_date = st.date_input("📅 Start Date", value=datetime(2024, 1, 1))
end_date = st.date_input("📅 End Date", value=datetime(2024, 12, 31))

KEYWORDS = [
    "energy", "oil", "gas", "petroleum", "natural gas", "refinery", "refining", 
    "crude", "pricing", "shipping", "downstream", "IOCL", "ONGC", "BPCL", "HPCL",
    "Ministry of Petroleum", "hydrocarbon"
]

def extract_pdf_links(base_url):
    response = requests.get(base_url)
    soup = BeautifulSoup(response.text, "html.parser")
    anchors = soup.find_all("a", href=True)
    pdf_links = []

    for a in anchors:
        text = a.get_text(strip=True).lower()
        if any(kw.lower() in text for kw in KEYWORDS):
            link = a['href']
            if link.endswith(".pdf"):
                date_match = re.search(r'(\d{2})/(\d{2})/(\d{4})', a.parent.text)
                if date_match:
                    day, month, year = map(int, date_match.groups())
                    pub_date = datetime(year, month, day)
                    if start_date <= pub_date <= end_date:
                        pdf_links.append(("https://www.pib.gov.in" + link, pub_date.strftime("%Y-%m-%d")))
    return pdf_links

def extract_text_from_pdf(url):
    response = requests.get(url)
    reader = PdfReader(BytesIO(response.content))
    return "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])

def summarize(text):
    if len(text) < 100:
        return "Text too short to summarize."
    chunks = [text[i:i+1024] for i in range(0, len(text), 1024)]
    summaries = [summarizer(chunk, max_length=150, min_length=30, do_sample=False)[0]['summary_text'] for chunk in chunks]
    return " ".join(summaries)

if st.button("🔍 Fetch and Summarize PDFs"):
    if not pib_url:
        st.warning("Please enter a valid PIB URL.")
    else:
        st.info("🔎 Searching for PDFs on page...")
        links = extract_pdf_links(pib_url)

        if not links:
            st.warning("⚠️ No relevant PDFs found in this date range with matching keywords.")
        else:
            data = []
            for idx, (url, date) in enumerate(links):
                st.write(f"\n📄 Processing PDF {idx+1}/{len(links)}")
                try:
                    text = extract_text_from_pdf(url)
                    summary = summarize(text)
                    data.append({"Date": date, "URL": url, "Summary": summary})
                except Exception as e:
                    st.error(f"Error processing PDF {url}: {e}")

            if data:
                df = pd.DataFrame(data)
                st.dataframe(df)

                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Summary')
                    writer.close()
                st.download_button("📥 Download Summary as Excel", output.getvalue(), file_name="pib_summary.xlsx")
