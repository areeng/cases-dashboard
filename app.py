import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import timedelta

st.set_page_config(page_title="CASES Dashboard", layout="wide")
st.title("CASES Dashboard")

# 📦 Список тарифів і відповідних Google Drive ID
tariff_files = {
    "Full Access 0UAH": "1XoUhnsGUeVL3qwHMYJbk4mpCn3lhoEkB",
    "Full Access 5UAH": "1ngAmfUoL3qYM6l_URNDECZRW35XC_thY",
    "Full Access 250UAH": "1G60JUAk_vQVXVQnjZF9uK2VwUbYDlK6P",
    "Full Access 350UAH": "1eYubeexGVF5MKJFZIF6ZOwEfDDad1zPB",
    "Full Access 390UAH": "1xeTeJV8JvOowE8JG5I6tog3euIKvDDNj",
    "Full Access 550UAH": "1b5fMQ_5Y522zJssO_AikhkLBTfI3p_Bf",
    "Full Access 1000UAH": "1mOZsP89AhTufFvG2nSmbV6w5GSOKyGVx",
    "Theory Only 0UAH": "1SyARqxHQzEPlK9GEuUvNV1SEFeghJ1pr",
    "Theory Only 250UAH": "1q4c0m434WK46Thei_pgkdVB5lLDnQqZz",
    "Theory Only 550UAH": "1eFhAfdSC2LOLX3tJX5BWyGM693d0ASyK",
}

# 🧩 Контрол для вибору тарифів
selected_tariffs = st.multiselect(
    "Оберіть тариф(и)",
    options=list(tariff_files.keys()),
    default=["Full Access 0UAH"]
)

# 🧾 Завантаження та об'єднання CSV-файлів
dfs = []
for tariff in selected_tariffs:
    file_id = tariff_files[tariff]
    csv_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    df_part = pd.read_csv(csv_url)
    df_part["tariff_name"] = tariff  # додаємо колонку з назвою тарифу
    dfs.append(df_part)

# 🧮 Об'єднуємо всі обрані таблиці в одну
df = pd.concat(dfs, ignore_index=True)

# 🗓 Обробка дати
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df = df.dropna(subset=["date"])

# 📆 Діапазон доступних дат
min_date = df["date"].min()
max_date = df["date"].max()

# 🔎 Фільтр за датою (останні 30 днів за замовчуванням)
st.sidebar.header("Фільтр за датою")
default_end = max_date
default_start = default_end - timedelta(days=30)

start_date, end_date = st.sidebar.date_input(
    "Оберіть період",
    [default_start, default_end],
    min_value=min_date,
    max_value=max_date
)

# 🔍 Фільтрація даних за вибраним періодом
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

# 📊 Метрики на початок та кінець періоду
start_value_row = df[df["date"] == pd.to_datetime(start_date)]
start_value = int(pd.to_numeric(start_value_row["start"], errors="coerce").fillna(0).values[0]) if not start_value_row.empty else "—"

end_value_row = df[df["date"] == pd.to_datetime(end_date)]
end_value = int(pd.to_numeric(end_value_row["end"], errors="coerce").fillna(0).values[0]) if not end_value_row.empty else "—"

# 📈 Метрики за сумою
new_subs = int(filtered_df["new"].sum())
reactivated = int(filtered_df["reactivated"].sum())
upgraded = int(filtered_df["upgradedEnter"].sum())
downgraded = int(filtered_df["downgradedEnter"].sum())

# 🔁 Розрахунок Churned Users по днях
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

# 📌 Виведення основних метрик в один ряд
st.subheader("Метрики")
col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
col1.metric("Підписників\nна початок періоду", start_value)
col2.metric("Підписників\nна кінець періоду", end_value)
col3.metric("Нових\nпідписників", new_subs)
col4.metric("Реактивованих\nпідписників", reactivated)
col5.metric("Upgrade\n(вхід)", upgraded)
col6.metric("Downgrade\n(вхід)", downgraded)
col7.metric("Churned\nUsers", churned_total)

# ➕ Додавання колонки Churned Users до таблиці
filtered_df["Churned Users"] = churned_series

# 📈 Графік "Users"
st.subheader("Користувачі")

chart_data = filtered_df[["date", "start", "new", "reactivated", "Churned Users"]].copy()
chart_data = chart_data.sort_values("date")

