import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Compare Periods",
    page_icon="📊",
    layout="wide"
)

# --------------------------------------------------
# LOAD DATA FROM DASHBOARD
# --------------------------------------------------

if "df" not in st.session_state:
    st.warning("Please upload a CSV on the Earnings Dashboard first.")
    st.stop()

df = st.session_state["df"].copy()

# --------------------------------------------------
# CLEAN / VALIDATE DATA
# --------------------------------------------------

df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

money_columns = [
    "Gross earnings",
    "Service fee",
    "Cleaning fee",
    "Amount",
    "Airbnb remitted tax"
]

for column in money_columns:
    if column in df.columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        ).fillna(0)

if "Nights" in df.columns:
    df["Nights"] = pd.to_numeric(
        df["Nights"],
        errors="coerce"
    ).fillna(0)

df = df.dropna(subset=["Date"])

if df.empty:
    st.error("No valid payout dates were found in the uploaded CSV.")
    st.stop()

# --------------------------------------------------
# PAGE HEADER
# --------------------------------------------------

st.title("📊 Compare Time Periods")
st.write(
    "Compare monthly or yearly earnings across properties."
)

# --------------------------------------------------
# PROPERTY FILTER
# --------------------------------------------------

listings = sorted(
    df["Listing"]
    .dropna()
    .unique()
    .tolist()
)

selected_listing = st.selectbox(
    "Property",
    ["All Properties"] + listings
)

# Filter property first so available periods match the selected property
working_df = df.copy()

if selected_listing != "All Properties":
    working_df = working_df[
        working_df["Listing"] == selected_listing
    ].copy()

if working_df.empty:
    st.warning("No data is available for the selected property.")
    st.stop()

# --------------------------------------------------
# COMPARISON SETTINGS
# --------------------------------------------------

comparison_type = st.radio(
    "Comparison Type",
    ["Month", "Year"],
    horizontal=True
)

number_of_periods = st.selectbox(
    "Number of periods to compare",
    [2, 3, 4],
    index=0
)

comparison_results = []

# --------------------------------------------------
# HELPER FUNCTION
# --------------------------------------------------

def summarize_period(period_df, label):
    period_df = period_df.copy()

    period_df["Airbnb Payout"] = (
        period_df["Gross earnings"]
        - period_df["Service fee"]
    )

    period_df["True Earnings"] = (
        period_df["Gross earnings"]
        - period_df["Service fee"]
        - period_df["Cleaning fee"]
    )

    return {
        "Period": label,
        "True Earnings": period_df["True Earnings"].sum(),
        "Airbnb Payout": period_df["Airbnb Payout"].sum(),
        "Gross Earnings": period_df["Gross earnings"].sum(),
        "Service Fees": period_df["Service fee"].sum(),
        "Cleaning Fees": period_df["Cleaning fee"].sum(),
        "Nights": period_df["Nights"].sum()
    }

# --------------------------------------------------
# MONTH COMPARISON
# --------------------------------------------------

if comparison_type == "Month":

    # Create one option for every month/year actually present in the data
    month_options = (
        working_df["Date"]
        .dt.to_period("M")
        .drop_duplicates()
        .sort_values()
        .tolist()
    )

    if not month_options:
        st.warning("No monthly data is available.")
        st.stop()

    st.subheader("Choose Months")

    selected_months = []

    for i in range(number_of_periods):
        default_index = max(0, len(month_options) - number_of_periods + i)

        selected_period = st.selectbox(
            f"Period {i + 1}",
            month_options,
            index=default_index,
            format_func=lambda p: p.strftime("%B %Y"),
            key=f"month_period_{i}"
        )

        selected_months.append(selected_period)

    for selected_period in selected_months:
        period_df = working_df[
            working_df["Date"].dt.to_period("M") == selected_period
        ].copy()

        label = selected_period.strftime("%B %Y")

        comparison_results.append(
            summarize_period(period_df, label)
        )

# --------------------------------------------------
# YEAR COMPARISON
# --------------------------------------------------

