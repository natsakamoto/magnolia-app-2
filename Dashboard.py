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
# FILE UPLOAD + SESSION STATE
# --------------------------------------------------

# Airbnb provides past/payout data and future booking data separately.
# Upload both reports here and the dashboard will standardize and merge them.

if "df" not in st.session_state:

    st.subheader("Upload Airbnb Data")
    st.caption(
        "Upload the past earnings/payout CSV and the future bookings CSV. "
        "The dashboard will combine them automatically."
    )

    upload_col1, upload_col2 = st.columns(2)

    with upload_col1:
        past_file = st.file_uploader(
            "Past Earnings / Payout CSV",
            type=["csv"],
            key="past_airbnb_csv"
        )

    with upload_col2:
        future_file = st.file_uploader(
            "Future Bookings CSV",
            type=["csv"],
            key="future_airbnb_csv"
        )

    if past_file is not None and future_file is not None:

        past_df = pd.read_csv(past_file)
        future_df = pd.read_csv(future_file)

        past_df.columns = past_df.columns.str.strip()
        future_df.columns = future_df.columns.str.strip()

        # Keep the source file for reference. Booking Status itself will be
        # recalculated later from Start date and today's date.
        past_df["Data Source"] = "Past Earnings / Payout"
        future_df["Data Source"] = "Future Bookings"

        all_columns = list(
            dict.fromkeys(
                list(past_df.columns) + list(future_df.columns)
            )
        )

        for column in all_columns:
            if column not in past_df.columns:
                past_df[column] = pd.NA
            if column not in future_df.columns:
                future_df[column] = pd.NA

        past_df = past_df[all_columns]
        future_df = future_df[all_columns]

        df = pd.concat(
            [past_df, future_df],
            ignore_index=True
        )

        date_columns = [
            "Date",
            "Arriving by",
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
            "Paid out",
            "Service fee",
            "Fast pay fee",
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

        # --------------------------------------------------
        # REMOVE DUPLICATE RESERVATIONS
        # --------------------------------------------------
        # The same reservation can appear in an older Future Bookings report
        # and a newer Past Earnings / Payout report. Prefer the Past/Payout
        # version because it contains the finalized financial information.
        if "Confirmation code" in df.columns:

            df["Confirmation code"] = (
                df["Confirmation code"]
                .astype("string")
                .str.strip()
            )

            has_code = (
                df["Confirmation code"].notna()
                & (df["Confirmation code"] != "")
                & (df["Confirmation code"].str.lower() != "nan")
            )

            coded_rows = df.loc[has_code].copy()
            uncoded_rows = df.loc[~has_code].copy()

            if not coded_rows.empty:
                coded_rows["_source_priority"] = (
                    coded_rows["Data Source"]
                    .eq("Past Earnings / Payout")
                    .astype(int)
                )

                coded_rows = (
                    coded_rows
                    .sort_values("_source_priority")
                    .drop_duplicates(
                        subset=["Confirmation code"],
                        keep="last"
                    )
                    .drop(columns="_source_priority")
                )

            df = pd.concat(
                [coded_rows, uncoded_rows],
                ignore_index=True
            )

        # --------------------------------------------------
        # CLASSIFY PAST VS FUTURE USING TODAY'S DATE
        # --------------------------------------------------
        # This makes an older Future Bookings export safe to use. A stay that
        # has already begun will be treated as Past even if it came from the
        # Future Bookings CSV.
        today = pd.Timestamp.today().normalize()

        if "Start date" in df.columns:
            df["Booking Status"] = "Unknown"

            valid_start = df["Start date"].notna()

            df.loc[
                valid_start & (df["Start date"] < today),
                "Booking Status"
            ] = "Past"

            df.loc[
                valid_start & (df["Start date"] >= today),
                "Booking Status"
            ] = "Future"

            df = df.sort_values(
                "Start date",
                na_position="last"
            ).reset_index(drop=True)

        st.session_state["df"] = df
        st.session_state["past_file_name"] = past_file.name
        st.session_state["future_file_name"] = future_file.name

        st.rerun()

    elif past_file is not None or future_file is not None:
        st.info("Upload the other Airbnb CSV to combine and load the data.")

if "df" not in st.session_state:
    st.info("Upload both Airbnb CSV files above to get started.")
    st.stop()

# --------------------------------------------------
# USE STORED DATA
# --------------------------------------------------

df = st.session_state["df"].copy()

past_count = (df["Booking Status"] == "Past").sum()
future_count = (df["Booking Status"] == "Future").sum()
unknown_count = (df["Booking Status"] == "Unknown").sum()

status_message = (
    f"Combined data loaded: {len(df):,} rows "
    f"({past_count:,} past, {future_count:,} future)"
)

if unknown_count:
    status_message += f" • {unknown_count:,} row(s) have no valid Start date"

st.success(status_message)

clear_col, _ = st.columns([1, 4])

with clear_col:
    if st.button(
        "Clear / Upload New Files",
        type="secondary"
    ):
        keys_to_clear = [
            "df",
            "past_file_name",
            "future_file_name",
            "past_airbnb_csv",
            "future_airbnb_csv",
            "start_month",
            "start_year",
            "start_day",
            "end_month",
            "end_year",
            "end_day"
        ]

        for key in keys_to_clear:
            st.session_state.pop(key, None)

        st.rerun()

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
# DISPLAY CONTROLS
# --------------------------------------------------

st.subheader("Display Options")

control1, control2 = st.columns([2, 1])

with control1:
    display_metric = st.radio(
        "Earnings Metric",
        [
            "True Earnings",
            "Airbnb Payout",
            "Gross Earnings"
        ],
        horizontal=True
    )

with control2:
    chart_type = st.radio(
        "Chart Type",
        ["Line", "Bar"],
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

    if chart_type == "Line":
        fig = px.line(
            monthly_earnings,
            x="Month",
            y=selected_metric_column,
            markers=True
        )
    else:
        fig = px.bar(
            monthly_earnings,
            x="Month",
            y=selected_metric_column,
            text=selected_metric_column
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

    if chart_type == "Bar":
        fig.update_traces(
            texttemplate="$%{text:,.0f}",
            hovertemplate=(
                "<b>%{x}</b><br>"
                + display_metric
                + ": $%{y:,.2f}<extra></extra>"
            )
        )
    else:
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
    "Booking Status",
    "Data Source",
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