fig = px.line(
    chart_data,
    x="date",
    y=["start", "new", "reactivated", "Churned Users"],
    markers=True,
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

# 🧮 Виведення цільових метрик
col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
col1.metric("MRR", mrr)
col2.metric("Churn rate", churn_rate_str)
col3.metric("Growth rate", growth_rate_str)
col4.metric("Lifetime (міс.)", lifetime_str)
col5.metric("LTV", ltv_str)
col6.metric("CAC", cac_str)
col7.metric("LTV / CAC", ltv_cac_str)

# 📊 Графік MRR по днях
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
# st.subheader("Дані за вибраний період:")
# st.dataframe(filtered_df, use_container_width=True)

# 📊 Порівняння тарифів
st.subheader("Порівняння тарифів")

# 🧾 Показники, які хочемо порівнювати
metrics_list = [
    "Підписники на початок періоду",
    "Підписники на кінець періоду",
    "Нові користувачі",
    "Реактивовані користувачі",
    "Churned users",
    "MRR",
    "Churn rate",
    "Lifetime (міс.)",
    "ARPPU",
    "LTV",
    "CAC",
    "LTV / CAC"
]

# 🔀 Групування тарифів
tariff_names = list(tariff_files.keys())
theory_tariffs = [name for name in tariff_names if "Theory Only" in name]
full_tariffs = [name for name in tariff_names if "Full Access" in name]

# 🧱 Створення заголовків MultiIndex
multi_columns = pd.MultiIndex.from_tuples([
    ("Лише теорія", name.replace("Theory Only ", "").replace("UAH", "грн")) for name in theory_tariffs
] + [
    ("Повний доступ", name.replace("Full Access ", "").replace("UAH", "грн")) for name in full_tariffs
])

# 📐 Порожня таблиця з MultiIndex-колонками
data = pd.DataFrame(index=metrics_list, columns=multi_columns)

# 🔄 Проходимо по всім тарифам і обчислюємо метрики
for tariff in theory_tariffs + full_tariffs:
    file_id = tariff_files[tariff]
    csv_url = f"https://drive.google.com/uc?export=download&id={file_id}"

    try:
        df_tariff = pd.read_csv(csv_url)
        df_tariff["date"] = pd.to_datetime(df_tariff["date"], errors="coerce")
        df_tariff = df_tariff.dropna(subset=["date"])
        df_tariff = df_tariff.sort_values("date")

        # Фільтр по даті
        mask = (df_tariff["date"] >= pd.to_datetime(start_date)) & (df_tariff["date"] <= pd.to_datetime(end_date))
        df_filtered = df_tariff[mask].copy()

        # Перетворення на числа
        for col in cols_to_convert:
            if col in df_filtered.columns:
                df_filtered[col] = pd.to_numeric(df_filtered[col], errors="coerce").fillna(0)
            else:
                df_filtered[col] = 0

        # Метрики
        start_row = df_tariff[df_tariff["date"] == pd.to_datetime(start_date)]
        end_row = df_tariff[df_tariff["date"] == pd.to_datetime(end_date)]

        start_val = int(start_row["start"].values[0]) if not start_row.empty else 0
        end_val = int(end_row["end"].values[0]) if not end_row.empty else 0
        new_val = int(df_filtered["new"].sum())
        reactivated_val = int(df_filtered["reactivated"].sum())

        churned_series = (
            df_filtered["start"]
            + df_filtered["new"]
            + df_filtered["reactivated"]
            + df_filtered["upgradedEnter"]
            + df_filtered["downgradedEnter"]
            - df_filtered["end"]
            - df_filtered["upgradedExit"]
            - df_filtered["downgradedExit"]
        ).clip(lower=0)

        churned_val = int(churned_series.sum())
        mrr_val = int(df_filtered["start"].mean() * subscription_price) if not df_filtered.empty else 0

        churn_rate = churned_val / start_val if start_val else None
        lifetime = 1 / churn_rate if churn_rate else None
        arppu = mrr_val / end_val if end_val else None
        ltv = lifetime * arppu if lifetime and arppu else None
        cac = ad_budget / new_val if new_val else None
        ltv_cac = ltv / cac if ltv and cac else None

        # Визначаємо колонку в таблиці
        col_label = tariff.replace("Theory Only ", "").replace("Full Access ", "").replace("UAH", "грн")
        col_group = "Лише теорія" if "Theory Only" in tariff else "Повний доступ"

        # Запис значень у таблицю
        data.loc["Підписники на початок періоду", (col_group, col_label)] = start_val
        data.loc["Підписники на кінець періоду", (col_group, col_label)] = end_val
        data.loc["Нові користувачі", (col_group, col_label)] = new_val
        data.loc["Реактивовані користувачі", (col_group, col_label)] = reactivated_val
        data.loc["Churned users", (col_group, col_label)] = churned_val
        data.loc["MRR", (col_group, col_label)] = mrr_val
        data.loc["Churn rate", (col_group, col_label)] = f"{churn_rate:.1%}" if churn_rate is not None else "—"
        data.loc["Lifetime (міс.)", (col_group, col_label)] = f"{lifetime:.1f}" if lifetime is not None else "—"
        data.loc["ARPPU", (col_group, col_label)] = f"{arppu:.0f}" if arppu is not None else "—"
        data.loc["LTV", (col_group, col_label)] = f"{ltv:.0f}" if ltv is not None else "—"
        data.loc["CAC", (col_group, col_label)] = f"{cac:.2f}" if cac is not None else "—"
        data.loc["LTV / CAC", (col_group, col_label)] = f"{ltv_cac:.2f}" if ltv_cac is not None else "—"

    except Exception as e:
        st.warning(f"Не вдалося завантажити або обробити дані для тарифу {tariff}: {e}")

# 🖼 Вивід кастомної таблиці з центруванням заголовків
st.markdown(
    data.style
    .set_table_styles([
        {"selector": "thead th", "props": [("text-align", "center")]}
    ])
    .to_html(),
    unsafe_allow_html=True
)