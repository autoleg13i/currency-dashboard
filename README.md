# 💱 Курси валют від українських банків

[![Streamlit App](https://img.shields.io/badge/Streamlit-Live_App-success?logo=streamlit&labelColor=gray&color=brightgreen)](https://currency-dashboard.streamlit.app)
[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-lightgray.svg)](LICENSE)

> 📊 Інтерактивний дашборд для моніторингу курсів валют USD, EUR, BTC в Monobank і PrivatBank — з автооновленням і підсвіткою найвигідніших курсів.

---

## 🔍 Можливості

- 📡 Підключення до API Monobank та PrivatBank
- 🎛️ Динамічний фільтр за валютою
- ⏱️ Автоматичне оновлення кожні 5 хвилин з таймером і прогрес-баром
- 🟢 Підсвітка найкращого курсу купівлі (зелений фон, червоний шрифт)
- 🟡 Підсвітка найкращого курсу продажу (жовтий фон, синій шрифт)
- 🔘 Кнопка “Оновити зараз” для миттєвого ререндеру
- 📋 Виведення журналу API-помилок (якщо наявні)

---

## 🚀 Як запустити локально

```bash
git clone https://github.com/autoleg13i/currency-dashboard.git
cd currency-dashboard
pip install -r requirements.txt
streamlit run app.py

![Dashboard Screenshot](images/screenshot.png)

## 🌐 Онлайн-версія

Застосунок доступний тут:  
🔗 [currency-dashboard.streamlit.app](https://currency-dashboard.streamlit.app)

## 👤 Автор

Створено [Олегом (autoleg13i)](https://github.com/autoleg13i)  
💻 Python + Streamlit  
☁️ Хостинг: Streamlit Cloud  
📦 API: Monobank, PrivatBank