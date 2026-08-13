import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Future Earnings",
    page_icon="📅",
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

date_columns = [
    "Date",
    "Booking date",
    "Start date",
    "End date"
]

for column in date_columns:
    if column in df.columns:
        df[column] = pd.to_datetime(
            df[column],
            errors="coerce"
        )

money_columns = [
    "Amount",
    "Service fee",
    "Cleaning fee",
    "Gross earnings",
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

required_columns = [
    "Start date",
    "Listing",
    "Gross earnings",
    "Service fee",
    "Cleaning fee",
    "Nights"
]

missing_columns = [
    column
    for column in required_columns
    if column not in df.columns
]

if missing_columns:
    st.error(
        "The uploaded CSV is missing required columns: "
        + ", ".join(missing_columns)
    )
    st.stop()

# --------------------------------------------------
# CALCULATED EARNINGS
# --------------------------------------------------

df["Airbnb Payout"] = (
    df["Gross earnings"]
    - df["Service fee"]
)

df["True Earnings"] = (
    df["Gross earnings"]
    - df["Service fee"]
    - df["Cleaning fee"]
)

# --------------------------------------------------
# PAGE HEADER
# --------------------------------------------------

st.title("📅 Future Earnings")
st.write(
    "View earnings from reservations with upcoming check-in dates."
)

st.caption(
    "True Earnings = Gross Earnings − Service Fee − Cleaning Fee"
)

# --------------------------------------------------
# SIDEBAR FILTERS
# --------------------------------------------------

st.sidebar.header("Filters")

listings = sorted(
    df["Listing"]
    .dropna()
    .unique()
    .tolist()
)

selected_listing = st.sidebar.selectbox(
    "Property",
    ["All Properties"] + listings
)

# Use today's date as the default definition of "future"
today = pd.Timestamp.today().normalize()

# Remove rows without a valid start date
future_df = df[
    df["Start date"].notna()
    &
    (df["Start date"] >= today)
].copy()

if selected_listing != "All Properties":
    future_df = future_df[
        future_df["Listing"] == selected_listing
    ].copy()

# Optional future horizon
future_horizon = st.sidebar.selectbox(
    "Show bookings within",
    [
        "All Future Bookings",
        "Next 30 Days",
        "Next 60 Days",
        "Next 90 Days",
        "Next 6 Months",
        "Next 12 Months"
    ]
)

horizon_days = {
    "Next 30 Days": 30,
    "Next 60 Days": 60,
    "Next 90 Days": 90,
    "Next 6 Months": 183,
    "Next 12 Months": 365
}

if future_horizon in horizon_days:
    cutoff_date = today + pd.Timedelta(
        days=horizon_days[future_horizon]
    )

    future_df = future_df[
        future_df["Start date"] <= cutoff_date
    ].copy()

# --------------------------------------------------
# NO FUTURE BOOKINGS
# --------------------------------------------------

if future_df.empty:
    st.info(
        "No future reservations were found for the selected filters."
    )
    st.stop()

# --------------------------------------------------
# SUMMARY METRICS
# --------------------------------------------------

expected_true_earnings = future_df["True Earnings"].sum()
expected_airbnb_payout = future_df["Airbnb Payout"].sum()
upcoming_cleaning_fees = future_df["Cleaning fee"].sum()
future_booked_nights = future_df["Nights"].sum()

if "Confirmation code" in future_df.columns:
    future_bookings = (
        future_df["Confirmation code"]
        .dropna()
        .nunique()
    )
else:
    future_bookings = len(future_df)

st.subheader("Upcoming Earnings Overview")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "⭐ Expected True Earnings",
        f"${expected_true_earnings:,.2f}"
    )
    st.caption(
        "Gross Earnings − Service Fee − Cleaning Fee"
    )

with col2:
    st.metric(
        "Expected Airbnb Payout",
        f"${expected_airbnb_payout:,.2f}"
    )
    st.caption(
        "Gross Earnings − Service Fee"
    )

with col3:
    st.metric(
        "Upcoming Cleaning Fees",
        f"${upcoming_cleaning_fees:,.2f}"
    )

col4, col5 = st.columns(2)

with col4:
    st.metric(
        "Future Bookings",
        f"{future_bookings:,}"
    )

with col5:
    st.metric(
        "Future Booked Nights",
        f"{future_booked_nights:,.0f}"
    )

# --------------------------------------------------
# EARNINGS BY UPCOMING MONTH
# --------------------------------------------------

