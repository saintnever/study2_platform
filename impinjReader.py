import socket
import queue
import threading
import random
import numpy as np
import pandas as pd
import time
import pickle
import select

class ImpinjReader(threading.Thread):
    def __init__(self, stop_event, sig):
        threading.Thread.__init__(self)
        self.stopped = stop_event
        self.signal = sig
        self.TCP_IP = "127.0.0.1"
        self.TCP_PORT = 14
        self.BUFFER_SIZE = 512
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.s.settimeout(0.01)
        try:
            self.s.connect((self.TCP_IP, self.TCP_PORT))
        except BlockingIOError:
            pass
        print("connected: ", self.s)
        # self.dataq = dataq
        self.tag = 'E20000193907006713102965'
        # self.ready = select.select([self.s], [], [], 0.1)

    def run(self):
        while not self.stopped.is_set():
            try:
                data = None
                # if self.ready[0]:
                data = self.s.recv(self.BUFFER_SIZE).decode("utf-8").split(',')
            # self.dataq.put(data[5])
                if -90 < float(data[5]) < -20:
                    self.signal = float(data[5])
                else:
                    continue
            except socket.timeout as e:
                err = e.args[0]
                if err == 'time out':
                    self.signal = -100
            except (socket.error, IndexError, ValueError) as e:
                print(e)
                continue
            # time.sleep(0.001)
        self.s.close()

    def get_signal(self):
        return self.signal


if __name__ == '__main__':
    q = queue.Queue()
    stop_event = threading.Event()
    data_reader = ImpinjReader(stop_event, q)
    data_reader.start()
    # time.sleep(10)
    # while not q.empty():
    while True:
        print(q.get())


