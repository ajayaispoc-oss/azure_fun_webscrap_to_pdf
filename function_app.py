import azure.functions as func
import logging
import requests
import io
from fpdf import FPDF  # ➡️ Zero-dependency pure Python PDF generator

app = func.FunctionApp()

@app.timer_trigger(schedule="0 */10 * * * *", arg_name="scrapetimer", run_on_startup=False)
@app.blob_output(arg_name="pdfblob", 
                 path="input-container/scraped_report_{DateTime}.pdf", 
                 connection="AzureWebJobsStorage",
                 data_type="binary") # ➡️ Leaves the file as binary PDF bytes
def web_scrape_to_pdf_pipeline(scrapetimer: func.TimerRequest, pdfblob: func.Out[bytes]):
    logging.info("--- Automated Web Scraping & PDF Ingestion Started ---")

    target_url = "https://example.com" 
    
    try:
        # 1. WEB SCRAPE: Fetch the active web page text
        logging.info(f"Scraping content from target: {target_url}")
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(target_url, headers=headers, timeout=20)
        
        if response.status_code != 200:
            logging.error(f"❌ Scraping failed. Status: {response.status_code}")
            return
            
        # Extract a structured text string from the response 
        web_text = response.text[:5000] 

        # 2. PDF GENERATION: Compile document structure in memory via FPDF
        logging.info("Compiling data stream into pure-Python PDF format...")
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        
        # Write the text into the PDF document safely handling character encodings
        pdf.multi_cell(0, 10, txt=web_text.encode('utf-8').decode('latin-1', 'ignore'))
        
        # Convert the compiled internal PDF stream to output bytes
        pdf_bytes = pdf.output()

        # 3. EXPORT TO AZURE STORAGE
        if len(pdf_bytes) == 0:
            logging.error("❌ Generated PDF is empty. Aborting write.")
            return

        pdfblob.set(pdf_bytes)
        logging.info(f"✓ Success! Web page saved as PDF file size: {len(pdf_bytes)} bytes.")

    except Exception as e:
        logging.error(f"❌ Pipeline module failed: {str(e)}")