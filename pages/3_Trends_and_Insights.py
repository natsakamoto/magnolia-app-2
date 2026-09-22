import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import calendar

# --------------------------------------------------
# PAGE SETUP
# --------------------------------------------------

st.set_page_config(
    page_title="Trends & Insights",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Trends & Insights")
st.caption(
    "Explore seasonality, property performance, booking behavior, "
    "historical trends, forecasts, and future booking pace."
)

# --------------------------------------------------
# LOAD DATA FROM MAIN DASHBOARD
# --------------------------------------------------

if "df" not in st.session_state:
    st.warning(
        "No Airbnb data is loaded yet. Go to the Earnings Dashboard and "
        "upload the Past Earnings / Payout and Future Bookings CSV files first."
    )
    st.stop()

df = st.session_state["df"].copy()

# --------------------------------------------------
# CLEAN / PREPARE DATA
# --------------------------------------------------

date_columns = [
    "Date",
    "Booking date",
    "Start date",
    "End date",
    "Arriving by"
]

for column in date_columns:
    if column in df.columns:
        df[column] = pd.to_datetime(df[column], errors="coerce")

numeric_columns = [
    "Nights",
    "Amount",
    "Service fee",
    "Cleaning fee",
    "Gross earnings",
    "Airbnb remitted tax"
]

for column in numeric_columns:
    if column in df.columns:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)

required_columns = [
    "Start date",
    "Booking date",
    "Nights",
    "Listing",
    "Gross earnings",
    "Service fee",
    "Cleaning fee"
]

missing_columns = [c for c in required_columns if c not in df.columns]

if missing_columns:
    st.error(
        "The combined Airbnb data is missing these required columns: "
        + ", ".join(missing_columns)
    )
    st.stop()

# Keep reservation-level records when Airbnb includes payout summary rows.
if "Type" in df.columns:
    reservation_mask = (
        df["Type"]
        .astype("string")
        .str.strip()
        .str.casefold()
        .eq("reservation")
    )

    # Only filter when reservation rows actually exist.
    if reservation_mask.any():
        df = df.loc[reservation_mask].copy()

df = df.dropna(subset=["Start date"]).copy()

if df.empty:
    st.info("There are no reservation rows with valid Start dates to analyze.")
    st.stop()

# Core calculated metrics
df["Airbnb Payout"] = (
    df["Gross earnings"] - df["Service fee"]
)

df["True Earnings"] = (
    df["Gross earnings"]
    - df["Service fee"]
    - df["Cleaning fee"]
)

df["Year"] = df["Start date"].dt.year
df["Month Number"] = df["Start date"].dt.month
df["Month"] = df["Month Number"].map(
    lambda x: calendar.month_abbr[int(x)]
)

df["Year-Month"] = df["Start date"].dt.to_period("M")
df["Month Label"] = df["Year-Month"].dt.strftime("%b %Y")
df["Check-in Day"] = df["Start date"].dt.day_name()

df["Lead Time"] = (
    df["Start date"] - df["Booking date"]
).dt.days

# Negative lead times are usually bad/misaligned records.
df.loc[df["Lead Time"] < 0, "Lead Time"] = np.nan

df["Earnings/Night"] = np.where(
    df["Nights"] > 0,
    df["True Earnings"] / df["Nights"],
    np.nan
)

# --------------------------------------------------
# TOP FILTERS
# --------------------------------------------------

st.subheader("Analysis Filters")

filter_col1, filter_col2 = st.columns(2)

listings = sorted(df["Listing"].dropna().astype(str).unique().tolist())
available_years = sorted(df["Year"].dropna().astype(int).unique().tolist())

with filter_col1:
    selected_listing = st.selectbox(
        "Property",
        ["All Properties"] + listings,
        key="trends_property"
    )

with filter_col2:
    selected_years = st.multiselect(
        "Years",
        available_years,
        default=available_years,
        key="trends_years"
    )

analysis_df = df.copy()

if selected_listing != "All Properties":
    analysis_df = analysis_df[
        analysis_df["Listing"].astype(str) == selected_listing
    ]

