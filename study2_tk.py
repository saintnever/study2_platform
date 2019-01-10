#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from PIL import Image, ImageTk
from recognizer import Recognizer
import threading
import random
import queue


class MainApplication(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
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
        self.pats_selected = None
        self.stop_event = threading.Event()
        self.select_event = threading.Event()
        self.n = 0
        self.pats_status = None
        self.cases = [3]
        # self.recog_typelist = ['corr', 'baye', 'ml']
        self.recog_typelist = ['corr', 'corr', 'corr']
        self.recog = None
        self.recog_type = None
        self.task_cnt = 0
        self.session_cnt = 0
        self.rest_cnt = 20
        self.seq = []
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

    def set_pats(self, pat_set):
        self.pats = pat_set

    def state_machine(self):
        # init the task sequence for current session
        if self.task_cnt == 0:
            for case in self.cases:
                for rcog in self.recog_typelist:
                    self.seq.append([case, rcog])
            random.shuffle(self.seq)
        # assign n and recognizer type for current task
        self.n = self.seq[self.task_cnt][0]
        self.recog_type = self.seq[self.task_cnt][1]
        self.posters_selected = random.sample(self.other_posters, self.n - 1) + [self.target_poster]
        random.shuffle(self.posters_selected)
        for pat in self.pats:
            if len(pat) == self.n:
                self.pats_selected = pat
        assert len(self.posters_selected) == len(self.pats_selected)

    def id_input(self):
        pass

    def selection_task(self, event):
        if self.task_cnt == len(self.cases) * len(self.recog_typelist):
            # clean from previous task
            self.clean_task()
            self.clean_session()
            self.rest_text = self.w.create_text(int(self.width / 2), int(self.height / 2), anchor='center',
                                                fill='orange', font=("Microsoft YaHei", 50),
                                                text='Remaining rest time {}s'.format(self.rest_cnt))
            self.rest_handles.append(self.root.after(1, self.rest))
        else:
            # clean from previous task
            self.clean_task()
            self.state_machine()
            self.pats_status = [0] * self.n
            # start new recognizer thread for the new task
            self.stop_event.clear()
            self.recog = Recognizer(self.stop_event, self.select_event, self.cases.index(self.n), self.recog_type,
                                    self.n)
            self.recog.start()
            # draw the posters and dots
            self.display()
            # blink the dot according to pats
            for i, item in enumerate(self.w.find_withtag('dot')):
                # print(self.pats_selected[i], i, item)
                self.after_handles.append(self.root.after(self.pats_selected[i][1], self.flash, item, i, 0))
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
            col = i / n_col
            x_center = lpadding + row * (wpadding + image_width) + int(image_width / 2)
            y_center = tpadding + col * (hpadding + image_height) + int(image_height / 2)
            # print(col, x_center, y_center)
            tkimage = ImageTk.PhotoImage(image.resize(self.image_size, Image.ANTIALIAS))
            self.tkimages.append(tkimage)
            self.w.create_image(x_center, y_center, image=tkimage, anchor='center',
                                tags=(str(i) + '_poster', 'poster'))
            x_ne, y_ne = x_center + int(image_width / 2), y_center - int(image_height / 2)
            self.w.create_rectangle(x_ne - dot_size[0], y_ne, x_ne, y_ne + dot_size[1], fill="red",
                                    tags=(str(i) + '_dot', 'dot'), outline='')

    def selected_interface(self):
        target_i = self.recog.get_target()
        print(target_i)
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
            self.selected_interface()
            return
        # update the pattern display status
        self.recog.set_display(self.pats_status)
        self.check_handles.append(self.root.after(5, self.target_check))

    def flash(self, item, i, idx=0):
        # if a target is selected, stop blinking
        if self.select_event.is_set():
            self.w.itemconfigure(item, fill='')
            return
        if idx:
            self.w.itemconfigure(item, fill='red')
        else:
            self.w.itemconfigure(item, fill='')
        try:
            self.after_handles.append(self.root.after(self.pats_selected[i][0], self.flash, item, i, (idx + 1) % 2))
            self.pats_status[i] = idx
        except IndexError:
            print('IndexError: i is {}, pat length is {}, pat is {}'.format(i, len(self.pats_selected),
                                                                            self.pats_selected))

    def clean_task(self):
        # terminate the current thread and clear the selected flag
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
        if self.rest_text is not None:
            self.w.delete(self.rest_text)
        self.tkimages = []

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

    def space_pressed(self, event):
        if self.recog:
            self.recog.set_input(1)

    def space_released(self, event):
        if self.recog:
            self.recog.set_input(0)

    def on_closing(self, event):
        self._on_closing()

    def _on_closing(self):
        print('CLOSING THE WINDOW...')
        self.clean_task()
        self.clean_session()
        self.root.destroy()


periods_init = [[300, 450, 650], [300, 350, 400, 500, 600, 700], [300, 350, 400, 450, 500, 600, 600, 700, 700],
                [300, 350, 400, 450, 500, 550, 600, 650, 700, 700],
                [300, 350, 400, 400, 450, 450, 500, 500, 600, 600, 700, 700],
                [300, 350, 350, 400, 400, 450, 450, 500, 500, 550, 550, 600, 600, 700, 700],
                [300, 350, 350, 400, 400, 450, 450, 500, 500, 550, 550, 600, 600, 650, 650, 650, 700, 700]]

delays_init = [[0, 0, 0], [0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 396, 0, 433],
               [0, 0, 0, 0, 0, 0, 0, 0, 0, 467], [0, 0, 0, 200, 0, 225, 0, 320, 0, 396, 0, 467],
               [0, 0, 175, 0, 200, 0, 225, 0, 320, 0, 362, 0, 396, 0, 433],
               [0, 0, 175, 0, 200, 0, 225, 0, 320, 0, 362, 0, 396, 0, 198, 396, 0, 433]]

select_flag = -1


def pats_gen(periods_init, delays_init):
    n_pats = [3, 9, 10, 15]
    pats = [[] for _ in n_pats]
    for period, delay in zip(periods_init, delays_init):
        n = len(period)
        if n in n_pats:
            for p, d in zip(period, delay):
                pats[n_pats.index(n)].append([p, d])
    return pats


if __name__ == '__main__':
    # create window with background picture
    root = tk.Tk()
    root.attributes("-fullscreen", False)
    # win_size = (1920, 1080)
    app = MainApplication(root)
    bg_file = "./photo/bg.jpg"
    app.set_background(bg_file)

    # pass in poster filenames and blinking patterns
    poster_files = ["./photo/" + str(i) + ".jpeg" for i in range(15)]
    app.set_posters(poster_files)
    pats = pats_gen(periods_init, delays_init)
    app.set_pats(pats)

    # start mainloop
    root.mainloop()
