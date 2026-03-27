"""Use Gemini Vision to extract only the PPC sub-table from KDHP petition."""
import sys, os, fitz
sys.path.insert(0, r'c:\Users\adwai\OneDrive\Desktop\K-Project\kserc-trueup-engine')

from dotenv import load_dotenv
load_dotenv(r'c:\Users\adwai\OneDrive\Desktop\K-Project\kserc-trueup-engine\.env')

from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

# Convert petition pages to images
pdf_path = r'C:\Users\adwai\OneDrive\Desktop\K-Project\Documents\Petition for the approval of Truing up of accounts for the FYs 2024-25. - KDHPCL\1_Petition.pdf'
doc = fitz.open(pdf_path)

# Send ALL pages as images
parts = []
for i in range(len(doc)):
    pix = doc[i].get_pixmap(dpi=150)
    img_bytes = pix.tobytes("png")
    parts.append(types.Part.from_bytes(data=img_bytes, mime_type="image/png"))

parts.append(types.Part.from_text(text="""
Look at this KDHP petition PDF. Find the Power Purchase Cost sub-table.
This table has rows like:
- Normal Demand Charge, Excess Demand Charge, Total Demand Charges
- Energy Charge
- Total Charges-Rs/Lakhs (or Total Power Purchase Cost)
- Less: Adjustment for excess line loss
- Net Charges-Rs/Lakhs
- Rate per unit

Extract ALL values from the 2024-25 Audited/Actual column. Return as a simple numbered list.
Also find Total Power Purchase Cost from the main ARR summary table.
"""))

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=parts,
)

print(response.text)
doc.close()
