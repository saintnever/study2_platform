#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from PIL import Image, ImageTk
from collections import deque
import queue
import threading
from random import shuffle


def convert_tkimage(filename, image_size):
    if type(filename) is str:
        image = Image.open(filename).resize(image_size, Image.ANTIALIAS)
        tkimage = ImageTk.PhotoImage(image)
        return tkimage
    if len(filename) >= 1:
        tkimage = list()
        for image_file in filename:
            image = Image.open(image_file).resize(image_size, Image.ANTIALIAS)
            tkimage.append(ImageTk.PhotoImage(image))
        return tkimage
    else:
        return []


class Recognizer(threading.Thread):
    def __init__(self, stop_event, thread_id, name):
        threading.Thread.__init__(self)
        self.thread_id = thread_id
        self.name = name
        self.stopped = stop_event
        self.input_status = 0
        self.display_status = 0
        self.inteval = 0.02  # in ms
        self.win = 2
        self.step = 0.02
        self.data_queue = queue.LifoQueue(maxsize=int(self.win / self.step))
        self.display_queue = queue.LifoQueue(maxsize=int(self.win / self.step))

    def set_input(self, _input):
        self.input_status = _input

    def set_display(self, display):
        self.display_status = display

    def run(self):
        while not self.stopped.wait(self.inteval):
            # print(self.input_status, self.display_status)
            self.data_queue.put(self.input_status)
            self.display_queue.put(self.display_status)
            data, state = -1, -1
            if self.data_queue.full():
                data = self.data_queue.get()
            if self.display_queue.full():
                state = self.display_queue.get()
            print(data, state)
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
        self.after_handle = None
        self.images = None
        self.pats = None
        self.stop_event = threading.Event()
        self.recog = None

    def set_winsize(self, win_size):
        self.winsize = win_size

    def set_background(self, bg_tkimage):
        self.w.create_image(0, 0, image=bg_tkimage, anchor='nw')

    def set_images(self, image_seq):
        self.images = image_seq

    def set_pats(self, pat_set):
        self.pats = pat_set

    def id_input(self):
        pass

    def selection_task(self, event):
        self.clean()
        shuffle(self.images)
        self.stop_event.clear()
        self.recog = Recognizer(self.stop_event, 1, 'test')
        self.recog.start()
        print(threading.activeCount())
        self.task()
        self.flash()

    def task(self):
        assert len(self.images) == len(self.pats)
        n = len(self.images)
        image_size = (int(1200 / n), int(1778 / n))
        dot_size = (40, 40)
        left_padding = 200
        dist = 400
        for i, image in enumerate(self.images):
            x_center = left_padding + i * dist + (i + 1) * int(image_size[0] / 2)
            y_center = int(win_size[1] / 2)
            self.w.create_image(x_center, y_center, image=image, anchor='center', tags=(str(i) + '_poster', 'poster'))
            x_ne, y_ne = x_center + int(image_size[0] / 2), y_center - int(image_size[1] / 2)
            self.w.create_rectangle(x_ne - dot_size[0], y_ne, x_ne, y_ne + dot_size[1], fill="red",
                                    tags=(str(i) + '_dot', 'dot'), outline='')
        # print(self.w.find_withtag('poster')+self.w.find_withtag('dot'))

    def clean(self):
        # terminate the current thread
        self.stop_event.set()
        if self.recog:
            self.recog.join()
        # cancel the on-going after function
        if self.after_handle:
            self.root.after_cancel(self.after_handle)
        # delete all poster and dot items on the canvas
        items = self.w.find_withtag('poster') + self.w.find_withtag('dot')
        if len(items) > 0:
            # delete can only take one item at a time
            for item in items:
                self.w.delete(item)

    def flash(self, idx=0):
        if self.recog:
            self.recog.set_display(idx)
        # cancel the previous after function
        if self.after_handle:
            self.root.after_cancel(self.after_handle)
        stipples = ['', '@transparent.xbm']
        for i in range(3):
            # print(self.w.find_withtag('dot'))
            self.w.itemconfigure(self.w.find_withtag(str(i) + '_dot'), fill='red', stipple=stipples[idx])
        self.after_handle = self.root.after(500, self.flash, (idx + 1) % 2)

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


if __name__ == '__main__':
    # create window with background picture
    root = tk.Tk()
    win_size = (1920, 1080)

    app = MainApplication(root)
    app.set_winsize(win_size)
    bg_tkimage = convert_tkimage("./photo/bg.jpg", app.winsize)
    app.set_background(bg_tkimage)

    n = 3
    poster_files = ["./photo/" + str(i) + ".jpeg" for i in range(n)]
    posters_tk = convert_tkimage(poster_files, (int(1200 / n), int(1778 / n)))
    app.set_images(posters_tk)
    app.set_pats(range(n))
    app.w.focus_set()
    app.w.bind('<Return>', app.selection_task)

    # collect space key status
    app.w.bind('<KeyPress-space>', app.space_pressed)
    app.w.bind('<KeyRelease-space>', app.space_released)
    # app.task(posters_tk, range(n))
    app.root.protocol("WM_DELETE_WINDOW", app.on_closing)

    app.w.pack()

    root.mainloop()
