import csv
import datetime
import os
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from google_play_scraper import app as gp_app
from itunes_app_scraper.scraper import AppStoreScraper

warnings.filterwarnings("ignore")

# Список банковских приложений для мониторинга
APPS = {
    "Paritetbank (iParitet)": {"play_id": "by.iparitet", "apple_id": "1543156711"},
    "Belarusbank (M-Belarusbank)": {
        "play_id": "com.mobicon.mbank2.belarusbank",
        "apple_id": "549469274",
    },
    "Priorbank (Prior Online)": {
        "play_id": "by.st.priormobile",
        "apple_id": "521143601",
    },
    "MTBank (Moby)": {"play_id": "by.mtbank.Moby", "apple_id": "1534853667"},
    "BNB-Bank (Iskra)": {
        "play_id": "com.iskra.mobile",
        "apple_id": "6480586304",
    },
    "Alfa-Bank (INSNC)": {"play_id": "by.alfabank.app.insnc3", "apple_id": None},
}

CSV_FILE = "banking_apps_history.csv"
CURRENT_DATE = datetime.date.today().strftime("%Y-%m-%d")
DASHBOARD_FILE = f"dashboard_{CURRENT_DATE}.png"


def collect_store_data():
    """Сбор текущих срезов и точной детализации оценок (только Google Play)."""
    apple_scraper = AppStoreScraper()
    parsed_rows = []

    print(
        f"[1/3] Сбор данных и детальной структуры оценок на дату: {CURRENT_DATE}"
    )

    for bank, ids in APPS.items():
        # Инициализируем переменные для Google Play
        play_rating, p1, p2, p3, p4, p5 = None, 0, 0, 0, 0, 0
        try:
            gp_info = gp_app(ids["play_id"], lang="ru", country="by")
            play_rating = gp_info.get("score")
            hist = gp_info.get("histogram")
            if hist and len(hist) == 5:
                p1, p2, p3, p4, p5 = (
                    hist[0],
                    hist[1],
                    hist[2],
                    hist[3],
                    hist[4],
                )
        except Exception as e:
            print(f"  [Ошибка GP] {bank}: {e}")

        # Собираем только средний рейтинг Apple (без симуляции звезд)
        apple_rating = None
        if ids["apple_id"]:
            try:
                ap_info = apple_scraper.get_app_details(
                    ids["apple_id"], country="by"
                )
                if ap_info:
                    apple_rating = ap_info.get("averageUserRating")
            except Exception as e:
                print(f"  [Ошибка AS] {bank}: {e}")

        # Теперь в итоговый реестр идут только реальные оценки из Google Play
        total_1 = p1
        total_2 = p2
        total_3 = p3
        total_4 = p4
        total_5 = p5

        # Вычисляем комбинированный рейтинг (среднее между GP и App Store, если оба доступны)
        if play_rating and apple_rating:
            combined_rating = round((play_rating + apple_rating) / 2, 2)
        else:
            combined_rating = round(play_rating or apple_rating or 0, 2)

        parsed_rows.append(
            [
                CURRENT_DATE,
                bank,
                combined_rating,
                total_1,
                total_2,
                total_3,
                total_4,
                total_5,
            ]
        )

    # Запись результатов в сквозной CSV-файл
    file_exists = os.path.isfile(CSV_FILE)
    with open(CSV_FILE, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(
                [
                    "Date",
                    "Bank",
                    "Rating",
                    "1_Star",
                    "2_Star",
                    "3_Star",
                    "4_Star",
                    "5_Star",
                ]
            )
        writer.writerows(parsed_rows)
    print(f"[Успешно] Текущие данные добавлены в сквозной реестр: {CSV_FILE}")


def generate_report_and_visualization():
    """Чтение истории из CSV и генерация графиков."""
    if not os.path.isfile(CSV_FILE):
        print(f"[Ошибка] Файл {CSV_FILE} не найден. Нечего визуализировать.")
        return

    # Читаем данные
    df = pd.read_csv(CSV_FILE)

    # Берем только самые свежие данные для построения структуры оценок
    latest_date = df["Date"].max()
    df_latest = df[df["Date"] == latest_date]

    # Настройка сетки графиков (1 строка, 2 колонки)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    # График 1: Текущий комбинированный рейтинг банков
    banks = df_latest["Bank"]
    ratings = df_latest["Rating"]
    
    # ИСПРАВЛЕНО: Используем современный способ получения палитры цветов
    colors = plt.colormaps["viridis"](np.linspace(0, 1, len(banks)))

    bars = ax1.barh(banks, ratings, color=colors, edgecolor="black", height=0.6)
    ax1.set_xlim(0, 5.5)
    ax1.set_xlabel("Комбинированный рейтинг (0-5)")
    ax1.set_title(f"Сравнение рейтингов банков на {latest_date}")
    ax1.grid(axis="x", linestyle="--", alpha=0.7)

    # Добавляем подписи со значениями рейтингов на столбцы
    for bar in bars:
        width = bar.get_width()
        ax1.text(
            width + 0.05,
            bar.get_y() + bar.get_height() / 2,
            f"{width:.2f}",
            va="center",
            ha="left",
            fontsize=10,
            weight="bold",
        )

    # График 2: Структура распределения реальных оценок (1-5 звезд из GP)
    stars_columns = ["1_Star", "2_Star", "3_Star", "4_Star", "5_Star"]

    # Переводим абсолютные значения в проценты для наглядности
    df_pct = df_latest.set_index("Bank")[stars_columns]
    df_pct = df_pct.div(df_pct.sum(axis=1), axis=0).fillna(0) * 100

    # ИСПРАВЛЕНО: Заменили height=0.6 на width=0.6, так как для barh в pandas толщина задается через width
    df_pct.plot(
        kind="barh",
        stacked=True,
        ax=ax2,
        color=["#e74c3c", "#e67e22", "#f1c40f", "#3498db", "#2ecc71"],
        edgecolor="black",
        width=0.6,
    )


    ax2.set_xlim(0, 100)
    ax2.set_xlabel("Доля оценок в % (Данные Google Play)")
    ax2.set_title("Структура отзывов (от 1 до 5 звезд)")
    ax2.legend(
        ["1 ⭐", "2 ⭐", "3 ⭐", "4 ⭐", "5 ⭐"],
        bbox_to_anchor=(1.05, 1),
        loc="upper left",
    )
    ax2.grid(axis="x", linestyle="--", alpha=0.7)

    plt.tight_layout()
    plt.savefig(DASHBOARD_FILE, dpi=150)
    plt.close()

    print(
        f"[Успешно] Комплексный архивный дашборд сохранен как '{DASHBOARD_FILE}'"
    )



if __name__ == "__main__":
    collect_store_data()
    generate_report_and_visualization()
    print("\n[Выполнение завершено] Данные и дашборд успешно заархивированы.")