if selected_years:
    analysis_df = analysis_df[
        analysis_df["Year"].isin(selected_years)
    ]
else:
    st.info("Select at least one year to view trends.")
    st.stop()

if analysis_df.empty:
    st.info("No reservations match the selected filters.")
    st.stop()

# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def monthly_summary(data):
    """Create one row per calendar month."""
    out = (
        data.groupby("Year-Month", as_index=False)
        .agg(
            Booked_Nights=("Nights", "sum"),
            Reservations=("Start date", "size"),
            True_Earnings=("True Earnings", "sum")
        )
    )

    out["Earnings_per_Night"] = np.where(
        out["Booked_Nights"] > 0,
        out["True_Earnings"] / out["Booked_Nights"],
        np.nan
    )

    out["Month Date"] = out["Year-Month"].dt.to_timestamp()
    out["Month"] = out["Month Date"].dt.strftime("%b %Y")
    return out.sort_values("Month Date")


def add_complete_months(data):
    """
    Add zero-demand months between the first and last observed stay month.
    This prevents missing months from disappearing from historical charts.
    """
    if data.empty:
        return data

    first_month = data["Year-Month"].min()
    last_month = data["Year-Month"].max()
    all_months = pd.period_range(first_month, last_month, freq="M")

    base = pd.DataFrame({"Year-Month": all_months})
    summary = monthly_summary(data)

    merged = base.merge(
        summary.drop(columns=["Month Date", "Month"]),
        on="Year-Month",
        how="left"
    )

    for col in ["Booked_Nights", "Reservations", "True_Earnings"]:
        merged[col] = merged[col].fillna(0)

    merged["Earnings_per_Night"] = np.where(
        merged["Booked_Nights"] > 0,
        merged["True_Earnings"] / merged["Booked_Nights"],
        np.nan
    )
    merged["Month Date"] = merged["Year-Month"].dt.to_timestamp()
    merged["Month"] = merged["Month Date"].dt.strftime("%b %Y")
    return merged


# ==================================================
# 1. SEASONALITY
# ==================================================

st.divider()
st.header("🌤️ Seasonality")
st.write("**What months historically have the greatest demand?**")

season_metric = st.radio(
    "Measure demand by",
    [
        "Booked Nights",
        "Reservations",
        "True Earnings",
        "Earnings/Night"
    ],
    horizontal=True,
    key="season_metric"
)

# First aggregate within each year/month so that we can average comparable
# months across years instead of allowing years with more rows to dominate.
season_year_month = (
    analysis_df
    .groupby(["Year", "Month Number"], as_index=False)
    .agg(
        Booked_Nights=("Nights", "sum"),
        Reservations=("Start date", "size"),
        True_Earnings=("True Earnings", "sum")
    )
)

season_year_month["Earnings_per_Night"] = np.where(
    season_year_month["Booked_Nights"] > 0,
    season_year_month["True_Earnings"]
    / season_year_month["Booked_Nights"],
    np.nan
)

seasonality = (
    season_year_month
    .groupby("Month Number", as_index=False)
    .agg(
        Booked_Nights=("Booked_Nights", "mean"),
        Reservations=("Reservations", "mean"),
        True_Earnings=("True_Earnings", "mean"),
        Earnings_per_Night=("Earnings_per_Night", "mean")
    )
)

seasonality["Month"] = seasonality["Month Number"].map(
    lambda x: calendar.month_abbr[int(x)]
)

metric_map = {
    "Booked Nights": "Booked_Nights",
    "Reservations": "Reservations",
    "True Earnings": "True_Earnings",
    "Earnings/Night": "Earnings_per_Night"
}

season_col = metric_map[season_metric]

season_fig = px.bar(
    seasonality,
    x="Month",
    y=season_col,
    category_orders={
        "Month": [calendar.month_abbr[i] for i in range(1, 13)]
    },
    text=season_col
)

season_fig.update_layout(
    xaxis_title="Stay Month",
    yaxis_title=season_metric
)

