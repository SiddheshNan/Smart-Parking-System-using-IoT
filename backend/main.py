from tornado import websocket, web, ioloop
from abc import ABC
import mysql.connector
import json
import logging
from threading import Thread
import RPi.GPIO as GPIO
import time

# DISPLAY_SCL = 3
# DISPLAY_SDA = 2

SENSOR_1_TRIGGER = 14
SENSOR_1_ECHO = 15

SENSOR_2_TRIGGER = 10
SENSOR_2_ECHO = 9

SENSOR_3_TRIGGER = 23
SENSOR_3_ECHO = 24

SENSOR_4_TRIGGER = 17
SENSOR_4_ECHO = 18

# SENSOR_1_GATE = 20
# SENSOR_2_GATE = 21

DISTANCE = 8

config = {
    "WEB_SERVER": {
        "host": "0.0.0.0",
        "port": 8888
    },
    "DATABASE": {
        "host": "localhost",
        "user": "root",
        "password": "root",
        "database_name": "iot_parking_system"
    }
}

logging.basicConfig(format='%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d | %(message)s',
                    datefmt='%d-%m-%Y %H:%M:%S', level=logging.DEBUG)

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(SENSOR_1_TRIGGER, GPIO.OUT)
GPIO.setup(SENSOR_1_ECHO, GPIO.IN)
GPIO.output(SENSOR_1_TRIGGER, False)

GPIO.setup(SENSOR_2_TRIGGER, GPIO.OUT)
GPIO.setup(SENSOR_2_ECHO, GPIO.IN)
GPIO.output(SENSOR_2_TRIGGER, False)

GPIO.setup(SENSOR_3_TRIGGER, GPIO.OUT)
GPIO.setup(SENSOR_3_ECHO, GPIO.IN)
GPIO.output(SENSOR_3_TRIGGER, False)

GPIO.setup(SENSOR_4_TRIGGER, GPIO.OUT)
GPIO.setup(SENSOR_4_ECHO, GPIO.IN)
GPIO.output(SENSOR_4_TRIGGER, False)

time.sleep(1)

logging.info('Program Started!')

db = mysql.connector.connect(
    host=config["DATABASE"]["host"],
    user=config["DATABASE"]["user"],
    password=config["DATABASE"]["password"],
    database=config["DATABASE"]["database_name"],
    raise_on_warnings=True
)

app_state = {
    'slot_1': {
        'vacant': None,
        'time': 'N/A'
    },
    'slot_2': {
        'vacant': None,
        'time': 'N/A'
    },
    'slot_3': {
        'vacant': None,
        'time': 'N/A'
    },
    'slot_4': {
        'vacant': None,
        'time': 'N/A'
    }
}


def getHistory():
    sql = "SELECT * FROM `history` ORDER BY id DESC;"
    cursor = db.cursor()
    logging.debug(f"Executing query: {sql}")
    cursor.execute(sql)
    result = cursor.fetchall()
    return result


def addHistory(in_time, out_time, charge, slot):
    sql = "INSERT INTO `history` (`id`, `in_time`, `out_time`, `charge`, `slot`) VALUES (NULL, %s, %s, %s, %s);"
    val = (in_time, out_time, charge, slot)
    cursor = db.cursor()
    logging.debug(f"Executing query: {sql % val}")
    cursor.execute(sql, val)
    db.commit()


def deleteHistory(item_id):
    sql = "DELETE FROM `history` WHERE `history`.`id` = %s"
    val = (item_id,)
    cursor = db.cursor()
    logging.debug(f"Executing query: {sql % val}")
    cursor.execute(sql, val)
    db.commit()


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
        if len(cls.clients):
            for client in cls.clients:
                client.write_message(message)

    def on_message(self, message):
        logging.info(f"Msg received from client: {message}")
        incoming_data = json.loads(message)
        if incoming_data['delete'] is not None:
            deleteHistory(int(incoming_data['delete']))


def readSensorDistance(GPIO_ECHO, GPIO_TRIGGER):
    GPIO.output(GPIO_TRIGGER, True)

    # set Trigger after 0.01ms to LOW
    time.sleep(0.00001)
    GPIO.output(GPIO_TRIGGER, False)

    StartTime = time.time()
    StopTime = time.time()

    count = time.time()
    # save StartTime
    while GPIO.input(GPIO_ECHO) == GPIO.LOW and time.time() - count < 0.1:
        StartTime = time.time()

    count = time.time()
    # save time of arrival
    while GPIO.input(GPIO_ECHO) == GPIO.HIGH and time.time() - count < 0.1:
        StopTime = time.time()

    # time difference between start and arrival
    TimeElapsed = StopTime - StartTime
    # multiply with the sonic speed (34300 cm/s)
    # and divide by 2, because there and back
    distance = (TimeElapsed * 34300) / 2
    return int(distance)


def sendMsg(vehicle_num, action, charge):
    msg = f'Vehicle {vehicle_num} has {action}'
    if charge is not None:
        msg += f", Charge: Rs. {charge}"
    logging.info(msg)
    WebSocketHandler.send_message(json.dumps({'msg': msg}))


def detectVehicleChange(slot_num, distance):
    logging.debug(f"slot {slot_num}: {distance} cm")
    current_time = str(int(time.time()))
    if app_state[f'slot_{slot_num}']['vacant'] is None:
        app_state[f'slot_{slot_num}']['vacant'] = bool(distance >= DISTANCE)
    elif distance >= DISTANCE and app_state[f'slot_{slot_num}']['vacant'] is False:
        if app_state[f'slot_{slot_num}']['time'] != 'N/A':  # add in db
            charge = calculateCharge(app_state[f'slot_{slot_num}']['time'], current_time)
            Thread(target=addHistory, args=(app_state[f'slot_{slot_num}']['time'], current_time, charge, slot_num),
                   daemon=True).start()
            Thread(target=sendMsg, args=(slot_num, 'left', charge), daemon=True).start()
        app_state[f'slot_{slot_num}']['vacant'] = True
        app_state[f'slot_{slot_num}']['time'] = current_time
    elif distance < DISTANCE and app_state[f'slot_{slot_num}']['vacant'] is True:
        app_state[f'slot_{slot_num}']['vacant'] = False
        app_state[f'slot_{slot_num}']['time'] = current_time
        Thread(target=sendMsg, args=(slot_num, 'arrived', None), daemon=True).start()
    time.sleep(0.3)


def calculateCharge(in_time, out_time):
    return int(out_time) - int(in_time)


class GpioThread(Thread):
    def __init__(self):
        Thread.__init__(self)
        logging.debug('Started GPIO Thread')

    def run(self):
        while True:
            detectVehicleChange(1, readSensorDistance(SENSOR_1_ECHO, SENSOR_1_TRIGGER))
            detectVehicleChange(2, readSensorDistance(SENSOR_2_ECHO, SENSOR_2_TRIGGER))
            detectVehicleChange(3, readSensorDistance(SENSOR_3_ECHO, SENSOR_3_TRIGGER))
            detectVehicleChange(4, readSensorDistance(SENSOR_4_ECHO, SENSOR_4_TRIGGER))


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
    periodic_callback1 = ioloop.PeriodicCallback(
        lambda: WebSocketHandler.send_message(json.dumps({'info': app_state})), 1000
    )
    periodic_callback2 = ioloop.PeriodicCallback(
        lambda: WebSocketHandler.send_message(json.dumps({'history': getHistory()})), 2000
    )
    GpioThread().start()
    periodic_callback1.start()
    periodic_callback2.start()
    io_loop.start()


if __name__ == '__main__':
    main()
