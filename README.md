# KSERC Autonomous Regulatory Agent (ARA) - Backend

## Overview

This repository contains the **backend system** for the **Autonomous Regulatory Agent (ARA)**, developed for the **Kerala State Electricity Regulatory Commission (KSERC)**. The system automates the scrutiny of "Truing Up of Accounts" petitions submitted by electricity distribution licensees (Technopark, Infopark, KDHPCL, etc.).

### What is Truing Up?

"Truing Up" is a regulatory process where actual expenditures and revenues of electricity licensees are compared against their approved Annual Revenue Requirement (ARR). The ARA automates this comparison, identifies deviations, and ensures mathematical precision in regulatory analysis.

## Key Features

✅ **PDF Ingestion** - Automatically extracts financial tables from KSERC regulatory order PDFs  
✅ **Zero-Error Mathematics** - Performs precise calculations with automatic validation  
✅ **Deviation Analysis** - Identifies significant deviations between ARR and actuals  
✅ **Compliance Checks** - Automated regulatory compliance verification  
✅ **REST API** - High-performance API built with FastAPI for easy integration  
✅ **Comprehensive Logging** - Detailed logging for debugging and audit trails  
✅ **Auto-Generated Documentation** - Interactive API documentation via Swagger UI  
✅ **AI Executive Summary (Free Tier)** - Optional LLM summary via Hugging Face Inference API  
✅ **RAG + 4-LLM Verdicts** - Multi-agent pipeline with final PDF output  

## Technology Stack

### Core Framework
- **Python 3.10+** - Modern Python with type hints and async support
- **FastAPI** - High-performance web framework (chosen for speed and auto-documentation)
- **Uvicorn** - Lightning-fast ASGI server

### Data Processing
- **pdfplumber** - Superior PDF table extraction (better than PyPDF2 for structured tables)
- **Pydantic** - Data validation using Python type hints

### Development Tools
Code generation and optimization supported by:
- **Codeium** - AI-powered code completion
- **Sourcery** - Code quality and refactoring suggestions
- **Tabnine** - Intelligent code suggestions

> Note: `pandas` is now optional and only required if you call `response_to_dataframe()`.
> Note: `Pillow` is an indirect dependency of `pdfplumber` and will install a compatible version automatically.

## Project Structure

```
kserc-ara-backend/
├── .gitignore              # Files to exclude from version control
├── vercel.json             # Vercel static frontend configuration
├── frontend/               # Static dashboard frontend
├── requirements.txt        # Python dependencies
├── README.md              # This file
└── src/
    ├── __init__.py        # Package initialization
    ├── main.py            # FastAPI application entry point
    ├── config.py          # Environment configuration
    ├── models/
    │   ├── __init__.py
    │   └── schemas.py     # Pydantic models for data validation
    ├── services/
    │   ├── __init__.py
    │   ├── pdf_ingestion.py  # PDF parsing and extraction logic
    │   └── analyzer.py       # Compliance checks and gap analysis
    └── utils/
        ├── __init__.py
        └── logger.py         # Custom logging configuration
```

## Installation & Setup

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- Virtual environment tool (venv or virtualenv)

### Step 1: Clone the Repository

```bash
git clone https://github.com/prak05/KSERCnew.git
cd KSERCnew
```

### Step 2: Create Virtual Environment

```bash
# On Linux/Mac
python3 -m venv venv
source venv/bin/activate

# On Windows
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment (Optional)

Create a `.env` file in the root directory for custom configuration:

```env
# Server Configuration
HOST=0.0.0.0
PORT=8000

# Logging Configuration
LOG_LEVEL=INFO
DEBUG_MODE=True

# File Upload Configuration
MAX_UPLOAD_SIZE=52428800  # 50 MB in bytes
```

## Running the Application

### Development Mode

```bash
# Run with auto-reload (recommended for development)
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Or simply:

```bash
python src/main.py
```

### Production Mode

```bash
# Run with multiple workers for production
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

The server will start at: `http://localhost:8000`

## API Documentation

### Interactive Documentation

Once the server is running, access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### API Endpoints

#### 1. Health Check
```
GET /
```
Returns the health status of the API.

**Response:**
```json
{
  "status": "active",
  "system": "ARA Backend v1.0.0",
  "timestamp": "2024-02-18T10:30:45.123456",
  "version": "1.0.0"
}
```

#### 2. API Information
```
GET /info
```
Returns detailed information about the API capabilities.

#### 3. Analyze Regulatory Order
```
POST /analyze-order/
```
Upload a KSERC regulatory order PDF and get truing up analysis.

**Request:** Multipart form data with PDF file

**Response:**
```json
{
  "licensee_name": "Infopark",
  "financial_year": "2023-24",
  "financial_summary": [
    {
      "particulars": "Power Purchase Cost",
      "arr_approved": 3103.55,
      "trued_up_value": 3370.52,
      "deviation": 266.97
    }
  ],
  "net_surplus_deficit": -150.75,
  "total_arr_approved": 5000.00,
  "total_trued_up": 5150.75,
  "analysis_timestamp": "2024-02-18T10:30:45.123456",
  "compliance_status": "Analysis Complete"
}
```

#### 4. Compliance Check
```
POST /compliance-check/
```
Performs comprehensive compliance checks on the uploaded regulatory order.

**Response:** Detailed compliance report with checks, warnings, and executive summary.

