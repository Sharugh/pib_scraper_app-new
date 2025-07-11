# pib_scraper_streamlit.py

import streamlit as st
from selenium import webdriver
from selenium.webdriver.edge.service import Service  # ✅ NEW: Use Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd

# ✅ 1️⃣ YOUR DRIVER PATH
edge_driver_path = "C:\\Users\\sharugh.a\\Downloads\\edgedriver_win64\\msedgedriver.exe"

# ✅ 2️⃣ Setup Selenium Options
options = Options()
options.use_chromium = True
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")

# ✅ 3️⃣ Streamlit UI
st.title("📄 PIB Press Release PDF Collector (Edge Headless + Selenium)")
url = st.text_input(
    "🔗 Enter PIB Press Release Page URL",
    "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2121952"
)

if st.button("🔍 Scrape Press Release"):
    with st.spinner("Launching Edge headless browser and scraping..."):
        try:
            # ✅ 4️⃣ Setup Service for Edge (Selenium 4+)
            service = Service(executable_path=edge_driver_path)

            # ✅ 5️⃣ Start WebDriver with Service
            driver = webdriver.Edge(service=service, options=options)
            driver.get(url)

            wait = WebDriverWait(driver, 20)

            # ✅ 6️⃣ Try to find Ministry name
            ministry_name = wait.until(
                EC.presence_of_element_located((By.XPATH, "//span[@id='lblMinistry']"))
            ).text.strip()

            # ✅ 7️⃣ Find Press Release Title
            title = wait.until(
                EC.presence_of_element_located((By.XPATH, "//span[@id='lblTitle']"))
            ).text.strip()

            # ✅ 8️⃣ Find PDF download link (if any)
            pdf_link = ""
            try:
                pdf_element = driver.find_element(By.XPATH, "//a[contains(@href, '.pdf')]")
                pdf_link = pdf_element.get_attribute("href")
            except:
                pdf_link = "No PDF found"

            # ✅ 9️⃣ Get Date (optional)
            date = wait.until(
                EC.presence_of_element_located((By.XPATH, "//span[@id='lblDate']"))
            ).text.strip()

            # ✅ 10️⃣ Create DataFrame
            data = {
                "Ministry": [ministry_name],
                "Title": [title],
                "Date": [date],
                "PDF Link": [pdf_link],
                "Source URL": [url]
            }
            df = pd.DataFrame(data)

            st.success("✅ Scraping Complete!")
            st.dataframe(df)

            # ✅ 11️⃣ Download CSV
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Download CSV",
                csv,
                "press_release.csv",
                "text/csv"
            )

            driver.quit()

        except Exception as e:
            st.error(f"❌ Scraping failed: {e}")