else:

    year_options = sorted(
        working_df["Date"]
        .dt.year
        .dropna()
        .unique()
        .tolist()
    )

    if not year_options:
        st.warning("No yearly data is available.")
        st.stop()

    st.subheader("Choose Years")

    selected_years = []

    for i in range(number_of_periods):
        default_index = max(0, len(year_options) - number_of_periods + i)

        selected_year = st.selectbox(
            f"Period {i + 1}",
            year_options,
            index=default_index,
            key=f"year_period_{i}"
        )

        selected_years.append(selected_year)

    for selected_year in selected_years:
        period_df = working_df[
            working_df["Date"].dt.year == selected_year
        ].copy()

        comparison_results.append(
            summarize_period(
                period_df,
                str(selected_year)
            )
        )

# --------------------------------------------------
# RESULTS TABLE
# --------------------------------------------------

comparison_df = pd.DataFrame(comparison_results)

st.divider()
st.subheader("Comparison")

st.dataframe(
    comparison_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "True Earnings": st.column_config.NumberColumn(
            "True Earnings",
            format="$%.2f"
        ),
        "Airbnb Payout": st.column_config.NumberColumn(
            "Airbnb Payout",
            format="$%.2f"
        ),
        "Gross Earnings": st.column_config.NumberColumn(
            "Gross Earnings",
            format="$%.2f"
        ),
        "Service Fees": st.column_config.NumberColumn(
            "Service Fees",
            format="$%.2f"
        ),
        "Cleaning Fees": st.column_config.NumberColumn(
            "Cleaning Fees",
            format="$%.2f"
        ),
        "Nights": st.column_config.NumberColumn(
            "Nights",
            format="%.0f"
        )
    }
)

# --------------------------------------------------
# % DIFFERENCE FOR TWO PERIODS
# --------------------------------------------------

if len(comparison_df) == 2:

    st.subheader(
        f"Change: {comparison_df.loc[0, 'Period']} → "
        f"{comparison_df.loc[1, 'Period']}"
    )

    metrics = [
        "True Earnings",
        "Airbnb Payout",
        "Gross Earnings",
        "Service Fees",
        "Cleaning Fees",
        "Nights"
    ]

    top_cols = st.columns(3)
    bottom_cols = st.columns(3)

    for idx, metric in enumerate(metrics):

        first_value = comparison_df.loc[0, metric]
        second_value = comparison_df.loc[1, metric]

        difference = second_value - first_value

        if first_value != 0:
            percent_change = (
                difference / first_value
            ) * 100
            delta_text = f"{percent_change:+.1f}%"
        else:
            delta_text = "N/A"

        if metric == "Nights":
            value_text = f"{difference:+,.0f}"
        else:
            value_text = f"${difference:+,.2f}"

        target_cols = top_cols if idx < 3 else bottom_cols
        target_col = target_cols[idx % 3]

        with target_col:
            st.metric(
                metric,
                value_text,
                delta_text
            )

# --------------------------------------------------
# PLOTLY COMPARISON CHART
# --------------------------------------------------

st.subheader("Comparison Chart")

comparison_metric = st.selectbox(
    "Compare metric",
    [
        "True Earnings",
        "Airbnb Payout",
        "Gross Earnings",
        "Service Fees",
        "Cleaning Fees",
        "Nights"
    ]
)

fig_compare = px.bar(
    comparison_df,
    x="Period",
    y=comparison_metric,
    text=comparison_metric
)

fig_compare.update_layout(
    xaxis_title="",
    yaxis_title=comparison_metric,
    showlegend=False
)

if comparison_metric != "Nights":

    fig_compare.update_yaxes(
        tickprefix="$",
        tickformat=",.0f"
    )

    fig_compare.update_traces(
        texttemplate="$%{text:,.0f}",
        hovertemplate=(
            "<b>%{x}</b><br>"
            + comparison_metric
            + ": $%{y:,.2f}"
            + "<extra></extra>"
        )
    )

else:

    fig_compare.update_traces(
        texttemplate="%{text:,.0f}",
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Nights: %{y:,.0f}"
            "<extra></extra>"
        )
    )

st.plotly_chart(
    fig_compare,
    use_container_width=True
)
