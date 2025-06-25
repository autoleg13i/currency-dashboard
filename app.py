import streamlit as st
from streamlit_autorefresh import st_autorefresh
from currency_utils import get_monobank_data, get_privatbank_data
from parsers import parse_monobank, parse_privatbank
import pandas as pd
import os

st.set_page_config(page_title="Курси валют", page_icon="💱")
st.title("💱 Курси валют від банків України")

# 🔁 Автоматичне оновлення щоп’ять хвилин
st_autorefresh(interval=300000, key="refresh")

# 📥 Отримання і парсинг даних
mono_raw = get_monobank_data()["data"]
privat_raw = get_privatbank_data()["data"]

mono = parse_monobank(mono_raw) if mono_raw else []
privat = parse_privatbank(privat_raw) if privat_raw else []

# 🧩 Об'єднання в один датафрейм
df = pd.DataFrame(mono + privat)
df["Банк"] = ["Monobank"] * len(mono) + ["PrivatBank"] * len(privat)

# 🎛️ Фільтр за обраною валютою
валюти = sorted(df["ccy"].unique())
обрана_валюта = st.selectbox("Оберіть валюту", валюти, index=валюти.index("USD") if "USD" in валюти else 0)

df_filtered = df[df["ccy"] == обрана_валюта]

# 🌍 Перейменування колонок для українізованого інтерфейсу
df_filtered = df_filtered.rename(columns={
    "ccy": "Валюта",
    "rateBuy": "Курс купівлі",
    "rateSell": "Курс продажу",
    "Банк": "Банк"
})

# 🌟 Визначення найкращих курсів
best_buy = df_filtered["Курс купівлі"].max()
best_sell = df_filtered["Курс продажу"].min()

# 🎨 Функція стилізації
def highlight_best(row):
    styles = []
    for col in df_filtered.columns:
        style = ""
        if col == "Курс купівлі" and row["Курс купівлі"] == best_buy:
            style = "background-color: #d4edda; color: red"
        elif col == "Курс продажу" and row["Курс продажу"] == best_sell:
            style = "background-color: #ffeeba; color: blue"
        styles.append(style)
    return styles

# 📊 Вивід у таблицю з підсвіткою
if not df_filtered.empty:
    st.markdown(f"**💱 Поточна валюта:** `{обрана_валюта}`")
    st.dataframe(
        df_filtered.style.apply(highlight_best, axis=1),
        use_container_width=True
    )
else:
    st.warning("Немає даних для вибраної валюти.")

# 🧾 Виведення логів помилок
if os.path.exists("api_errors.log"):
    with open("api_errors.log", "r") as log_file:
        st.expander("📋 Лог помилок API").write(log_file.read())
else:
    st.caption("Лог-файл ще не створено або помилок не було 🎉")