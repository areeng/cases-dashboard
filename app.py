import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="CASES Dashboard", layout="wide")
st.title("CASES Dashboard")

# Завантаження CSV-файлу
uploaded_file = st.file_uploader("Завантажте CSV-файл", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    # Обробка дати
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    # Діапазон доступних дат
    min_date = df["date"].min()
    max_date = df["date"].max()

    # Фільтр за датою
    st.sidebar.header("Фільтр за датою")
    start_date, end_date = st.sidebar.date_input("Оберіть період", [min_date, max_date])

    # Фільтрація даних за вибраним періодом
    mask = (df["date"] >= pd.to_datetime(start_date)) & (df["date"] <= pd.to_datetime(end_date))
    filtered_df = df[mask]

    # 🔧 Перетворення колонок на числові типи
    cols_to_convert = [
        "start", "new", "reactivated", "upgradedEnter", "downgradedEnter",
        "end", "upgradedExit", "downgradedExit"
    ]

    for col in cols_to_convert:
        if col in filtered_df.columns:
            filtered_df[col] = pd.to_numeric(filtered_df[col], errors="coerce").fillna(0)
        else:
            filtered_df[col] = 0

    # Метрики на початок та кінець періоду
    start_value_row = df[df["date"] == pd.to_datetime(start_date)]
    start_value = int(pd.to_numeric(start_value_row["start"], errors="coerce").fillna(0).values[0]) if not start_value_row.empty else "—"

    end_value_row = df[df["date"] == pd.to_datetime(end_date)]
    end_value = int(pd.to_numeric(end_value_row["end"], errors="coerce").fillna(0).values[0]) if not end_value_row.empty else "—"

    # Метрики за сумою
    new_subs = int(filtered_df["new"].sum())
    reactivated = int(filtered_df["reactivated"].sum())
    upgraded = int(filtered_df["upgradedEnter"].sum())
    downgraded = int(filtered_df["downgradedEnter"].sum())

    # Розрахунок Churned Users по днях
    churned_series = (
        filtered_df["start"]
        + filtered_df["new"]
        + filtered_df["reactivated"]
        + filtered_df["upgradedEnter"]
        + filtered_df["downgradedEnter"]
        - filtered_df["end"]
        - filtered_df["upgradedExit"]
        - filtered_df["downgradedExit"]
    ).clip(lower=0)

    churned_total = int(churned_series.sum())

    # Виведення основних метрик в один ряд
    st.subheader("Метрики")
    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
    col1.metric("Підписників\nна початок періоду", start_value)
    col2.metric("Підписників\nна кінець періоду", end_value)
    col3.metric("New\nSubscribers", new_subs)
    col4.metric("Reactivated\nUsers", reactivated)
    col5.metric("Upgrade\n(вхід)", upgraded)
    col6.metric("Downgrade\n(вхід)", downgraded)
    col7.metric("Churned\nUsers", churned_total)

    # Додавання колонки Churned Users в таблицю
    filtered_df["Churned Users"] = churned_series

    # 📈 Графік "Users"
    st.subheader("Users")

    # Підготовка даних до графіка
    chart_data = filtered_df[["date", "start", "new", "reactivated", "Churned Users"]].copy()
    chart_data = chart_data.sort_values("date")

    # Побудова графіка
    fig = px.line(
        chart_data,
        x="date",
        y=["start", "new", "reactivated", "Churned Users"],
        markers=True
    )
    fig.update_layout(xaxis_title=None, yaxis_title=None)
    fig.update_xaxes(tickmode="linear", tickangle=45)

    st.plotly_chart(fig, use_container_width=True)

    # 💰 Цільові показники місяця
    st.subheader("Цільові показники місяця")

    subscription_price = 1000
    ad_budget = 5000  # рекламний бюджет

    # MRR
    if not filtered_df.empty:
        mrr = int(filtered_df["start"].mean() * subscription_price)
    else:
        mrr = "—"

    # Churn Rate
    try:
        churn_rate = churned_total / start_value
        churn_rate_str = f"{churn_rate:.1%}"
    except (ZeroDivisionError, TypeError):
        churn_rate = None
        churn_rate_str = "—"

    # Growth Rate
    first_day_row = df[df["date"] == pd.to_datetime(start_date)]
    last_day_row = df[df["date"] == pd.to_datetime(end_date)]

    try:
        mrr_first = float(first_day_row["start"].values[0]) * subscription_price
        mrr_last = float(last_day_row["start"].values[0]) * subscription_price
        growth_rate = (mrr_last - mrr_first) / mrr_last if mrr_last != 0 else 0
        growth_rate_str = f"{growth_rate:.1%}"
    except (IndexError, ValueError, ZeroDivisionError):
        growth_rate_str = "—"

    # Lifetime
    if churn_rate and churn_rate != 0:
        lifetime = 1 / churn_rate
        lifetime_str = f"{lifetime:.1f}"
    else:
        lifetime = None
        lifetime_str = "—"

    # ARPPU (внутрішня метрика)
    try:
        arppu = mrr / end_value
    except (ZeroDivisionError, TypeError):
        arppu = None

    # LTV
    if lifetime and arppu:
        ltv = int(lifetime * arppu)
    else:
        ltv = None
    ltv_str = ltv if ltv is not None else "—"

    # CAC
    try:
        cac = ad_budget / new_subs
        cac = round(cac, 2)
        cac_str = f"{cac:.2f}"
    except (ZeroDivisionError, TypeError):
        cac = None
        cac_str = "—"

    # LTV / CAC
    try:
        ltv_cac = ltv / cac
        ltv_cac_str = f"{ltv_cac:.2f}"
    except (ZeroDivisionError, TypeError):
        ltv_cac_str = "—"

    # Виведення цільових метрик
    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
    col1.metric("MRR", mrr)
    col2.metric("Churn rate", churn_rate_str)
    col3.metric("Growth rate", growth_rate_str)
    col4.metric("Lifetime (міс.)", lifetime_str)
    col5.metric("LTV", ltv_str)
    col6.metric("CAC", cac_str)
    col7.metric("LTV / CAC", ltv_cac_str)

    # 📈 Графік MRR по днях
    st.subheader("MRR")

    filtered_df["MRR"] = filtered_df["start"] * subscription_price

    fig_mrr = px.line(
        filtered_df,
        x="date",
        y="MRR",
        markers=True
    )
    fig_mrr.update_layout(xaxis_title=None, yaxis_title=None)
    fig_mrr.update_xaxes(tickmode="linear", tickangle=45)

    st.plotly_chart(fig_mrr, use_container_width=True)

    # 📋 Таблиця даних
    st.subheader("Дані за вибраний період:")
    st.dataframe(filtered_df, use_container_width=True)