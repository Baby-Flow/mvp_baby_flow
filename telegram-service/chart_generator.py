import matplotlib
matplotlib.use('Agg')  # Для работы без GUI
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import io
import base64
from typing import List, Dict


def create_sleep_chart(daily_data: List[Dict]) -> bytes:
    """Создает график сна за неделю"""
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(10, 6))

    dates = []
    hours = []

    for day in daily_data:
        date = datetime.fromisoformat(day['date'])
        dates.append(date)
        hours.append(day['sleep']['total_hours'])

    ax.bar(dates, hours, color='#6B5B95', alpha=0.7, edgecolor='#4B3B65', linewidth=2)

    # Настройка осей
    ax.set_xlabel('Дата', fontsize=12, fontweight='bold')
    ax.set_ylabel('Часы сна', fontsize=12, fontweight='bold')
    ax.set_title('Сон за неделю', fontsize=14, fontweight='bold', pad=20)

    # Форматирование дат
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
    ax.xaxis.set_major_locator(mdates.DayLocator())
    fig.autofmt_xdate()

    # Добавление сетки
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)

    # Добавление значений на столбцы
    for i, (date, hour) in enumerate(zip(dates, hours)):
        ax.text(date, hour + 0.1, f'{hour:.1f}ч', ha='center', va='bottom', fontsize=10)

    # Сохранение в байты
    buffer = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
    buffer.seek(0)
    chart_bytes = buffer.getvalue()
    plt.close()

    return chart_bytes


def create_feeding_chart(daily_data: List[Dict]) -> bytes:
    """Создает график кормлений за неделю"""
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

    dates = []
    counts = []
    volumes = []

    for day in daily_data:
        date = datetime.fromisoformat(day['date'])
        dates.append(date)
        counts.append(day['feeding']['count'])
        volumes.append(day['feeding']['total_ml'] or 0)

    # График количества кормлений
    ax1.plot(dates, counts, marker='o', color='#FF6B6B', linewidth=2, markersize=8)
    ax1.fill_between(dates, counts, alpha=0.3, color='#FF6B6B')
    ax1.set_ylabel('Количество кормлений', fontsize=12, fontweight='bold')
    ax1.set_title('Кормления за неделю', fontsize=14, fontweight='bold', pad=20)
    ax1.grid(True, alpha=0.3, linestyle='--')
    ax1.set_axisbelow(True)

    # Добавление значений
    for date, count in zip(dates, counts):
        ax1.text(date, count + 0.2, str(count), ha='center', va='bottom', fontsize=10)

    # График объема
    ax2.bar(dates, volumes, color='#4ECDC4', alpha=0.7, edgecolor='#3EADA4', linewidth=2)
    ax2.set_xlabel('Дата', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Объем (мл)', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3, linestyle='--')
    ax2.set_axisbelow(True)

    # Добавление значений
    for date, vol in zip(dates, volumes):
        if vol > 0:
            ax2.text(date, vol + 10, f'{int(vol)}мл', ha='center', va='bottom', fontsize=10)

    # Форматирование дат
    for ax in [ax1, ax2]:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
        ax.xaxis.set_major_locator(mdates.DayLocator())

    fig.autofmt_xdate()

    # Сохранение в байты
    buffer = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
    buffer.seek(0)
    chart_bytes = buffer.getvalue()
    plt.close()

    return chart_bytes


def create_activity_summary_chart(stats_data: Dict) -> bytes:
    """Создает круговую диаграмму с общей статистикой"""
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))

    # Сон - среднее время
    sleep_data = [stats_data['sleep']['avg_duration_hours'],
                  24 - stats_data['sleep']['avg_duration_hours']]
    colors1 = ['#6B5B95', '#E8E8E8']
    ax1.pie(sleep_data, labels=['Сон', 'Бодрствование'], colors=colors1,
            autopct='%1.1f%%', startangle=90)
    ax1.set_title('Средний сон в день', fontsize=12, fontweight='bold')

    # Типы кормления
    if stats_data['feeding']['by_type']:
        feeding_types = list(stats_data['feeding']['by_type'].keys())
        feeding_values = list(stats_data['feeding']['by_type'].values())
        colors2 = ['#FF6B6B', '#FFB6C1', '#FFA07A', '#FFD700']
        ax2.pie(feeding_values, labels=feeding_types, colors=colors2[:len(feeding_types)],
                autopct='%1.0f', startangle=90)
        ax2.set_title('Типы кормления', fontsize=12, fontweight='bold')
    else:
        ax2.text(0.5, 0.5, 'Нет данных', ha='center', va='center', fontsize=14)
        ax2.set_xlim(0, 1)
        ax2.set_ylim(0, 1)
        ax2.axis('off')

    # Подгузники по типам
    if stats_data['diapers']['by_type']:
        diaper_types = list(stats_data['diapers']['by_type'].keys())
        diaper_values = list(stats_data['diapers']['by_type'].values())
        colors3 = ['#4ECDC4', '#95E1D3', '#A8E6CF']
        ax3.pie(diaper_values, labels=diaper_types, colors=colors3[:len(diaper_types)],
                autopct='%1.0f', startangle=90)
        ax3.set_title('Типы подгузников', fontsize=12, fontweight='bold')
    else:
        ax3.text(0.5, 0.5, 'Нет данных', ha='center', va='center', fontsize=14)
        ax3.set_xlim(0, 1)
        ax3.set_ylim(0, 1)
        ax3.axis('off')

    # Общая статистика - столбчатая диаграмма
    categories = ['Сон\n(раз)', 'Кормления', 'Прогулки', 'Подгузники']
    values = [
        stats_data['sleep']['count'],
        stats_data['feeding']['count'],
        stats_data['walks']['count'],
        stats_data['diapers']['count']
    ]
    colors4 = ['#6B5B95', '#FF6B6B', '#FFA500', '#4ECDC4']
    bars = ax4.bar(categories, values, color=colors4, alpha=0.7, edgecolor='black', linewidth=1)
    ax4.set_ylabel('Количество', fontsize=12, fontweight='bold')
    ax4.set_title('Активности за неделю', fontsize=12, fontweight='bold')
    ax4.grid(True, alpha=0.3, axis='y', linestyle='--')
    ax4.set_axisbelow(True)

    # Добавление значений на столбцы
    for bar, value in zip(bars, values):
        ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                str(value), ha='center', va='bottom', fontsize=10)

    plt.suptitle('Недельная статистика малыша', fontsize=16, fontweight='bold', y=1.02)

    # Сохранение в байты
    buffer = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
    buffer.seek(0)
    chart_bytes = buffer.getvalue()
    plt.close()

    return chart_bytes