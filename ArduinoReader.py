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
        #self.TCP_IP = "127.0.0.1"
        #self.TCP_PORT = 14
        #self.BUFFER_SIZE = 1024
        #self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #self.s.connect((self.TCP_IP, self.TCP_PORT))
        # port = '/dev/cu.usbmodem14431'
        port = "COM6"
        self.s = serial.Serial(port, 9600, timeout=1, rtscts=True, dsrdtr=True)
        if not self.s.isOpen():
            self.s.open()
        print("connected: ", self.s)

    def run(self):
        while not self.stopped.is_set():
            print(self.s.readline().rstrip())
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
            print('the serial port is open? {}'.format(self.s.isOpen()))


if __name__ == '__main__':
    q = queue.Queue()
    stop_event = threading.Event()
    data_reader = ImpinjReader(stop_event, q)
    data_reader.start()
    # time.sleep(10)
    # while not q.empty():
    while True:
        print(q.get())