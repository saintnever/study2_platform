#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from PIL import Image, ImageTk
from recognizer import Recognizer
import threading
import random
import queue
import pandas as pd
import time
import numpy as np
import csv
import os


class MainApplication(tk.Frame):
    def __init__(self, parent, n_pats, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.root = parent
        self.width = self.winfo_screenwidth()
        self.height = self.winfo_screenheight()
        self.winsize = (self.width, self.height)
        self.after_handles = []
        self.rest_handles = []
        self.check_handles = []
        self.rest_text = None
        self.posters = []
        self.other_posters = None
        self.target_poster = None
        self.posters_selected = None
        self.tkimages = []
        self.tkbg = None
        self.poster_size = None
        self.poster_aratio = None
        self.image_size = None
        self.pats = None
        self.pats_dict = dict()
        self.pat_type = None
        self.pats_selected = None
        self.stop_event = threading.Event()
        self.select_event = threading.Event()
        self.n = 0
        self.pats_status = None
        self.cases = n_pats
        # self.recog_typelist = ['corr', 'baye', 'ml']
        self.recog_typelist = ['corr', 'baye']
        self.recog = None
        self.recog_type = None
        self.task_cnt = 0
        self.session_cnt = 0
        self.rest_cnt = 20
        self.seq = []
        self.id = tk.StringVar()

        # create canvas
        self.w = tk.Canvas(self.root, width=self.winsize[0], height=self.winsize[1])
        self.w.pack()
        # start new selection task when hit Return
        self.w.focus_set()
        self.w.bind('<Return>', self.selection_task)
        # collect space key status
        self.w.bind('<KeyPress-space>', self.space_pressed)
        self.w.bind('<KeyRelease-space>', self.space_released)
        # clean when closing the window
        self.w.bind('<Escape>', self.on_closing)
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.model_period = pd.read_csv('./model/freq_allstudy1.csv')
        self.model_delay = pd.read_csv('./model/delay_allstudy1.csv')
        self.signal = 0
        self.p = list()
        self.tprev = time.time()
        self.wins = {'corr3': 2, 'corr9': 5, 'corr10': 5, 'corr15': 7, 'corr21':7,
                     'baye3': 2, 'baye9': 5, 'baye10': 5, 'baye15': 6, 'baye21':7}
        self.THs = {'corr3': 0.3, 'corr9': 0.2, 'corr10': 0.2, 'corr15': 0.2, 'corr21': 0.3,
                    'baye3': 0.4, 'baye9': 0.4, 'baye10': 0.4, 'baye15': 0.3, 'baye21': 0.2}
        self.win = 2
        self.interval = 0.01
        self.sig_queue = None
        self.pat_queues = list()
        self.task_time = 0
        self.fpress_time = 0
        self.L1 = None
        self.E1 = None
        self.id_input()
        self.df = pd.DataFrame()
        self.target = None
        self.pressed = 0
        self.csvfile = None
        self.csvwriter = None
        self.raw_csvwriter = None
        self.raw_csvfile = None
        self.raw_row = list()
        self.rest_flag = 0

    def id_input(self):
        self.L1 = tk.Label(self.root, text='Your Student ID:')
        # L1.pack(side=tk.LEFT)
        # E1 = tk.Entry(self.root, bd=5)
        # E1.pack(side=tk.RIGHT)
        self.E1 = tk.Entry(self.root, bd=5, textvariable=self.id)
        self.E1.bind('<Return>', self.selection_task)
        self.w.create_window(50, 50, window=self.L1, anchor='center', tags=('id', ))
        self.w.create_window(200, 50, window=self.E1, anchor='center', tags=('id', ))

    def set_winsize(self, win_size):
        self.winsize = win_size
        self.width = self.winsize[0]
        self.height = self.winsize[1]
        self.w.configure(width=self.width, height=self.height)
        self.w.pack()

    def set_background(self, bg_file):
        image = Image.open(bg_file).resize(self.winsize, Image.ANTIALIAS)
        self.tkbg = ImageTk.PhotoImage(image)
        self.w.create_image(0, 0, image=self.tkbg, anchor='nw')

    def set_posters(self, poster_files):
        for iamge_file in poster_files:
            self.posters.append(Image.open(iamge_file))
        self.other_posters = self.posters[1:]
        self.target_poster = self.posters[0]
        self.poster_size = (self.target_poster.width, self.target_poster.height)
        print(self.poster_size)
        self.poster_aratio = float(self.target_poster.height) / float(self.target_poster.width)

    def set_images(self, image_seq):
        self.posters_selected = image_seq

    def set_pats(self, pat_opt, pat_worst, pat_rand):
        self.pats_dict['opt'] = pat_opt
        self.pats_dict['worst'] = pat_worst
        self.pats_dict['rand'] = pat_rand

    def task_init(self):

        # init the task sequence for current session
        if self.task_cnt == 0:
            for case in self.cases:
                for rcog in self.recog_typelist:
                    for pats in self.pats_dict.keys():
                        self.seq.append([case, rcog, pats])
            random.shuffle(self.seq)
        # assign n and recognizer type for current task
        self.n = self.seq[self.task_cnt][0]
        self.recog_type = self.seq[self.task_cnt][1]
        self.pat_type = self.seq[self.task_cnt][2]
        self.pats = self.pats_dict[self.pat_type]
        self.posters_selected = random.sample(self.other_posters, self.n - 1) + [self.target_poster]
        random.shuffle(self.posters_selected)
        self.target = self.posters_selected.index(self.target_poster)
        for pat in self.pats:
            if len(pat) == self.n:
                self.pats_selected = pat
        assert len(self.posters_selected) == len(self.pats_selected)

        # init queue
        self.win = self.wins.get(self.recog_type + str(self.n))
        self.sig_queue = queue.Queue(maxsize=int(self.win / self.interval))
        self.pat_queues = [queue.Queue(maxsize=int(self.win / self.interval)) for _ in range(self.n)]

    def selection_task(self, event):
        if self.task_cnt == len(self.cases) * len(self.recog_typelist) * len(self.pats_dict.keys()):
            # clean from previous task
            self.clean_task()
            self.clean_session()
            self.rest_cnt = 60
            self.rest_text = self.w.create_text(int(self.width / 2), int(self.height / 2), anchor='center',
                                                fill='orange', font=("Microsoft YaHei", 50),
                                                text='Remaining rest time {}s'.format(self.rest_cnt), tags=('text', ))
            self.rest_handles.append(self.root.after(1, self.rest))
        elif self.task_cnt % 6 == 0 and self.task_cnt > 0 and self.rest_flag == 0:
            self.clean_task()
            self.rest_cnt = 30
            self.rest_text = self.w.create_text(int(self.width / 2), int(self.height / 2), anchor='center',
                                                fill='orange', font=("Microsoft YaHei", 50),
                                                text='Remaining rest time {}s'.format(self.rest_cnt), tags=('text', ))
            self.rest_handles.append(self.root.after(1, self.rest_within))
            self.rest_flag = 1
        else:
            # clean from previous task
            self.clean_task()
            self.task_init()
            self.pats_status = [0] * self.n
            print(self.session_cnt, self.task_cnt, self.recog_type)
            # self.df = pd.DataFrame(columns=['signal'] + ['pat'+str(i) for i in range(self.n)])
            # start new recognizer thread for the new task
            self.stop_event.clear()
            self.recog = Recognizer(self.stop_event, self.select_event, self.sig_queue, self.pat_queues, self.recog_type,
                                    self.n, self.interval, self.pats_selected, self.model_period, self.model_delay, self.wins, self.THs)
            self.recog.start()
            # draw the posters and dots
            self.display()
            # blink the dot according to pats
            for i, item in enumerate(self.w.find_withtag('dot')):
                # print(self.pats_selected[i], i, item)
                self.after_handles.append(self.root.after(self.pats_selected[i][1], self.flash, item, i, 0))
            self.task_time = time.time()
            self.task_cnt += 1
            self.check_handles.append(self.root.after(1, self.target_check))

    def display(self):
        if self.n == 3:
            self.draw(1, 3, int(self.width / 20))
        elif self.n == 9:
            self.draw(3, 3, int(self.height / 30))
        elif self.n == 10:
            self.draw(2, 5, int(self.width / 20))
        elif self.n == 15:
            self.draw(3, 5, int(self.height / 30))
        elif self.n == 21:
            self.draw(3, 7, int(self.height / 30))

    def draw(self, n_row, n_col, padding):
        if n_row <= 2:
            wpadding = padding
            lpadding = rpadding = wpadding * 2
            image_width = int((self.width - lpadding - rpadding - wpadding * (n_col - 1)) / n_col)
            image_height = int(image_width * self.poster_aratio)
            tpadding = bpadding = hpadding = int((self.height - n_row * image_height) / (n_row + 1))
        else:
            hpadding = padding
            bpadding = hpadding
            tpadding = hpadding / 2
            image_height = int((self.height - tpadding - bpadding - hpadding * (n_row - 1)) / n_row)
            image_width = int(image_height / self.poster_aratio)
            wpadding = int(image_width / n_col)
            lpadding = rpadding = int((self.width - n_col * image_width - (n_col - 1) * wpadding) / 2)

        self.image_size = (image_width, image_height)
        dot_size = (40, 40)
        for i, image in enumerate(self.posters_selected):
            row = i % n_col
            col = int(i / n_col)
            x_center = lpadding + row * (wpadding + image_width) + int(image_width / 2)
            y_center = tpadding + col * (hpadding + image_height) + int(image_height / 2)
            # print(row, col, x_center, y_center)
            tkimage = ImageTk.PhotoImage(image.resize(self.image_size, Image.ANTIALIAS))
            self.tkimages.append(tkimage)
            self.w.create_image(x_center, y_center, image=tkimage, anchor='center',
                                tags=(str(i) + '_poster', 'poster'))
            x_ne, y_ne = x_center + int(image_width / 2), y_center - int(image_height / 2)
            self.w.create_rectangle(x_ne - dot_size[0], y_ne, x_ne, y_ne + dot_size[1], fill="red",
                                    tags=(str(i) + '_dot', 'dot'), outline='')

    def selected_interface(self):
        target_i = self.recog.get_target()
        target_poster = self.w.find_withtag(str(target_i) + '_poster')
        target_pos = self.w.coords(target_poster)
        rect_ltx = target_pos[0] - int(self.image_size[0] / 2)
        rect_lty = target_pos[1] - int(self.image_size[1] / 2)
        rect_rbx = target_pos[0] + int(self.image_size[0] / 2)
        rect_rby = target_pos[1] + int(self.image_size[1] / 2)
        self.w.create_rectangle(rect_ltx, rect_lty, rect_rbx, rect_rby, fill='', outline='cyan', width=10,
                                tag=('select',))

    def target_check(self):
        if self.select_event.is_set():
            self.stop_event.set()
            self.task_time = time.time() - self.task_time
            self.fpress_time = time.time() - self.fpress_time
            print('the mean is {}, median is {}, duration is {}'.format(np.mean(self.p[1:]), np.median(self.p[1:]), self.task_time))
            self.selected_interface()
            self.csvwriter.writerow([self.id, self.session_cnt, self.task_cnt-1, self.recog_type, self.pat_type, self.n,
                                     self.target, self.recog.get_target(), self.task_time, self.fpress_time])
            # self.df.loc[len(self.df.index)] = [self.id, self.session_cnt, self.task_cnt-1, self.recog_type, self.n, self.target, self.recog.get_target(),
            #                 self.task_time, self.fpress_time]
            # print(self.df)
            directory = './data/'+str(self.id)
            if not os.path.exists(directory):
                os.makedirs(directory)
            rawfile = directory +'/n'+str(self.n)+'_session'+str(self.session_cnt)+'_task'+\
                           str(self.task_cnt-1)+'_'+self.recog_type+'_'+self.pat_type + '_target'+str(self.target)+\
                           '_selected'+str(self.recog.get_target())+'.csv'
            with open(rawfile, 'w', newline='') as file:
                rawcsvwriter = csv.writer(file, delimiter=',')
                rawcsvwriter.writerow(['signal'] + ['pat'+str(i) for i in range(self.n)])
                for row in self.raw_row:
                    rawcsvwriter.writerow(row)
            return
        # update the input signal and pattern display status
        self.q_put(self.sig_queue, self.signal)
        for q, state in zip(self.pat_queues, self.pats_status):
            self.q_put(q, state)
        # self.df.loc[len(self.df.index)] = [self.signal] + self.pats_status
        self.raw_row.append([self.signal] + self.pats_status)
        self.check_handles.append(self.root.after(int(self.interval*1000), self.target_check))

    def q_put(self, q, data):
        if q.full():
            q.get()
        q.put(data)

    def flash(self, item, i, ptime, idx=0):
        # if a target is selected, stop blinking
        if self.select_event.is_set():
            self.w.itemconfigure(item, fill='')
            return
        # print(self.pats_selected[i], time.time()-ptime)
        # ptime = time.time()
        if idx:
            self.w.itemconfigure(item, fill='red')
        else:
            self.w.itemconfigure(item, fill='')
        try:
            self.after_handles.append(self.root.after(self.pats_selected[i][0], self.flash, item, i, ptime, (idx + 1) % 2))
            self.pats_status[i] = idx
            self.recog.set_display(self.pats_status)  # this is effectively a global variable, so single pass is enough
        except IndexError:
            print('IndexError: i is {}, pat length is {}, pat is {}'.format(i, len(self.pats_selected),
                                                                            self.pats_selected))

    def clean_task(self):
        self.rest_flag = 0
        self.w.focus_set()
        items = self.w.find_withtag('id')
        if len(items) > 0:
            self.L1.destroy()
            self.E1.destroy()
            self.id = self.id.get()
            print(self.id)
            for item in items:
                self.w.delete(item)
            self.csvfile = open('data/'+str(self.id)+'.csv', 'w', newline='')
            self.csvwriter = csv.writer(self.csvfile, delimiter=',')
            self.csvwriter.writerow(['user', 'session', 'block', 'recognizer', 'pat', 'nums', 'target_i', 'index_est', 'ctime', 'ttime'])

        # terminate the current thread and clear the selected flag
        self.p = list()
        self.stop_event.set()
        self.select_event.clear()
        if self.recog:
            self.recog.join()

        # cancel all after functions started in the current selection task
        if len(self.after_handles) > 0:
            for handle in self.after_handles:
                self.root.after_cancel(handle)
        if len(self.check_handles) > 0:
            for handle in self.check_handles:
                self.root.after_cancel(handle)
        # delete all poster and dot items on the canvas
        items = self.w.find_withtag('poster') + self.w.find_withtag('dot') + self.w.find_withtag('select')
        if len(items) > 0:
            # delete can only take one item at a time
            for item in items:
                self.w.delete(item)

        items = self.w.find_withtag('text')
        if len(items) > 0:
            # delete can only take one item at a time
            for item in items:
                self.w.delete(item)
        # if self.rest_text is not None:
        #     self.w.delete(self.rest_text)
        self.tkimages = []
        # self.df = pd.DataFrame()
        self.raw_row = list()
        # if self.sig_queue:
        #     with self.sig_queue.mutex:
        #         del self.sig_queue
        #     for q in self.pat_queues:
        #         with q.mutex:
        #             del q

    def clean_session(self):
        if len(self.rest_handles) > 0:
            for handle in self.rest_handles:
                self.root.after_cancel(handle)
        self.seq = []
        self.task_cnt = 0
        self.session_cnt += 1
        self.rest_cnt = 20

    def rest(self):
        self.w.itemconfigure(self.rest_text,
                             text='Session ' + str(self.session_cnt) + ' completed! Remaining rest time {}s'.format(
                                 self.rest_cnt))
        if self.rest_cnt == 0:
            self.w.itemconfigure(self.rest_text, text='Press RETURN to start session ' + str(self.session_cnt + 1))
        else:
            self.rest_cnt -= 1
            self.rest_handles.append(self.root.after(1000, self.rest))

    def rest_within(self):
        self.w.itemconfigure(self.rest_text,
                             text='Remaining rest time {}s'.format(self.rest_cnt))
        if self.rest_cnt == 0:
            self.w.itemconfigure(self.rest_text, text='Press RETURN to start!')
        else:
            self.rest_cnt -= 1
            self.rest_handles.append(self.root.after(1000, self.rest_within))

    def space_pressed(self, event):
        self.pressed += 1
        if self.pressed == 1:
            self.fpress_time = time.time()
        if self.signal == 0:
            self.p.append(time.time() - self.tprev)
            # print("pressed, time delta is {}".format(time.time() - self.tprev))
            self.tprev = time.time()
        if self.recog:
            self.signal = 1
            # self.recog.set_input(1)

    def space_released(self, event):
        if self.signal == 1:
            self.p.append(time.time() - self.tprev)
            # print("released, time delta is {}".format(time.time() - self.tprev))
            self.tprev = time.time()
        if self.recog:
            self.signal = 0
            # self.recog.set_input(0)

    def on_closing(self, event):
        self._on_closing()

    def _on_closing(self):
        print('CLOSING THE WINDOW...')
        self.clean_task()
        self.clean_session()
        self.csvfile.close()
        self.root.destroy()


periods_optimized = [[300, 450, 650], [300, 350, 400, 500, 600, 700], [300, 350, 400, 450, 500, 550, 600, 650, 700],
                [300, 350, 400, 450, 500, 550, 600, 650, 700, 700],
                [300, 350, 400, 450, 500, 550, 550, 600, 600, 650, 650, 650, 700, 700, 700],
                [300, 350, 400, 400, 450, 450, 500, 500, 500, 550, 550, 550, 600, 600, 600, 650, 650, 650, 700, 700, 700]]

delays_optimized = [[0, 0, 0], [0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0],
               [0, 0, 0, 0, 0, 0, 0, 0, 0, 467],
               [0, 0, 0, 0, 0, 0, 367, 0, 400, 0, 216, 433, 0, 233, 467],
               [0, 0, 0, 200, 0, 225, 0, 167, 333, 0, 183, 367, 0, 200, 400, 0, 216, 433, 0, 233, 467]]

periods_worst = [[300, 350, 350], [300, 350, 350, 400, 400, 450, 450, 500, 500],
                 [300, 350, 350, 400, 400, 450, 450, 500, 500, 500, 550, 550, 550, 600, 600],
                 [300, 350, 350, 400, 400, 450, 450, 500, 500, 500, 550, 550, 550, 600, 600, 600, 650, 650, 650, 700, 700]]
delays_worst = [[0, 0, 175], [0, 0, 175, 0, 200, 0, 225, 0, 167],
                [0, 0, 175, 0, 200, 0, 225, 0, 167, 333, 0, 183, 367, 0, 200],
                [0, 0, 175, 0, 200, 0, 225, 0, 167, 333, 0, 183, 367, 0, 200, 400, 0, 216, 433, 0, 233]]

all_pats = [[300, 0], [350, 0], [350, 175], [400, 0], [400, 200], [450, 0], [450, 225], [500, 0], [500, 167], [500, 333],
            [550, 0], [550, 183], [550, 367], [600, 0], [600, 200], [600, 400], [650, 0], [650, 216], [650, 433],
            [700, 0], [700, 233], [700, 467]]

pats_rand = [[[500, 0], [650, 433], [650, 216]],
             [[300, 0], [350, 175], [400, 200], [500, 167], [550, 183], [600, 400], [650, 433], [700, 0], [700, 467]],
             [[350, 175], [400, 0], [450, 225], [500, 0], [500, 167], [550, 367], [550, 0], [600, 400], [600, 0], [600, 200],
              [650, 216], [650, 433], [650, 0], [700, 0], [700, 233]],
             [[300, 0], [350, 175], [350, 0], [400, 200], [400, 0], [450, 0], [450, 225], [500, 333], [500, 0], [500, 167],
              [550, 0], [550, 367], [550, 183], [600, 0], [600, 200], [600, 400], [650, 433], [650, 0], [650, 216], [700, 467], [700, 0]]]

select_flag = -1


def pats_gen(periods_init, delays_init, n_pats):
    pats = [[] for _ in n_pats]
    for period, delay in zip(periods_init, delays_init):
        n = len(period)
        if n in n_pats:
            for p, d in zip(period, delay):
                pats[n_pats.index(n)].append([p, d])
    return pats


def randpat_get(all_pats, n_pats):
    random.seed(3)
    pats =[[] for _ in n_pats]
    for i, n in enumerate(n_pats):
        pats[i] = random.sample(all_pats, n)
        pats[i].sort(key=lambda x: x[0])
    return pats


if __name__ == '__main__':
    # create window with background picture
    root = tk.Tk()
    root.attributes("-fullscreen", True)
    # win_size = (1920, 1080)
    n_pats = [3, 9, 15, 21]
    app = MainApplication(root, n_pats)
    # app.set_winsize((1680, 1050))
    bg_file = "./photo/bg.jpg"
    app.set_background(bg_file)

    # pass in poster filenames and blinking patterns
    poster_files = ["./photo/" + str(i) + ".jpeg" for i in range(21)]
    app.set_posters(poster_files)
    pats_opt = pats_gen(periods_optimized, delays_optimized, n_pats)
    pats_worst = pats_gen(periods_worst, delays_worst, n_pats)
    # pats_rand = randpat_get(all_pats, n_pats)
    # print(pats_rand)
    app.set_pats(pats_opt, pats_worst, pats_rand)
    #
    # start mainloop
    root.mainloop()

    # n_pats = [3, 9, 15]
    # pats_opt = pats_gen(periods_optimized, delays_optimized, n_pats)
    # pats_worst = pats_gen(periods_worst, delays_worst, n_pats)
    # pats_rand = randpat_get(all_pats, n_pats)
    # print(pats_rand)
