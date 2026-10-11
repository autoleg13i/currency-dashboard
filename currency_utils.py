import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
import streamlit as st

KYIV = ZoneInfo("Europe/Kyiv")
CACHE_TTL = 300  # 5 хвилин: Monobank дозволяє приблизно 1 запит на 5 хв

logger = logging.getLogger(__name__)


# Кешовані функції кидають виняток при помилці: Streamlit не кешує винятки,
# тож невдала відповідь не "застрягне" в кеші на 5 хвилин.
@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def _fetch_monobank():
    res = requests.get("https://api.monobank.ua/bank/currency", timeout=10)
    res.raise_for_status()
    return res.json(), datetime.now(KYIV)


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def _fetch_privatbank():
    res = requests.get(
        "https://api.privatbank.ua/p24api/pubinfo?exchange&json&coursid=5", timeout=10
    )
    res.raise_for_status()
    return res.json(), datetime.now(KYIV)


def _safe(fetch, provider):
    try:
        data, fetched_at = fetch()
        return {"provider": provider, "data": data, "timestamp": fetched_at}
    except Exception as e:
        logger.warning("%s API failed: %s", provider, e)
        return {"provider": provider, "data": None, "error": str(e)}


def get_monobank_data():
    return _safe(_fetch_monobank, "Monobank")


def get_privatbank_data():
    return _safe(_fetch_privatbank, "PrivatBank")


def clear_cache():
    _fetch_monobank.clear()
    _fetch_privatbank.clear()
