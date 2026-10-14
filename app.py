
import io
import json

import pandas as pd
import plotly.express as px
import streamlit as st
import databricks.sql

from groq import Groq
from ai_agent import analyze_root_causes

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)


# =========================================================
# 1. PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Agentic DataOps Control Center",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# 2. CUSTOM CSS
# =========================================================

st.markdown(
    """
    <style>
    .stApp {
        background-color: #0e1117;
        color: #fafafa;
    }

    [data-testid="stSidebar"] {
        background-color: #151922;
    }

    [data-testid="stMetric"] {
        background-color: #191f2b;
        border: 1px solid #30394a;
        padding: 16px;
        border-radius: 12px;
    }

    div[data-testid="stMetricValue"] {
        color: #60a5fa;
    }

    .main-title {
        font-size: 2.2rem;
        font-weight: 750;
        color: #60a5fa;
        margin-bottom: 0;
    }

    .sub-title {
        color: #aab4c5;
        margin-top: 4px;
        margin-bottom: 24px;
    }

    .small-note {
        color: #aab4c5;
        font-size: 0.85rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 3. HEADER
# =========================================================

st.markdown(
    '<p class="main-title">📊 Agentic DataOps Control Center</p>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <p class="sub-title">
    Databricks • PySpark Data Quality • Revenue Validation
    • AI Investigation • Pipeline Monitoring
    </p>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 4. DATABRICKS CONNECTION
# =========================================================

def get_databricks_connection():
    """Connect to Databricks using Streamlit secrets."""

    return databricks.sql.connect(
        server_hostname=st.secrets["DATABRICKS_SERVER_HOSTNAME"],
        http_path=st.secrets["DATABRICKS_HTTP_PATH"],
        access_token=st.secrets["DATABRICKS_TOKEN"],
    )


@st.cache_data(ttl=300, show_spinner=False)
def load_table(table_name):
    """Load data from an allowlisted Databricks table."""

    allowed_tables = {
        "sales_raw",
        "sales_cleaned",
        "sales_anomalies",
        "pipeline_monitoring",
    }

    if table_name not in allowed_tables:
        raise ValueError("Table is not allowed.")

    connection = get_databricks_connection()

    try:
        cursor = connection.cursor()

        try:
            if table_name == "sales_anomalies":
                query = """
                    SELECT *
                    FROM sales_anomalies
                    WHERE anomaly_status = 'Anomaly'
                """
            else:
                query = f"SELECT * FROM {table_name}"

            cursor.execute(query)

            rows = cursor.fetchall()
            columns = [item[0] for item in cursor.description]

            return pd.DataFrame(rows, columns=columns)

        finally:
            cursor.close()

    finally:
        connection.close()


# =========================================================
# 5. HELPER FUNCTIONS
# =========================================================

def normalize_columns(data):
    """Standardize column names."""

    data = data.copy()
    data.columns = [
        str(column).strip().lower()
        for column in data.columns
    ]

    return data


def safe_number(value, default=0):
    """Convert values to numbers safely."""

    result = pd.to_numeric(value, errors="coerce")

    if pd.isna(result):
        return default

    return float(result)


def format_number(value):
    """Format a value with thousands separators."""

    try:
        return f"{int(value):,}"
    except (TypeError, ValueError, OverflowError):
        return "0"


def prepare_pipeline_history(monitoring_df):
    """Validate and prepare pipeline monitoring records."""

    history = monitoring_df.copy()

    required_columns = [
        "run_timestamp",
        "pipeline_status",
        "raw_rows",
        "cleaned_rows",
        "rows_removed",
        "anomaly_rows",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in history.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing pipeline monitoring columns: "
            + ", ".join(missing_columns)
        )

    history["run_timestamp"] = pd.to_datetime(
        history["run_timestamp"],
        errors="coerce",
        utc=True,
    )

    for column in [
        "raw_rows",
        "cleaned_rows",
        "rows_removed",
        "anomaly_rows",
    ]:
        history[column] = pd.to_numeric(
            history[column],
            errors="coerce",
        )

    history = history.dropna(
        subset=["run_timestamp"]
    )

    return history.sort_values(
        "run_timestamp",
        ascending=False,
    )


def make_csv(data):
    """Return a UTF-8 CSV download payload."""

    return data.to_csv(index=False).encode("utf-8")


# =========================================================
# 6. LOAD DATABRICKS TABLES
# =========================================================

try:
    with st.spinner("Loading Databricks data..."):
        raw_df = normalize_columns(
            load_table("sales_raw")
        )

        df = normalize_columns(
            load_table("sales_cleaned")
        )

        anomalies_df = normalize_columns(
            load_table("sales_anomalies")
        )

        monitoring_df = normalize_columns(
            load_table("pipeline_monitoring")
        )

except Exception as error:
    st.error("Could not load data from Databricks.")
    st.code(str(error))

    st.info(
        "Check your Streamlit secrets, Databricks SQL warehouse, "
        "permissions, and table names."
    )

    st.stop()


# =========================================================
# 7. VALIDATE SALES SCHEMA
# =========================================================

required_sales_columns = [
    "order_id",
    "order_date",
    "product",
    "category",
    "city",
    "state",
    "quantity",
    "unit_price",
    "revenue",
]

missing_columns = [
    column
    for column in required_sales_columns
    if column not in df.columns
]

if missing_columns:
    st.error(
        "sales_cleaned is missing these columns: "
        + ", ".join(missing_columns)
    )
    st.stop()


# =========================================================
# 8. PREPARE SALES DATA
# =========================================================

df = df.copy()

df["order_date"] = pd.to_datetime(
    df["order_date"],
    errors="coerce",
)

for column in ["quantity", "unit_price", "revenue"]:
    df[column] = pd.to_numeric(
        df[column],
        errors="coerce",
    )

df["expected_revenue"] = (
    df["quantity"] * df["unit_price"]
)

df["revenue_difference"] = (
    df["revenue"] - df["expected_revenue"]
)

# Revenue is considered matching if the difference is <= 0.01.
df["revenue_match"] = (
    df["revenue"].notna()
    & df["expected_revenue"].notna()
    & (df["revenue_difference"].abs() <= 0.01)
)

mismatch_df = df.loc[
    ~df["revenue_match"]
].copy()

total_rows = len(df)

matching_rows = int(
    df["revenue_match"].sum()
)

mismatch_count = len(mismatch_df)

mismatch_rate = (
    mismatch_count / total_rows * 100
    if total_rows
    else 0
)

completeness = (
    df[required_sales_columns].notna().all(axis=1).mean() * 100
    if total_rows
    else 0
)

duplicate_rows = int(
    df.duplicated(subset=["order_id"]).sum()
)

duplicate_free_rate = (
    (total_rows - duplicate_rows) / total_rows * 100
    if total_rows
    else 0
)

# Illustrative composite score; adjust weights to business rules.
quality_score = (
    0.50 * completeness
    + 0.35 * (100 - mismatch_rate)
    + 0.15 * duplicate_free_rate
)

quality_score = max(
    0,
    min(100, quality_score),
)

if total_rows == 0:
    quality_label = "NO DATA"
elif completeness < 95 or mismatch_rate > 10:
    quality_label = "WARNING"
else:
    quality_label = "SUCCESS"


# =========================================================
# 9. PREPARE PIPELINE HISTORY
# =========================================================

try:
    pipeline_history = prepare_pipeline_history(
        monitoring_df
    )

except ValueError as error:
    st.error(str(error))
    st.stop()


# =========================================================
# 10. SIDEBAR FILTERS
# =========================================================

st.sidebar.title("🎛️ Dashboard Controls")

st.sidebar.caption(
    "Filters apply to sales analytics and revenue validation."
)

if st.sidebar.button(
    "🔄 Refresh Databricks Data",
    use_container_width=True,
):
    load_table.clear()
    st.rerun()

categories = sorted(
    df["category"].dropna().astype(str).unique().tolist()
)

products = sorted(
    df["product"].dropna().astype(str).unique().tolist()
)

cities = sorted(
    df["city"].dropna().astype(str).unique().tolist()
)

selected_categories = st.sidebar.multiselect(
    "Category",
    categories,
    default=categories,
)

selected_products = st.sidebar.multiselect(
    "Product",
    products,
    default=products,
)

selected_cities = st.sidebar.multiselect(
    "City",
    cities,
    default=cities,
)

valid_dates = df["order_date"].dropna()

if not valid_dates.empty:
    min_date = valid_dates.min().date()
    max_date = valid_dates.max().date()

    selected_dates = st.sidebar.date_input(
        "Order date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
else:
    selected_dates = (None, None)


# =========================================================
# 11. APPLY FILTERS
# =========================================================

filtered_df = df[
    df["category"].astype(str).isin(selected_categories)
    & df["product"].astype(str).isin(selected_products)
    & df["city"].astype(str).isin(selected_cities)
].copy()

if (
    isinstance(selected_dates, (tuple, list))
    and len(selected_dates) == 2
    and selected_dates[0] is not None
    and selected_dates[1] is not None
):
    start_date, end_date = selected_dates

    filtered_df = filtered_df[
        filtered_df["order_date"].dt.date.between(
            start_date,
            end_date,
        )
    ]

filtered_mismatch_df = filtered_df.loc[
    ~filtered_df["revenue_match"]
].copy()

filtered_rows = len(filtered_df)
filtered_mismatch_count = len(filtered_mismatch_df)

filtered_mismatch_rate = (
    filtered_mismatch_count / filtered_rows * 100
    if filtered_rows
    else 0
)

filtered_revenue = safe_number(
    filtered_df["revenue"].sum()
)

filtered_expected_revenue = safe_number(
    filtered_df["expected_revenue"].sum()
)


# =========================================================
# 12. DASHBOARD TABS
# =========================================================

(
    tab_overview,
    tab_quality,
    tab_revenue,
    tab_anomalies,
    tab_ai,
    tab_pdf,
    tab_history,
    tab_root_cause,
) = st.tabs(
    [
        "📊 Overview",
        "🧪 Data Quality",
        "💰 Revenue Analytics",
        "🚨 Anomalies",
        "🤖 AI Analyst",
        "📄 PDF Report",
        "🕒 Pipeline History",
        "🔎 Root Cause Analysis",
    ]
)


# =========================================================
# 13. OVERVIEW
# =========================================================

with tab_overview:
    st.subheader("Executive Overview")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Raw Records",
        format_number(len(raw_df)),
    )

    c2.metric(
        "Cleaned Records",
        format_number(total_rows),
    )

    c3.metric(
        "Revenue Mismatches",
        format_number(mismatch_count),
        delta=f"{mismatch_rate:.2f}% of cleaned rows",
        delta_color="inverse",
    )

    c4.metric(
        "Data Quality Score",
        f"{quality_score:.1f}/100",
    )

    st.markdown("---")

    left, right = st.columns(2)

    with left:
        st.markdown("### Records by Category")

        if not filtered_df.empty:
            category_data = (
                filtered_df.groupby("category", dropna=False)
                .size()
                .reset_index(name="records")
                .sort_values("records", ascending=False)
            )

            fig = px.bar(
                category_data,
                x="category",
                y="records",
                title="Cleaned Records by Category",
                template="plotly_dark",
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
            )
        else:
            st.info("No records match the filters.")

    with right:
        st.markdown("### Revenue by City")

        if not filtered_df.empty:
            city_data = (
                filtered_df.groupby("city", dropna=False)["revenue"]
                .sum()
                .reset_index()
                .sort_values("revenue", ascending=False)
                .head(15)
            )

            fig = px.bar(
                city_data,
                x="city",
                y="revenue",
                title="Revenue by City",
                template="plotly_dark",
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
            )
        else:
            st.info("No revenue data is available.")

    st.markdown("### Recent Cleaned Records")

    st.dataframe(
        filtered_df.head(20),
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        "⬇️ Download Filtered Sales CSV",
        data=make_csv(filtered_df),
        file_name="filtered_sales_data.csv",
        mime="text/csv",
    )


# =========================================================
# 14. DATA QUALITY
# =========================================================

with tab_quality:
    st.subheader("Data Quality Validation")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Rows Checked",
        format_number(filtered_rows),
    )

    c2.metric(
        "Revenue Matches",
        format_number(
            int(filtered_df["revenue_match"].sum())
            if filtered_rows
            else 0
        ),
    )

    c3.metric(
        "Revenue Mismatches",
        format_number(filtered_mismatch_count),
    )

    c4.metric(
        "Mismatch Rate",
        f"{filtered_mismatch_rate:.2f}%",
    )

    quality_components = pd.DataFrame(
        {
            "Component": [
                "Completeness",
                "Revenue Validation",
                "Duplicate-Free Rate",
            ],
            "Score": [
                completeness,
                100 - mismatch_rate,
                duplicate_free_rate,
            ],
        }
    )

    fig = px.bar(
        quality_components,
        x="Component",
        y="Score",
        range_y=[0, 100],
        text_auto=".1f",
        title="Quality Component Scores",
        template="plotly_dark",
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

    st.caption(
        "Illustrative quality score: 50% completeness, "
        "35% revenue validation, and 15% duplicate-free rate."
    )

    st.markdown("### Revenue Mismatch Records")

    mismatch_columns = [
        "order_id",
        "product",
        "quantity",
        "unit_price",
        "revenue",
        "expected_revenue",
        "revenue_difference",
    ]

    st.dataframe(
        filtered_mismatch_df[mismatch_columns].head(100),
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        "⬇️ Download Revenue Mismatches",
        data=make_csv(filtered_mismatch_df),
        file_name="revenue_mismatches.csv",
        mime="text/csv",
    )

    st.markdown("### Missing Values")

    completeness_data = pd.DataFrame(
        {
            "Column": required_sales_columns,
            "Missing Values": [
                int(df[column].isna().sum())
                for column in required_sales_columns
            ],
        }
    )

    st.dataframe(
        completeness_data,
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### Duplicate Order IDs")

    duplicate_data = df.loc[
        df.duplicated(
            subset=["order_id"],
            keep=False,
        )
    ]

    st.write(
        f"Rows with repeated order IDs: {len(duplicate_data):,}"
    )

    if not duplicate_data.empty:
        st.dataframe(
            duplicate_data.head(50),
            use_container_width=True,
            hide_index=True,
        )


# =========================================================
# 15. REVENUE ANALYTICS
# =========================================================

with tab_revenue:
    st.subheader("Revenue Analytics")

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Actual Revenue",
        f"{filtered_revenue:,.2f}",
    )

    c2.metric(
        "Expected Revenue",
        f"{filtered_expected_revenue:,.2f}",
    )

    c3.metric(
        "Revenue Difference",
        f"{filtered_revenue - filtered_expected_revenue:,.2f}",
    )

    st.markdown("### Revenue Trend")

    dated_data = filtered_df.dropna(
        subset=["order_date"]
    ).copy()

    if not dated_data.empty:
        daily_revenue = (
            dated_data.groupby(
                dated_data["order_date"].dt.date
            )["revenue"]
            .sum()
            .reset_index()
        )

        daily_revenue.columns = [
            "order_date",
            "revenue",
        ]

        fig = px.line(
            daily_revenue,
            x="order_date",
            y="revenue",
            markers=True,
            title="Daily Revenue Trend",
            template="plotly_dark",
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )
    else:
        st.info("No valid order dates are available.")

    left, right = st.columns(2)

    with left:
        st.markdown("### Revenue by Product")

        if not filtered_df.empty:
            product_data = (
                filtered_df.groupby("product")["revenue"]
                .sum()
                .reset_index()
                .sort_values("revenue", ascending=False)
                .head(15)
            )

            fig = px.bar(
                product_data,
                x="revenue",
                y="product",
                orientation="h",
                title="Top Products by Revenue",
                template="plotly_dark",
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
            )

    with right:
        st.markdown("### Revenue by State")

        if not filtered_df.empty:
            state_data = (
                filtered_df.groupby("state")["revenue"]
                .sum()
                .reset_index()
                .sort_values("revenue", ascending=False)
            )

            fig = px.pie(
                state_data,
                names="state",
                values="revenue",
                title="Revenue Distribution by State",
                template="plotly_dark",
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
            )


# =========================================================
# 16. ANOMALIES
# =========================================================

with tab_anomalies:
    st.subheader("Anomaly Investigation")

    c1, c2 = st.columns(2)

    c1.metric(
        "Rows in Anomaly Table",
        format_number(len(anomalies_df)),
    )

    c2.metric(
        "Revenue Mismatches",
        format_number(mismatch_count),
    )

    st.caption(
        "A statistical anomaly is not automatically a data error. "
        "Validate unusual records against business rules."
    )

    if anomalies_df.empty:
        st.info("No anomaly records were returned.")
    else:
        st.dataframe(
            anomalies_df.head(200),
            use_container_width=True,
            hide_index=True,
        )

        st.download_button(
            "⬇️ Download Anomaly Records",
            data=make_csv(anomalies_df),
            file_name="sales_anomalies.csv",
            mime="text/csv",
        )

    st.markdown("### Largest Revenue Differences")

    if not mismatch_df.empty:
        largest = mismatch_df.copy()

        largest["absolute_difference"] = (
            largest["revenue_difference"].abs()
        )

        largest = largest.sort_values(
            "absolute_difference",
            ascending=False,
        )

        st.dataframe(
            largest[
                [
                    "order_id",
                    "product",
                    "quantity",
                    "unit_price",
                    "revenue",
                    "expected_revenue",
                    "revenue_difference",
                ]
            ].head(20),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.success("No revenue mismatches detected.")


# =========================================================
# 17. AI ANALYST
# =========================================================

with tab_ai:
    st.subheader("🤖 AI-Powered Data Quality Analyst")

    st.write(
        "Generate a Groq AI report using real data-quality "
        "metrics and representative records."
    )

    st.warning(
        "AI findings are recommendations, not verified root causes. "
        "No data is changed automatically."
    )

    if st.button(
        "Analyze Data Quality with AI",
        type="primary",
        key="run_ai_quality",
    ):
        if "GROQ_API_KEY" not in st.secrets:
            st.error("GROQ_API_KEY is missing from Streamlit secrets.")
        else:
            try:
                with st.spinner("Analyzing data quality..."):
                    client = Groq(
                        api_key=st.secrets["GROQ_API_KEY"]
                    )

                    samples = (
                        mismatch_df[
                            [
                                "order_id",
                                "product",
                                "quantity",
                                "unit_price",
                                "revenue",
                                "expected_revenue",
                                "revenue_difference",
                            ]
                        ]
                        .head(10)
                        .to_dict(orient="records")
                    )

                    anomaly_samples = (
                        anomalies_df.head(10)
                        .to_dict(orient="records")
                    )

                    summary = {
                        "raw_rows": len(raw_df),
                        "cleaned_rows": total_rows,
                        "matching_rows": matching_rows,
                        "mismatch_count": mismatch_count,
                        "mismatch_rate_percent": round(
                            mismatch_rate, 2
                        ),
                        "completeness_percent": round(
                            completeness, 2
                        ),
                        "duplicate_rows": duplicate_rows,
                        "quality_score": round(
                            quality_score, 2
                        ),
                    }

                    prompt = f"""
You are an evidence-based DataOps analyst.

Metrics:
{json.dumps(summary, default=str, indent=2)}

Revenue mismatch samples:
{json.dumps(samples, default=str, indent=2)}

Anomaly samples:
{json.dumps(anomaly_samples, default=str, indent=2)}

Use these headings:
1. Main Data Quality Issues
2. Evidence from Actual Records
3. Possible Root Causes
4. Recommended Investigations
5. Corrective Actions Requiring Approval

Distinguish observations from hypotheses.
Do not invent data or claim a cause is confirmed without evidence.
Do not assume discounts or taxes exist without evidence.
Never claim you changed any data.
Use simple language.
"""

                    response = client.chat.completions.create(
                        model="openai/gpt-oss-120b",
                        messages=[
                            {
                                "role": "system",
                                "content": (
                                    "You are a careful DataOps analyst. "
                                    "Use evidence and never modify data."
                                ),
                            },
                            {
                                "role": "user",
                                "content": prompt,
                            },
                        ],
                        temperature=0.2,
                    )

                    st.session_state["ai_report"] = (
                        response.choices[0].message.content
                    )

            except Exception as error:
                st.error("AI analysis failed.")
                st.code(str(error))

    if st.session_state.get("ai_report"):
        st.markdown("### AI Analysis Results")

        st.markdown(
            st.session_state["ai_report"]
        )

        st.download_button(
            "⬇️ Download AI Analysis",
            data=st.session_state["ai_report"],
            file_name="ai_data_quality_analysis.md",
            mime="text/markdown",
        )


# =========================================================
# 18. PDF REPORT FUNCTION
# =========================================================

def generate_quality_pdf(
    metrics,
    mismatch_records,
    anomaly_records,
    ai_report=None,
):
    """Generate a PDF report in memory."""

    output = io.BytesIO()

    document = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        rightMargin=0.45 * inch,
        leftMargin=0.45 * inch,
        topMargin=0.45 * inch,
        bottomMargin=0.45 * inch,
    )

    styles = getSampleStyleSheet()
    story = []

    story.append(
        Paragraph(
            "Agentic DataOps Control Center",
            styles["Title"],
        )
    )

    story.append(
        Paragraph(
            "Data Quality and Pipeline Report",
            styles["Heading2"],
        )
    )

    story.append(
        Paragraph(
            f"Generated at: {pd.Timestamp.now(tz='UTC')}",
            styles["Normal"],
        )
    )

    story.append(Spacer(1, 16))

    metric_rows = [
        ["Metric", "Value"],
        ["Pipeline Status", str(metrics["pipeline_status"])],
        ["Raw Rows", str(metrics["raw_rows"])],
        ["Cleaned Rows", str(metrics["cleaned_rows"])],
        ["Rows Removed", str(metrics["rows_removed"])],
        ["Anomaly Rows", str(metrics["anomaly_rows"])],
        ["Revenue Matches", str(metrics["matching_rows"])],
        ["Revenue Mismatches", str(metrics["mismatch_count"])],
        ["Mismatch Rate", f"{metrics['mismatch_rate']:.2f}%"],
        ["Completeness", f"{metrics['completeness']:.2f}%"],
        ["Duplicate Rows", str(metrics["duplicate_rows"])],
        ["Quality Score", f"{metrics['quality_score']:.2f}/100"],
    ]

    metric_table = Table(
        metric_rows,
        colWidths=[2.3 * inch, 2.2 * inch],
        repeatRows=1,
    )

    metric_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#1D4ED8"),
                ),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    story.append(metric_table)
    story.append(Spacer(1, 18))

    story.append(
        Paragraph(
            "Revenue Mismatch Samples",
            styles["Heading2"],
        )
    )

    mismatch_rows = [
        [
            "Order ID",
            "Product",
            "Quantity",
            "Unit Price",
            "Revenue",
            "Expected",
            "Difference",
        ]
    ]

    for _, row in mismatch_records.head(15).iterrows():
        mismatch_rows.append(
            [
                str(row.get("order_id", ""))[:22],
                str(row.get("product", ""))[:22],
                str(row.get("quantity", "")),
                str(row.get("unit_price", "")),
                str(row.get("revenue", "")),
                str(row.get("expected_revenue", "")),
                str(row.get("revenue_difference", "")),
            ]
        )

    mismatch_table = Table(
        mismatch_rows,
        repeatRows=1,
    )

    mismatch_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#1D4ED8"),
                ),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("PADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )

    story.append(mismatch_table)
    story.append(Spacer(1, 18))

    story.append(
        Paragraph(
            "Anomaly Samples",
            styles["Heading2"],
        )
    )

    if anomaly_records.empty:
        story.append(
            Paragraph(
                "No anomaly records were returned.",
                styles["Normal"],
            )
        )
    else:
        anomaly_columns = [
            column
            for column in [
                "order_id",
                "product",
                "anomaly_status",
                "revenue",
            ]
            if column in anomaly_records.columns
        ]

        if anomaly_columns:
            anomaly_rows = [anomaly_columns]

            for _, row in anomaly_records[
                anomaly_columns
            ].head(15).iterrows():
                anomaly_rows.append(
                    [
                        str(row.get(column, ""))[:35]
                        for column in anomaly_columns
                    ]
                )

            anomaly_table = Table(
                anomaly_rows,
                repeatRows=1,
            )

            anomaly_table.setStyle(
                TableStyle(
                    [
                        (
                            "BACKGROUND",
                            (0, 0),
                            (-1, 0),
                            colors.HexColor("#1D4ED8"),
                        ),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                        ("FONTSIZE", (0, 0), (-1, -1), 7),
                        ("PADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )

            story.append(anomaly_table)

    if ai_report:
        story.append(PageBreak())

        story.append(
            Paragraph(
                "AI Data Quality Analysis",
                styles["Heading1"],
            )
        )

        for paragraph in ai_report.splitlines():
            paragraph = paragraph.strip()

            if paragraph:
                safe_paragraph = (
                    paragraph.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                )

                story.append(
                    Paragraph(
                        safe_paragraph,
                        styles["Normal"],
                    )
                )

                story.append(Spacer(1, 6))

    story.append(Spacer(1, 18))

    story.append(
        Paragraph(
            "Important: Revenue mismatches and statistical anomalies "
            "require business-rule validation. This report does not "
            "confirm the root cause of each issue. No sales data was "
            "modified by generating this report.",
            styles["Italic"],
        )
    )

    document.build(story)

    output.seek(0)

    return output.getvalue()


# =========================================================
# 19. PDF REPORT TAB
# =========================================================

with tab_pdf:
    st.subheader("📄 Data Quality PDF Report")

    st.write(
        "Generate a report containing pipeline metrics, "
        "revenue mismatch samples, anomalies and AI analysis."
    )

    latest_status = (
        str(pipeline_history.iloc[0]["pipeline_status"])
        if not pipeline_history.empty
        else "NO HISTORY"
    )

    latest_raw_rows = (
        safe_number(pipeline_history.iloc[0]["raw_rows"])
        if not pipeline_history.empty
        else len(raw_df)
    )

    latest_cleaned_rows = (
        safe_number(pipeline_history.iloc[0]["cleaned_rows"])
        if not pipeline_history.empty
        else len(df)
    )

    latest_rows_removed = (
        safe_number(pipeline_history.iloc[0]["rows_removed"])
        if not pipeline_history.empty
        else max(0, len(raw_df) - len(df))
    )

    latest_anomaly_rows = (
        safe_number(pipeline_history.iloc[0]["anomaly_rows"])
        if not pipeline_history.empty
        else len(anomalies_df)
    )

    report_metrics = {
        "pipeline_status": latest_status,
        "raw_rows": latest_raw_rows,
        "cleaned_rows": latest_cleaned_rows,
        "rows_removed": latest_rows_removed,
        "anomaly_rows": latest_anomaly_rows,
        "matching_rows": matching_rows,
        "mismatch_count": mismatch_count,
        "mismatch_rate": mismatch_rate,
        "completeness": completeness,
        "duplicate_rows": duplicate_rows,
        "quality_score": quality_score,
    }

    if st.button(
        "Generate PDF Report",
        type="primary",
        key="generate_pdf",
    ):
        try:
            pdf_bytes = generate_quality_pdf(
                metrics=report_metrics,
                mismatch_records=mismatch_df,
                anomaly_records=anomalies_df,
                ai_report=st.session_state.get("ai_report"),
            )

            st.session_state["quality_pdf"] = pdf_bytes

            st.success("PDF report generated.")

        except Exception as error:
            st.error("Could not generate PDF.")
            st.code(str(error))

    if st.session_state.get("quality_pdf"):
        st.download_button(
            "⬇️ Download PDF Report",
            data=st.session_state["quality_pdf"],
            file_name="agentic_dataops_quality_report.pdf",
            mime="application/pdf",
        )


# =========================================================
# 20. PIPELINE HISTORY TAB
# =========================================================

with tab_history:
    st.subheader("🕒 Pipeline Run History")

    st.caption(
        "Historical monitoring records from Databricks."
    )

    if pipeline_history.empty:
        st.info("No pipeline history is available.")
    else:
        latest = pipeline_history.iloc[0]

        status = str(latest["pipeline_status"]).upper()

        if status == "SUCCESS":
            st.success(f"Latest pipeline status: {status}")
        elif status in {
            "WARNING",
            "FAILED",
            "FAILURE",
            "ERROR",
        }:
            st.warning(f"Latest pipeline status: {status}")
        else:
            st.info(f"Latest pipeline status: {status}")

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Latest Raw Rows",
            format_number(latest["raw_rows"]),
        )

        c2.metric(
            "Latest Cleaned Rows",
            format_number(latest["cleaned_rows"]),
        )

        c3.metric(
            "Rows Removed",
            format_number(latest["rows_removed"]),
        )

        c4.metric(
            "Anomaly Rows",
            format_number(latest["anomaly_rows"]),
        )

        history_display = pipeline_history.copy()

        history_display["run_timestamp"] = (
            history_display["run_timestamp"]
            .dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        )

        st.markdown("### Recorded Runs")

        st.dataframe(
            history_display,
            use_container_width=True,
            hide_index=True,
        )

        st.download_button(
            "⬇️ Download Pipeline History CSV",
            data=make_csv(history_display),
            file_name="pipeline_run_history.csv",
            mime="text/csv",
        )

        st.markdown("### Record Counts Across Runs")

        chart_data = pipeline_history.sort_values(
            "run_timestamp"
        ).set_index("run_timestamp")

        st.line_chart(
            chart_data[
                [
                    "raw_rows",
                    "cleaned_rows",
                    "anomaly_rows",
                ]
            ]
        )

        st.markdown("### Pipeline Status Distribution")

        status_counts = (
            pipeline_history["pipeline_status"]
            .astype(str)
            .value_counts()
            .rename_axis("pipeline_status")
            .reset_index(name="run_count")
        )

        fig = px.bar(
            status_counts,
            x="pipeline_status",
            y="run_count",
            text_auto=True,
            title="Recorded Runs by Status",
            template="plotly_dark",
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )

        st.caption(
            "These charts show records already present in "
            "pipeline_monitoring. They do not create new runs."
        )


# =========================================================
# 21. ROOT CAUSE ANALYSIS TAB
# =========================================================

with tab_root_cause:
    st.subheader("🔎 AI-Powered Root Cause Analysis")

    st.write(
        "Investigate actual revenue mismatches and anomaly "
        "records using evidence-based AI recommendations."
    )

    st.warning(
        "Possible causes are hypotheses until verified. "
        "No corrective changes are executed automatically."
    )

    # Select records from the complete cleaned dataset.
    # This avoids limiting root-cause analysis to sidebar filters.
    root_cause_mismatches = mismatch_df.copy()

    if not root_cause_mismatches.empty:
        root_cause_mismatches["absolute_difference"] = (
            root_cause_mismatches["revenue_difference"].abs()
        )

        root_cause_mismatches = (
            root_cause_mismatches.sort_values(
                "absolute_difference",
                ascending=False,
            )
        )

    mismatch_columns = [
        "order_id",
        "product",
        "quantity",
        "unit_price",
        "revenue",
        "expected_revenue",
        "revenue_difference",
    ]

    mismatch_records = (
        root_cause_mismatches[
            mismatch_columns
        ]
        .head(20)
        .to_dict(orient="records")
        if not root_cause_mismatches.empty
        else []
    )

    anomaly_records = (
        anomalies_df.head(20)
        .to_dict(orient="records")
    )

    quality_summary = {
        "raw_rows": len(raw_df),
        "cleaned_rows": total_rows,
        "revenue_matches": matching_rows,
        "revenue_mismatches": mismatch_count,
        "revenue_mismatch_rate_percent": round(
            mismatch_rate,
            2,
        ),
        "completeness_percent": round(
            completeness,
            2,
        ),
        "duplicate_rows": duplicate_rows,
        "quality_score": round(
            quality_score,
            2,
        ),
    }

    with st.expander("View records selected for investigation"):
        st.write(
            "The AI receives up to 20 largest revenue mismatches "
            "and 20 anomaly records."
        )

        if mismatch_records:
            st.dataframe(
                pd.DataFrame(mismatch_records),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No revenue mismatch records are available.")

        if anomaly_records:
            st.markdown("### Anomaly Samples")

            st.dataframe(
                pd.DataFrame(anomaly_records),
                use_container_width=True,
                hide_index=True,
            )

    if st.button(
        "🔍 Run Root Cause Analysis",
        type="primary",
        key="run_root_cause_analysis",
    ):
        try:
            with st.spinner(
                "Groq AI is investigating actual records..."
            ):
                report = analyze_root_causes(
                    mismatch_records=mismatch_records,
                    anomaly_records=anomaly_records,
                    quality_summary=quality_summary,
                )

                st.session_state["root_cause_report"] = report

        except Exception as error:
            st.error(
                "Root Cause Analysis could not be completed."
            )
            st.code(str(error))

    report = st.session_state.get(
        "root_cause_report"
    )

    if report:
        st.markdown("---")
        st.markdown("### Investigation Report")
        st.markdown(report)

        st.download_button(
            "⬇️ Download Root Cause Analysis",
            data=report,
            file_name="root_cause_analysis.md",
            mime="text/markdown",
            key="download_root_cause_report",
        )


# =========================================================
# 22. FOOTER
# =========================================================

st.markdown("---")

st.markdown(
    """
    <p class="small-note">
    Agentic DataOps Control Center | Databricks + Streamlit + Groq
    <br>
    Read-only sales analytics. AI recommendations require human review.
    </p>
    """,
    unsafe_allow_html=True,
)