if season_metric in ["True Earnings", "Earnings/Night"]:
    season_fig.update_yaxes(tickprefix="$", tickformat=",.0f")
    season_fig.update_traces(texttemplate="$%{text:,.0f}")
else:
    season_fig.update_traces(texttemplate="%{text:,.1f}")

st.plotly_chart(season_fig, use_container_width=True)

if not seasonality.empty:
    peak = seasonality.loc[seasonality[season_col].idxmax()]
    st.info(
        f"Highest historical average for **{season_metric}**: "
        f"**{peak['Month']}** ({peak[season_col]:,.1f}"
        + (" dollars" if season_metric in ["True Earnings", "Earnings/Night"] else "")
        + ")."
    )

st.caption(
    "Booked Nights measures reservation volume, while earnings measures financial "
    "performance. Looking at both helps separate high demand from high pricing."
)

# ==================================================
# 2. PROPERTY PERFORMANCE
# ==================================================

st.divider()
st.header("🏠 Property Performance")
st.write("**How do the properties compare?**")

property_summary = (
    analysis_df
    .groupby("Listing", as_index=False)
    .agg(
        Booked_Nights=("Nights", "sum"),
        Reservations=("Start date", "size"),
        True_Earnings=("True Earnings", "sum"),
        Avg_Stay=("Nights", "mean"),
        Avg_Lead_Time=("Lead Time", "mean")
    )
)

property_summary["Earnings_per_Night"] = np.where(
    property_summary["Booked_Nights"] > 0,
    property_summary["True_Earnings"]
    / property_summary["Booked_Nights"],
    np.nan
)

property_metric = st.selectbox(
    "Compare properties by",
    [
        "Booked Nights",
        "Reservations",
        "True Earnings",
        "Earnings/Night",
        "Average Stay Length",
        "Average Booking Lead Time"
    ],
    key="property_metric"
)

property_map = {
    "Booked Nights": "Booked_Nights",
    "Reservations": "Reservations",
    "True Earnings": "True_Earnings",
    "Earnings/Night": "Earnings_per_Night",
    "Average Stay Length": "Avg_Stay",
    "Average Booking Lead Time": "Avg_Lead_Time"
}

property_col = property_map[property_metric]

property_fig = px.bar(
    property_summary.sort_values(property_col, ascending=True),
    x=property_col,
    y="Listing",
    orientation="h",
    text=property_col
)

property_fig.update_layout(
    xaxis_title=property_metric,
    yaxis_title="Property"
)

if property_metric in ["True Earnings", "Earnings/Night"]:
    property_fig.update_xaxes(tickprefix="$", tickformat=",.0f")
    property_fig.update_traces(texttemplate="$%{text:,.0f}")
else:
    property_fig.update_traces(texttemplate="%{text:,.1f}")

st.plotly_chart(property_fig, use_container_width=True)

# ==================================================
# 3. BOOKING BEHAVIOR
# ==================================================

st.divider()
st.header("🧳 Booking Behavior")
st.write("**How far ahead do guests book, and how long do they stay?**")

behavior_col1, behavior_col2, behavior_col3 = st.columns(3)

valid_lead = analysis_df["Lead Time"].dropna()

with behavior_col1:
    st.metric(
        "Average Booking Lead Time",
        f"{valid_lead.mean():.1f} days" if not valid_lead.empty else "N/A"
    )

with behavior_col2:
    st.metric(
        "Average Stay",
        f"{analysis_df['Nights'].mean():.1f} nights"
    )

with behavior_col3:
    st.metric(
        "Average True Earnings / Night",
        (
            f"${analysis_df['True Earnings'].sum() / analysis_df['Nights'].sum():,.2f}"
            if analysis_df["Nights"].sum() > 0
            else "N/A"
        )
    )

behavior_left, behavior_right = st.columns(2)

