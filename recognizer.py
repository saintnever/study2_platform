import queue
import threading
import random
import numpy as np
import pandas as pd
import time


class Recognizer(threading.Thread):
    def __init__(self, stop_event, select_event, sig_queue, pat_queues, algo, n, interval, pats, model_period, model_delay):
        threading.Thread.__init__(self)
        self.algo = algo
        self.stopped = stop_event
        self.select = select_event
        self.pats = pats
        self.pats_baye = dict()
        self.target = -1
        self.n = n
        self.THs = {'corr3': 0.5, 'corr10': 0.4, 'corr15': 0.4, 'baye3': 0.7, 'baye10': 0.3, 'baye15': 0.3}
        self.wins = {'corr3': 3, 'corr10': 5, 'corr15': 5, 'baye3': 2, 'baye10': 5, 'baye15': 6}
        self.win = 2
        self.TH = 0.5
        if self.algo + str(self.n) in self.THs.keys():
            self.win = self.wins.get(self.algo + str(self.n))
            self.TH = self.THs.get(self.algo + str(self.n))
            print(self.win, self.TH, self.n)
        self.inteval = interval  # in second
        self.win_n = int(self.win / self.inteval)
        self.step = self.inteval
        self.pats_status = [0 for _ in range(self.n)]
        self.data_queue = sig_queue
        self.pat_queues = pat_queues
        self.sigs_q = list()
        self.pats_q = [[] for _ in self.pat_queues]
        if self.algo == 'baye':
            self.model_period = model_period
            self.model_delay = model_delay
            self.mchanges_prev = None
        self.init_algo()


    def init_algo(self):
            # self.model_period = model_period
            print('the pattern set is'.format(self.pats))
            # print(self.model_period.head(), self.model_delay.head())
            for i, pat in enumerate(self.pats):
                try:
                    self.pats_baye[pat[0]].append(i)
                except KeyError:
                    self.pats_baye[pat[0]] = [i]
            print(self.pats_baye)

    def set_display(self, display):
        self.pats_status = display

    def get_target(self):
        return self.target

    def run(self):
        data, status = -1, []
        while not self.stopped.is_set():
            # get input queue and start recog for current win
            try:
                self.sigs_q.append(self.data_queue.get(timeout=1))
                for pat, q_pat in zip(self.pats_q, self.pat_queues):
                    pat.append(q_pat.get(timeout=1))
            except queue.Empty:
                continue
            # print(len(self.sigs_q))
            if len(self.sigs_q) > self.win_n:
                self.start_recog()
            # if len(self.sigs_q) == int(self.win / self.inteval):
            #     self.start_recog()
            #     self.sigs_q = self.sigs_q[1:]
            #     for pat in self.pats_q:
            #         pat = pat[1:]
            #         print( len(pat) == len(self.sigs_q))

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
        signal = self.sigs_q[-self.win_n:]
        probs = list()
        for pat in self.pats_q:
            # probs.append(abs(np.corrcoef(signal, pat[-self.win_n:])[0][1]))
            probs.append(np.corrcoef(signal, pat[-self.win_n:])[0][1])

        # select target
        if np.max(probs) > self.TH:
            self.select.set()
            self.target = np.argmax(probs)
            print('recog {}, selected {}'.format(self.algo, self.pats[self.target]))

    def recog_baye(self):
        signal = self.sigs_q
        # print(signal)
        m_changes = list()
        i = 0
        while True:
            try:
                if signal[-i] is not self.sigs_q[-(i+1)]:
                    m_changes.append(len(self.sigs_q) - i)
                    if i > self.win_n:
                        break
                i += 1
            except IndexError:
                break

        m_changes = m_changes[1:]
        m_changes.reverse()
        if m_changes == self.mchanges_prev:
            return
        self.mchanges_prev = m_changes
        m_periods = [(m_changes[i + 1] - m_changes[i] + 1) * self.inteval * 1000 for i in range(len(m_changes) - 1)]
        median_period = np.median(m_periods)
        # print('recog thread delta {}, mean {}, median {}'.format(m_periods, np.mean(m_periods), median_period))
        # calculate delay for each period
        prob_all = [[] for _ in self.pats_q]
        # prob_periods = dict()

        # pats with different delays for current period
        for i in range(1, len(m_changes)):
            if i > 0:
                # get probability for all periods. The measured period is the time different between the current tap and the previous tap
                mperiod = int((m_changes[i] - m_changes[i - 1]) * self.inteval * 1000)
                prob_period = dict()
                for period in self.pats_baye.keys():
                    dpats = self.pats_baye[period]
                    try:
                        prob_period[period] = self.model_period.loc[int(mperiod - 200), str(period)] * len(dpats)
                    except KeyError:
                        prob_period[period] = 0
                # print(prob_period)
                factor = np.sum([v for k, v in prob_period.items()])
                # get overall probability with delay
                for period in self.pats_baye.keys():
                    dpats = self.pats_baye[period]
                    prob_period[period] = prob_period[period] / factor
                    if len(dpats) == 1:
                        prob_all[dpats[0]].append(prob_period[period])
                    else:
                        prob_delay = list()
                        for p in dpats:
                            pat = self.pats_q[p]
                            m_delay = self.measure_delay(m_changes[i], pat)
                            # print(period, m_delay)
                            # m_d[i].append(m_delay)
                            try:
                                prob_delay.append(self.model_delay.loc[int(m_delay + 400), str(period)])
                            except KeyError:
                                prob_delay.append(0)
                            # print(prob_temp, period, p)
                        prob_delay_norm = prob_delay / np.sum(prob_delay)
                        for j, p in enumerate(dpats):
                            prob_all[p].append(prob_period[period] * prob_delay_norm[j])
                    # print('period {}, dpats {}, prob_period {},  prob_all {}'.format(period, dpats,
                    #                                                     prob_period[period], prob_all))

        # average for all taps
        prob_all = [np.mean(x) for x in prob_all]
        prob_all = prob_all / np.sum(prob_all)
        # print(prob_all)
        prob_all_sorted = np.sort(prob_all)
        print(prob_all, prob_all_sorted, np.max(prob_all), np.argmax(prob_all))

        if np.max(prob_all) > self.TH:
        # if prob_all_sorted[-1] - prob_all_sorted[-2] > self.TH:
            self.select.set()
            self.target = np.argmax(prob_all)
            # self.target = list(prob_all).index(prob_all_sorted[-1])
            print('recog {}, selected {}'.format(self.algo, self.pats[self.target]))

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

    def measure_delay_edge(self, iperiod, sign, pat):
        pidx = nidx = iperiod
        istate = pat[iperiod]
        m_delay = len(pat)
        if sign == 0:
            edge = -1
        else:
            edge = 1
        # sign = 0, falling edge; sign = 1, rising edge
        while nidx > 0 or pidx < len(pat):
            if nidx > 0:
                nidx -= 1
                if pat[nidx + 1] - pat[nidx] == edge:
                    m_delay = (iperiod - nidx) * self.inteval * 1000
                    break
            if pidx < len(pat) - 1:
                pidx += 1
                if pat[pidx] - pat[pidx - 1] == edge:
                    m_delay = (iperiod - pidx) * self.inteval * 1000
                    break
        return m_delay

    def recog_ML(self):
        return 0

    def quit(self):
        print('stopped')
        # if self.data_queue:
        #     with self.data_queue.mutex:
        #         del self.data_queue
        #     for q in self.pat_queues:
        #         with q.mutex:
        #             del q
        pass
