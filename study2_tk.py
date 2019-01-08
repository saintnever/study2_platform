#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from PIL import Image, ImageTk
from collections import deque
import _thread
from random import shuffle


class MainApplication(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.root = parent
        self.winsize = (1920, 1080)
        self.w = tk.Canvas(self.root, width=self.winsize[0], height=self.winsize[1])
        self.after_handle = None
        self.images = None
        self.pats = None

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
        print(self.w.find_withtag('poster')+self.w.find_withtag('dot'))

    def clean(self):
        if self.after_handle:
            self.root.after_cancel(self.after_handle)
        items = self.w.find_withtag('poster')+self.w.find_withtag('dot')
        if len(items) > 0:
            for item in items:
                self.w.delete(item)

    def flash(self, idx=0):
        print(idx)
        # cancel the previous after function
        if self.after_handle:
            self.root.after_cancel(self.after_handle)
        stipples = ['', '@transparent.xbm']
        for i in range(3):
            print(self.w.find_withtag('dot'))
            self.w.itemconfigure(self.w.find_withtag(str(i)+'_dot'), fill='red', stipple=stipples[idx])
        self.after_handle = self.root.after(500, self.flash, (idx + 1) % 2)


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
    app.w.bind('<Button-1>', app.selection_task)
    # app.bind('<Key>', app.clean())
    # app.task(posters_tk, range(n))
    app.w.pack()

    root.mainloop()

