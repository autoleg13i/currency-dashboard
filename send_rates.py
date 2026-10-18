"""Щоденна розсилка курсів валют поштою (запускається з GitHub Actions).

Змінні оточення (задаються в Settings → Secrets and variables → Actions):
  GMAIL_USER          — адреса Gmail, з якої йде лист
  GMAIL_APP_PASSWORD  — пароль застосунку Gmail (16 символів), НЕ основний пароль
  MAIL_TO             — одержувачі через кому
  TELEGRAM_TOKEN      — токен Telegram-бота (необов'язково)
  TELEGRAM_CHAT_ID    — chat id одержувачів через кому (необов'язково)
"""

import html
import os
import smtplib
import sys
from datetime import datetime
from email.message import EmailMessage
from zoneinfo import ZoneInfo

import requests

from parsers import parse_kurs, parse_monobank, parse_privatbank, parse_pumb

KYIV = ZoneInfo("Europe/Kyiv")
DASHBOARD_URL = "https://currency-dashboard-fqthyr7kw4y82avgaqnp9o.streamlit.app/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Accept-Language": "uk-UA,uk;q=0.9",
}
KURS_HEADERS = {"X-Requested-With": "XMLHttpRequest", "Referer": "https://kurs.com.ua/"}
KURS_URL = "https://kurs.com.ua/ajax/organization/cash?currency_from=usd&organizations={}"

# Назва банку → (URL, як читати відповідь, парсер, додаткові заголовки)
SOURCES = {
    "Monobank": ("https://api.monobank.ua/bank/currency", "json", parse_monobank, {}),
    "PrivatBank": ("https://api.privatbank.ua/p24api/pubinfo?exchange&json&coursid=5",
                   "json", parse_privatbank, {}),
    "ПУМБ": ("https://about.pumb.ua/info/currency_converter", "text", parse_pumb, {}),
    "Райффайзен": (KURS_URL.format(98), "json", parse_kurs, KURS_HEADERS),
    "Укргазбанк": (KURS_URL.format(122), "json", parse_kurs, KURS_HEADERS),
    "Кредобанк": (KURS_URL.format(146), "json", parse_kurs, KURS_HEADERS),
}


def is_send_time():
    """GitHub запускає за UTC, а Київ живе то за UTC+3 (літо), то за UTC+2 (зима).
    Розклад має два запуски; надсилаємо лише той, що припадає на ~10:00 за Києвом."""
    if os.environ.get("GITHUB_EVENT_NAME") != "schedule":
        return True  # ручний запуск — надсилаємо завжди
    cron_hour_utc = int(os.environ.get("CRON_SCHEDULE", "").split()[1])
    offset = datetime.now(KYIV).utcoffset().total_seconds() / 3600
    return (cron_hour_utc + offset) % 24 == 9  # 9:58 за Києвом + затримка GitHub ≈ 10:00


def load_rates():
    now = datetime.now(KYIV)
    rows, failed = [], []
    for bank, (url, kind, parse, headers) in SOURCES.items():
        try:
            res = requests.get(url, headers={**HEADERS, **headers}, timeout=20)
            res.raise_for_status()
            parsed = parse(res.json() if kind == "json" else res.text)
            if not parsed:
                raise ValueError("курси не знайдено")
            rows += [{"bank": bank, **r, "updated": r["updated"] or now} for r in parsed]
        except Exception as e:
            print(f"{bank}: {e}", file=sys.stderr)
            failed.append(bank)
    return rows, failed


def currency_table(rows, ccy):
    data = sorted((r for r in rows if r["ccy"] == ccy), key=lambda r: r["rateSell"])
    if not data:
        return "", ""
    best_buy = max(r["rateBuy"] for r in data)
    best_sell = min(r["rateSell"] for r in data)
    good = "background:#d9f2e0;font-weight:600"
    cell = "padding:6px 12px;border-bottom:1px solid #e5e5e5"

    html_rows = "".join(
        f"<tr><td style='{cell}'>{r['bank']}</td>"
        f"<td style='{cell};text-align:right;{good if r['rateBuy'] == best_buy else ''}'>{r['rateBuy']:.2f}</td>"
        f"<td style='{cell};text-align:right;{good if r['rateSell'] == best_sell else ''}'>{r['rateSell']:.2f}</td>"
        f"<td style='{cell};color:#888'>{r['updated']:%d.%m %H:%M}</td></tr>"
        for r in data
    )
    head = "".join(f"<th style='{cell};text-align:left;color:#555'>{h}</th>"
                   for h in ("Банк", "Купівля", "Продаж", "Оновлено"))
    seller = next(r["bank"] for r in data if r["rateSell"] == best_sell)
    buyer = next(r["bank"] for r in data if r["rateBuy"] == best_buy)
    html = (
        f"<h3 style='margin:24px 0 4px'>{ccy}</h3>"
        f"<p style='margin:0 0 8px;color:#333'>Купити найдешевше: <b>{best_sell:.2f} ₴</b> ({seller}) · "
        f"продати найдорожче: <b>{best_buy:.2f} ₴</b> ({buyer})</p>"
        f"<table style='border-collapse:collapse;font-size:14px'><tr>{head}</tr>{html_rows}</table>"
    )
    text = f"\n{ccy}: купити {best_sell:.2f} ({seller}), продати {best_buy:.2f} ({buyer})\n" + "".join(
        f"  {r['bank']:<12} {r['rateBuy']:>7.2f} / {r['rateSell']:<7.2f}  ({r['updated']:%d.%m %H:%M})\n"
        for r in data
    )
    return html, text


