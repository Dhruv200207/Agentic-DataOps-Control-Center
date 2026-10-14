
import json

import streamlit as st
from groq import Groq


def analyze_root_causes(
    mismatch_records,
    anomaly_records=None,
    quality_summary=None,
):
    """
    Analyze real data-quality records and return
    evidence-based investigation recommendations.

    This function does not modify source data.
    """

    anomaly_records = anomaly_records or []
    quality_summary = quality_summary or {}

    if not mismatch_records and not anomaly_records:
        return (
            "No mismatch or anomaly records were provided. "
            "There is insufficient evidence for root-cause analysis."
        )

    if "GROQ_API_KEY" not in st.secrets:
        raise ValueError(
            "GROQ_API_KEY is missing from Streamlit secrets."
        )

    client = Groq(
        api_key=st.secrets["GROQ_API_KEY"]
    )

    prompt = f"""
You are an evidence-based Data Quality and DataOps analyst.

Analyze the actual records and metrics below.

QUALITY SUMMARY:
{json.dumps(quality_summary, default=str, indent=2)}

REVENUE MISMATCH RECORDS:
{json.dumps(mismatch_records, default=str, indent=2)}

ANOMALY RECORDS:
{json.dumps(anomaly_records, default=str, indent=2)}

For every important issue, return:

1. Issue title
2. Affected order ID or record identifier, when available
3. Evidence observed in the supplied data
4. Possible root causes
5. Confidence level: Low, Medium, or High
6. Investigation steps
7. Recommended corrective action
8. Whether human approval is required

Important rules:
- Distinguish observed facts from hypotheses.
- Never claim a possible cause is confirmed without evidence.
- For revenue validation, compare revenue with quantity * unit_price.
- Do not assume discounts, taxes, fees, or adjustments exist.
- Do not invent source records or values.
- Do not claim that SQL updates or fixes have been executed.
- Do not modify, delete, or update any data.
- Recommend checking source records, transformation logic,
  data types, joins, and business rules when relevant.
- Keep recommendations specific to the supplied evidence.
- If evidence is insufficient, state what additional information
  is needed.
- Require human review before any corrective change.

Return readable Markdown with these sections:

# Root Cause Analysis
# Confirmed Data Observations
# Issue-by-Issue Investigation
# Recommended Investigation Priority
# Corrective Actions Requiring Approval
# Additional Evidence Needed
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a careful DataOps investigator. "
                    "Use only the evidence provided, clearly label "
                    "uncertainty, and never modify source data."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.2,
    )

    return response.choices[0].message.content
