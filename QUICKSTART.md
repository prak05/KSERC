# KSERC ARA Backend - Quick Start Guide

## 🚀 Get Started in 3 Minutes

This guide will help you get the KSERC ARA Backend running on your local machine in just a few minutes.

### Prerequisites

- Python 3.10+ installed
- Internet connection (for installing dependencies)

### Installation Steps

#### 1. Clone the Repository

```bash
git clone https://github.com/prak05/KSERCnew.git
cd KSERCnew
```

#### 2. Create Virtual Environment

**On Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

#### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- FastAPI (web framework)
- Uvicorn (ASGI server)
- pdfplumber (PDF parsing)
- Pandas (data analysis)
- Pydantic (data validation)
- And other dependencies

#### 4. Start the Server

```bash
python src/main.py
```

Or alternatively:
```bash
uvicorn src.main:app --reload
```

You should see output like:
```
============================================================
Starting KSERC Autonomous Regulatory Agent (ARA) v1.0.0
Server: 0.0.0.0:8000
Debug Mode: True
============================================================
INFO:     Uvicorn running on http://0.0.0.0:8000
```

#### 5. Test the API

Open your browser and navigate to:

- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/

### Using the Interactive API Documentation

1. Open http://localhost:8000/docs in your browser
2. You'll see the Swagger UI with all available endpoints
3. Click on any endpoint to expand it
4. Click "Try it out" to test the endpoint
5. For file upload endpoints, select a PDF file and click "Execute"

### Testing with the Test Script

Run the included test script to verify everything works:

```bash
python test_api.py
```

Expected output:
```
============================================================
KSERC ARA Backend API Tests
============================================================
Health Check......................................✓ PASS
API Info..........................................✓ PASS
Analyze Order.....................................✓ PASS
Compliance Check..................................✓ PASS

Total: 4/4 tests passed
🎉 All tests passed!
```

### Example: Analyze a Regulatory Order

#### Using cURL:

```bash
curl -X POST "http://localhost:8000/analyze-order/" \
  -F "file=@/path/to/kserc-order.pdf"
```

#### Using Python:

```python
import requests

with open('kserc-order.pdf', 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:8000/analyze-order/', files=files)
    print(response.json())
```

#### Expected Response:

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
  "total_trued_up": 5150.75
}
```

### Configuration (Optional)

Create a `.env` file in the root directory to customize settings:

```env
# Server Configuration
HOST=0.0.0.0
PORT=8000

# Logging
LOG_LEVEL=INFO
DEBUG_MODE=True

# File Upload
MAX_UPLOAD_SIZE=52428800
```

### API Endpoints Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/info` | GET | API information |
| `/analyze-order/` | POST | Upload PDF for analysis |
| `/compliance-check/` | POST | Get detailed compliance report |
| `/rag/index-seed` | POST | Index RAG seed docs |
| `/rag/upload` | POST | Upload + index RAG docs |
| `/rag/refresh` | POST | Refresh RAG index from remote |
| `/docs` | GET | Interactive API documentation |
| `/redoc` | GET | Alternative API documentation |

### Offload RAG Indexing to Cloudflare

If local indexing is crashing your machine, deploy the Worker in
`cloudflare/worker/` and use it for indexing.

1. Install wrangler:
```bash
npm install -g wrangler
```

2. Create an R2 bucket:
```bash
wrangler r2 bucket create kserc-rag
```

3. Deploy the Worker:
```bash
cd cloudflare/worker
npm install
wrangler deploy
```

4. (Optional) Upload seed docs to R2:
```bash
wrangler r2 object put kserc-rag/rag/seed/your.pdf --file /path/to/your.pdf
```

5. Index remotely:
```bash
curl -X POST https://YOUR-WORKER-URL/rag/index-seed
```

6. Point backend to the Worker:
```env
RAG_REMOTE_BASE_URL=https://YOUR-WORKER-URL
RAG_REMOTE_TOKEN=
```

7. Refresh backend cache:
```bash
curl -X POST http://localhost:8000/rag/refresh
```

### Troubleshooting

#### Port Already in Use

If port 8000 is already in use, specify a different port:

```bash
uvicorn src.main:app --port 8001
```

#### Import Errors

Make sure you're in the project root directory and virtual environment is activated:

```bash
cd KSERCnew
source venv/bin/activate  # On Linux/Mac
# or
venv\Scripts\activate  # On Windows
```

#### Dependency Issues

Update pip and reinstall dependencies:

```bash
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

### Next Steps

1. **Read the Full Documentation**: Check [README.md](README.md) for detailed information
2. **Explore the Code**: All code is extensively commented
3. **Test with Real PDFs**: Upload actual KSERC regulatory orders
4. **Customize**: Modify the code to meet your specific requirements

### Support

For questions or issues:
- Check the [README.md](README.md) documentation
- Review the inline code comments (every line is documented)
- Contact: [@prak05](https://github.com/prak05)

### Production Deployment

For production deployment, consider:

1. **Disable Debug Mode**: Set `DEBUG_MODE=False` in `.env`
2. **Use Multiple Workers**: `uvicorn src.main:app --workers 4`
3. **Set Up Reverse Proxy**: Use Nginx or similar
4. **Enable HTTPS**: Use SSL/TLS certificates
5. **Configure CORS**: Restrict allowed origins
6. **Add Authentication**: Implement API key or OAuth
7. **Set Up Logging**: Configure file-based logging
8. **Monitor Performance**: Use tools like Prometheus

---

**Built for KSERC** | **Developer**: [@prak05](https://github.com/prak05) | **Status**: Production Ready
