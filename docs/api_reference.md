# KSERC SDL Truing-Up Platform: API Reference

This document outlines the REST API endpoints available in the KSERC Truing-Up analysis platform.

## Base URL
All API requests must be made against the base URL (default: `http://localhost:8000`).

---

## 1. Upload and Analyze Petition

Uploads a Truing-Up petition PDF for automated analysis.

**Endpoint:** `POST /`

**Content-Type:** `multipart/form-data`

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | `UploadFile` | Yes | The petition document (PDF format only, max 50MB). |
| `licensee` | `string` | Yes | Name of the SDL (e.g., `Technopark`, `Infopark`, `CSEZA`, `KDHP`). |
| `financial_year` | `string` | Yes | The financial year applicable for truing up (e.g., `2022-23`). |

### Success Response (200 OK)

A JSON object detailing the analysis results, extracted tables, component-level gap validations, and disallowance logs.

```json
{
  "analysis_id": "uuid-string",
  "licensee_name": "Technopark",
  "financial_year": "2022-23",
  "original_filename": "petition.pdf",
  "timestamp": "2024-05-20T10:30:00.000",
  "total_claimed_expenditure": 1500.50,
  "total_approved_expenditure": 1450.00,
  "total_claimed_revenue": 1400.00,
  "total_approved_revenue": 1400.00,
  "final_revenue_gap_surplus": -50.00,
  "components": [
    {
       "key": "employee_cost",
       "name": "Employee Cost",
       "claimed": 300.00,
       "approved": 250.00,
       "variance": -50.00,
       "variance_pct": -16.67,
       "status": "reduced",
       "status_label": "Reduced",
       "justification": "Employee cost capped at MYT baseline + CPI/WPI escalation."
    }
  ],
  "disallowances": [
    {
      "item": "Employee Cost",
      "claimed": 300.00,
      "approved": 250.00,
      "amount_cut": 50.00,
      "justification": "Employee cost capped at MYT baseline + CPI/WPI escalation."
    }
  ],
  "pdf_available": true
}
```

---

## 2. Check Analysis Status

Polls the analysis pipeline for the current status and returns the result if completed.

**Endpoint:** `GET /api/status/{analysis_id}`

### URL Parameters
* `analysis_id`: The UUID of the analysis session returned upon upload.

### Success Response (200 OK)

```json
{
  "status": "COMPLETED",
  "result": {
    // ... Full analysis result object as shown in the POST / response
  }
}
```
*Possible Statuses: `RUNNING`, `COMPLETED`, `FAILED`.*

---

## 3. Human-in-the-Loop Override

Allows a human auditor to override the system-approved amount for a specific expense component.

**Endpoint:** `POST /api/override`

**Content-Type:** `application/json`

### Request Body

```json
{
  "analysis_id": "uuid-string",
  "component_key": "employee_cost",
  "new_approved_amount": 280.00,
  "justification": "Approved partial exception due to 7th Pay Commission arrears.",
  "user_id": "auditor_kserc_01"
}
```

### Success Response (200 OK)

```json
{
  "status": "success",
  "message": "Override applied and logged."
}
```

*(Note: Applying an override will automatically regenerate the PDF Order and log the decision to the Audit Trail).*

---

## 4. Download PDF Order

Downloads the officially formatted KSERC Truing-Up Order document.

**Endpoint:** `GET /api/download/{analysis_id}`

### URL Parameters
* `analysis_id`: The UUID of the analysis session.

### Success Response (200 OK)
* `Content-Type: application/pdf`
* Returns the generated PDF file.

### Error Response (404 Not Found)
* Returned if the `analysis_id` does not exist or if the PDF has not been generated yet.
