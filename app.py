import streamlit as st
import time
import pandas as pd
import os
from currency_utils import get_monobank_data, get_privatbank_data
from parsers import parse_monobank, parse_privatbank

# ⚙️ Конфігурація сторінки
st.set_page_config(page_title="Курси валют", page_icon="💱")

# ⏱️ Автооновлення
REFRESH_INTERVAL = 300
now = time.time()
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = now

time_since = int(now - st.session_state.last_refresh)
time_left = max(REFRESH_INTERVAL - time_since, 0)

# 🔄 Автооновлення без rerun
if time_left <= 0:
    st.session_state.last_refresh = now
    st.stop()

# 🏷️ Заголовок
st.title("💱 Курси валют від банків України")

# 🕒 Таймер через st.empty()
timer_placeholder = st.empty()
progress_placeholder = st.empty()

timer_placeholder.markdown(
    f"<h5 style='color:gray;'>⏱️ Автооновлення через: "
    f"<span style='color:black;'>{time_left} сек</span></h5>",
    unsafe_allow_html=True
)
progress_placeholder.progress(int((REFRESH_INTERVAL - time_left) / REFRESH_INTERVAL * 100))

# 🔘 Ручне оновлення
if st.button("🔄 Оновити зараз"):
    st.session_state.last_refresh = time.time()
    st.rerun()

# 📡 Дані з API
mono_raw = get_monobank_data()["data"]
privat_raw = get_privatbank_data()["data"]

mono = parse_monobank(mono_raw) if mono_raw else []
privat = parse_privatbank(privat_raw) if privat_raw else []

# 🧩 DataFrame
df = pd.DataFrame(mono + privat)
df["Банк"] = ["Monobank"] * len(mono) + ["PrivatBank"] * len(privat)

# 🎛️ Вибір валюти
валюти = sorted(df["ccy"].unique())
обрана_валюта = st.selectbox("Оберіть валюту", валюти, index=валюти.index("USD") if "USD" in валюти else 0)
df_filtered = df[df["ccy"] == обрана_валюта]

# 🌍 Перейменування колонок
df_filtered = df_filtered.rename(columns={
    "ccy": "Валюта",
    "rateBuy": "Курс купівлі",
    "rateSell": "Курс продажу",
    "Банк": "Банк"
})

# 🌟 Найкращі курси
best_buy = df_filtered["Курс купівлі"].max()
best_sell = df_filtered["Курс продажу"].min()

def highlight_best(row):
    return [
        "background-color: #d4edda; color: red" if col == "Курс купівлі" and row["Курс купівлі"] == best_buy
        else "background-color: #ffeeba; color: blue" if col == "Курс продажу" and row["Курс продажу"] == best_sell
        else ""
        for col in df_filtered.columns
    ]

# 📈 Таблиця
if not df_filtered.empty:
    st.markdown(f"**💱 Поточна валюта:** `{обрана_валюта}`")
    st.dataframe(df_filtered.style.apply(highlight_best, axis=1), use_container_width=True)
else:
    st.warning("Немає даних для вибраної валюти.")

# 🧾 Лог файли
if os.path.exists("api_errors.log"):
    with open("api_errors.log", "r") as log_file:
        st.expander("📋 Лог помилок API").write(log_file.read())
else:
    st.caption("Лог-файл ще не створено або помилок не було 🎉")

# ℹ️ Інфо
with st.expander("ℹ️ Про застосунок"):
    st.markdown("""
    Цей дашборд показує актуальні **курси валют USD, EUR, тощо** з Monobank і PrivatBank в Україні 📈  
    Дані автоматично оновлюються **кожні 5 хвилин**, з підсвіткою найкращих курсів 💡  
    [GitHub репозиторій](https://github.com/autoleg13i)  
    """)