def build_message(rows, failed, sender, recipients):
    today = datetime.now(KYIV)
    parts = [currency_table(rows, c) for c in ("USD", "EUR")]
    note = f"<p style='color:#a15c00'>Не вдалося отримати: {', '.join(failed)}</p>" if failed else ""
    html = (
        "<div style='font-family:-apple-system,Segoe UI,Arial,sans-serif;max-width:560px'>"
        f"<h2 style='margin:0'>💱 Курси валют на {today:%d.%m.%Y}</h2>"
        f"<p style='color:#888;margin:4px 0 0'>Станом на {today:%H:%M} за Києвом. "
        "Зеленим — найвигідніший курс.</p>"
        + "".join(p[0] for p in parts) + note +
        f"<p style='margin-top:24px'><a href='{DASHBOARD_URL}'>Відкрити дашборд</a></p></div>"
    )
    text = f"Курси валют на {today:%d.%m.%Y} ({today:%H:%M})\n" + "".join(p[1] for p in parts)
    if failed:
        text += f"\nНе вдалося отримати: {', '.join(failed)}\n"
    text += f"\n{DASHBOARD_URL}\n"

    msg = EmailMessage()
    msg["Subject"] = f"💱 Курси валют на {today:%d.%m.%Y}"
    msg["From"] = f"Курси валют <{sender}>"
    msg["To"] = ", ".join(recipients)
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")
    return msg


def build_telegram(rows, failed):
    """Коротке повідомлення для Telegram: найкращі курси + компактна таблиця."""
    today = datetime.now(KYIV)
    lines = [f"💱 <b>Курси валют на {today:%d.%m.%Y}</b> ({today:%H:%M})"]
    for ccy in ("USD", "EUR"):
        data = sorted((r for r in rows if r["ccy"] == ccy), key=lambda r: r["rateSell"])
        if not data:
            continue
        best_buy = max(r["rateBuy"] for r in data)
        best_sell = min(r["rateSell"] for r in data)
        seller = next(r["bank"] for r in data if r["rateSell"] == best_sell)
        buyer = next(r["bank"] for r in data if r["rateBuy"] == best_buy)
        table = "\n".join(
            f"{r['bank']:<11}{r['rateBuy']:>6.2f} {r['rateSell']:>6.2f}"
            + ("  ⏱" + f"{r['updated']:%d.%m}" if r["updated"].date() != today.date() else "")
            for r in data
        )
        lines.append(
            f"\n<b>{ccy}</b>\n"
            f"🟢 Купити: <b>{best_sell:.2f}</b> — {html.escape(seller)}\n"
            f"🟢 Продати: <b>{best_buy:.2f}</b> — {html.escape(buyer)}\n"
            f"<pre>{'Банк':<11}{'Куп.':>6} {'Прод.':>6}\n{html.escape(table)}</pre>"
        )
    if failed:
        lines.append(f"⚠️ Не вдалося отримати: {html.escape(', '.join(failed))}")
    lines.append(f'<a href="{DASHBOARD_URL}">Відкрити дашборд</a>')
    return "\n".join(lines)


def send_email(rows, failed):
    sender = os.environ["GMAIL_USER"]
    recipients = [a.strip() for a in os.environ["MAIL_TO"].split(",") if a.strip()]
    msg = build_message(rows, failed, sender, recipients)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sender, os.environ["GMAIL_APP_PASSWORD"])
        smtp.send_message(msg)
    return f"пошта: {len(recipients)} одержувачів"


def send_telegram(rows, failed):
    token = os.environ["TELEGRAM_TOKEN"]
    chats = [c.strip() for c in os.environ["TELEGRAM_CHAT_ID"].split(",") if c.strip()]
    text = build_telegram(rows, failed)
    for chat in chats:
        res = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": text, "parse_mode": "HTML",
                  "disable_web_page_preview": True},
            timeout=20,
        )
        if not res.ok:
            raise RuntimeError(f"Telegram {res.status_code}: {res.json().get('description')}")
    return f"Telegram: {len(chats)} чат(и)"


def main():
    if not is_send_time():
        print("Не той запуск для поточного часового поясу — пропускаю.")
        return
    rows, failed = load_rates()
    if not rows:
        sys.exit("Жоден банк не відповів — нічого не надіслано.")

    # Кожен канал вмикається, лише якщо для нього задано секрети; збій одного не зупиняє інший.
    channels = []
    if os.environ.get("GMAIL_APP_PASSWORD"):
        channels.append(send_email)
    if os.environ.get("TELEGRAM_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"):
        channels.append(send_telegram)
    if not channels:
        sys.exit("Не задано жодного каналу (пошта чи Telegram).")

    errors = []
    for send in channels:
        try:
            print("Надіслано —", send(rows, failed))
        except Exception as e:
            print(f"{send.__name__}: {e}", file=sys.stderr)
            errors.append(send.__name__)
    print(f"Банків: {len(SOURCES) - len(failed)}/{len(SOURCES)}")
    if errors:
        sys.exit("Не вдалося: " + ", ".join(errors))


if __name__ == "__main__":
    main()
