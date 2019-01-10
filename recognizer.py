import queue
import threading
import random
import numpy as np
import pandas as pd

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
        self.init_algo()
        self.model_freq = None
        self.model_delay = None

    def init_algo(self):
        if self.algo == 'baye':
            self.model_freq = pd.read_csv('./model/freq_allstudy1.csv')
            self.model_delay = pd.read_csv('./model/delay_allstudy1.csv')

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
            # maintain display status queues
            for state, pat_queue in zip(self.pats_status, self.pat_queues):
                pat_queue.put(state)
                if pat_queue.full():
                    status.append(pat_queue.get())
        self.quit()

    def start_recog(self):
        if self.algo == 'corr':
            self.recog_corr()
        elif self.algo == 'baye':
            self.recog_baye()
        elif self.algo == 'ml':
            self.recog_ML()
        else:
            print('Recognizer does not exist!')

    def recog_corr(self):
        # if np.sum(signal) == 0 and np.sum(signal) == len(signal) and np.sum(pat) == 0 and np.sum(pat) == len(pat):
        #     return 0
        signal = list(self.data_queue.queue)
        probs = list()
        for i, q in enumerate(self.pat_queues):
            pat = list(q.queue)
            probs.append(abs(np.corrcoef(signal, pat)[0][1]))

        # select target
        if np.max(probs) > self.TH:
            self.select.set()
            self.target = np.argmax(probs)

    def recog_baye(self):
        # calculate the input period and delay
        signal = self.input_baye()
        probs = list()
        # select target
        if np.max(probs) > self.TH:
            self.select.set()
            self.target = np.argmax(probs)

    def input_baye(self):
        signal = list(self.data_queue.queue)
        m_periods = list()
        for i, state in enumerate(signal[1:]):
            if state != signal[i-1]:
                m_periods.append(i)
        # can estimate freq now

        # calcualte delay
        m_d = [[] for _ in self.pat_queues]
        for i, q in enumerate(self.pat_queues):
            pat = list(q.queue)
            for iperiod in m_periods:
                m_delay = self.measure_delay(iperiod, pat)
                m_d[i].append(m_delay)
            # estimate delay
        return 0

    def measure_delay(self, iperiod, pat):
        m_delay = 0
        return m_delay

    def recog_ML(self):
        return 0

    def quit(self):
        # after the thread is joined, all data will be self destroyed
        pass
