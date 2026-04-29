import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.express as px

st.set_page_config(layout="wide")


# -------- BASE DIR FIX --------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CUSTOMER_FILE = os.path.join(BASE_DIR, "customers.csv")


# -------- LOAD DATA --------
def load_data(username):
    file = os.path.join(BASE_DIR, username + ".csv")

    if not os.path.exists(file):
        return pd.DataFrame()

    df = pd.read_csv(file)

    # clean column names
    df.columns = df.columns.str.strip()

    # auto map columns
    column_map = {}
    for col in df.columns:
        c = col.lower().replace(" ", "").replace("_", "")

        if "month" in c:
            column_map[col] = "Month"
        elif "unit" in c:
            column_map[col] = "Units_Consumed"
        elif "bill" in c:
            column_map[col] = "Total_Bill"
        elif "device" in c:
            column_map[col] = "Highly_used_device"

    df.rename(columns=column_map, inplace=True)

    # remove duplicate columns after renaming
    df = df.loc[:, ~df.columns.duplicated()]

    # ensure required columns exist
    required = ["Month", "Units_Consumed", "Total_Bill", "Highly_used_device"]
    for col in required:
        if col not in df.columns:
            df[col] = 0

    return df


# -------- ANALYTICS --------
def get_analytics(df):
    df = df.copy()
    df["Units_Consumed"] = pd.to_numeric(df["Units_Consumed"], errors="coerce").fillna(0)
    df["Total_Bill"] = pd.to_numeric(df["Total_Bill"], errors="coerce").fillna(0)
    peak_units = df["Units_Consumed"].max()
    growth = df["Units_Consumed"].pct_change().fillna(0) * 100
    avg_growth = round(growth.mean(), 2)

    if avg_growth > 5:
        trend = "Rising ⚠️"
    elif avg_growth < -5:
        trend = "Improving ✅"
    else:
        trend = "Stable⚡"

    highest_bill = df.loc[df["Total_Bill"].idxmax(), "Month"]
    lowest_bill = df.loc[df["Total_Bill"].idxmin(), "Month"]
    top_device = df["Highly_used_device"].astype(str).value_counts().idxmax()

    return avg_growth,trend,highest_bill,lowest_bill,top_device,peak_units


# -------- PREDICTION --------
def estimate_next(df):
    df = df.copy()
    df["Units_Consumed"] = pd.to_numeric(df["Units_Consumed"], errors="coerce").fillna(0)
    df["Total_Bill"] = pd.to_numeric(df["Total_Bill"], errors="coerce").fillna(0)

    avg_units = df["Units_Consumed"].mean()
    avg_bill = df["Total_Bill"].mean()
    growth = df["Units_Consumed"].pct_change().fillna(0).mean()

    return int(avg_units * (1 + growth)), int(avg_bill * (1 + growth))


# -------- FORMAT TABLE --------
def format_table(df):
    df_display = df.copy()

    df_display["Units_Consumed"] = pd.to_numeric(
        df_display["Units_Consumed"], errors="coerce"
    ).fillna(0)
    df_display["Total_Bill"] = pd.to_numeric(
        df_display["Total_Bill"], errors="coerce"
    ).fillna(0)

    df_display["Units_Consumed"] = df_display["Units_Consumed"].astype(str) + " kWh"
    df_display["Total_Bill"] = "₹ " + df_display["Total_Bill"].astype(str)

    df_display = df_display.reset_index(drop=True)
    df_display.index = df_display.index + 1
    df_display.index.name = None

    return df_display


# -------- LOGIN --------
if "user" not in st.session_state:

    st.title("⚡Electricity Monitoring Dashboard Login")

    username = st.text_input("Username", key="login_user")
    password = st.text_input("Password", type="password", key="login_pass")

    if st.button("Login"):

        if not os.path.exists(CUSTOMER_FILE):
            st.error(f"customers.csv missing at: {CUSTOMER_FILE}")
        else:
            users = pd.read_csv(CUSTOMER_FILE)
            users.columns = users.columns.str.strip()
            users["username"] = users["username"].astype(str).str.strip()
            users["password"] = users["password"].astype(str).str.strip()

            match = users[
                (users["username"] == username.strip()) &
                (users["password"] == password.strip())
            ]

            if match.empty:
                st.error("Invalid login")
            else:
                st.session_state["user"] = username.strip()
                st.rerun()

