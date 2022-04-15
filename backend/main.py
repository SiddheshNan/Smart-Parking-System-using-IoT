from tornado import websocket, web, ioloop
from abc import ABC
import mysql.connector
import json
import logging
import threading

logging.basicConfig(format='%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d | %(message)s',
                    datefmt='%d-%m-%Y %H:%M:%S', level=logging.DEBUG)

config = {
    "WEB_SERVER": {
        # "host": "0.0.0.0",
        "port": 8888
    },
    "DATABASE": {
        "host": "localhost",
        "user": "root",
        "password": "",
        "database_name": "iot_parking_system"
    }
}

logging.info('Program Started!')

db = mysql.connector.connect(
    host=config["DATABASE"]["host"],
    user=config["DATABASE"]["user"],
    password=config["DATABASE"]["password"],
    database=config["DATABASE"]["database_name"],
    raise_on_warnings=True
)

connected_clients = []

app_state = {
    'slot_1': {
        'vacant': True,
        'time': 'N/A'
    },
    'slot_2': {
        'vacant': True,
        'time': 'N/A'
    },
    'slot_3': {
        'vacant': True,
        'time': 'N/A'
    },
    'slot_4': {
        'vacant': True,
        'time': 'N/A'
    },
}


class WebSocketHandler(websocket.WebSocketHandler, ABC):
    clients = set()

    def check_origin(self, origin):
        return True

    def open(self):
        WebSocketHandler.clients.add(self)
        logging.info("Client connected")

    def on_close(self):
        WebSocketHandler.clients.remove(self)
        logging.info("Client disconnected")

    @classmethod
    def send_message(cls, message: str):
        for client in cls.clients:
            client.write_message(message)

    def on_message(self, message):
        logging.info(f"Msg received: {message}")


class GpioThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        pass


def main():
    app = web.Application([
        (r'/ws', WebSocketHandler),
    ],
        websocket_ping_interval=10,
        websocket_ping_timeout=30,
        debug=True,
        autoreload=True,
    )
    app.listen(config["WEB_SERVER"]["port"])
    io_loop = ioloop.IOLoop.current()
    periodic_callback = ioloop.PeriodicCallback(
        lambda: WebSocketHandler.send_message(json.dumps(app_state)), 1000
    )
    GpioThread().start()
    periodic_callback.start()
    io_loop.start()


if __name__ == '__main__':
    main()
