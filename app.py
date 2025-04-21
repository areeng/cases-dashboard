import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="CASES Dashboard", layout="wide")
st.title("CASES Dashboard")

uploaded_file = st.file_uploader("Загрузите CSV-файл", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    # Обработка даты
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    # Диапазон дат
    min_date = df["date"].min()
    max_date = df["date"].max()

    # Фильтр по дате
    st.sidebar.header("Фильтр по дате")
    start_date, end_date = st.sidebar.date_input("Выберите период", [min_date, max_date])

    # Фильтрация по диапазону
    mask = (df["date"] >= pd.to_datetime(start_date)) & (df["date"] <= pd.to_datetime(end_date))
    filtered_df = df[mask]

    # 🔧 Приводим нужные колонки к числовому типу
    cols_to_convert = [
        "start", "new", "reactivated", "upgradedEnter", "downgradedEnter",
        "end", "upgradedExit", "downgradedExit"
    ]

    for col in cols_to_convert:
        if col in filtered_df.columns:
            filtered_df[col] = pd.to_numeric(filtered_df[col], errors="coerce").fillna(0)
        else:
            filtered_df[col] = 0

    # Метрики по началу и концу
    start_value_row = df[df["date"] == pd.to_datetime(start_date)]
    start_value = int(pd.to_numeric(start_value_row["start"], errors="coerce").fillna(0).values[0]) if not start_value_row.empty else "—"

    end_value_row = df[df["date"] == pd.to_datetime(end_date)]
    end_value = int(pd.to_numeric(end_value_row["end"], errors="coerce").fillna(0).values[0]) if not end_value_row.empty else "—"

    # Метрики по суммам
    new_subs = int(filtered_df["new"].sum())
    reactivated = int(filtered_df["reactivated"].sum())
    upgraded = int(filtered_df["upgradedEnter"].sum())
    downgraded = int(filtered_df["downgradedEnter"].sum())

    # Вычисление Churned users по дням
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

    # Вывод всех метрик в одну строку
    st.subheader("Метрики")
    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
    col1.metric("Подписчиков\nна начало периода", start_value)
    col2.metric("Подписчиков\nна конец периода", end_value)
    col3.metric("New\nSubscribers", new_subs)
    col4.metric("Reactivated\nUsers", reactivated)
    col5.metric("Upgrade\n(вхід)", upgraded)
    col6.metric("Downgrade\n(вхід)", downgraded)
    col7.metric("Churned\nUsers", churned_total)

    # Вычисление Churned Users по дням (в виде столбца)
    filtered_df["Churned Users"] = (
        filtered_df["start"]
        + filtered_df["new"]
        + filtered_df["reactivated"]
        + filtered_df["upgradedEnter"]
        + filtered_df["downgradedEnter"]
        - filtered_df["end"]
        - filtered_df["upgradedExit"]
        - filtered_df["downgradedExit"]
    ).clip(lower=0)

    # График "Users"
    st.subheader("Users")

    # Подготовка данных для графика
    chart_data = filtered_df[["date", "start", "new", "reactivated", "Churned Users"]].copy()
    chart_data = chart_data.sort_values("date")

    # Построение графика
    fig = px.line(
        chart_data,
        x="date",
        y=["start", "new", "reactivated", "Churned Users"],
        markers=True
    )

    # Удалим подписи осей
    fig.update_layout(
        xaxis_title=None,
        yaxis_title=None
    )

    # Покажем все даты на оси X
    fig.update_xaxes(tickmode="linear", tickangle=45)

    st.plotly_chart(fig, use_container_width=True)

    # 💰 Цільові показники місяця
    st.subheader("Цільові показники місяця")

    subscription_price = 1000
    ad_budget = 5000  # рекламный бюджет

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

    # ARPPU (внутренне)
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

    # Вывод всех метрик в 7 колонках
    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
    col1.metric("MRR", mrr)
    col2.metric("Churn rate", churn_rate_str)
    col3.metric("Growth rate", growth_rate_str)
    col4.metric("Lifetime (міс.)", lifetime_str)
    col5.metric("LTV", ltv_str)
    col6.metric("CAC", cac_str)
    col7.metric("LTV / CAC", ltv_cac_str)

    # 📈 График MRR по дням
    st.subheader("MRR")

    # Добавим колонку с ежедневным MRR
    filtered_df["MRR"] = filtered_df["start"] * subscription_price

    # Строим график
    fig_mrr = px.line(
        filtered_df,
        x="date",
        y="MRR",
        markers=True
    )

    # Убираем подписи осей
    fig_mrr.update_layout(
        xaxis_title=None,
        yaxis_title=None
    )

    # Показываем все даты на оси X
    fig_mrr.update_xaxes(tickmode="linear", tickangle=45)

    # Отображаем график
    st.plotly_chart(fig_mrr, use_container_width=True)

    # Таблица
    st.subheader("Данные за выбранный период:")
    st.dataframe(filtered_df, use_container_width=True)
