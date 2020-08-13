import serial
import serial.tools.list_ports as list_ports
import time
import sys
from config import config
from threading import Thread
import threading
import requests
import socket
import os
from gpiozero import LED


ip_config = config('config.ini', 'HostAddress')
door_config = config('config.ini', 'Door')
model_uri = 'http://{0}{1}'.format(ip_config['model'], ip_config['model_path'])
display_uri = 'http://{0}{1}'.format(ip_config['display'], ip_config['display_path'])
payload = {'id': None, 'type': door_config['type'], 'vehicle_type': door_config['vechicle_type'], 'ip_gate': None}
host_name = socket.gethostname()
access_token = ip_config['access_token']
apikey = ip_config['apikey']

sound_config = config('config.ini', 'Sound')
speak_thread = None

relay = LED(17)


def search_port(search):
    ports = list(list_ports.comports())
    for p in ports:
        if search in p.description:
            return p[0]
    else:
        return False


def arduino_connect():
    ser = serial.Serial()
    ser.baudrate = 9600
    port = search_port('ttyACM0')
    if port:
        ser.port = port
        ser.open()
    return ser


def open_gate():
    relay.on()
    time.sleep(5)
    relay.off()
    time.sleep(1)


def main_process():
    global speak_thread
    arduino = arduino_connect()
    print('Started')
    while True:
        try:
            if arduino.is_open:
                code = arduino.readline().decode().rstrip()
                print('Read rfid code {0}'.format(code))
                print('checking authorized')
                payload['id'] = code
                payload['ip_gate'] = socket.gethostbyname(host_name)
                r = requests.post(model_uri, params=payload, headers={'Authorization':access_token, 'apikey': apikey}).json()
                if r:
                    r = "&".join("%s=%s" % (k, v) for k, v in r.items())
                    Thread(target=requests.get, args=(display_uri, r)).start()
                    print('Requested to display @ {0}'.format(display_uri))
                    thread_relay = Thread(target=open_gate).start()
                    if int(sound_config['is_play']):
                        if speak_thread is None:
                            command = 'espeak -s160 -ven+m3 "{0}" --stdout|aplay -D "sysdefault:CARD=Headphones"'.format(sound_config['text'])
                            speak_thread = Thread(target=os.system, args=(command,)).start()
                        elif not speak_thread.is_alive():
                            command = 'espeak -s160 -ven+m3 "{0}" --stdout|aplay -D "sysdefault:CARD=Headphones"'.format(sound_config['text'])
                            speak_thread = Thread(target=os.system, args=(command,)).start()
            else:
                print('Restarted.')
                arduino = arduino_connect()
                time.sleep(5)
        except Exception as e:
            print(e)


if __name__ == '__main__':
    main_process()
    print('Exited')
    sys.exit(0)