#### 5. AI Summary (Free Tier)
```
POST /ai-summary/
```
Generates an executive summary using a free-tier LLM API.  
Send the JSON output from `/analyze-order/` as `analysis`, and optionally `compliance_report` from `/compliance-check/`.

#### 6. RAG Indexing (Backend Admin)
```
POST /rag/index-seed
POST /rag/upload
POST /rag/refresh
```
Indexes KSERC reference PDFs and regulatory documents for retrieval.

#### 6.1 Remote RAG Indexing (Cloudflare Worker + R2)
To offload indexing from your local machine, deploy the Cloudflare Worker in
`cloudflare/worker/` and set:

- `RAG_REMOTE_BASE_URL` to the Worker URL
- `RAG_REMOTE_TOKEN` if you enabled auth

Then use the Worker to index (seed or upload), and call:

```
POST /rag/refresh
```

to refresh the backend cache.

#### 7. Final Verdict (ARR + Truing-Up)
```
POST /verdict/
```
Upload ARR + Truing-Up PDFs to generate a final KSERC-style verdict and a downloadable PDF.

## Cloud Storage (Verdict PDFs)

If `GCS_BUCKET_NAME` is set, verdict PDFs are uploaded to Google Cloud Storage and returned as a public URL.

## Usage Examples

### Using cURL

```bash
# Health check
curl http://localhost:8000/

# Analyze a regulatory order
curl -X POST http://localhost:8000/analyze-order/ \
  -F "file=@path/to/kserc-order.pdf" \
  -H "accept: application/json"
```

### Using Python Requests

```python
import requests

# Analyze a regulatory order
with open('kserc-order.pdf', 'rb') as f:
    files = {'file': f}
    response = requests.post(
        'http://localhost:8000/analyze-order/',
        files=files
    )
    result = response.json()
    print(f"Licensee: {result['licensee_name']}")
    print(f"Net Surplus/Deficit: ₹{result['net_surplus_deficit']} Lakhs")

# AI summary (optional)
summary_payload = {
    "analysis": result,
    "compliance_report": None
}
summary_response = requests.post(
    "http://localhost:8000/ai-summary/",
    json=summary_payload
)
print(summary_response.json())

# Generate verdict from ARR + Truing-Up PDFs
with open("arr.pdf", "rb") as arr, open("truing.pdf", "rb") as truing:
    files = {"arr_pdf": arr, "truing_pdf": truing}
    verdict_response = requests.post(
        "http://localhost:8000/verdict/",
        files=files
    )
    print(verdict_response.json())

## Frontend (Vercel-ready)

A static frontend is included in `frontend/` with:
- ARR + Truing-Up upload
- RAG indexing (admin) with optional Cloudflare index service URL
- Verdict PDF download

Vercel deployment is configured via `vercel.json` at repo root.
```

## Code Documentation

This codebase follows professional documentation standards:

✅ **Every line is commented** (except basic Python operations)  
✅ **Source attribution** - Each function notes its source (library vs. user-defined)  
✅ **Library explanations** - Every library function includes "Why" it's used  
✅ **Function purpose** - Clear docstrings explaining what each function does  
✅ **Pattern documentation** - Design patterns and architectural decisions are explained  

## Development Notes

### Code Style

- **Type Hints**: All functions use type hints for better IDE support
- **Pydantic Models**: Data validation using Pydantic ensures type safety
- **Async/Await**: Async operations for I/O-bound tasks (file uploads)
- **Error Handling**: Comprehensive exception handling with proper HTTP status codes

### Logging

The application uses a custom logging system with:
- Colored console output for better readability
- Configurable log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Optional file logging for production environments
- Detailed function call tracking

### Testing

To test the API with a sample PDF:

1. Use the Swagger UI at http://localhost:8000/docs
2. Navigate to `/analyze-order/` endpoint
3. Click "Try it out"
4. Upload a KSERC regulatory order PDF
5. Click "Execute" to see the results

## Source References

This backend is based on:

1. **KSERC Work Order No. KSERC/CSO/03-05** - Project specification
2. **KSERC (Terms and Conditions for Determination of Tariff) Regulations, 2021** - Regulatory framework
3. **KSERC Regulatory Orders** (4oCC..., 4tJU..., OyFwUM...) - Real-world examples for table structures

## Contributing

This is an academic/professional project for KSERC. For questions or contributions:

- **Developer**: Prakash (@prak05)
- **GitHub**: https://github.com/prak05
- **Timeline**: 2-week delivery to KSERC

## Future Enhancements

Potential improvements for future iterations:

- [ ] Database integration for storing analysis history
- [ ] Multi-year comparison analysis
- [ ] Advanced table detection using ML models
- [ ] Export functionality (Excel, CSV, PDF reports)
- [ ] Real-time collaborative analysis
- [ ] Integration with KSERC official systems
- [ ] Automated email notifications
- [x] Dashboard UI (static frontend, Vercel-ready)

## License

This project is developed for the Kerala State Electricity Regulatory Commission (KSERC).

## Acknowledgments

- **KSERC** - For the opportunity and project requirements
- **AI Assistants** - Codeium, Sourcery, and Tabnine for code optimization
- **Open Source Community** - For the excellent libraries used in this project

---

**Built with ❤️ for Kerala State Electricity Regulatory Commission**

**Last Updated**: February 2024  
**Version**: 1.0.0  
**Status**: Production Ready
