#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from PIL import Image, ImageTk
import queue
import threading
import random


class Recognizer(threading.Thread):
    def __init__(self, stop_event, thread_id, name, n):
        threading.Thread.__init__(self)
        self.thread_id = thread_id
        self.name = name
        self.stopped = stop_event
        self.input_status = 0
        self.inteval = 0.01  # in second
        self.win = 2
        self.step = 0.01
        self.n = n
        self.pats_status = [0 for _ in range(self.n)]
        self.data_queue = queue.Queue(maxsize=int(self.win / self.step))
        self.pat_queues = [queue.Queue(maxsize=int(self.win / self.step)) for _ in range(self.n)]

    def set_input(self, _input):
        self.input_status = _input

    def set_display(self, display):
        self.pats_status = display

    def run(self):
        while not self.stopped.wait(self.inteval):
            self.data_queue.put(self.input_status)
            data, status = -1, []
            if self.data_queue.full():
                data = self.data_queue.get()
            for state, pat_queue in zip(self.pats_status, self.pat_queues):
                pat_queue.put(state)
                if pat_queue.full():
                    status.append(pat_queue.get())
            # print(data, status)
        self.quit()

    def quit(self):
        # after the thread is joined, all data will be self destroyed
        pass


class MainApplication(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.root = parent
        self.winsize = (1920, 1080)
        self.w = tk.Canvas(self.root, width=self.winsize[0], height=self.winsize[1])
        self.after_handles = []
        self.pats_status = []
        self.posters = []
        self.other_posters = None
        self.target_poster = None
        self.posters_selected = None
        self.tkimages = []
        self.pats = None
        self.pats_selected = None
        self.stop_event = threading.Event()
        self.recog = None
        self.n = 0
        self.cases = [3, 9, 15]
        self.task_cnt = 0
        self.session_cnt = 0

    def set_winsize(self, win_size):
        self.winsize = win_size
        self.w.configure(width=self.winsize[0], height=self.winsize[1])

    def set_background(self, bg_file):
        image = Image.open(bg_file).resize(self.winsize, Image.ANTIALIAS)
        self.tkbg = ImageTk.PhotoImage(image)
        self.w.create_image(0, 0, image=self.tkbg, anchor='nw')

    def set_posters(self, poster_files):
        for iamge_file in poster_files:
            self.posters.append(Image.open(iamge_file))
        self.other_posters = self.posters[1:]
        self.target_poster = self.posters[0]

    def set_images(self, image_seq):
        self.posters_selected = image_seq

    def set_pats(self, pat_set):
        self.pats = pat_set

    def state_machine(self):
        self.n = random.sample(self.cases, 1)[0]
        self.posters_selected = random.sample(self.other_posters, self.n - 1) + [self.target_poster]
        random.shuffle(self.posters_selected)
        self.pats_selected = self.pats[self.cases.index(self.n)]
        print(self.n, self.posters_selected, self.pats_selected)

    def id_input(self):
        pass

    def selection_task(self, event):
        self.state_machine()
        assert len(self.posters_selected) == len(self.pats_selected)
        self.n = len(self.posters_selected)
        self.pats_status = [0] * self.n
        # clean from previous task
        self.clean()
        # draw the posters and dots
        self.display()
        # start new recognizer thread for the new task
        self.stop_event.clear()
        self.recog = Recognizer(self.stop_event, 1, 'test', self.n)
        self.recog.start()
        # blink the dot according to pats
        for i, item in enumerate(self.w.find_withtag('dot')):
            # print(self.pats_selected[i], i, item)
            self.root.after(self.pats_selected[i][1], self.flash, item, i, 0)
        self.recog.set_display(self.pats_status)

    def display(self):
        image_size = (int(1200 / 5), int(1778 / 5))
        dot_size = (40, 40)
        left_padding = 100
        dist = 200
        for i, image in enumerate(self.posters_selected):
            x_center = left_padding + i * dist + (i + 1) * int(image_size[0] / 2)
            y_center = int(win_size[1] / 2)
            tkimage = ImageTk.PhotoImage(image.resize(image_size, Image.ANTIALIAS))
            self.tkimages.append(tkimage)
            self.w.create_image(x_center, y_center, image=tkimage, anchor='center', tags=(str(i) + '_poster', 'poster'))
            x_ne, y_ne = x_center + int(image_size[0] / 2), y_center - int(image_size[1] / 2)
            self.w.create_rectangle(x_ne - dot_size[0], y_ne, x_ne, y_ne + dot_size[1], fill="red",
                                    tags=(str(i) + '_dot', 'dot'), outline='')
        # print(self.w.find_withtag('poster')+self.w.find_withtag('dot'))

    def flash(self, item, i, idx=0):
        # cancel the previous after function (not necessary)
        # if self.after_handle:
        #     self.root.after_cancel(self.after_handle)
        stipples = ['@transparent.xbm', '']
        self.w.itemconfigure(item, fill='red', stipple=stipples[idx])
        # print(self.pats_selected, i)
        self.after_handles.append(self.root.after(self.pats_selected[i][0], self.flash, item, i, (idx + 1) % 2))
        self.pats_status[i] = idx

    def clean(self):
        # terminate the current thread
        self.stop_event.set()
        if self.recog:
            self.recog.join()
        # cancel all after functions started in the current selection task
        if len(self.after_handles) > 0:
            for handle in self.after_handles:
                self.root.after_cancel(handle)
        # delete all poster and dot items on the canvas
        items = self.w.find_withtag('poster') + self.w.find_withtag('dot')
        if len(items) > 0:
            # delete can only take one item at a time
            for item in items:
                self.w.delete(item)
        self.tkimages = []

    def space_pressed(self, event):
        if self.recog:
            self.recog.set_input(1)

    def space_released(self, event):
        if self.recog:
            self.recog.set_input(0)

    def on_closing(self):
        print('CLOSING THE WINDOW...')
        self.clean()
        self.root.destroy()


periods_init = [[300, 450, 650], [300, 350, 400, 500, 600, 700], [300, 350, 400, 450, 500, 600, 600, 700, 700],
                [300, 350, 400, 400, 450, 450, 500, 500, 600, 600, 700, 700],
                [300, 350, 350, 400, 400, 450, 450, 500, 500, 550, 550, 600, 600, 700, 700],
                [300, 350, 350, 400, 400, 450, 450, 500, 500, 550, 550, 600, 600, 650, 650, 650, 700, 700]]

delays_init = [[0, 0, 0], [0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 396, 0, 433],
               [0, 0, 0, 200, 0, 225, 0, 320, 0, 396, 0, 433],
               [0, 0, 175, 0, 200, 0, 225, 0, 320, 0, 362, 0, 396, 0, 433],
               [0, 0, 175, 0, 200, 0, 225, 0, 320, 0, 362, 0, 396, 0, 198, 396, 0, 433]]


def pats_gen(periods_init, delays_init):
    n_pats = [3, 9, 15]
    pats = [[] for _ in n_pats]
    for period, delay in zip(periods_init, delays_init):
        n = len(period)
        if n in n_pats:
            for p, d in zip(period, delay):
                pats[n_pats.index(n)].append([p, d])
    return pats

bg_file = "./photo/bg.jpg"

if __name__ == '__main__':
    # create window with background picture
    root = tk.Tk()
    # win_size = (1920, 1080)
    win_size = (3840, 2160)
    print(win_size)
    app = MainApplication(root)
    # app.set_winsize(win_size)
    app.set_background(bg_file)

    poster_files = ["./photo/" + str(i) + ".jpeg" for i in range(15)]
    app.set_posters(poster_files)
    pats = pats_gen(periods_init, delays_init)
    app.set_pats(pats)

    # start new selection task when hit Return
    app.w.focus_set()
    app.w.bind('<Return>', app.selection_task)
    # collect space key status
    app.w.bind('<KeyPress-space>', app.space_pressed)
    app.w.bind('<KeyRelease-space>', app.space_released)
    # app.task(posters_tk, range(n))
    app.root.protocol("WM_DELETE_WINDOW", app.on_closing)

    app.w.pack()

    root.mainloop()
