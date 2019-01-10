import queue
import threading
import random
global select_flag
class Recognizer(threading.Thread):
    def __init__(self, stop_event, select_event, thread_id, name, n):
        threading.Thread.__init__(self)
        self.thread_id = thread_id
        self.name = name
        self.stopped = stop_event
        self.select = select_event
        self.target = -1
        self.input_status = 0
        # self.select_flag = select_flag
        self.inteval = 0.01  # in second
        self.win = 3
        self.step = 0.01
        self.n = n
        self.pats_status = [0 for _ in range(self.n)]
        self.data_queue = queue.Queue(maxsize=int(self.win / self.step))
        self.pat_queues = [queue.Queue(maxsize=int(self.win / self.step)) for _ in range(self.n)]
        # self.qflag = qflag

    def set_input(self, _input):
        self.input_status = _input

    def set_display(self, display):
        self.pats_status = display

    def get_target(self):
        return self.target

    def run(self):
        while not self.stopped.wait(self.inteval):
            self.data_queue.put(self.input_status)
            data, status = -1, []
            if self.data_queue.full():
                data = self.data_queue.get()
                self.select.set()
                self.target = random.sample(range(self.n), 1)[0]

            for state, pat_queue in zip(self.pats_status, self.pat_queues):
                pat_queue.put(state)
                if pat_queue.full():
                    status.append(pat_queue.get())
            # print(data, status)
        self.quit()

    def quit(self):
        # after the thread is joined, all data will be self destroyed
        pass