# KSERC AI Truing-Up Analytical Tool - User Manual

This manual provides instructions for using the AI-based tool for truing-up of accounts for distribution licensees.

## Overview

The KSERC AI Truing-Up Tool automates the process of analyzing financial data, identifying deviations, and generating regulatory reports. It uses a combination of formulaic analysis and Large Language Models (LLM) for prudence checks.

## Key Features

- **Automated Extraction**: Upload PDF documents to extract financial data (Cost Heads and Revenue).
- **Intelligent Prudence Check**: AI-powered analysis of cost deviations with descriptive reasoning.
- **Manual Overrides**: Human-in-the-loop capability to modify allowed amounts and verdicts.
- **Regulatory Report Generation**: One-click generation of formal KSERC Truing-Up Orders in markdown, PDF, and DOCX formats.
- **Chat Interface**: Query the AI about specific cases and regulatory rules.
- **Local Database**: All data is stored locally for maximum privacy and performance.

## Operating Instructions

### 1. Initializing a Case
1. Navigate to the **Home** dashboard.
2. Enter the **Licensee Name**, **Financial Year**, and **Case ID**.
3. (Optional) Provide additional context for the analysis.
4. Click **Start Analysis**.

### 2. Data Extraction and Analysis
1. Upload the relevant truing-up petition documents (PDF).
2. The system will extract cost heads and revenue data.
3. The AI will immediately perform a prudence check, flagging deviations and suggesting allowed amounts.

### 3. Reviewing Results
1. On the **Analysis Results** page, review the cost heads table.
2. Flagged items (Capped, Rejected) are highlighted.
3. Click "Modify Value manually" on any item to override the AI's decision if necessary.
4. Use the **AI Chat** on the right to ask clarifying questions about the data.

### 4. Generating the Report
1. Once the review is complete, click **Generate Report**.
2. Review the formal regulatory language.
3. Export the report as **PDF** or **Word Document**.

## Data Privacy

All data is stored in a local file named `.local-db.json` within the application directory. No data is sent to external servers except for the transient LLM analysis requests.

## Troubleshooting

- **No Results Found**: Ensure the Case ID is correct in the URL.
- **Extraction Failed**: Ensure the uploaded PDF is of good quality.
- **Report Generation Error**: Check your internet connection for LLM access.

---
*Developed for Kerala State Electricity Regulatory Commission (KSERC)*
