import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import re
from datetime import timedelta

# ==== Глобальна функція форматування чисел ====

from streamlit.delta_generator import DeltaGenerator

def format_number(val):
    """
    Форматує числа у стилі UA:
    - цілі: розділяє тисячі пробілом (12 345 678)
    - дробові: розділяє тисячі пробілом і використовує кому як десятковий роздільник (12 345 678,90)
    """
    import numpy as _np

    # ціле число
    if isinstance(val, (int, _np.integer)):
        s = f"{val:,}"            # '12,345,678'
        return s.replace(",", " ")  # '12 345 678'

    # число з плаваючою крапкою
    elif isinstance(val, (float, _np.floating)):
        s = f"{val:,.2f}"         # '12,345,678.90'
        s = s.replace(",", " ")   # '12 345 678.90'
        return s.replace(".", ",")  # '12 345 678,90'

    # рядок із десятковим роздільником у вигляді крапки
    elif isinstance(val, str):
        # замінюємо крапку на кому
        return val.replace(".", ",")

    # усе інше повертаємо без змін
    return val

# ==== Підміна методу metric у DeltaGenerator, щоб автоматично форматувати числа ====
_orig_dd_metric = DeltaGenerator.metric

def _dd_metric(self, label: str, value, delta=None, **kwargs):
    """
    Обгортка над DeltaGenerator.metric, яка форматирує value і delta
    через format_number.
    """
    # Форматуємо ВСЕ: int, float і рядки
    formatted_value = format_number(value)
    formatted_delta = format_number(delta) if delta is not None else None
    return _orig_dd_metric(self, label, formatted_value, formatted_delta, **kwargs)

# Підміна оригінальної функції
DeltaGenerator.metric = _dd_metric

@st.cache_data(show_spinner=False)
def load_tariff_df(file_id):
    """Завантажує CSV з Google Drive, перетворює дату і повертає DataFrame"""
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    df = pd.read_csv(url)
    df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d", errors="coerce")
    df = df.dropna(subset=["date"])
    df = df.sort_values("date")
    return df

st.set_page_config(page_title="CASES Dashboard", layout="wide")

# CSS для плавного скролу з відступом
st.markdown(
    """
    <style>
      /* додаємо відступ зверху для всіх підзаголовків */
      h3 { scroll-margin-top: 100px; }
    </style>
    """,
    unsafe_allow_html=True
)

# Заголовок дашборда
st.title("CASES Dashboard")

# 📂 Список файлів зі статистикою по компаніям, студентам, профілям та тріалам
statistic_files = {
    "companies": "1OVBwvUjNbJFY_cvLCh6RynL_WKowqXJ2",
    "students": "1gJTkWUssnOKKlBSIxk6rQETuEaFTA9EL",
    "users": "1nuxKPhBP1qx09FcuCPG1uIobrG92dxHE",
    "trials": "1AsIIcj-2lYQWXHfPoMWsdtA46nqUbduH"
}

# 📦 Список тарифів
tariff_files = {
    "Full Access 0UAH": "1XoUhnsGUeVL3qwHMYJbk4mpCn3lhoEkB",
    # "Full Access 5UAH": "1ngAmfUoL3qYM6l_URNDECZRW35XC_thY",   це технічний тариф
    "Full Access 250UAH": "1G60JUAk_vQVXVQnjZF9uK2VwUbYDlK6P",
    "Full Access 350UAH": "1eYubeexGVF5MKJFZIF6ZOwEfDDad1zPB",
    "Full Access 390UAH": "1xeTeJV8JvOowE8JG5I6tog3euIKvDDNj",
    "Full Access 550UAH": "1b5fMQ_5Y522zJssO_AikhkLBTfI3p_Bf",
    "Full Access 1000UAH": "1mOZsP89AhTufFvG2nSmbV6w5GSOKyGVx",
    "Full Access 1200UAH": "1M1u8AAQHFv81BNtlvi4P6llT0OO817dj",
    "Theory Only 0UAH": "1SyARqxHQzEPlK9GEuUvNV1SEFeghJ1pr",
    "Theory Only 250UAH": "1q4c0m434WK46Thei_pgkdVB5lLDnQqZz",
    "Theory Only 500UAH": "1eFhAfdSC2LOLX3tJX5BWyGM693d0ASyK",
    "Theory Only 600UAH": "1EdZRWRQxLUfKprV5GgRWjjR_Jzyc7CEh",
}

