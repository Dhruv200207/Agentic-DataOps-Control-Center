# 🚀 Agentic DataOps Control Center

An AI-powered DataOps dashboard built using **Python, Streamlit, Databricks SQL, and Groq** to monitor data quality, analyze revenue mismatches, investigate anomalies, and generate reports.

## 🌐 Live Demo

**Try the live application here:**

👉 [Agentic DataOps Control Center — Live App](https://agentic-dataops-control-center-hcinjbvs9en5lrxqgn3ztu.streamlit.app/)

## 📌 Project Overview

The Agentic DataOps Control Center is an interactive dashboard designed to support data quality monitoring and data investigation workflows.

It connects to Databricks SQL tables, analyzes sales data, highlights revenue inconsistencies, and uses a Groq-powered AI assistant to generate investigation suggestions based on available records.

The dashboard brings data quality metrics, anomaly analysis, pipeline history, and downloadable reports together in one interface.

## ✨ Key Features

### 📊 1. Data Quality Monitoring
- Monitor raw and cleaned sales records.
- Review data completeness and validation metrics.
- Identify revenue inconsistencies.
- Calculate revenue validation statistics.

### 💰 2. Revenue Analytics
- Analyze revenue across products, categories, cities, and states.
- Explore sales metrics through interactive charts.
- Filter records to investigate specific business segments.

### 🔎 3. Anomaly Detection
- Review records flagged as anomalies.
- Identify unusually high, low, or inconsistent revenue values.
- Investigate suspicious sales records.

### 🤖 4. AI Analyst
- Generate AI-powered summaries of data quality findings.
- Ask for insights based on available dashboard data.
- Receive investigation suggestions using the Groq API.

### 🧠 5. AI-Powered Root Cause Analysis
- Analyze problematic revenue records.
- Review observed evidence and possible root causes.
- Generate issue-by-issue investigation recommendations.
- Suggest corrective actions requiring human approval.
- Distinguish confirmed observations from unverified hypotheses.

**Note:** AI-generated root causes are investigation hypotheses, not confirmed explanations. Validate them against source records and business rules before making changes.

### ⚙️ 6. Pipeline History
- View available pipeline execution records.
- Review pipeline status and row-count metrics.
- Compare raw rows, cleaned rows, removed rows, and anomaly counts.

Pipeline history displays records available in the Databricks monitoring table. The dashboard does not automatically execute or log new pipeline runs unless that functionality is implemented separately.

### 📄 7. PDF Reporting
- Generate downloadable PDF reports.
- Include data quality metrics and revenue validation findings.
- Review anomaly information and available AI analysis.

### 📥 8. Data Export
- Download filtered data as CSV.
- Use exported records for further analysis and investigation.

## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| Python | Application logic and data processing |
| Streamlit | Interactive dashboard interface |
| Databricks SQL | Data storage and SQL-based access |
| Pandas | Data manipulation and analysis |
| Plotly | Interactive data visualizations |
| Groq API | AI-powered analysis and investigation suggestions |
| ReportLab | PDF report generation |
| Git and GitHub | Version control and source code hosting |

## 🏗️ Project Architecture

```text
Sales Data in Databricks
          |
          v
     Databricks SQL
          |
          v
 Python Data Processing
       (Pandas)
          |
          v
 Streamlit Dashboard
          |
          +--------------------+
          |                    |
          v                    v
  Data Quality &          Groq AI
 Revenue Validation       Analysis
          |                    |
          v                    v
 Anomaly Investigation   Root Cause Suggestions
          |
          v
   CSV / PDF Reports
```

## 📁 Project Structure

```text
Agentic_DataOps_Project/
│
├── app.py
├── ai_agent.py
├── test_connection.py
├── requirements.txt
├── README.md
├── .gitignore
└── .streamlit/
    └── secrets.toml
```

**Security note:** `.streamlit/secrets.toml` is a local configuration file and must not be committed to GitHub.

## 🗄️ Databricks Tables

The application uses the following Databricks tables:

| Table | Purpose |
|---|---|
| `sales_raw` | Raw sales records |
| `sales_cleaned` | Cleaned sales records |
| `sales_anomalies` | Records flagged for anomaly investigation |
| `pipeline_monitoring` | Pipeline execution metrics and status history |

The tables must exist in the configured Databricks environment, and the SQL Warehouse must be accessible to the application.

## ⚙️ Local Installation and Setup

### Prerequisites

- Python installed on your system
- A GitHub account
- Access to a Databricks SQL Warehouse
- A Groq API key

### Step 1: Clone the Repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd Agentic_DataOps_Project
```

Replace `YOUR_GITHUB_REPOSITORY_URL` with the HTTPS URL of this GitHub repository.

### Step 2: Create a Virtual Environment

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Secrets

Create the file `.streamlit/secrets.toml` and add your own credentials:

```toml
DATABRICKS_SERVER_HOSTNAME = "your-databricks-hostname"
DATABRICKS_HTTP_PATH = "your-databricks-http-path"
DATABRICKS_TOKEN = "your-databricks-token"
GROQ_API_KEY = "your-groq-api-key"
```

Replace the example values with your actual credentials. Never publish API keys, access tokens, or other secrets.

### Step 5: Test the Databricks Connection

```bash
python test_connection.py
```

### Step 6: Run the Application

```bash
streamlit run app.py
```

The application should open in your browser.

## 🔐 Security

- Keep API keys and Databricks credentials private.
- Exclude `.streamlit/secrets.toml` from Git tracking.
- Configure deployment secrets through Streamlit Community Cloud settings.
- Avoid displaying confidential or sensitive records in a public dashboard.
- Review AI-generated recommendations before applying corrective changes.

## 🚀 Deployment

The application is deployed on Streamlit Community Cloud.

**Live URL:** [Open Agentic DataOps Control Center](https://agentic-dataops-control-center-hcinjbvs9en5lrxqgn3ztu.streamlit.app/)

Deployment requires the GitHub repository, a valid `app.py` entry point, the required Python dependencies, and correctly configured Databricks and Groq secrets.

## 🔮 Future Improvements

- Automated data quality checks
- Configurable validation rules
- Pipeline failure notifications
- Historical data quality trend analysis
- Enhanced anomaly investigation
- Human-approved data correction workflows
- Additional monitoring and reporting capabilities