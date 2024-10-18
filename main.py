import os
import json
from dotenv import load_dotenv
import requests
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QApplication, QMainWindow, QComboBox, QLabel
from PyQt5.QtCore import QTimer
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from datetime import datetime
import matplotlib.dates as mdates

# Load environment variables from .env file
load_dotenv()
API_KEY = os.getenv("API_KEY")
ASSET_LIST_FILE = 'list.json'

# Начальный капитал
INITIAL_CAPITAL = 100
GRID_SIZE = 10  # Разделение капитала на 10 частей
PART_SIZE = INITIAL_CAPITAL / GRID_SIZE  # Размер одной части капитала
investment_positions = []  # Для хранения позиций

# Параметры торговли
BUY_THRESHOLD = 0.02  # Условие покупки: падение цены на 2%
SELL_THRESHOLD = 0.02  # Условие продажи: рост цены на 2%

def get_asset_list():
    if os.path.exists(ASSET_LIST_FILE):
        try:
            with open(ASSET_LIST_FILE, 'r', encoding='utf-8') as f:
                assets = json.load(f)
            print("Загружены данные из локального файла.")
            return assets
        except UnicodeDecodeError:
            print("Ошибка кодировки при чтении локального файла.")
            return []
    else:
        print("Файл не найден. Выполняется запрос к API...")
        url = 'https://api.coingecko.com/api/v3/coins/list'
        response = requests.get(url)
        if response.status_code == 200:
            assets = response.json()
            with open(ASSET_LIST_FILE, 'w', encoding='utf-8') as f:
                json.dump(assets, f)
            print("Данные успешно сохранены в list.json.")
            return assets
        else:
            print("Ошибка при запросе данных.")
            return []

def get_current_price(asset_id, timeout=10, vs_currency='usd'):
    url = 'https://api.coingecko.com/api/v3/simple/price'
    params = {
        'ids': asset_id,
        'vs_currencies': vs_currency
    }
    response = requests.get(url, params=params, timeout=timeout)
    if response.status_code == 200:
        price_info = response.json()
        return price_info.get(asset_id, {}).get(vs_currency, None)
    else:
        return None

class CustomFigCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super(CustomFigCanvas, self).__init__(self.fig)
        self.ax = self.fig.add_subplot(111)
        self.x_data = []
        self.y_data = []
        self.line, = self.ax.plot(self.x_data, self.y_data)

        self.ax.set_xlabel('Время')
        self.ax.set_ylabel('Цена')
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

    def addData(self, x, y):
        self.x_data.append(x)
        self.y_data.append(y)
        self.line.set_data(self.x_data, self.y_data)
        self.ax.relim()
        self.ax.autoscale_view()

        if len(self.y_data) >= 2:
            margin = (self.y_data[-1] - self.y_data[-2]) * 10
            y_min = min(self.y_data[-2:]) - margin
            y_max = max(self.y_data[-2:]) + margin
            self.ax.set_ylim(y_min, y_max)

        self.ax.xaxis_date()
        self.draw()

    def reset_graph(self):
        self.x_data.clear()
        self.y_data.clear()
        self.ax.cla()
        self.ax.set_xlabel('Время')
        self.ax.set_ylabel('Цена')
        self.line, = self.ax.plot(self.x_data, self.y_data)
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

def append_data_to_graph(graph, data):
    try:
        price = data['price']
        timestamp = datetime.now()

        print(f"Добавление данных на график: время = {timestamp}, цена = {price}")
        graph.addData(timestamp, price)
    except ValueError:
        print("Ошибка при добавлении данных на график")

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
    assets = get_asset_list()

    app = QApplication([])

    mainWindow = QMainWindow()
    mainWindow.setGeometry(100, 100, 800, 600)
    mainWindow.setWindowTitle("Live Trading Data")

    layout = QVBoxLayout()

    coin_selector = QComboBox()
    coin_selector.setEditable(True)
    asset_symbol_map = {}

    for asset in assets:
        asset_name = f"{asset['symbol'].upper()} - {asset['name']}"
        coin_selector.addItem(asset_name)
        asset_symbol_map[asset_name] = asset['id']

    layout.addWidget(coin_selector)

    graph_canvas = CustomFigCanvas()
    layout.addWidget(graph_canvas)

    # Добавление QLabel для отображения состояния счета
    status_label = QLabel("Текущие позиции: []")
    layout.addWidget(status_label)

    mainWindow_widget = QWidget()
    mainWindow_widget.setLayout(layout)
    mainWindow.setCentralWidget(mainWindow_widget)
    mainWindow.show()

    def update_graph():
        selected_asset_name = coin_selector.currentText()
        selected_symbol = asset_symbol_map.get(selected_asset_name)

        if selected_symbol:
            price = get_current_price(selected_symbol)
            if price:
                append_data_to_graph(graph_canvas, {'timestamp': datetime.now(), 'price': price})
                update_trading_status(price)
                status_label.setText(f"Текущие позиции: {investment_positions}")  # Обновление состояния счета
            else:
                print("Ошибка получения цены для выбранной монеты.")
        else:
            print("Монета не найдена или не выбрана.")

    def on_coin_selected():
        graph_canvas.reset_graph()
        update_graph()

    coin_selector.currentIndexChanged.connect(on_coin_selected)

    timer = QTimer()
    timer.timeout.connect(update_graph)
    timer.start(10000)  # Обновление графика каждые 10 секунд

    app.exec_()

if __name__ == '__main__':
    main()