tabs = st.tabs([
    "Статистика передплат",
    "Порівняння тарифів",
    "Статистика профілів та тріалів"
])

with tabs[0]:

    # 🧩 Контрол для вибору тарифів
    selected_tariffs = st.multiselect(
        "Оберіть тарифи",
        options=list(tariff_files.keys()),
        default=["Full Access 250UAH"]
    )

    # 🧾 Завантаження та об'єднання CSV-файлів
    dfs = []
    for tariff in selected_tariffs:
        file_id = tariff_files[tariff]
        csv_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        df_part = pd.read_csv(csv_url)
        df_part["tariff_name"] = tariff  # додаємо колонку з назвою тарифу

        # Додаємо колонку з ціною тарифу (витягуємо з назви)
        match = re.search(r"(\d+)UAH", tariff)
        if match:
            df_part["price"] = int(match.group(1))
        else:
            df_part["price"] = 0  # якщо раптом немає ціни в назві тарифу

        dfs.append(df_part)

    # 🧮 Об'єднуємо всі обрані таблиці в одну
    df = pd.concat(dfs, ignore_index=True)

    # 🗓 Обробка дати
    df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d", errors="coerce")
    df = df.dropna(subset=["date"])

    # 📆 Діапазон доступних дат
    min_date = df["date"].min()
    max_date = df["date"].max()

    # 🔎 Контрол з календарем (останні 30 днів за замовчуванням)
    from datetime import datetime

    # 📅 Сьогоднішній день
    today = pd.to_datetime(datetime.today().date())
    min_date = df["date"].min()
    max_data_date = df["date"].max()

    st.sidebar.header("Фільтр за датою")

    # 🧭 Випадаючий список періодів
    preset_option = st.sidebar.selectbox(
        "Швидкий вибір періоду:",
        (
            "Останні 30 днів",
            "Попередній місяць",
            "Останні 3 місяці",
            "Останні 6 місяців",
            "Останній рік",
            "Весь час"
        )
    )

    # 🔁 Обчислення періоду на основі вибору
    if preset_option == "Останні 30 днів":
        end_default = min(today, max_data_date)
        start_default = end_default - timedelta(days=30)

    elif preset_option == "Попередній місяць":
        first_day_this_month = today.replace(day=1)
        last_day_prev_month = first_day_this_month - timedelta(days=1)
        start_default = last_day_prev_month.replace(day=1)
        end_default = last_day_prev_month

    elif preset_option == "Останні 3 місяці":
        end_default = min(today, max_data_date)
        start_default = end_default - pd.DateOffset(months=3)

    elif preset_option == "Останні 6 місяців":
        end_default = min(today, max_data_date)
        start_default = end_default - pd.DateOffset(months=6)

    elif preset_option == "Останній рік":
        end_default = min(today, max_data_date)
        start_default = end_default - pd.DateOffset(years=1)

    elif preset_option == "Весь час":
        start_default = min_date
        end_default = max_data_date

    # 📆 Календар з передзаповненим періодом
    start_date, end_date = st.sidebar.date_input(
        "Або оберіть вручну:",
        value=[start_default, end_default],
        min_value=min_date,
        max_value=max_data_date
    )

    # Посилання на інструкцію з оновлення даних
    st.sidebar.markdown(
        '<a href="https://docs.google.com/document/d/1YkcEtLCvnzlOZdBO5tPzCs35sQ87u9xmHiJuPS2TuBY/edit?tab=t.0" target="_blank">Як оновити дані</a>',
        unsafe_allow_html=True
    )


    # Навигація по розділам
    # st.sidebar.header("Навігація")
    # nav_items = {
    #     "Статистика передплат": "metrics",
    #     "Порівняння тарифів": "tariff-comparison",
    #     "Статистика профілів та тріалів": "companies-students-profiles-trials"
    # }
    # for label, anchor in nav_items.items():
    #     st.sidebar.markdown(f"<a href='#{anchor}'>{label}</a>", unsafe_allow_html=True)

    # Визначаємо колонки для числового перетворення
    cols_to_convert = [
        "start", "new", "reactivated",
        "upgradedEnter", "downgradedEnter",
        "end", "upgradedExit", "downgradedExit"
    ]

    # 🔍 Фільтрація даних за вибраним періодом
    mask = (df["date"] >= pd.to_datetime(start_date)) & (df["date"] <= pd.to_datetime(end_date))
    filtered_raw = df.loc[mask].copy()

    # 📊 Завантаження та обробка статистики по компаніям, студентам і профілям
    def load_stat_file(file_id):
        url = f"https://drive.google.com/uc?export=download&id={file_id}"
        df_stat = pd.read_csv(url)
        df_stat["date"] = pd.to_datetime(df_stat["date"], format="%Y-%m-%d", errors="coerce")
        df_stat = df_stat.dropna(subset=["date"])
        return df_stat

    # Завантаження статистики
    companies_df = load_stat_file(statistic_files["companies"])
    students_df  = load_stat_file(statistic_files["students"])
    users_df     = load_stat_file(statistic_files["users"])
    trials_df    = load_stat_file(statistic_files["trials"])

    # Фільтрація по вибраному періоду
    companies_filtered = companies_df[(companies_df["date"] >= pd.to_datetime(start_date)) &
                                    (companies_df["date"] <= pd.to_datetime(end_date))]
    students_filtered  = students_df [(students_df["date"]  >= pd.to_datetime(start_date)) &
                                    (students_df["date"]  <= pd.to_datetime(end_date))]
    users_filtered     = users_df    [(users_df["date"]     >= pd.to_datetime(start_date)) &
                                    (users_df["date"]     <= pd.to_datetime(end_date))]
    trials_filtered    = trials_df    [(trials_df["date"]     >= pd.to_datetime(start_date)) &
                                    (trials_df["date"]     <= pd.to_datetime(end_date))]

    # Обчислення медіани для тріалів за вибраний період
    median_trials = trials_filtered["active"].median() if not trials_filtered.empty else 0

    # 🔧 Перетворення колонок на числові типи
    for col in cols_to_convert:
        filtered_raw[col] = pd.to_numeric(filtered_raw.get(col, 0), errors="coerce").fillna(0)

    # Агрегування даних по даті для всіх вибраних тарифів
    aggregated_df = (
        filtered_raw
        .groupby("date", as_index=False)[cols_to_convert]
        .sum()
    )

    # Розрахунок Churned Users
    aggregated_df["Churned Users"] = (
        aggregated_df["start"]
        + aggregated_df["new"]
        + aggregated_df["reactivated"]
        + aggregated_df["upgradedEnter"]
        + aggregated_df["downgradedEnter"]
        - aggregated_df["end"]
        - aggregated_df["upgradedExit"]
        - aggregated_df["downgradedExit"]
    ).clip(lower=0)

    # 📊 Метрики на початок та кінець періоду
    start_value_row = df[df["date"] == pd.to_datetime(start_date)]
    start_value = int(
        aggregated_df.loc[
            aggregated_df["date"] == pd.to_datetime(start_date),
            "start"
        ].sum()
    ) if not aggregated_df.empty else "—"

    end_value_row = df[df["date"] == pd.to_datetime(end_date)]
    end_value = int(
        aggregated_df.loc[
            aggregated_df["date"] == pd.to_datetime(end_date),
            "end"
        ].sum()
    ) if not aggregated_df.empty else "—"

    # 📈 Метрики за сумою
    new_subs = int(aggregated_df["new"].sum())
    reactivated = int(aggregated_df["reactivated"].sum())
    upgraded = int(aggregated_df["upgradedEnter"].sum())
    downgraded = int(aggregated_df["downgradedEnter"].sum())
    churned_total= int(aggregated_df["Churned Users"].sum())

    # 🔁 Розрахунок Churned Users по днях
    churned_series = (
        aggregated_df["start"]
        + aggregated_df["new"]
        + aggregated_df["reactivated"]
        + aggregated_df["upgradedEnter"]
        + aggregated_df["downgradedEnter"]
        - aggregated_df["end"]
        - aggregated_df["upgradedExit"]
        - aggregated_df["downgradedExit"]
    ).clip(lower=0)

    churned_total = int(churned_series.sum())    

    # 📌 Виведення основних метрик в один ряд
    st.markdown("<a id='metrics'></a>", unsafe_allow_html=True)
    st.subheader("Статистика передплат")

    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
    col1.metric("Користувачів\nна початок періоду", start_value)
    col2.metric("Користувачів\nна кінець періоду", end_value)
    col3.metric("Нових\nкористувачів", new_subs)
    col4.metric("Реактивованих\nкористувачів", reactivated)
    col5.metric("Upgrade\n(вхід)", upgraded)
    col6.metric("Downgrade\n(вхід)", downgraded)
    col7.metric("Churned\nUsers", churned_total)

    # ➕ Додавання колонки Churned Users до таблиці
    aggregated_df["Churned Users"] = churned_series

    # 📈 Графік "Users"
    st.subheader("Користувачі")

    fig = px.line(
        aggregated_df,
        x="date",
        y=["start", "new", "reactivated", "Churned Users"],
        markers=True,
    )
    fig.update_layout(xaxis_title=None, yaxis_title=None)
    fig.update_xaxes(tickmode="linear", tickangle=45)

    st.plotly_chart(fig, use_container_width=True)

    # 💰 Цільові показники
    st.markdown("<a id='monthly-targets'></a>", unsafe_allow_html=True)
    st.subheader("Цільові показники")

    ad_budget = 5000  # рекламний бюджет

    # MRR

    # Групуємо по назві тарифу та розраховуємо середній start
    mrr = 0
    for tariff in selected_tariffs:
        # Фільтруємо агрегований датафрейм по тарифу
        tariff_df = filtered_raw[filtered_raw["tariff_name"] == tariff]
        if not tariff_df.empty:
            avg_start = tariff_df["start"].mean()
            price = tariff_df["price"].iloc[0]  # ціна для цього тарифу
            mrr += avg_start * price

    mrr = int(round(mrr))

    # Churn Rate
    try:
        churn_rate = churned_total / start_value
        churn_rate_str = f"{churn_rate:.1%}"
    except (ZeroDivisionError, TypeError):
        churn_rate = None
        churn_rate_str = "—"

    # Growth Rate
    # 💡 Розрахунок MRR на початок і кінець періоду з урахуванням усіх тарифів

    def calc_mrr_on_date(date, df):
        mrr = 0
        for tariff in selected_tariffs:
            sub = df[(df["date"] == pd.to_datetime(date)) & (df["tariff_name"] == tariff)]
            if not sub.empty:
                start = sub["start"].values[0]
                price = sub["price"].values[0]
                mrr += start * price
        return mrr

    mrr_first = calc_mrr_on_date(start_date, filtered_raw)
    mrr_last  = calc_mrr_on_date(end_date, filtered_raw)

    try:
        growth_rate = (mrr_last - mrr_first) / mrr_first if mrr_first != 0 else 0
        growth_rate_str = f"{growth_rate:.1%}"
    except ZeroDivisionError:
        growth_rate_str = "—"

    # Lifetime
    if churn_rate and churn_rate != 0:
        lifetime = 1 / churn_rate
        lifetime_str = f"{lifetime:.1f}"
    else:
        lifetime = None
        lifetime_str = "—"

    # ARPPU — середній дохід на платника
    try:
        arppu = mrr / end_value if end_value else None
        arppu_str = f"{arppu:.2f}" if arppu is not None else "—"
    except ZeroDivisionError:
        arppu = None
        arppu_str = "—"

    # LTV — життєвий цикл клієнта
    if lifetime and arppu:
        ltv = lifetime * arppu
        ltv_str = f"{int(ltv)}"
    else:
        ltv = None
        ltv_str = "—"

    # CAC — вартість залучення одного користувача
    try:
        cac = ad_budget / new_subs if new_subs else None
        cac_str = f"{cac:.2f}" if cac is not None else "—"
    except ZeroDivisionError:
        cac = None
        cac_str = "—"

    # LTV / CAC
    try:
        ltv_cac = ltv / cac if (ltv is not None and cac) else None
        ltv_cac_str = f"{ltv_cac:.2f}" if ltv_cac is not None else "—"
    except ZeroDivisionError:
        ltv_cac_str = "—"

    # 🧮 Виведення цільових метрик
    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
    col1.metric("MRR", mrr)
    col2.metric("Churn rate", churn_rate_str)
    col3.metric("Growth rate", growth_rate_str)
    col4.metric("Lifetime (міс.)", lifetime_str)
    col5.metric("LTV", ltv_str)
    #col6.metric("CAC", cac_str)
    #col7.metric("LTV / CAC", ltv_cac_str)

    # 📊 Графік MRR по днях
    st.subheader("MRR")

    # Додаємо в aggregated_df стовпець MRR по днях (з урахуванням цін тарифів)
    def calc_mrr_day(day):
        # day — дата
        mrr_day = 0
        for tariff in selected_tariffs:
            # Знаходимо всі рядки в filtered_raw з потрібною датою і тарифом
            sub = filtered_raw[(filtered_raw["date"] == day) & (filtered_raw["tariff_name"] == tariff)]
            if not sub.empty:
                start = sub["start"].values[0]
                price = sub["price"].values[0]
                mrr_day += start * price
        return mrr_day

    aggregated_df["MRR"] = aggregated_df["date"].apply(calc_mrr_day)

    # Будуємо графік за новим стовпчиком
    fig_mrr = px.line(
        aggregated_df,
        x="date",
        y="MRR",
        markers=True
    )
    fig_mrr.update_layout(xaxis_title=None, yaxis_title=None)
    fig_mrr.update_xaxes(tickmode="linear", tickangle=45)

    st.plotly_chart(fig_mrr, use_container_width=True)

