import queue
import threading
import random
import numpy as np
import pandas as pd
import time
import pickle
# import tsfresh
# from tsfresh.feature_extraction import MinimalFCParameters


class Recognizer(threading.Thread):
    def __init__(self, stop_event, select_event, sig_queue, pat_queues, algo, n, interval, pats, model_period, model_delay, wins, THs, modality):
        threading.Thread.__init__(self)
        self.algo = algo
        self.stopped = stop_event
        self.select = select_event
        self.pats = pats
        self.pats_baye = dict()
        self.target = -1
        self.n = n
        self.wins = wins
        self.THs = THs
        # self.THs = {'corr3': 0.5, 'corr9': 0.4, 'corr10': 0.4, 'corr15': 0.4,
        #             'baye3': 0.7, 'baye9': 0.4, 'baye10': 0.3, 'baye15': 0.3}
        # self.THs = {'corr3': 0.5, 'corr10': 0.4, 'corr15': 0.4, 'baye3': 1.0/3, 'baye10': 1.0/10, 'baye15': 1.0/20}
        # self.wins = {'corr3': 3, 'corr10': 5, 'corr9': 5, 'corr15': 5,
        #              'baye3': 2, 'baye9': 5, 'baye10': 5, 'baye15': 6}
        self.win = 2
        self.TH = 0.5
        if self.algo + str(self.n) in self.THs.keys():
            self.win = self.wins.get(self.algo + str(self.n))
            self.TH = self.THs.get(self.algo + str(self.n))
            print(self.win, self.TH, self.n)
        self.inteval = interval + 0.0002  # in second. add residue time to match timed from main thread
        self.win_n = int(self.win / self.inteval)
        self.step = self.inteval
        self.pats_status = [0 for _ in range(self.n)]
        self.data_queue = sig_queue
        self.pat_queues = pat_queues
        self.sigs_q = list()
        self.mchanges_prev = None
        self.pats_q = [[] for _ in self.pat_queues]
        if self.algo == 'baye':
            self.model_period = model_period
            self.model_delay = model_delay
        if self.algo == 'ml':
            with open('../random_forest_clf_minimal.pickle', 'rb') as file:
                self.model_ML = pickle.load(file)
            with open('features.pickle', 'rb') as file:
                self.feature_ML = pickle.load(file)
        self.init_algo()
        self.timer = time.time()
        if modality == 'foot':
            self.delayi = 10

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
            # print(time.time() - self.timer)
            if time.time() - self.timer > 15:
                self.select.set()
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

        self.quit()

    def start_recog(self):
        if self.algo == 'corr':
            self.recog_corr()
        elif self.algo == 'baye':
            self.recog_baye_emg()
        elif self.algo == 'ml':
            self.recog_ML()
        else:
            print('Recognizer does not exist!')

    def moving_average(self, x, n_ma):
        signal = list()
        for i, item in enumerate(x):
            if i == 0:
                signal.append(item)
            elif i < n_ma:
                signal.append(np.nanmean(x[:i]))
            else:
                signal.append(np.mean(x[i - n_ma:i]))
        return signal

    def recog_corr(self):
        # if np.sum(signal) == 0 and np.sum(signal) == len(signal) and np.sum(pat) == 0 and np.sum(pat) == len(pat):
        #     return 0
        signal_raw = self.sigs_q[-self.win_n:]
        n_ma = 10
        signal = self.moving_average(signal_raw, n_ma)
        # signal = np.sign(signal - np.mean(signal))
        # print(signal_raw)
        # print(signal)
        # print(signal[-10:])
        probs = list()
        for pat in self.pats_q:
            # probs.append(abs(np.corrcoef(signal, pat[-self.win_n:])[0][1]))
            pat_smooth = self.moving_average(pat[-self.win_n:], n_ma)
            pat_smooth = np.roll(pat_smooth, self.delayi)
            probs.append(abs(np.corrcoef(signal, pat_smooth)[0][1]))

        # select target
        if np.max(probs) > self.TH:
            self.select.set()
            self.target = np.argmax(probs)
            print('recog {}, selected {}'.format(self.algo, self.pats[self.target]))

    def recog_baye_emg(self):
        t_start = time.time()
        signal = self.sigs_q
        # signal_raw = self.sigs_q
        # print(signal_raw)
        # n_ma = 10
        # signal = list()
        # for i in range(self.win_n + 10):
        #     signal.append(np.mean(signal_raw[-i - n_ma:-i]))
        # signal = signal - np.nanmean(signal)
        # print(signal)
        m_changes = list()
        i = 0
        while True:
            try:
                if signal[-i] - signal[-(i + 1)] == 1:
                    if len(m_changes) == 0 or abs(i - m_changes[-1]) > 0.3/self.inteval:
                        m_changes.append(len(self.sigs_q) - i)
                    if i > self.win_n:
                        break
                i += 1
            except IndexError:
                break

        m_changes = m_changes[1:]
        m_changes.reverse()
        # print(m_changes)
        if m_changes == self.mchanges_prev:
            return
        self.mchanges_prev = m_changes
        # m_periods = [(m_changes[i + 1] - m_changes[i] + 1) * self.inteval * 1000 for i in range(len(m_changes) - 1)]
        # median_period = np.median(m_periods)
        # calculate delay for each period
        prob_all = [[] for _ in self.pats_q]
        # prob_periods = dict()
        m_periods = list()
        # pats with different delays for current period
        for i in range(1, len(m_changes)):
            # get probability for all periods. The measured period is the time different between the current tap and the previous tap
            mperiod = int((m_changes[i] - m_changes[i - 1] + 2) * 0.5 * self.inteval * 1000)

            m_periods.append(mperiod)
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
                            # prob_delay.append(self.model_delay.loc[int(m_delay + 400), str(period)])
                            prob_delay.append(self.model_delay.loc[int(m_delay + 400), str(period)])
                        except KeyError:
                            prob_delay.append(0)
                        # print(prob_temp, period, p)
                    prob_delay_norm = prob_delay / np.sum(prob_delay)
                    for j, p in enumerate(dpats):
                        prob_all[p].append(prob_period[period] * prob_delay_norm[j])
                # print('period {}, dpats {}, prob_period {},  prob_all {}'.format(period, dpats,
                #                                                     prob_period[period], prob_all))
        print('recog thread delta {}, mean {}, median {}'.format(m_periods, np.mean(m_periods), np.median(m_periods)))

        # average for all taps
        prob_all = [np.mean(x) for x in prob_all]
        prob_all = prob_all / np.sum(prob_all)
        # print(prob_all)
        # prob_all_sorted = np.sort(prob_all)
        # print(prob_all, prob_all_sorted, np.max(prob_all), np.argmax(prob_all))
        if np.max(prob_all) > self.TH:
            # if prob_all_sorted[-1] - prob_all_sorted[-2] > self.TH:
            self.select.set()
            self.target = np.argmax(prob_all)
            # self.target = list(prob_all).index(prob_all_sorted[-1])
            print('recog {}, selected {}'.format(self.algo, self.pats[self.target]))
        # print('recog time is {}'.format(time.time() - t_start))


    def recog_baye(self):
        t_start = time.time()
        # signal = self.sigs_q
        signal_raw = self.sigs_q
        # print(signal_raw)
        n_ma = 10
        signal = list()
        for i in range(self.win_n + 10):
            signal.append(np.mean(signal_raw[-i - n_ma:-i]))
        signal = signal - np.nanmean(signal)
        print(signal)
        m_changes = list()
        i = 0
        while True:
            try:
                if signal[-i] * signal[-(i+1)] < 0:
                    m_changes.append(len(self.sigs_q) - i)
                    if i > self.win_n:
                        break
                i += 1
            except IndexError:
                break

        m_changes = m_changes[1:]
        m_changes.reverse()
        print(m_changes)
        if m_changes == self.mchanges_prev:
            return
        self.mchanges_prev = m_changes
        # m_periods = [(m_changes[i + 1] - m_changes[i] + 1) * self.inteval * 1000 for i in range(len(m_changes) - 1)]
        # median_period = np.median(m_periods)
        # calculate delay for each period
        prob_all = [[] for _ in self.pats_q]
        # prob_periods = dict()
        m_periods = list()
        # pats with different delays for current period
        for i in range(1, len(m_changes)):
            # get probability for all periods. The measured period is the time different between the current tap and the previous tap
            if i >= 2:
                mperiod = int((m_changes[i] - m_changes[i - 2] + 2) * 0.5 * self.inteval * 1000)
            else:
                mperiod = int((m_changes[i] - m_changes[i - 1] + 1) * self.inteval * 1000)
            m_periods.append(mperiod)
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
        print('recog thread delta {}, mean {}, median {}'.format(m_periods, np.mean(m_periods), np.median(m_periods)))

        # average for all taps
        prob_all = [np.mean(x) for x in prob_all]
        prob_all = prob_all / np.sum(prob_all)
        # print(prob_all)
        # prob_all_sorted = np.sort(prob_all)
        # print(prob_all, prob_all_sorted, np.max(prob_all), np.argmax(prob_all))
        if np.max(prob_all) > self.TH:
        # if prob_all_sorted[-1] - prob_all_sorted[-2] > self.TH:
            self.select.set()
            self.target = np.argmax(prob_all)
            # self.target = list(prob_all).index(prob_all_sorted[-1])
            print('recog {}, selected {}'.format(self.algo, self.pats[self.target]))
        print('recog time is {}'.format(time.time() - t_start))

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
        pass

    def feature(self, mperiods):
        X = list()
        X.append(np.max(mperiods))
        X.append(np.mean(mperiods))
        X.append(np.median(mperiods))
        X.append(np.min(mperiods))
        X.append(np.std(mperiods))
        X.append(np.sum(mperiods))
        X.append(np.var(mperiods))
        return np.array(X)

    def quit(self):
        self.timer = 0
        print('stopped')
        # if self.data_queue:
        #     with self.data_queue.mutex:
        #         del self.data_queue
        #     for q in self.pat_queues:
        #         with q.mutex:
        #             del q
        pass