with behavior_left:
    lead_df = analysis_df.dropna(subset=["Lead Time"]).copy()

    if not lead_df.empty:
        lead_bins = [-1, 7, 14, 30, 60, 90, np.inf]
        lead_labels = [
            "0–7 days",
            "8–14 days",
            "15–30 days",
            "31–60 days",
            "61–90 days",
            "90+ days"
        ]

        lead_df["Lead Time Group"] = pd.cut(
            lead_df["Lead Time"],
            bins=lead_bins,
            labels=lead_labels
        )

        lead_counts = (
            lead_df["Lead Time Group"]
            .value_counts(sort=False)
            .rename_axis("Lead Time")
            .reset_index(name="Reservations")
        )

        fig_lead = px.bar(
            lead_counts,
            x="Lead Time",
            y="Reservations",
            text="Reservations",
            title="How far in advance do guests book?"
        )
        fig_lead.update_layout(
            xaxis_title="Booking Lead Time",
            yaxis_title="Reservations"
        )
        st.plotly_chart(fig_lead, use_container_width=True)
    else:
        st.info("Booking-date data is unavailable for lead-time analysis.")

with behavior_right:
    stay_counts = (
        analysis_df
        .groupby("Nights", as_index=False)
        .size()
        .rename(columns={"size": "Reservations"})
        .sort_values("Nights")
    )

    fig_stay = px.bar(
        stay_counts,
        x="Nights",
        y="Reservations",
        text="Reservations",
        title="How long do guests stay?"
    )
    fig_stay.update_layout(
        xaxis_title="Nights",
        yaxis_title="Reservations"
    )
    st.plotly_chart(fig_stay, use_container_width=True)

# ==================================================
# 4. HISTORICAL TRENDS
# ==================================================

st.divider()
st.header("📊 Historical Trends")
st.write("**How have demand and earnings changed over time?**")

history_metric = st.radio(
    "Historical metric",
    [
        "Booked Nights",
        "Reservations",
        "True Earnings",
        "Earnings/Night"
    ],
    horizontal=True,
    key="history_metric"
)

historical = add_complete_months(analysis_df)
history_col = metric_map[history_metric]

history_fig = px.line(
    historical,
    x="Month Date",
    y=history_col,
    markers=True
)

history_fig.update_layout(
    xaxis_title="Stay Month",
    yaxis_title=history_metric,
    hovermode="x unified"
)

if history_metric in ["True Earnings", "Earnings/Night"]:
    history_fig.update_yaxes(tickprefix="$", tickformat=",.0f")

st.plotly_chart(history_fig, use_container_width=True)

# ==================================================
# 5. FORECAST
# ==================================================

st.divider()
st.header("🔮 Forecast")
st.write("**What might upcoming monthly demand or earnings look like?**")

st.caption(
    "This is a simple seasonal historical-average forecast, not a trained ML "
    "model. It provides a transparent baseline that can later be compared with "
    "regression or machine-learning forecasts."
)

forecast_metric = st.radio(
    "Forecast",
    ["Booked Nights", "True Earnings"],
    horizontal=True,
    key="forecast_metric"
)

forecast_months = st.slider(
    "Months to forecast",
    min_value=1,
    max_value=12,
    value=6,
    key="forecast_months"
)

# Use only stays before the current month to build the historical baseline.
today = pd.Timestamp.today().normalize()
current_period = today.to_period("M")

historical_only = analysis_df[
    analysis_df["Year-Month"] < current_period
].copy()

forecast_col = metric_map[forecast_metric]

if historical_only.empty:
    st.info("More completed historical data is needed to create a forecast.")