#----------------------------------------------------------------------------------------------------------------

with tabs[1]:

    # 📋 Таблиця даних
    # st.subheader("Дані за вибраний період:")
    # st.dataframe(aggregated_df, use_container_width=True)

    # 📊 Порівняння тарифів
    st.markdown("<a id='tariff-comparison'></a>", unsafe_allow_html=True)
    st.subheader("Порівняння тарифів")

    # 🧾 Показники, які хочемо порівнювати
    metrics_list = [
        "Користувачів на початок періоду",
        "Користувачів на кінець періоду",
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
        ("Лише теорія", name.replace("Theory Only ", "").replace("UAH", " грн")) for name in theory_tariffs
    ] + [
        ("Повний доступ", name.replace("Full Access ", "").replace("UAH", " грн")) for name in full_tariffs
    ])

    # 📐 Порожня таблиця з MultiIndex-колонками
    data = pd.DataFrame(index=metrics_list, columns=multi_columns)

    # 🔄 Проходимо по всім тарифам і обчислюємо метрики
    for tariff in theory_tariffs + full_tariffs:
        file_id = tariff_files[tariff]
        csv_url = f"https://drive.google.com/uc?export=download&id={file_id}"

        try:
            df_tariff = load_tariff_df(file_id)

            # Додаємо колонку price, витягуючи ціну з назви тарифу
            match = re.search(r"(\d+)UAH", tariff)
            if match:
                df_tariff["price"] = int(match.group(1))
            else:
                df_tariff["price"] = 0        

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
            if not df_filtered.empty:
                price = df_filtered["price"].iloc[0]
                mrr_val = int(df_filtered["start"].mean() * price)
            else:
                mrr_val = 0

            churn_rate = churned_val / start_val if start_val else None
            lifetime = 1 / churn_rate if churn_rate else None
            arppu = mrr_val / end_val if end_val else None
            ltv = lifetime * arppu if lifetime and arppu else None
            cac = ad_budget / new_val if new_val else None
            ltv_cac = ltv / cac if ltv and cac else None

            # Визначаємо колонку в таблиці
            col_label = tariff.replace("Theory Only ", "").replace("Full Access ", "").replace("UAH", " грн")
            col_group = "Лише теорія" if "Theory Only" in tariff else "Повний доступ"

            # Запис значень у таблицю
            data.loc["Користувачів на початок періоду", (col_group, col_label)] = start_val
            data.loc["Користувачів на кінець періоду", (col_group, col_label)] = end_val
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




    #Тимчасово приховуємо два рядки таблиці
    hide_metrics = ["CAC", "LTV / CAC"]
    data = data.drop(index=hide_metrics)






    # 🖼 Вивід кастомної таблиці з центруванням заголовків
    st.markdown(
        data.style
            .format(format_number)  # застосовуємо функцію форматування до всіх комірок
            .set_table_styles([
                {"selector": "thead th", "props": [("text-align", "center")]}
            ])
            .to_html(),
        unsafe_allow_html=True
    )

