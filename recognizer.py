import queue
import threading
import random
import numpy as np


class Recognizer(threading.Thread):
    def __init__(self, stop_event, select_event, thread_id, algo, n):
        threading.Thread.__init__(self)
        self.thread_id = thread_id
        self.algo = algo
        self.stopped = stop_event
        self.select = select_event
        self.target = -1
        self.input_status = 0
        self.n = n
        self.THs = {'corr3': 0.5, 'corr10': 0.4, 'corr15': 0.4, 'baye3': 0.7, 'baye10': 0.4, 'baye15': 0.3}
        self.wins = {'corr3': 3, 'corr10': 5, 'corr15': 5, 'baye3': 2, 'baye10': 5, 'baye15': 6}
        self.win = 2
        self.TH = 0.5
        if self.algo+str(self.n) in self.THs.keys():
            self.win = self.wins.get(self.algo + str(self.n))
            self.TH = self.THs.get(self.algo + str(self.n))
        self.inteval = 0.01  # in second
        self.step = 0.01
        self.pats_status = [0 for _ in range(self.n)]
        self.data_queue = queue.Queue(maxsize=int(self.win / self.step))
        self.pat_queues = [queue.Queue(maxsize=int(self.win / self.step)) for _ in range(self.n)]

    def set_input(self, _input):
        self.input_status = _input

    def set_display(self, display):
        self.pats_status = display

    def get_target(self):
        return self.target

    def run(self):
        data, status = -1, []
        while not self.stopped.wait(self.inteval):
            # maintain input queue and start recog for current win
            self.data_queue.put(self.input_status)
            if self.data_queue.full():
                data = self.data_queue.get()
                self.start_recog()
            # maintain display status
            for state, pat_queue in zip(self.pats_status, self.pat_queues):
                pat_queue.put(state)
                if pat_queue.full():
                    status.append(pat_queue.get())
        self.quit()

    def start_recog(self):
        signal = list(self.data_queue.queue)
        for i, q in enumerate(self.pat_queues):
            pat = list(q.queue)
            if self.algo == 'corr':
                self.recog_corr(signal, pat, i)
            elif self.algo == 'baye':
                self.recog_baye(signal, pat, i)
            elif self.algo == 'ml':
                self.recog_ML(signal, pat, i)
            else:
                print('Recognizer does not exist!')
            if self.select.is_set():
                break

    def recog_corr(self, signal, pat, i):
        # if np.sum(signal) == 0 and np.sum(signal) == len(signal) and np.sum(pat) == 0 and np.sum(pat) == len(pat):
        #     return
        corr = abs(np.corrcoef(signal, pat)[0][1])
        print(i, corr)
        if corr > self.TH:
            self.select.set()
            self.target = i

    def recog_baye(self, signal, pat, i):
        if abs(np.corrcoef(signal, pat)[0][1]) > 0.7:
            self.select.set()
            self.target = i

    def recog_ML(self, signal, pat, i):
        if abs(np.corrcoef(signal, pat)[0][1]) > 0.7:
            self.select.set()
            self.target = i

    def quit(self):
        # after the thread is joined, all data will be self destroyed
        pass
