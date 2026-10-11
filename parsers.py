# parsers.py
# Кожен парсер повертає список {"ccy", "rateBuy", "rateSell", "updated"},
# де updated — datetime останнього оновлення курсу банком (або None, якщо невідомо).

import re
from datetime import datetime

TARGET = ("USD", "EUR")


def parse_monobank(data_raw):
    """Monobank API: валютні пари задані ISO-кодами (840 USD, 978 EUR, 980 UAH)."""
    codes = {840: "USD", 978: "EUR"}
    result = []
    for item in data_raw:
        ccy = codes.get(item.get("currencyCodeA"))
        if ccy and item.get("currencyCodeB") == 980 and item.get("rateBuy"):
            result.append({
                "ccy": ccy,
                "rateBuy": round(item["rateBuy"], 2),
                "rateSell": round(item["rateSell"], 2),
                "updated": None,
            })
    return result


def parse_privatbank(data_raw):
    """PrivatBank API: курси в касах банку (coursid=5)."""
    result = []
    for item in data_raw:
        if item.get("ccy") in TARGET:
            try:
                result.append({
                    "ccy": item["ccy"],
                    "rateBuy": round(float(item["buy"]), 2),
                    "rateSell": round(float(item["sale"]), 2),
                    "updated": None,
                })
            except (KeyError, ValueError):
                continue
    return result


def parse_pumb(html):
    """Сторінка курсів ПУМБ: перша таблиця з атрибутами data-currency-USDBuy тощо."""
    result = []
    for ccy in TARGET:
        buy = re.search(rf"data-currency-{ccy}Buy[^>]*>\s*([\d.,]+)", html)
        sell = re.search(rf"data-currency-{ccy}Sell[^>]*>\s*([\d.,]+)", html)
        if buy and sell:
            result.append({
                "ccy": ccy,
                "rateBuy": round(float(buy.group(1).replace(",", ".")), 2),
                "rateSell": round(float(sell.group(1).replace(",", ".")), 2),
                "updated": None,
            })
    return result


def parse_kurs(data_raw):
    """kurs.com.ua: JSON, у якому view.default — HTML-рядки таблиці готівкових курсів банку."""
    html = (data_raw.get("view") or {}).get("default", "")
    result = []
    for row in html.split("<tr")[1:]:
        ccy = re.search(r"valyuta/([a-z]+)", row)
        if not ccy or ccy.group(1).upper() not in TARGET:
            continue
        values = re.findall(r'class="value">\s*([\d,.]+)', row)
        if len(values) < 2:
            continue
        stamp = re.search(r'title="(\d{4}-\d\d-\d\d \d\d:\d\d)"', row)
        result.append({
            "ccy": ccy.group(1).upper(),
            "rateBuy": round(float(values[0].replace(",", ".")), 2),
            "rateSell": round(float(values[1].replace(",", ".")), 2),
            "updated": datetime.strptime(stamp.group(1), "%Y-%m-%d %H:%M") if stamp else None,
        })
    return result