st.divider()
st.subheader("Earnings by Upcoming Month")

future_df["Month"] = (
    future_df["Start date"]
    .dt.to_period("M")
    .dt.to_timestamp()
)

monthly_future = (
    future_df
    .groupby("Month", as_index=False)
    .agg({
        "True Earnings": "sum",
        "Airbnb Payout": "sum",
        "Cleaning fee": "sum",
        "Nights": "sum"
    })
    .sort_values("Month")
)

display_metric = st.radio(
    "Display Metric",
    [
        "True Earnings",
        "Airbnb Payout",
        "Cleaning Fees",
        "Booked Nights"
    ],
    horizontal=True
)

metric_map = {
    "True Earnings": "True Earnings",
    "Airbnb Payout": "Airbnb Payout",
    "Cleaning Fees": "Cleaning fee",
    "Booked Nights": "Nights"
}

selected_metric = metric_map[display_metric]

fig = px.bar(
    monthly_future,
    x="Month",
    y=selected_metric,
    text=selected_metric
)

fig.update_layout(
    xaxis_title="Check-in Month",
    yaxis_title=display_metric,
    showlegend=False
)

fig.update_xaxes(
    tickformat="%b %Y"
)

if display_metric != "Booked Nights":
    fig.update_yaxes(
        tickprefix="$",
        tickformat=",.0f"
    )

    fig.update_traces(
        texttemplate="$%{text:,.0f}",
        hovertemplate=(
            "<b>%{x|%B %Y}</b><br>"
            + display_metric
            + ": $%{y:,.2f}"
            + "<extra></extra>"
        )
    )
else:
    fig.update_traces(
        texttemplate="%{text:,.0f}",
        hovertemplate=(
            "<b>%{x|%B %Y}</b><br>"
            "Booked Nights: %{y:,.0f}"
            "<extra></extra>"
        )
    )

st.plotly_chart(
    fig,
    use_container_width=True
)

# --------------------------------------------------
# MONTHLY SUMMARY TABLE
# --------------------------------------------------

st.subheader("Monthly Summary")

monthly_display = monthly_future.copy()

monthly_display["Month"] = (
    monthly_display["Month"]
    .dt.strftime("%B %Y")
)

monthly_display = monthly_display.rename(
    columns={
        "Cleaning fee": "Cleaning Fees",
        "Nights": "Booked Nights"
    }
)

st.dataframe(
    monthly_display,
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
        "Cleaning Fees": st.column_config.NumberColumn(
            "Cleaning Fees",
            format="$%.2f"
        ),
        "Booked Nights": st.column_config.NumberColumn(
            "Booked Nights",
            format="%.0f"
        )
    }
)

# --------------------------------------------------
# UPCOMING RESERVATIONS TABLE
# --------------------------------------------------

st.divider()
st.subheader("Upcoming Reservations")

display_columns = [
    "Start date",
    "End date",
    "Confirmation code",
    "Guest",
    "Listing",
    "Nights",
    "Gross earnings",
    "Service fee",
    "Cleaning fee",
    "Airbnb Payout",
    "True Earnings"
]

available_columns = [
    column
    for column in display_columns
    if column in future_df.columns
]

reservations_display = (
    future_df[available_columns]
    .sort_values("Start date")
    .copy()
)

for column in ["Start date", "End date"]:
    if column in reservations_display.columns:
        reservations_display[column] = (
            reservations_display[column]
            .dt.strftime("%m/%d/%Y")
        )

reservations_display = reservations_display.rename(
    columns={
        "Start date": "Check-in",
        "End date": "Check-out",
        "Gross earnings": "Gross Earnings",
        "Service fee": "Service Fee",
        "Cleaning fee": "Cleaning Fee"
    }
)

st.dataframe(
    reservations_display,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Gross Earnings": st.column_config.NumberColumn(
            "Gross Earnings",
            format="$%.2f"
        ),
        "Service Fee": st.column_config.NumberColumn(
            "Service Fee",
            format="$%.2f"
        ),
        "Cleaning Fee": st.column_config.NumberColumn(
            "Cleaning Fee",
            format="$%.2f"
        ),
        "Airbnb Payout": st.column_config.NumberColumn(
            "Airbnb Payout",
            format="$%.2f"
        ),
        "True Earnings": st.column_config.NumberColumn(
            "True Earnings",
            format="$%.2f"
        )
    }
)