else:
    hist_season = (
        historical_only
        .groupby(["Year", "Month Number"], as_index=False)
        .agg(
            Booked_Nights=("Nights", "sum"),
            True_Earnings=("True Earnings", "sum")
        )
    )

    month_baseline = (
        hist_season
        .groupby("Month Number", as_index=False)[
            ["Booked_Nights", "True_Earnings"]
        ]
        .mean()
    )

    overall_fallback = historical_only.agg(
        Booked_Nights=("Nights", "sum"),
        True_Earnings=("True Earnings", "sum")
    )

    future_periods = pd.period_range(
        start=current_period,
        periods=forecast_months,
        freq="M"
    )

    forecast_rows = []

    # Fallback monthly averages in case a month has never appeared historically.
    historical_monthly = monthly_summary(historical_only)
    fallback_values = {
        "Booked_Nights": historical_monthly["Booked_Nights"].mean(),
        "True_Earnings": historical_monthly["True_Earnings"].mean()
    }

    for period in future_periods:
        month_num = period.month
        match = month_baseline[
            month_baseline["Month Number"] == month_num
        ]

        if not match.empty:
            value = float(match.iloc[0][forecast_col])
        else:
            value = float(fallback_values[forecast_col])

        forecast_rows.append(
            {
                "Month Date": period.to_timestamp(),
                "Month": period.strftime("%b %Y"),
                "Forecast": value
            }
        )

    forecast_df = pd.DataFrame(forecast_rows)

    forecast_fig = px.line(
        forecast_df,
        x="Month Date",
        y="Forecast",
        markers=True
    )

    forecast_fig.update_layout(
        xaxis_title="Stay Month",
        yaxis_title=f"Forecast {forecast_metric}"
    )

    if forecast_metric == "True Earnings":
        forecast_fig.update_yaxes(tickprefix="$", tickformat=",.0f")

    st.plotly_chart(forecast_fig, use_container_width=True)

# ==================================================
# 6. BOOKING PACE
# ==================================================

st.divider()
st.header("⏱️ Booking Pace")
st.write(
    "**How much business is already booked for upcoming months?**"
)

if "Booking Status" in analysis_df.columns:
    future_df = analysis_df[
        analysis_df["Booking Status"].astype(str).eq("Future")
    ].copy()
else:
    future_df = analysis_df[
        analysis_df["Start date"] >= today
    ].copy()

if future_df.empty:
    st.info("There are no future reservations in the selected data.")
else:
    pace = (
        future_df
        .groupby("Year-Month", as_index=False)
        .agg(
            Booked_Nights=("Nights", "sum"),
            Reservations=("Start date", "size"),
            True_Earnings=("True Earnings", "sum")
        )
    )

    pace["Month Date"] = pace["Year-Month"].dt.to_timestamp()
    pace["Month"] = pace["Month Date"].dt.strftime("%b %Y")

    pace_metric = st.radio(
        "Future booking pace metric",
        ["Booked Nights", "Reservations", "True Earnings"],
        horizontal=True,
        key="pace_metric"
    )

    pace_map = {
        "Booked Nights": "Booked_Nights",
        "Reservations": "Reservations",
        "True Earnings": "True_Earnings"
    }

    pace_col = pace_map[pace_metric]

    pace_fig = px.bar(
        pace,
        x="Month",
        y=pace_col,
        text=pace_col
    )

    pace_fig.update_layout(
        xaxis_title="Upcoming Stay Month",
        yaxis_title=pace_metric
    )

    if pace_metric == "True Earnings":
        pace_fig.update_yaxes(tickprefix="$", tickformat=",.0f")
        pace_fig.update_traces(texttemplate="$%{text:,.0f}")
    else:
        pace_fig.update_traces(texttemplate="%{text:,.0f}")

    st.plotly_chart(pace_fig, use_container_width=True)

    st.caption(
        "This shows what is currently on the books. A true historical pace "
        "comparison (for example, 'December is 20% ahead of where it was at "
        "this point last year') requires historical snapshots of what was "
        "booked as of the same lead date."
    )

# --------------------------------------------------
# NOTES / LIMITATIONS
# --------------------------------------------------

st.divider()
with st.expander("About these metrics"):
    st.markdown(
        """
- **Booked Nights** = total nights from reservations.
- **Reservations** = number of reservation records.
- **True Earnings** = Gross Earnings − Service Fee − Cleaning Fee.
- **Earnings/Night** = True Earnings ÷ Booked Nights.
- **Booking Lead Time** = Start Date − Booking Date.
- **Seasonality** averages each calendar month's totals across the selected years.
- **Forecast** is currently a seasonal historical-average baseline, not an ML model.
- **Booking Pace** shows future business currently on the books. Comparing today's pace with the same point in prior years requires historical booking snapshots.
- **Occupancy rate is intentionally not shown** because the Airbnb exports do not tell us how many nights each property was actually available for booking.
        """
    )
