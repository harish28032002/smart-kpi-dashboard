# RetailIQ — Smart KPI Dashboard

An AI-powered operational intelligence dashboard that ingests structured business data, visualises key performance metrics, and generates plain-English narrative insights using a large language model. Built as a POC for the Firstsource STEM assessment.

---

## Quick Start

### Prerequisites

- Python 3.11 or higher
- A free [Groq API key](https://console.groq.com)
- A Gmail account with an [App Password](https://myaccount.google.com/apppasswords) enabled (for email export)

### Installation

```bash
# Clone the repository
git clone https://github.com/harish28032002/smart-kpi-dashboard.git
cd smart-kpi-dashboard

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Environment Setup

Create a `.env` file in the root directory:

```
GROQ_API_KEY=your_groq_api_key_here
SENDER_EMAIL=your_gmail_address@gmail.com
SENDER_APP_PASSWORD=your_16_character_app_password
```

### Run the Dashboard

```bash
streamlit run app.py
```

The dashboard will open at `http://localhost:8501`.

---

## Dataset

**Source:** [Sample Superstore — Kaggle](https://www.kaggle.com/datasets/vivek468/superstore-dataset-final)

**File:** `Sample - Superstore.csv`

Place the CSV file in the root of the project directory before running the app.

| Column | Description |
|---|---|
| Order Date | Transaction date, used for time-series aggregation |
| Region | Geographic region: Central, East, South, West |
| Category | Product line: Furniture, Office Supplies, Technology |
| Sub-Category | Granular product grouping (28 sub-categories) |
| Sales | Revenue per order row |
| Profit | Profit per order row |
| Quantity | Units ordered |
| Discount | Discount rate applied (0.0 to 1.0) |
| Order ID | Unique order identifier for order-level aggregation |

The dataset contains 9,994 rows spanning January 2014 to December 2017.

---

## Data Ingestion and Visualisation Flow

### Ingestion

```python
@st.cache_data
def load_data():
    df = pd.read_csv("Sample - Superstore.csv", encoding="latin-1")
    df["Order Date"] = pd.to_datetime(df["Order Date"])
    df["Month"] = df["Order Date"].dt.to_period("M").astype(str)
    return df
```

On load, the app validates that all required columns are present and checks for null values in Sales and Profit. If validation fails, the app stops and surfaces a clear error message.

### Filtering

Three sidebar filters are applied before any KPI is computed:

1. **Region** — filters to a single region or all four
2. **Product Line** — filters to a single category or all three
3. **Period Range** — a date slider that forces boundaries to the first and last day of the selected months using `calendar.monthrange` to avoid boundary inconsistencies

### KPI Computation

All KPIs are computed from the filtered dataframe after filters are applied:

| KPI | Calculation |
|---|---|
| Total Revenue | `filtered_df["Sales"].sum()` |
| Total Profit | `filtered_df["Profit"].sum()` |
| Profit Margin | `(Total Profit / Total Revenue) * 100` |
| Total Orders | `filtered_df["Order ID"].nunique()` |
| Average Discount | Weighted by order sales value: `(Discount * Sales).sum() / Sales.sum() * 100` |

The average discount uses a sales-weighted calculation rather than a simple mean to avoid over-representing small high-discount orders.

### Visualisation

Four charts are rendered using Plotly Express:

- **Monthly Revenue Trend with Forecast** — line chart showing actual revenue (blue) and a 3-month linear projection (orange)
- **Monthly Profit Trend** — line chart showing profit over time
- **Monthly Order Volume** — bar chart of order counts per month
- **Revenue by Product Line** — pie chart showing category revenue split

All charts respond dynamically to sidebar filter changes.

---

## AI Commentary Logic

### Model

**Groq API — LLaMA 3.3 70B Versatile**

Groq was selected over Gemini and OpenAI because it provides a genuinely free tier with no credit card requirement and sufficient quota for POC use. LLaMA 3.3 70B produces high-quality business narrative that follows structured prompt instructions reliably.

### Prompt Design

Each KPI receives its own API call with a context block containing specific data relevant to that metric. The prompt enforces a fixed three-label structure:

```
You are a senior business analyst preparing a KPI report for company leadership.

You must respond using EXACTLY these four labels, each on its own line.
Do not change the labels. Do not add extra lines. Do not use markdown or special characters.
Write all currency values as plain text.

WHAT IT MEANS: [one sentence explaining what this KPI value indicates]
TREND: [one sentence describing the trend over recent months]
NEXT STEP: [one sentence recommending a specific action for leadership]

KPI Name: {kpi_name}
Current Value: {value}
Supporting Data: {context_data}
Filters applied: Region: {selected_region} | Product Line: {selected_category} |
Date Range: {start_date_forced} to {end_date_forced}
```

Key prompt engineering decisions:

- **No generic language rule** — the prompt explicitly forbids phrases like "the company is performing well" and requires specific numbers in every sentence
- **Filter context injected** — when a region or category filter is active, the model is told it is analysing a filtered subset and must not make claims about the overall business
- **Currency formatting** — numbers are written as plain text to prevent Streamlit's markdown renderer from italicising comma-separated values

### Context Per KPI

Each KPI receives tailored context rather than a single shared summary. For example:

**Total Revenue context includes:**
- Full monthly revenue trend
- Best and worst revenue months
- Month-on-month change for the most recent period
- Top and bottom region and category breakdown

**Average Discount context includes:**
- Most discounted sub-category
- Revenue and profit from orders with over 20% discount
- Profit margin alongside the discount rate to surface the margin compression relationship

### Response Parsing

The raw model response is cleaned and parsed client-side:

```python
def parse_and_display_commentary(commentary, kpi_name):
    lines = commentary.strip().split("\n")
    parsed = {}
    keys = ["WHAT IT MEANS", "TREND", "NEXT STEP"]
    for line in lines:
        line = line.strip()
        for key in keys:
            if line.upper().startswith(key + ":"):
                content = line[len(key) + 1:].strip()
                parsed[key] = content
                break
```

This parser extracts the three fields regardless of minor formatting variations in the model output, ensuring consistent display across all KPIs and filter states.

### Example Input and Output

**Input — Total Revenue KPI**

```
KPI Name: Total Revenue
Current Value: USD 2,297,201
Supporting Data:
  Top region: West. Top category: Technology.
  Last 6 months trend: [{'Month': '2017-07', 'Revenue': 51843},
    {'Month': '2017-08', 'Revenue': 47648}, ...]
  Best month: 2017-11. Worst month: 2014-02.
  Month-on-month change: -15.5%.
```

**Output**

```
WHAT IT MEANS: Total revenue of 2.3 million dollars reflects strong overall
  demand, with Technology in the West region driving the highest contribution.

TREND: Revenue peaked at 118,447 dollars in November 2017 before declining
  15.5 percent in December, suggesting a seasonal dip following a strong Q4.

NEXT STEP: Leadership should investigate the December decline and consider
  targeted promotions in the West region to sustain Q4 momentum into Q1 2018.
```

---

## Anomaly Detection

Anomaly detection uses scikit-learn's **Isolation Forest** algorithm:

```python
from sklearn.ensemble import IsolationForest

def detect_anomalies_isolation_forest(series, contamination=0.1):
    if len(series) < 6:
        return np.zeros(len(series), dtype=int)
    data = series.values.reshape(-1, 1)
    model = IsolationForest(
        contamination=contamination,
        random_state=42,
        n_estimators=100
    )
    preds = model.fit_predict(data)
    return preds
```

`contamination=0.1` tells the model to expect approximately 10% of months to be anomalous. This was chosen as a sensible default for business time series data. The top 3 anomalies per metric are displayed, ranked by absolute deviation from the mean.

This replaces a fixed standard deviation threshold approach because Isolation Forest does not assume a normal distribution and adapts to the structure of the data.

---

## Additional Features

Beyond the core brief requirements, the following enhancements were built:

| Feature | Description |
|---|---|
| Period Comparison | Side-by-side KPI table for two user-defined date ranges with automatic newer vs older detection |
| KPI Target Tracking | Revenue, profit, and order targets with progress bars and an overall achievement percentage |
| Performance Heatmap | Profit margin by region and product category using `px.imshow`, highlights best and worst combinations |
| Revenue Forecast | 3-month linear projection using NumPy first-degree polynomial fit |
| Natural Language Q&A | Chat interface with full yearly and monthly context injected as system prompt, enforces 2 to 4 sentence limit |
| PDF Export | Full report with KPI table and AI insights using ReportLab |
| Email Export | HTML email with formatted KPI table and PDF attached via smtplib and Gmail SMTP |
| Data Validation | Column presence check and null value check on load |

---

## Limitations and Assumptions

**Data**
- The dashboard is built and tested against the Sample Superstore dataset. Other datasets will work if they contain the required columns listed in the Dataset section above.
- The date range slider operates at month granularity. Day-level filtering is not supported.
- All monetary values are assumed to be in USD.

**AI Commentary**
- Commentary quality depends on the volume of data in the selected filter range. Very narrow date ranges or single-region selections may produce less specific insights due to limited trend data.
- The Groq free tier has rate limits. Generating insights for all five KPIs in rapid succession may occasionally trigger a brief wait. The progress bar communicates this to the user.
- The natural language Q&A is grounded in the current filtered dataset only. It cannot answer questions about data outside the selected filters.

**Forecast**
- The revenue forecast uses a first-degree polynomial fit, which assumes a linear trend. It does not account for seasonality, cyclicality, or external factors. It is intended as a directional indicator, not a precise prediction.

**Anomaly Detection**
- Isolation Forest requires at least 6 months of data to produce meaningful results. If fewer than 6 months are in the filtered range, the anomaly section defaults to showing no anomalies.
- The `contamination=0.1` parameter is a fixed assumption. In production, this would be tuned based on historical anomaly rates for the specific business.

**Email Export**
- Requires a Gmail account with 2-Step Verification enabled and an App Password configured. Standard Gmail passwords are not supported.
- Email delivery depends on the recipient's spam filters. The HTML report may be caught by some filters.

---

## Project Structure

```
smart-kpi-dashboard/
├── app.py                    # Main Streamlit application
├── requirements.txt          # Python dependencies
├── Sample - Superstore.csv   # Dataset (download from Kaggle)
├── .env                      # API keys and email credentials (not committed)
├── .gitignore                # Excludes .env, venv, __pycache__
└── venv/                     # Virtual environment (not committed)
```

---

## Dependencies

```
streamlit
pandas
plotly
groq
scikit-learn
numpy
reportlab
python-dotenv
```

Full pinned versions are listed in `requirements.txt`.

---

## Submission

**Author:** Harish Kumar Saravanan
**Role applied for:** Forward Deployed Engineer, Firstsource Solutions
**Submission email:** Ricardo.castillo@na.firstsource.com
**Subject line:** STEM_POC_Harish Kumar Saravanan_Smart KPI Dashboard
