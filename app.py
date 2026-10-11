import time
from datetime import datetime

import pandas as pd
import streamlit as st

from currency_utils import KYIV, CACHE_TTL, clear_cache, get_monobank_data, get_privatbank_data
from parsers import parse_monobank, parse_privatbank

st.set_page_config(page_title="Курси валют", page_icon="💱")

CURRENCIES = ["USD", "EUR"]
SOURCES = [
    ("Monobank", get_monobank_data, parse_monobank),
    ("PrivatBank", get_privatbank_data, parse_privatbank),
]
MANUAL_REFRESH_COOLDOWN = 60  # сек між натисканнями «Оновити зараз»
BEST_STYLE = "background-color: rgba(46, 160, 67, 0.25); font-weight: 600"

st.title("💱 Курси валют від банків України")

currency = st.radio("Валюта", CURRENCIES, horizontal=True)


def load_rates():
    """Повертає (DataFrame з курсами, список недоступних банків, час отримання даних)."""
    rows, failed, timestamps = [], [], []
    for bank, fetch, parse in SOURCES:
        result = fetch()
        if not result["data"]:
            failed.append(bank)
            continue
        try:
            parsed = parse(result["data"])
        except Exception:
            failed.append(bank)
            continue
        timestamps.append(result["timestamp"])
        rows += [{"Банк": bank, **r} for r in parsed]
    df = pd.DataFrame(rows, columns=["Банк", "ccy", "rateBuy", "rateSell"])
    return df, failed, (min(timestamps) if timestamps else None)


@st.fragment(run_every=CACHE_TTL)
def rates_block(currency):
    df, failed, fetched_at = load_rates()

    col_time, col_btn = st.columns([3, 1], vertical_alignment="center")
    if fetched_at:
        col_time.caption(f"🕒 Оновлено о {fetched_at:%H:%M} · автооновлення кожні 5 хв")

    last = st.session_state.get("last_manual_refresh", 0)
    wait = int(MANUAL_REFRESH_COOLDOWN - (time.time() - last))
    if col_btn.button("🔄 Оновити", width="stretch", disabled=wait > 0,
                      help=f"Можна оновити через {wait} с" if wait > 0 else None):
        st.session_state.last_manual_refresh = time.time()
        clear_cache()
        st.rerun()

    for bank in failed if len(failed) < len(SOURCES) else []:
        st.warning(f"{bank} тимчасово не відповідає — показуємо дані інших банків.")

    data = df[df["ccy"] == currency].drop(columns="ccy")
    data = data[(data["rateBuy"] > 0) & (data["rateSell"] > 0)]
    if data.empty:
        st.error("Не вдалося отримати курси. Спробуйте трохи пізніше.")
        return

    data = data.rename(columns={"rateBuy": "Купівля", "rateSell": "Продаж"})
    data["Спред"] = data["Продаж"] - data["Купівля"]
    data = data.sort_values("Продаж").reset_index(drop=True)

    best_buy_row = data.loc[data["Купівля"].idxmax()]
    best_sell_row = data.loc[data["Продаж"].idxmin()]

    m1, m2 = st.columns(2)
    m1.metric(f"Купити {currency} найдешевше", f"{best_sell_row['Продаж']:.2f} ₴",
              best_sell_row["Банк"], delta_color="off")
    m2.metric(f"Продати {currency} найдорожче", f"{best_buy_row['Купівля']:.2f} ₴",
              best_buy_row["Банк"], delta_color="off")

    def highlight(col):
        if col.name == "Купівля":
            return [BEST_STYLE if v == col.max() else "" for v in col]
        if col.name == "Продаж":
            return [BEST_STYLE if v == col.min() else "" for v in col]
        return [""] * len(col)

    styled = data.style.apply(highlight).format(
        {"Купівля": "{:.2f}", "Продаж": "{:.2f}", "Спред": "{:.2f}"}
    )
    st.dataframe(styled, hide_index=True, width="stretch")
    st.caption("🟢 — найвигідніший курс. Купівля — за скільки банк купує валюту у вас, "
               "продаж — за скільки продає вам.")

    st.subheader("Конвертер")
    c1, c2 = st.columns(2)
    amount = c1.number_input(f"Сума, {currency}", min_value=0.0, value=1000.0, step=100.0)
    action = c2.radio("Що робите?", ["Купую", "Продаю"], horizontal=True)
    rate_col = "Продаж" if action == "Купую" else "Купівля"
    conv = data[["Банк", rate_col]].copy()
    conv["Сума, ₴"] = conv[rate_col] * amount
    conv = conv.sort_values("Сума, ₴", ascending=(action == "Купую"))
    verb = "заплатите" if action == "Купую" else "отримаєте"
    for i, r in enumerate(conv.itertuples(index=False)):
        mark = "🟢 " if i == 0 else ""
        st.markdown(f"{mark}**{r[0]}**: {verb} **{r[2]:,.2f} ₴**".replace(",", " "))
    if len(conv) > 1:
        diff = abs(conv["Сума, ₴"].iloc[-1] - conv["Сума, ₴"].iloc[0])
        st.caption(f"Різниця між банками: {diff:,.2f} ₴".replace(",", " "))


rates_block(currency)

with st.expander("ℹ️ Про застосунок"):
    st.markdown(
        "Дашборд порівнює курси **USD** і **EUR** у Monobank та PrivatBank і підсвічує "
        "найвигідніші. Дані оновлюються автоматично кожні 5 хвилин.  \n"
        "[Код на GitHub](https://github.com/autoleg13i/currency-dashboard)"
    )
