# Agentic DataOps Control Center

An AI-powered DataOps dashboard built using Python, Streamlit, Databricks SQL, and Groq.

## Overview

Agentic DataOps Control Center helps monitor data quality, identify revenue mismatches, investigate anomalies, and analyze pipeline execution history through an interactive dashboard.

## Features

- **Data Quality Monitoring:** Evaluate data completeness and revenue validation.
- **Revenue Analytics:** Explore revenue trends and product-level metrics.
- **Anomaly Detection:** Inspect suspicious records and revenue mismatches.
- **AI Analyst:** Generate AI-powered insights from data quality results.
- **AI Root Cause Analysis:** Investigate problematic records and suggest possible causes with evidence-based recommendations.
- **Pipeline History:** Review available pipeline execution records.
- **PDF Reporting:** Generate downloadable data quality reports.
- **CSV Export:** Export filtered data for further investigation.

## Tech Stack

- Python
- Streamlit
- Databricks SQL
- Pandas
- Plotly
- Groq API
- ReportLab
- Git and GitHub

## Project Structure

```text
Agentic_DataOps_Project/
├── app.py
├── ai_agent.py
├── test_connection.py
├── requirements.txt
├── .gitignore
└── .streamlit/
    └── secrets.toml
```

**Note:** The `secrets.toml` file is stored locally and must not be committed to GitHub.

## Local Setup

1. Clone the repository:

   ```bash
   git clone YOUR_GITHUB_REPOSITORY_URL
   cd Agentic_DataOps_Project
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   ```

   Windows PowerShell:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Configure your local `.streamlit/secrets.toml` file with your Databricks connection details and Groq API key.

5. Run the application:

   ```bash
   streamlit run app.py
   ```

## Security

API keys, access tokens, and other credentials must be kept private. Never commit secrets to GitHub.

## Future Improvements

- Automated pipeline execution and monitoring
- Configurable data quality rules
- More detailed anomaly investigation
- Enhanced reporting and alerting

## Author

Developed as a portfolio project to explore AI-powered data quality monitoring and DataOps workflows.