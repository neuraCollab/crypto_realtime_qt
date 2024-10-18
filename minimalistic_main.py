import os
import json
import requests
from datetime import datetime
from time import sleep

# Константы
API_URL = 'https://api.coingecko.com/api/v3/simple/price'
ASSET_LIST_FILE = 'list.json'
DEFAULT_CURRENCY = 'usd'

# Начальный капитал
INITIAL_CAPITAL = 100
GRID_SIZE = 10  # Разделение капитала на 10 частей
PART_SIZE = INITIAL_CAPITAL / GRID_SIZE  # Размер одной части капитала
investment_positions = []  # Для хранения позиций

# Параметры торговли
BUY_THRESHOLD = 0.02  # Условие покупки: падение цены на 2%
SELL_THRESHOLD = 0.02  # Условие продажи: рост цены на 2%

def load_assets():
    """Загрузить список активов из локального файла JSON или получить его через API."""
    if os.path.exists(ASSET_LIST_FILE):
        with open(ASSET_LIST_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        response = requests.get('https://api.coingecko.com/api/v3/coins/list')
        if response.status_code == 200:
            assets = response.json()
            with open(ASSET_LIST_FILE, 'w', encoding='utf-8') as f:
                json.dump(assets, f)
            return assets
        else:
            print("Ошибка при получении активов из API.")
            return []

def get_current_price(asset_id):
    """Получить текущую цену указанного актива."""
    params = {
        'ids': asset_id,
        'vs_currencies': DEFAULT_CURRENCY
    }
    response = requests.get(API_URL, params=params)
    if response.status_code == 200:
        price_info = response.json()
        return price_info.get(asset_id, {}).get(DEFAULT_CURRENCY)
    else:
        print("Ошибка при получении цены для", asset_id)
        return None

def print_assets(asset_map, columns=3):
    """Вывести доступные активы в несколько колонок."""
    asset_list = list(asset_map.keys())
    num_assets = len(asset_list)

    # Вычисляем количество строк, необходимых для вывода активов
    rows = (num_assets + columns - 1) // columns  # Округляем вверх
    for row in range(rows):
        for col in range(columns):
            index = row + col * rows
            if index < num_assets:
                print(f"{asset_list[index]:<35}", end='')  # Форматируем ширину 30 символов
        print()  # Новая строка после каждой строки активов

def update_trading_status(price):
    global investment_positions

    # Проверка условий покупки
    if len(investment_positions) < GRID_SIZE:  # Проверяем, можно ли купить еще
        if not investment_positions or price < investment_positions[-1]['buy_price'] * (1 - BUY_THRESHOLD):
            investment_positions.append({'buy_price': price, 'amount': PART_SIZE, 'status': 'open'})
            print(f"Куплено: {PART_SIZE}$ на цене {price}. Текущие позиции: {investment_positions}")

    # Проверка условий продажи
    for position in investment_positions:
        if position['status'] == 'open' and price > position['buy_price'] * (1 + SELL_THRESHOLD):
            position['status'] = 'closed'
            print(f"Продано: {position['amount']}$ на цене {price}. Текущие позиции: {investment_positions}")

def main():
    """Основная функция для работы торгового бота."""
    assets = load_assets()
    asset_map = {f"{asset['symbol'].upper()} - {asset['name']}": asset['id'] for asset in assets}

    while True:
        print("Доступные активы:")
        print_assets(asset_map, columns=3)  # Печатаем активы в колонках

        selected_asset = input("Введите актив, который хотите отслеживать (или 'exit' для выхода): ")
        if selected_asset.lower() == 'exit':
            break

        selected_id = asset_map.get(selected_asset)
        if selected_id:
            while True:
                price = get_current_price(selected_id)
                if price is not None:
                    print(f"Текущая цена {selected_asset}: {price} {DEFAULT_CURRENCY}")
                    update_trading_status(price)  # Обновляем статус торговли
                else:
                    print("Не удалось получить цену.")

                sleep(10)  # Обновление каждые 10 секунд
        else:
            print("Неверный выбор актива.")

if __name__ == '__main__':
    main()
