import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
import streamlit as st

from parsers import parse_kurs, parse_monobank, parse_privatbank, parse_pumb

KYIV = ZoneInfo("Europe/Kyiv")
CACHE_TTL = 300  # 5 хвилин: Monobank дозволяє приблизно 1 запит на 5 хв

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Accept-Language": "uk-UA,uk;q=0.9",
}

logger = logging.getLogger(__name__)


def _get(url, headers=None):
    res = requests.get(url, headers={**HEADERS, **(headers or {})}, timeout=10)
    res.raise_for_status()
    return res


# Кешовані функції кидають виняток при помилці: Streamlit не кешує винятки,
# тож невдала відповідь не "застрягне" в кеші на 5 хвилин.
@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def _fetch_monobank():
    return _get("https://api.monobank.ua/bank/currency").json(), datetime.now(KYIV)


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def _fetch_privatbank():
    url = "https://api.privatbank.ua/p24api/pubinfo?exchange&json&coursid=5"
    return _get(url).json(), datetime.now(KYIV)


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def _fetch_pumb():
    return _get("https://about.pumb.ua/info/currency_converter").text, datetime.now(KYIV)


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def _fetch_kurs(org_id):
    """Готівкові курси банку з агрегатора kurs.com.ua (id банку в їхньому каталозі)."""
    url = f"https://kurs.com.ua/ajax/organization/cash?currency_from=usd&organizations={org_id}"
    headers = {"X-Requested-With": "XMLHttpRequest", "Referer": "https://kurs.com.ua/"}
    return _get(url, headers).json(), datetime.now(KYIV)


# Назва банку → (функція завантаження, парсер)
SOURCES = {
    "Monobank": (_fetch_monobank, parse_monobank),
    "PrivatBank": (_fetch_privatbank, parse_privatbank),
    "ПУМБ": (_fetch_pumb, parse_pumb),
    "Райффайзен": (lambda: _fetch_kurs(98), parse_kurs),
    "Укргазбанк": (lambda: _fetch_kurs(122), parse_kurs),
}


def load_bank(bank):
    """Повертає (список курсів, час завантаження) або (None, None), якщо банк недоступний."""
    fetch, parse = SOURCES[bank]
    try:
        raw, fetched_at = fetch()
        rows = parse(raw)
        if not rows:
            raise ValueError("курси не знайдено у відповіді")
        for r in rows:
            r["updated"] = r["updated"] or fetched_at
        return rows, fetched_at
    except Exception as e:
        logger.warning("%s failed: %s", bank, e)
        return None, None


def clear_cache():
    for fn in (_fetch_monobank, _fetch_privatbank, _fetch_pumb, _fetch_kurs):
        fn.clear()
