import socket
import queue
import threading
import random
import numpy as np
import pandas as pd
import time
import pickle


class ImpinjReader(threading.Thread):
    def __init__(self, stop_event, dataq, sig):
        threading.Thread.__init__(self)
        self.stopped = stop_event
        self.signal = sig
        self.TCP_IP = "127.0.0.1"
        self.TCP_PORT = 14
        self.BUFFER_SIZE = 1024
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect((self.TCP_IP, self.TCP_PORT))
        print("connected: ", self.s)
        self.dataq = dataq
        self.tag = 'E20000193907006713102965'

    def run(self):
        while not self.stopped.is_set():
            data = self.s.recv(self.BUFFER_SIZE).decode("utf-8").split(',')
            self.dataq.put([data[4], data[5]])
            self.signal = data[5]
        self.s.close()


if __name__ == '__main__':
    q = queue.Queue()
    stop_event = threading.Event()
    data_reader = ImpinjReader(stop_event, q)
    data_reader.start()
    # time.sleep(10)
    # while not q.empty():
    while True:
        print(q.get())