# -------- MAIN --------
else:
    username = st.session_state["user"]
    df = load_data(username)

    option = st.sidebar.radio("Menu", ["Dashboard", "Analytics", "Data", "Logout"])

    # ================= DASHBOARD =================
    if option == "Dashboard":

        st.title(f"Welcome {username}")

        if not df.empty:
            df["Units_Consumed"] = pd.to_numeric(df["Units_Consumed"], errors="coerce").fillna(0)
            df["Total_Bill"] = pd.to_numeric(df["Total_Bill"], errors="coerce").fillna(0)

            total_units = int(df["Units_Consumed"].sum())
            total_bill = int(df["Total_Bill"].sum())
            top_device = df["Highly_used_device"].astype(str).value_counts().idxmax()

            col1, col2, col3 = st.columns(3)
            col1.metric("Total Units", f"{total_units} kWh")
            col2.metric("Total Bill", f"₹ {total_bill}")
            col3.metric("Top Device", top_device)

            st.markdown("---")

            # ---- LINE ----
            fig1 = px.line(
                df,
                x="Month",
                y="Units_Consumed",
                markers=True,
                template="plotly_dark",
                color_discrete_sequence=["cyan"],
                title="Units Consumed by Month"
            )
            fig1.update_traces(
                hovertemplate="Month: %{x}<br>Units Consumed: %{y} kWh"
            )
            fig1.update_layout(
                xaxis_title="Month",
                yaxis_title="Units Consumed (kWh)",
                title_x=0.02
            )
            st.plotly_chart(fig1, use_container_width=True)

            # ---- BAR ----
            fig2 = px.bar(
                df,
                x="Month",
                y="Total_Bill",
                template="plotly_dark",
                color_discrete_sequence=["orange"],
                title="Bill Amount by Month"
            )
            fig2.update_traces(
                hovertemplate="Month: %{x}<br>Bill Amount: ₹ %{y}"
            )
            fig2.update_layout(
                xaxis_title="Month",
                yaxis_title="Bill Amount (₹)",
                title_x=0.02
            )
            st.plotly_chart(fig2, use_container_width=True)

            # ---- PIE ----
            fig3 = px.pie(
                df,
                names="Month",
                values="Units_Consumed",
                template="plotly_dark",
                hole=0.4,
                color_discrete_sequence=px.colors.sequential.Teal,
                title="Monthly Energy Distribution"
            )
            fig3.update_traces(
                textposition="inside",
                textinfo="percent+label",
                marker=dict(line=dict(color="black", width=1)),
                hovertemplate="Month: %{label}<br>Units Consumed: %{value} kWh"
            )
            fig3.update_layout(
                font_color="white",
                title_x=0.02
            )
            st.plotly_chart(fig3, use_container_width=True)

        else:
            st.warning("No data available")

    # ================= ANALYTICS =================
    elif option == "Analytics":

        st.title("Analytics Engine")

        if not df.empty:

            avg_growth, trend, highest_bill, lowest_bill, top_device, peak_units = get_analytics(df)
            est_units, est_bill = estimate_next(df)

            # ---------- ROW 1 ----------
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Growth %", f"{avg_growth}%")
            c2.metric("Trend", trend)
            c3.metric("Top Device", top_device)
            c4.metric("Peak Usage", f"{peak_units} kWh")

            c5, c6, c7, c8 = st.columns(4)
            c5.metric("Highest Bill Month", highest_bill)
            c6.metric("Lowest Bill Month", lowest_bill)
            c7.metric("Next Month (Est)", f"{est_units} kWh")
            c8.metric("Estimated Bill (Next Month)", f"₹ {est_bill}")

            st.markdown("---")

            # ---- MONTH + DEVICE TABLE ----
            st.subheader("Monthly Device Usage")

            device_table = df[["Month", "Highly_used_device"]].copy()
            device_table = device_table.reset_index(drop=True)
            device_table.index = device_table.index + 1
            device_table.index.name = None
            st.dataframe(device_table, use_container_width=True)

            # ---- GROUPED TABLE ----
            st.subheader("Device Usage Summary")

            device_group = df["Highly_used_device"].value_counts().reset_index()
            device_group.columns = ["Device", "Count"]
            device_group = device_group.reset_index(drop=True)
            device_group.index = device_group.index + 1
            device_group.index.name = None
            st.dataframe(device_group, use_container_width=True)

            # ---- PIE ----
            device_counts = df["Highly_used_device"].value_counts()

            fig4 = px.pie(
                names=device_counts.index,
                values=device_counts.values,
                template="plotly_dark",
                hole=0.4,
                color_discrete_sequence=px.colors.sequential.RdBu,
                title="Highly Used Device Distribution"
            )
            fig4.update_traces(
                textposition="inside",
                textinfo="percent+label",
                marker=dict(line=dict(color="black", width=1)),
                hovertemplate="Device: %{label}<br>Count: %{value}"
            )
            fig4.update_layout(
                font_color="white",
                title_x=0.02
            )
            st.plotly_chart(fig4, use_container_width=True)

            # ---- OPTIMIZATION TIPS ----
            st.subheader("Optimization Tips")

            if top_device.upper() == "AC":
                tips = [
                    "Set AC temperature to 24–26°C",
                    "Use inverter AC",
                    "Clean filters regularly",
                    "Close doors/windows",
                    "Use curtains",
                    "Turn off when not needed"
                ]
            elif top_device.upper() == "TV":
                tips = [
                    "Reduce brightness",
                    "Turn off when not in use",
                    "Avoid standby",
                    "Use eco mode",
                    "Limit usage",
                    "Upgrade to LED"
                ]
            else:
                tips = [
                    "Turn off unused devices",
                    "Avoid standby power",
                    "Use efficient appliances",
                    "Maintain devices regularly",
                    "Track usage",
                    "Upgrade old appliances"
                ]

            for tip in tips:
                st.write("•", tip)

        else:
            st.warning("No data available")

    # ================= DATA =================
    elif option == "Data":
        if not df.empty:
            st.dataframe(format_table(df), use_container_width=True)
        else:
            st.warning("No data available")

    # ================= LOGOUT =================
    elif option == "Logout":
        st.session_state.clear()
        st.rerun()