#--------------------------------------------------------------------------------------

with tabs[2]:

    # 🧾 Розрахунок загальної статистики компаній, студентів і профілів
    # Беремо останнє значення total в отфильтрованных данных (companies_filtered, students_filtered, users_filtered)
    #total_companies = int(companies_filtered["total"].iloc[-1]) if not companies_filtered.empty else 0
    #total_students  = int(students_filtered["total"].iloc[-1])  if not students_filtered.empty  else 0
    #total_profiles  = int(users_filtered["total"].iloc[-1])     if not users_filtered.empty     else 0
    #total_trials  = int(trials_filtered["active"].iloc[-1])     if not trials_filtered.empty     else 0

    # Вивід блока метрик
    #st.subheader("Статистика профілів та тріалів")
    #c1, c2, c3, c4 = st.columns(4)
    #c1.metric("Компанії", total_companies)
    #c2.metric("Студенти", total_students)
    #c3.metric("Профілі", total_profiles)
    #c4.metric("Тріали", total_trials)

    # 📈 Графіки по кожному показнику

    st.markdown("<a id='companies-students-profiles-trials'></a>", unsafe_allow_html=True)
    row1_col1, row1_col2 = st.columns(2)

    with row1_col1:
        st.subheader("Компанії")
        chart_comp = companies_filtered[["date", "total"]].rename(columns={"total": "Компанії"})
        fig_comp = px.line(
            chart_comp,
            x="date",
            y="Компанії",
            markers=True,
        )
        fig_comp.update_layout(xaxis_title=None, yaxis_title=None)
        fig_comp.update_xaxes(tickmode="linear", tickangle=45)
        st.plotly_chart(fig_comp, use_container_width=True)

    with row1_col2:
        st.subheader("Тріали")
        chart_trial = trials_filtered[["date", "active"]].rename(columns={"active": "Тріали"})
        fig_trial = px.line(
            chart_trial,
            x="date",
            y="Тріали",
            markers=True,
        )
        fig_trial.update_layout(xaxis_title=None, yaxis_title=None)
        fig_trial.update_xaxes(tickmode="linear", tickangle=45)
        # Додаємо горизонтальну лінію-медіану
        fig_trial.add_hline(
            y=median_trials,
            line_dash="dash",
            line_color="orange",
            annotation_text=f"Медіана: {int(median_trials)}",
            annotation_position="top left"
        )        
        st.plotly_chart(fig_trial, use_container_width=True)

    row2_col1, row2_col2 = st.columns(2)

    with row2_col1:
        st.subheader("Студенти")
        chart_stud = students_filtered[["date", "total"]].rename(columns={"total": "Студенти"})
        fig_stud = px.line(
            chart_stud,
            x="date",
            y="Студенти",
            markers=True,
        )
        fig_stud.update_layout(xaxis_title=None, yaxis_title=None)
        fig_stud.update_xaxes(tickmode="linear", tickangle=45)
        st.plotly_chart(fig_stud, use_container_width=True)

    with row2_col2:
        st.subheader("Профілі")
        chart_prof = users_filtered[["date", "total"]].rename(columns={"total": "Профілі"})
        fig_prof = px.line(
            chart_prof,
            x="date",
            y="Профілі",
            markers=True,
        )
        fig_prof.update_layout(xaxis_title=None, yaxis_title=None)
        fig_prof.update_xaxes(tickmode="linear", tickangle=45)
        st.plotly_chart(fig_prof, use_container_width=True)