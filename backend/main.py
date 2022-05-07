from tornado import websocket, web, ioloop
from abc import ABC
import mysql.connector
import json
import logging
from threading import Thread
import RPi.GPIO as GPIO
import time
import RPi_I2C_driver

# DISPLAY_SCL = 3
# DISPLAY_SDA = 2

SENSOR_1 = 14
SENSOR_2 = 15
SENSOR_3 = 18
SENSOR_4 = 17
SENSOR_GATE = 21

servo_pin = 13

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

GPIO.setup(SENSOR_1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(SENSOR_2, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(SENSOR_3, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(SENSOR_4, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(SENSOR_GATE, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(servo_pin, GPIO.OUT)

mylcd = RPi_I2C_driver.lcd()

pwm = GPIO.PWM(servo_pin, 50)  # 50 Hz (20 ms PWM period)
pwm.start(2.0)
time.sleep(0.5)
pwm.ChangeDutyCycle(0)

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


def sendMsg(vehicle_num, action, charge):
    msg = f'Vehicle {vehicle_num} has {action}'
    if charge is not None:
        msg += f", Charge: Rs. {charge}"
    logging.info(msg)
    WebSocketHandler.send_message(json.dumps({'msg': msg}))


def calculateCharge(in_time, out_time):
    return int(out_time) - int(in_time)


def detectVehicleChange(slot_num, value):
    current_time = str(int(time.time()))
    if app_state[f'slot_{slot_num}']['vacant'] is None:
        app_state[f'slot_{slot_num}']['vacant'] = value
    elif app_state[f'slot_{slot_num}']['vacant'] is False and value is True:  # vehicle arrived
        print(f"vehicle {slot_num} left at", current_time)
        if app_state[f'slot_{slot_num}']['time'] != 'N/A':
            charge = calculateCharge(app_state[f'slot_{slot_num}']['time'], current_time)
            Thread(target=addHistory, args=(app_state[f'slot_{slot_num}']['time'], current_time, charge, slot_num),
                   daemon=True).start()
            Thread(target=sendMsg, args=(slot_num, 'Exited', charge), daemon=True).start()

        app_state[f'slot_{slot_num}']['vacant'] = True
        app_state[f'slot_{slot_num}']['time'] = current_time
        Thread(target=gate_open_close, args=(), daemon=True).start()


    elif app_state[f'slot_{slot_num}']['vacant'] is True and value is False:  # vehicle left
        print(f"vehicle {slot_num} arrived at", current_time)
        app_state[f'slot_{slot_num}']['vacant'] = False
        app_state[f'slot_{slot_num}']['time'] = current_time
        Thread(target=sendMsg, args=(slot_num, 'Arrived', None), daemon=True).start()

    time.sleep(0.1)


def gate_open_close():  # 7.0 is 90 | 2.0 is 0
    # start PWM by rotating to 90 degrees
    pwm.ChangeDutyCycle(7.0)  # rotate to 90 degrees
    time.sleep(0.5)
    pwm.ChangeDutyCycle(0.0)

    time.sleep(3)

    pwm.ChangeDutyCycle(2.0)
    time.sleep(0.5)
    pwm.ChangeDutyCycle(0.0)


def getStatusString(val):
    if val:
        return "Empty"
    else:
        return "Full "


def print_lcd():
    row1 = f"1:{getStatusString(app_state['slot_1']['vacant'])} 2:{getStatusString(app_state['slot_2']['vacant'])}"
    row2 = f"3:{getStatusString(app_state['slot_3']['vacant'])} 4:{getStatusString(app_state['slot_4']['vacant'])}"
    mylcd.lcd_display_string(row1, 1)
    mylcd.lcd_display_string(row2, 2)


class GpioThread(Thread):
    def __init__(self):
        Thread.__init__(self)
        logging.debug('Started GPIO Thread')

    def run(self):
        check = True
        while True:
            detectVehicleChange(1, GPIO.input(SENSOR_1) == GPIO.HIGH)
            detectVehicleChange(2, GPIO.input(SENSOR_2) == GPIO.HIGH)
            detectVehicleChange(3, GPIO.input(SENSOR_3) == GPIO.HIGH)
            detectVehicleChange(4, GPIO.input(SENSOR_4) == GPIO.HIGH)

            if GPIO.input(SENSOR_GATE) == GPIO.LOW and check is True:  # new vehcile arrived
                check = False
                if app_state[f'slot_1']['vacant'] or app_state[f'slot_2']['vacant'] or app_state[f'slot_3']['vacant'] or \
                        app_state[f'slot_3']['vacant']:
                    WebSocketHandler.send_message(json.dumps({'msg': "New vehicle arrived, Opening Gate.."}))
                    Thread(target=gate_open_close, args=(), daemon=True).start()
                else:
                    WebSocketHandler.send_message(json.dumps({'msg': "No Spots available to park!"}))

            elif GPIO.input(SENSOR_GATE) == GPIO.HIGH and check is False:
                check = True


def main():
    app = web.Application([
        (r'/ws', WebSocketHandler),
        (r"/(.*)", web.StaticFileHandler, {"path": './static', "default_filename": "index.html"})
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
    periodic_callback3 = ioloop.PeriodicCallback(
        lambda: print_lcd(), 1000
    )
    GpioThread().start()
    periodic_callback1.start()
    periodic_callback2.start()
    periodic_callback3.start()
    io_loop.start()


if __name__ == '__main__':
    main()
