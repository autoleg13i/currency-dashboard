import requests
import streamlit as st
import datetime
import logging

# 🔐 Налаштування логування
logging.basicConfig(filename="api_errors.log", level=logging.WARNING)

@st.cache_data(ttl=300)
def get_monobank_data():
    try:
        res = requests.get("https://api.monobank.ua/bank/currency", timeout=5)
        res.raise_for_status()
        return {"provider": "Monobank", "data": res.json(), "timestamp": datetime.datetime.now()}
    except requests.exceptions.RequestException as e:
        logging.warning(f"[{datetime.datetime.now()}] Monobank API failed: {e}")
        return {"provider": "Monobank", "data": None, "error": str(e)}

@st.cache_data(ttl=300)
def get_privatbank_data():
    try:
        res = requests.get("https://api.privatbank.ua/p24api/pubinfo?exchange&coursid=5", timeout=5)
        res.raise_for_status()
        return {"provider": "PrivatBank", "data": res.json(), "timestamp": datetime.datetime.now()}
    except requests.exceptions.RequestException as e:
        logging.warning(f"[{datetime.datetime.now()}] PrivatBank API failed: {e}")
        return {"provider": "PrivatBank", "data": None, "error": str(e)}