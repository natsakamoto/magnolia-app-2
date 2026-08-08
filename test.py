import streamlit as st

st.title("Date Picker Test")

date = st.date_input(
    "Choose a date",
    format="MM/DD/YYYY"
)

st.write(date)