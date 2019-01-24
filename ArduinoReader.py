import socket
import queue
import threading
import random
import numpy as np
import pandas as pd
import time
import pickle
import serial
import time

class ArduinoReader(threading.Thread):
    def __init__(self, stop_event, sig):
        threading.Thread.__init__(self)
        self.stopped = stop_event
        self.signal = sig
        port = "COM11"
        # self.s = serial.Serial(port, 9600, timeout=1, rtscts=True, dsrdtr=True)
        self.s = serial.Serial(port, 115200, timeout=0.1, rtscts=True, dsrdtr=True)
        if not self.s.isOpen():
            self.s.open()
        print("connected: ", self.s)

    def run(self):
        while not self.stopped.is_set():
            # print(self.s.readline().rstrip())
            try:
                self.signal = float(self.s.readline().rstrip())
            except ValueError:
                continue
        self.clean()

    def get_signal(self):
        return self.signal

    def clean(self):
        # self.s.cancel_read()
        while self.s.isOpen():
            self.s.close()
            # print('the serial port is open? {}'.format(self.s.isOpen()))


if __name__ == '__main__':
    q = queue.Queue()
    stop_event = threading.Event()
    data_reader = ArduinoReader(stop_event, q)
    data_reader.start()
    # time.sleep(10)
    # while not q.empty():
    while True:
        print(q.get())