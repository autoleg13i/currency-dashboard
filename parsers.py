# parsers.py

def parse_monobank(data_raw):
    """
    Парсинг відповіді Monobank API.
    Повертає список курсів USD, EUR і BTC по відношенню до гривні.
    """
    codes = {
        840: "USD",
        978: "EUR",
        980: "UAH",
        10000: "BTC"  # внутрішній код Mono для біткоїна
    }

    targets = [(840, 980), (978, 980), (10000, 980)]  # USD/UAH, EUR/UAH, BTC/UAH
    result = []

    for item in data_raw:
        if (item["currencyCodeA"], item["currencyCodeB"]) in targets:
            currency = codes.get(item["currencyCodeA"], str(item["currencyCodeA"]))
            result.append({
                "ccy": currency,
                "rateBuy": round(item.get("rateBuy", 0), 2),
                "rateSell": round(item.get("rateSell", 0), 2)
            })
    return result


def parse_privatbank(data_raw):
    """
    Парсинг відповіді PrivatBank API.
    Повертає список курсів USD, EUR і BTC по відношенню до гривні.
    """
    target_ccy = ["USD", "EUR", "BTC"]
    result = []

    for item in data_raw:
        if item.get("ccy") in target_ccy:
            try:
                result.append({
                    "ccy": item["ccy"],
                    "rateBuy": round(float(item["buy"]), 2),
                    "rateSell": round(float(item["sale"]), 2)
                })
            except (KeyError, ValueError):
                continue
    return result