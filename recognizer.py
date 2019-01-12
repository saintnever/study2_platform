import queue
import threading
import random
import numpy as np
import pandas as pd
import time


class Recognizer(threading.Thread):
    def __init__(self, stop_event, select_event, signal, algo, n, pats, model_period, model_delay):
        threading.Thread.__init__(self)
        self.algo = algo
        self.stopped = stop_event
        self.select = select_event
        self.pats = pats
        self.pats_baye = dict()
        self.target = -1
        self.input_status = signal
        self.n = n
        self.THs = {'corr3': 0.5, 'corr10': 0.4, 'corr15': 0.4, 'baye3': 0.7, 'baye10': 0.4, 'baye15': 0.3}
        self.wins = {'corr3': 3, 'corr10': 5, 'corr15': 5, 'baye3': 2, 'baye10': 5, 'baye15': 6}
        self.win = 2
        self.TH = 0.5
        if self.algo + str(self.n) in self.THs.keys():
            self.win = self.wins.get(self.algo + str(self.n))
            self.TH = self.THs.get(self.algo + str(self.n))
            print(self.win, self.TH, self.n)
        self.inteval = 0.01  # in second
        self.step = self.inteval
        self.pats_status = [0 for _ in range(self.n)]
        self.data_queue = queue.Queue(maxsize=int(self.win / self.inteval))
        self.pat_queues = [queue.Queue(maxsize=int(self.win / self.inteval)) for _ in range(self.n)]
        if self.algo == 'baye':
            self.model_period = model_period
            self.model_delay = model_delay
        self.init_algo()

    def init_algo(self):
            # self.model_period = model_period

            # print(self.model_period.head(), self.model_delay.head())
            for i, pat in enumerate(self.pats):
                try:
                    self.pats_baye[pat[0]].append(i)
                except KeyError:
                    self.pats_baye[pat[0]] = [i]
            print(self.pats_baye)

    def set_input(self, _input):
        self.input_status = _input

    def set_display(self, display):
        self.pats_status = display

    def get_target(self):
        return self.target

    def run(self):
        data, status = -1, []
        tmp = time.time()
        while not self.stopped.is_set():
            tmp = time.time()
            # maintain input queue and start recog for current win
            self.data_queue.put(self.input_status)
            if self.data_queue.full():
                self.data_queue.get()
                self.start_recog()
            # maintain display status queues
            for state, pat_queue in zip(self.pats_status, self.pat_queues):
                pat_queue.put(state)
                # print(state)
                if pat_queue.full():
                    pat_queue.get()
            delta = time.time() - tmp
            # print(self.input_status, self.inteval-delta)
            if delta < self.inteval:
                time.sleep(self.inteval - delta)


        # while not self.stopped.wait(timeout=self.inteval):
        #     print(self.input_status, time.time() - tmp)
            # maintain input queue and start recog for current win
            # self.data_queue.put_nowait([self.input_status, time.time()-tmp])
            # if self.data_queue.full():
            #     self.data_queue.get_nowait()
                # self.start_recog()
            # maintain display status queues
            # for state, pat_queue in zip(self.pats_status, self.pat_queues):
            #     pat_queue.put([state, time.time()-tmp])
            #     # print(state)
            #     if pat_queue.full():
            #         status.append(pat_queue.get_nowait())
            # tmp = time.time()

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
            pat = list(q)
            probs.append(abs(np.corrcoef(signal, pat)[0][1]))

        # select target
        if np.max(probs) > self.TH:
            self.select.set()
            self.target = np.argmax(probs)

    def recog_baye(self):
        signal = list(self.data_queue.queue)
        # print(signal)
        m_changes = list()
        for i in range(1, len(signal)):
            if signal[i] is not signal[i - 1]:
                m_changes.append(i)
        # print(m_changes)
        m_periods = [(m_changes[i + 1] - m_changes[i]) * self.inteval * 1000 for i in range(len(m_changes) - 1)]
        # print(m_periods)
        # match study1 to average consecutive periods
        m_periods = [(m_periods[i + 1] + m_periods[i]) / 2.0 for i in range(len(m_periods) - 1)]
        median_period = np.median(m_periods)
        # print(m_periods)
        # calculate delay for each period
        prob_all = [0] * self.n
        prob_periods = dict()
        # prob_delays = dict()
        for period in self.pats_baye.keys():
            # pats with different delays for current period
            dpats = self.pats_baye[period]
            # estimate prob for each available period
            prob_period = list()

            # for m_period in m_periods:
            #     # don't forget the priori!
            #     try:
            #         prob_period.append(self.model_period.loc[int(m_period - 200), str(period)])
            #     except KeyError:
            #         prob_period.append(0)
            try:
                prob_periods[period] = self.model_period.loc[int(median_period - 200), str(period)] * len(dpats)
            except (KeyError, ValueError) as e:
                prob_periods[period] = 0

        # normalized period prob
        factor = np.sum([v for k, v in prob_periods.items()])
        # print(prob_periods, factor)
        # calculate prob combined with delay
        for period in self.pats_baye.keys():
            prob_periods[period] = prob_periods[period] / factor
            # print(period, prob_periods[period])
            dpats = self.pats_baye[period]
            # m_d = [[] for _ in dpats]
            # calculate delay prob and the combined probs for all pattern.
            if len(dpats) == 1:
                prob_all[dpats[0]] = prob_periods[period]
            else:
                prob_delay = list()
                for p in dpats:
                    prob_temp = list()
                    pat = list(self.pat_queues[p].queue)
                    for iperiod in m_changes:
                        m_delay = self.measure_delay(iperiod, pat)
                        # m_d[i].append(m_delay)
                        try:
                            prob_temp.append(self.model_delay.loc[int(m_delay + 400), str(period)])
                        except KeyError:
                            prob_temp.append(0)
                    prob_delay.append(np.mean(prob_temp))
                    # print(prob_temp, period, p)
                factor = 1.0 / np.sum(prob_delay)
                prob_delay = [x*factor for x in prob_delay]
                # print(prob_delay)
                # print(period, dpats, prob_delay)
                for i, p in enumerate(dpats):
                    prob_all[p] = prob_periods[period] * prob_delay[i]

        # select target
        prob_all = prob_all / np.sum(prob_all)
        # print(prob_all, np.max(prob_all), np.argmax(prob_all))
        # print(prob_all, np.sum(prob_all))
        if np.max(prob_all) > self.TH:
            self.select.set()
            self.target = np.argmax(prob_all)
            print('selected {}'.format(self.pats[self.target]))

    def measure_delay(self, iperiod, pat):
        pidx = nidx = iperiod
        istate = pat[iperiod]
        m_delay = len(pat)
        while nidx > 0 or pidx < len(pat):
            if nidx > 0:
                nidx -= 1
                if pat[nidx] is not istate:
                    m_delay = (iperiod - nidx) * self.inteval * 1000
                    break
            if pidx < len(pat) - 1:
                pidx += 1
                if pat[pidx] is not istate:
                    m_delay = (iperiod - pidx) * self.inteval * 1000
                    break
        return m_delay

    def recog_ML(self):
        return 0

    def quit(self):
        del self.data_queue
        for q in self.pat_queues:
            del q
        pass
