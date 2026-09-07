import csv
import datetime
import os
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from google_play_scraper import app as gp_app
from itunes_app_scraper.scraper import AppStoreScraper


APPS = {
    "Paritetbank (iParitet)": {
        "play_id": "by.iparitet", 
        "apple_id": "1543156711"
    },
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
    "Alfa-Bank (INSNC)": {
        "play_id": "by.alfabank.app.insnc3", 
        "apple_id": None
    },
}

CSV_FILE = "banking_apps_history.csv"
CURRENT_DATE = datetime.date.today().strftime("%Y-%m-%d")
DASHBOARD_FILE = f"dashboard_{CURRENT_DATE}.png"


def collect_store_data():
    """Сбор текущих срезов и точной детализации оценок (только Google Play)."""
    apple_scraper = AppStoreScraper()
    parsed_rows = []

    print(
        f"Сбор данных и детальной структуры оценок на дату: {CURRENT_DATE}"
    )

    for bank, ids in APPS.items():
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

        total_1 = p1
        total_2 = p2
        total_3 = p3
        total_4 = p4
        total_5 = p5

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
    """Генерация графиков в точном соответствии с исходным визуальным стилем."""
    if not os.path.isfile(CSV_FILE):
        print(f"[Ошибка] Файл {CSV_FILE} не найден. Нечего визуализировать.")
        return

    df = pd.read_csv(CSV_FILE)
    
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date")
    df["Date_Str"] = df["Date"].dt.strftime("%Y-%m-%d")

    df = df.drop_duplicates(subset=["Date_Str", "Bank"], keep="last")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7))
    fig.suptitle(f"Отчет по мобильным приложениям (Срез {CURRENT_DATE})", fontsize=14, weight="bold")

    
    ax1.set_title("1. Динамика общих рейтингов розничных приложений", fontsize=11, weight="bold", pad=10)
    
    for bank in APPS.keys():
        bank_df = df[df["Bank"] == bank]
        if not bank_df.empty:
            ax1.plot(
                bank_df["Date_Str"], 
                bank_df["Rating"], 
                marker="o", 
                linewidth=1.8, 
                markersize=5, 
                label=bank
            )
            
    ax1.set_ylim(2.0, 5.1)
    ax1.set_ylabel("Средний балл приложения", fontsize=10)
    ax1.set_xlabel("Дата еженедельного среза", fontsize=10)
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.legend(loc="lower left", fontsize=8)

    
    ax2.set_title(f"2. Детализация структуры оценок (Срез на {CURRENT_DATE})", fontsize=11, weight="bold", pad=10)
    
    latest_date_str = df["Date_Str"].max()
    df_latest = df[df["Date_Str"] == latest_date_str].set_index("Bank")
    
    stars_columns = ["1_Star", "2_Star", "3_Star", "4_Star", "5_Star"]
    stars_labels = ["1★", "2★", "3★", "4★", "5★"]
    colors = ["#e74c3c", "#e67e22", "#f1c40f", "#3498db", "#2ecc71"] 

    existing_banks = [b for b in APPS.keys() if b in df_latest.index]
    df_stars = df_latest.loc[existing_banks, stars_columns]

    df_stars.plot(
        kind="bar",
        ax=ax2,
        color=colors,
        edgecolor="darkgray",
        linewidth=0.5,
        width=0.8,
        rot=15
    )
    
    ax2.set_yscale("log")
    ax2.set_ylabel("Количество выставленных оценок (Log scale)", fontsize=10)
    ax2.set_xlabel("", fontsize=10)
    ax2.grid(True, which="both", linestyle="--", alpha=0.3)
    
    plt.setp(ax2.get_xticklabels(), ha="right", fontsize=9)
    
    ax2.legend(
        stars_labels,
        title="Звезды",
        bbox_to_anchor=(1.02, 1),
        loc="upper left",
        fontsize=9
    )


    plt.tight_layout()
    plt.savefig(DASHBOARD_FILE, dpi=150)
    plt.close()

    print(f"[Успешно] Комплексный архивный дашборд сохранен как '{DASHBOARD_FILE}'")




if __name__ == "__main__":
    collect_store_data()
    generate_report_and_visualization()
    print("\n[Выполнение завершено] Данные и дашборд успешно заархивированы.")
