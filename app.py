import streamlit as st
import pandas as pd

# --------------------------------------------------
# PAGE SETUP
# --------------------------------------------------

st.set_page_config(
    page_title="Airbnb Earnings Dashboard",
    page_icon="🏠",
    layout="wide"
)

st.title("🏠 Airbnb Earnings Dashboard")
st.write("Upload an Airbnb earnings CSV to view and filter your earnings data.")

# --------------------------------------------------
# FILE UPLOAD
# --------------------------------------------------

uploaded_file = st.file_uploader(
    "Upload Airbnb CSV",
    type=["csv"]
)

if uploaded_file is not None:

    # Read CSV
    df = pd.read_csv(uploaded_file)

    # --------------------------------------------------
    # CLEAN DATA
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

    # --------------------------------------------------
    # SIDEBAR FILTERS
    # --------------------------------------------------

    st.sidebar.header("Filters")

    # Property filter
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

    # Date filter
    min_date = df["Date"].min().date()
    max_date = df["Date"].max().date()

    selected_dates = st.sidebar.date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    # --------------------------------------------------
    # APPLY FILTERS
    # --------------------------------------------------

    filtered_df = df.copy()

    if selected_listing != "All Properties":
        filtered_df = filtered_df[
            filtered_df["Listing"] == selected_listing
        ]

    if len(selected_dates) == 2:
        start_date = selected_dates[0]
        end_date = selected_dates[1]

        filtered_df = filtered_df[
            (filtered_df["Date"].dt.date >= start_date)
            &
            (filtered_df["Date"].dt.date <= end_date)
        ]

    # --------------------------------------------------
    # CALCULATE TOTALS
    # --------------------------------------------------

    gross_earnings = filtered_df["Gross earnings"].sum()
    service_fees = filtered_df["Service fee"].sum()
    cleaning_fees = filtered_df["Cleaning fee"].sum()
    taxes = filtered_df["Airbnb remitted tax"].sum()

    airbnb_amount = gross_earnings - service_fees
    true_earnings = gross_earnings - service_fees - cleaning_fees

    # --------------------------------------------------
    # SUMMARY METRICS
    # --------------------------------------------------

    st.subheader("Earnings Overview")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "True Earnings",
            f"${true_earnings:,.2f}"
        )
        st.caption("Gross Earnings − Service Fee − Cleaning Fee")

    with col2:
        st.metric(
            "Airbnb Amount",
            f"${airbnb_amount:,.2f}"
        )
        st.caption("Gross Earnings − Service Fee")

    with col3:
        st.metric(
            "Gross Earnings",
            f"${gross_earnings:,.2f}"
        )
        st.caption("Total earnings before deductions")

    with col4:
        st.metric(
            "Cleaning Fees",
            f"${cleaning_fees:,.2f}"
        )
        st.caption("Cleaning fees collected")

    # --------------------------------------------------
    # DISPLAY METRIC SELECTOR
    # --------------------------------------------------

    st.subheader("Display Metric")

    display_metric = st.radio(
        "Choose which earnings metric to display:",
        [
            "Airbnb Amount",
            "True Earnings",
            "Gross Earnings"
        ],
        horizontal=True
    )

    # Create True Earnings column
    filtered_df["True Earnings"] = (
        filtered_df["Amount"] - filtered_df["Cleaning fee"]
    )

    # Map display choice to dataframe column
    metric_column_map = {
        "Airbnb Amount": "Amount",
        "True Earnings": "True Earnings",
        "Gross Earnings": "Gross earnings"
    }

    selected_metric_column = metric_column_map[display_metric]

    # --------------------------------------------------
    # MONTHLY EARNINGS
    # --------------------------------------------------

    st.subheader(f"Monthly {display_metric}")

    monthly_df = filtered_df.copy()

    monthly_df["Month"] = (
        monthly_df["Date"]
        .dt.to_period("M")
        .astype(str)
    )

    monthly_earnings = (
        monthly_df
        .groupby("Month")[selected_metric_column]
        .sum()
    )

    st.bar_chart(monthly_earnings)

    # --------------------------------------------------
    # TRANSACTION TABLE
    # --------------------------------------------------

    st.subheader("Transactions")

    display_columns = [
        "Date",
        "Type",
        "Confirmation code",
        "Start date",
        "End date",
        "Nights",
        "Guest",
        "Listing",
        "Amount",
        "Service fee",
        "Cleaning fee",
        "Gross earnings",
        "Airbnb remitted tax"
    ]

    available_columns = [
        column
        for column in display_columns
        if column in filtered_df.columns
    ]

    st.dataframe(
        filtered_df[available_columns],
        use_container_width=True
    )

else:

    st.info(
        "Upload an Airbnb earnings CSV above to get started."
    )