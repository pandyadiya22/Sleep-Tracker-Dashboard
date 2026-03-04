import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, time, datetime, timedelta

# -------------------- PAGE CONFIG --------------------
st.set_page_config(page_title="Sleep Tracker Dashboard", page_icon="😴", layout="wide")

# -------------------- TITLE --------------------
st.markdown(
    """
    <h1 style="text-align:center; color:#333333; font-family: 'Segoe UI', sans-serif;">
        😴 Sleep Tracker Dashboard
    </h1>
    """,
    unsafe_allow_html=True
)

# -------------------- HELPER FUNCTIONS --------------------
def to_datetime(d, t):
    return datetime.combine(d, t)

def calc_duration(bed_dt, wake_dt):
    if wake_dt <= bed_dt:
        wake_dt += timedelta(days=1)
    return round((wake_dt - bed_dt).total_seconds() / 3600, 2)

def streak_count(df):
    if df.empty:
        return 0
    meets = df["Met Target"].tolist()
    best = cur = 0
    for m in meets:
        cur = cur + 1 if m else 0
        best = max(best, cur)
    return best

# -------------------- SESSION STATE DATA --------------------
if "sleep_data" not in st.session_state:
    st.session_state.sleep_data = pd.DataFrame(columns=[
        "Date", "Bedtime", "Wake Time", "Duration (h)", "Quality", "Naps (min)",
        "Caffeine", "Target (h)", "Met Target"
    ])

# -------------------- SIDEBAR FORM --------------------
st.sidebar.header("Add Sleep Entry")
with st.sidebar.form("sleep_form"):
    d = st.date_input("Date", date.today())
    bed = st.time_input("Bedtime", time(23, 0))
    wake = st.time_input("Wake Time", time(7, 0))
    quality = st.slider("Sleep Quality (1-5)", 1, 5, 4)
    naps = st.number_input("Naps (minutes)", 0, 600, 0, step=5)
    caffeine = st.checkbox("Caffeine after 2pm?")
    target = st.number_input("Target Sleep Hours", 4.0, 12.0, 8.0, 0.5)
    add_btn = st.form_submit_button("Add Entry")

if add_btn:
    bed_dt = to_datetime(d, bed)
    wake_dt = to_datetime(d, wake)
    duration = calc_duration(bed_dt, wake_dt)
    met_target = duration >= target

    new_entry = pd.DataFrame([{
        "Date": pd.to_datetime(d),
        "Bedtime": bed.strftime("%H:%M"),
        "Wake Time": wake.strftime("%H:%M"),
        "Duration (h)": duration,
        "Quality": quality,
        "Naps (min)": naps,
        "Caffeine": caffeine,
        "Target (h)": target,
        "Met Target": met_target
    }])
    st.session_state.sleep_data = pd.concat([st.session_state.sleep_data, new_entry], ignore_index=True)
    st.success("✅ Sleep entry added!")

df = st.session_state.sleep_data.copy()
if df.empty:
    st.info("No data yet. Add your first sleep entry in the sidebar.")
    st.stop()

# -------------------- KPI ROW --------------------
total_nights = len(df)
avg_duration = df["Duration (h)"].mean()
best_streak = streak_count(df)
avg_quality = df["Quality"].mean()
total_naps = df["Naps (min)"].sum()

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Nights Tracked", total_nights)
k2.metric("Avg Duration", f"{avg_duration:.2f} h")
k3.metric("Best Streak", best_streak)
k4.metric("Avg Quality", f"{avg_quality:.1f}/5")
k5.metric("Total Naps", f"{total_naps} min")

# -------------------- CHARTS ROW 1 --------------------
c1, c2, c3 = st.columns(3)

# Sleep Quality Pie
with c1:
    qual_counts = df["Quality"].value_counts().sort_index()
    fig_q = px.pie(values=qual_counts.values, names=qual_counts.index, hole=0.5,
                   title="Sleep Quality Distribution",
                   color_discrete_sequence=["#1F77B4", "#FF7F0E", "#2CA02C", "#D62728", "#9467BD"])
    fig_q.update_traces(textinfo='percent+label')
    st.plotly_chart(fig_q, use_container_width=True)

# Bed vs Wake Histogram
with c2:
    bed_hours = pd.to_datetime(df["Bedtime"], format="%H:%M").dt.hour
    wake_hours = pd.to_datetime(df["Wake Time"], format="%H:%M").dt.hour
    hist_df = pd.DataFrame({
        "Hour": pd.concat([bed_hours, wake_hours]),
        "Type": ["Bedtime"]*len(bed_hours) + ["Wake Time"]*len(wake_hours)
    })
    fig_hist = px.histogram(hist_df, x="Hour", color="Type", barmode="overlay",
                            title="Bedtime vs Wake Time",
                            color_discrete_map={"Bedtime": "#4E79A7", "Wake Time": "#F28E2B"})
    fig_hist.update_layout(bargap=0.2)
    st.plotly_chart(fig_hist, use_container_width=True)

# Avg Duration by Day
with c3:
    df["Day"] = df["Date"].dt.day_name()
    avg_by_day = df.groupby("Day")["Duration (h)"].mean().reindex(
        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    )
    fig_day = px.bar(x=avg_by_day.index, y=avg_by_day.values,
                     labels={"x": "Day", "y": "Avg Hours"},
                     title="Avg Duration by Day",
                     color=avg_by_day.values, color_continuous_scale=px.colors.sequential.Blugrn)
    st.plotly_chart(fig_day, use_container_width=True)

# -------------------- CHARTS ROW 2 --------------------
b1, b2 = st.columns(2)

# Duration Trend
with b1:
    fig_line = px.line(df, x="Date", y="Duration (h)", markers=True,
                       title="Sleep Duration Trend",
                       color_discrete_sequence=["#E15759"])
    fig_line.add_hline(y=df["Target (h)"].iloc[-1],
                       line_dash="dot", annotation_text="Target", annotation_position="bottom right")
    st.plotly_chart(fig_line, use_container_width=True)

# Caffeine Effect
with b2:
    avg_caffeine = df.groupby("Caffeine")["Duration (h)"].mean().reset_index()
    avg_caffeine["Caffeine"] = avg_caffeine["Caffeine"].map({True: "Yes", False: "No"})
    fig_caf = px.bar(avg_caffeine, x="Caffeine", y="Duration (h)",
                     title="Caffeine vs Sleep Duration",
                     color="Caffeine", color_discrete_map={"Yes": "#E15759", "No": "#76B7B2"})
    st.plotly_chart(fig_caf, use_container_width=True)

# -------------------- DATA TABLE --------------------
st.subheader("📋 Sleep Records")
st.dataframe(df.drop(columns=["Day"]), use_container_width=True)
