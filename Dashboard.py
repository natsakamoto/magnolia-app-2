import streamlit as st
import pandas as pd
import plotly.express as px
import calendar
from datetime import date

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

    # HERE DONT FORGET
    st.session_state["df"] = df

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

    # --------------------------------------------------
    # DATE FILTER
    # --------------------------------------------------

    # Get valid payout date range from the CSV
    valid_dates = df["Date"].dropna()

    min_date = valid_dates.min().date()
    max_date = valid_dates.max().date()

    years = list(range(min_date.year, max_date.year + 1))

    # --------------------------------------------------
    # START PAYOUT DATE
    # --------------------------------------------------

    st.sidebar.subheader("Start Payout Date")

    start_col1, start_col2, start_col3 = st.sidebar.columns([3, 2, 2])

    with start_col1:
        start_month = st.selectbox(
            "Month",
            range(1, 13),
            format_func=lambda x: calendar.month_name[x],
            index=min_date.month - 1,
            key="start_month"
        )

    with start_col2:
        start_year = st.selectbox(
            "Year",
            years,
            index=0,
            key="start_year"
        )

    # Determine valid number of days for selected month/year
    start_days_in_month = calendar.monthrange(
        start_year,
        start_month
    )[1]

    with start_col3:
        start_day = st.selectbox(
            "Day",
            range(1, start_days_in_month + 1),
            index=min(
                min_date.day,
                start_days_in_month
            ) - 1,
            key="start_day"
        )

    start_date = date(
        start_year,
        start_month,
        start_day
    )

    # Show selected date clearly
    st.sidebar.caption(
        f"Selected: {start_date.strftime('%m/%d/%Y')}"
    )

    # --------------------------------------------------
    # END PAYOUT DATE
    # --------------------------------------------------

    st.sidebar.subheader("End Payout Date")

    end_col1, end_col2, end_col3 = st.sidebar.columns([3, 2, 2])

    with end_col1:
        end_month = st.selectbox(
            "Month",
            range(1, 13),
            format_func=lambda x: calendar.month_name[x],
            index=max_date.month - 1,
            key="end_month"
        )

    with end_col2:
        end_year = st.selectbox(
            "Year",
            years,
            index=len(years) - 1,
            key="end_year"
        )

    end_days_in_month = calendar.monthrange(
        end_year,
        end_month
    )[1]

    with end_col3:
        end_day = st.selectbox(
            "Day",
            range(1, end_days_in_month + 1),
            index=min(
                max_date.day,
                end_days_in_month
            ) - 1,
            key="end_day"
        )

    end_date = date(
        end_year,
        end_month,
        end_day
    )

    # Show selected date clearly
    st.sidebar.caption(
        f"Selected: {end_date.strftime('%m/%d/%Y')}"
    )

    # --------------------------------------------------
    # VALIDATE DATES
    # --------------------------------------------------

    if start_date > end_date:
        st.sidebar.error(
            "Start date must be on or before end date."
        )
        st.stop()

    # --------------------------------------------------
    # APPLY FILTERS
    # --------------------------------------------------

    filtered_df = df.copy()

    # Property filter
    if selected_listing != "All Properties":
        filtered_df = filtered_df[
            filtered_df["Listing"] == selected_listing
        ]

    # Date filter
    filtered_df = filtered_df[
        (filtered_df["Date"].dt.date >= start_date)
        &
        (filtered_df["Date"].dt.date <= end_date)
    ]

    # --------------------------------------------------
    # CALCULATE ROW-LEVEL EARNINGS
    # --------------------------------------------------

    filtered_df["Airbnb Payout"] = (
        filtered_df["Gross earnings"]
        - filtered_df["Service fee"]
    )

    filtered_df["True Earnings"] = (
        filtered_df["Gross earnings"]
        - filtered_df["Service fee"]
        - filtered_df["Cleaning fee"]
    )

    # --------------------------------------------------
    # CALCULATE TOTALS
    # --------------------------------------------------

    gross_earnings = filtered_df["Gross earnings"].sum()
    service_fees = filtered_df["Service fee"].sum()
    cleaning_fees = filtered_df["Cleaning fee"].sum()
    taxes = filtered_df["Airbnb remitted tax"].sum()

    airbnb_amount = filtered_df["Airbnb Payout"].sum()
    true_earnings = filtered_df["True Earnings"].sum()

    # --------------------------------------------------
    # SUMMARY METRICS
    # --------------------------------------------------

    st.subheader("Earnings Overview")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "⭐ True Earnings",
            f"${true_earnings:,.2f}"
        )
        st.caption("Gross Earnings − Service Fee − Cleaning Fee")

    with col2:
        st.metric(
            "Airbnb Payout",
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
            "True Earnings",
            "Airbnb Payout",
            "Gross Earnings"
        ],
        horizontal=True
    )

    metric_column_map = {
        "True Earnings": "True Earnings",
        "Airbnb Payout": "Airbnb Payout",
        "Gross Earnings": "Gross earnings"
    }

    selected_metric_column = metric_column_map[display_metric]

    # --------------------------------------------------
    # MONTHLY EARNINGS
    # --------------------------------------------------

    st.subheader(f"Monthly {display_metric}")

    monthly_df = filtered_df.dropna(subset=["Date"]).copy()

    monthly_df["Month"] = (
        monthly_df["Date"]
        .dt.to_period("M")
        .astype(str)
    )

    monthly_earnings = (
        monthly_df
        .groupby("Month", as_index=False)[selected_metric_column]
        .sum()
    )

    if not monthly_earnings.empty:

        fig = px.line(
            monthly_earnings,
            x="Month",
            y=selected_metric_column,
            markers=True
        )

        fig.update_layout(
            xaxis_title="Month",
            yaxis_title=display_metric,
            hovermode="x unified"
        )

        fig.update_yaxes(
            tickprefix="$",
            tickformat=",.0f"
        )

        fig.update_traces(
            hovertemplate=(
                "<b>%{x}</b><br>"
                + display_metric
                + ": $%{y:,.2f}<extra></extra>"
            )
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    else:
        st.info("No earnings data available for the selected filters.")


    # --------------------------------------------------
    # TRANSACTION TABLE
    # --------------------------------------------------

    st.subheader("Transactions")

    display_columns = [
        "Date",
        "Confirmation code",
        "Booking date",
        "Start date",
        "End date",
        "Nights",
        "Guest",
        "Listing",
        "Gross earnings",
        "Service fee",
        "Cleaning fee",
        "Airbnb Payout",
        "True Earnings",
        "Airbnb remitted tax"
    ]

    available_columns = [
        column
        for column in display_columns
        if column in filtered_df.columns
    ]

    display_df = filtered_df[available_columns].copy()

    date_columns_display = [
        "Date",
        "Booking date",
        "Start date",
        "End date"
    ]

    for column in date_columns_display:
        if column in display_df.columns:
            display_df[column] = display_df[column].dt.strftime("%m/%d/%Y")

    display_df = display_df.rename(
        columns={
            "Date": "Payout Date"
        }
    )

    st.dataframe(
        display_df,
        use_container_width=True
    )

else:

    st.info(
        "Upload an Airbnb earnings CSV above to get started."
    )