from os import truncate
from random import random
from tkinter import DISABLED, NORMAL
from tkinter.ttk import Label

import serial
import threading
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import tkinter as tk
import time

from RepeatedTimer import RepeatedTimer

rt = None

PCK_SIZE = 512

dataDB = np.arange(PCK_SIZE + 1)
data = np.arange(PCK_SIZE)
payload_counter = 0

HEADER_A = 0x10
HEADER_B = 0x55
TAILER = 0xAA

N_POINTS_X = 512
N_POINTS_Y = 255
PLOT_HOP_SIZE = 10

pck_ready = False
pck_synced = False

header1_detected = False
header2_detected = False

data_plot = np.arange(N_POINTS_X)
data_accum = np.array([])

kill_thread = False
sample_rate_value = None

SampleCounter = 0


def serial_event():
    global serialInput, payload_counter, pck_ready, data, pck_synced, header1_detected, header2_detected, SampleCounter

    while kill_thread == False:
        input_byte = ord(serialInput.read(1))

        if pck_synced:
            dataDB[payload_counter] = input_byte
            payload_counter = payload_counter + 1

            if payload_counter > PCK_SIZE:
                if input_byte == TAILER:
                    data = np.copy(dataDB[0:(payload_counter - 1)])
                    pck_ready = True
                    pck_synced = False
                    SampleCounter = SampleCounter + PCK_SIZE + 1
                    payload_counter = 0

                else:
                    pck_synced = False
                    payload_counter = 0

        else:
            if input_byte == HEADER_A:
                header1_detected = True
            else:
                if header1_detected and input_byte == HEADER_B:
                    pck_synced = True


serialInput = None


def start_acq():
    global serialInput, kill_thread, stop, start, COMPort, rt
    # Init Serial Ports
    kill_thread = False
    portName = COMPort.get()
    if portName is not None:
        serialInput = serial.Serial(portName, 115200)
        thread_listener_serial = threading.Thread(target=serial_event)
        thread_listener_serial.start()
        stop['state'] = NORMAL
        start['state'] = DISABLED
        rt = RepeatedTimer(0.5, TimerHandler, 0.5)


def stop_acq():
    global serialInput, kill_thread
    kill_thread = True
    serialInput.close()
    start['state'] = NORMAL
    rt.stop()


# -----plot data-----

def plot_data():
    global cond, data, pck_ready, data_plot, data_accum

    if pck_ready:
        pck_ready = False

        # if len(data_accum) < PLOT_HOP_SIZE:
        #     data_accum = np.append(data_accum, data[0:PCK_SIZE])
        # else:
        #     for i in range(N_POINTS_X - PLOT_HOP_SIZE):
        #         data_plot[i] = data_plot[i + PLOT_HOP_SIZE - 1]
        #
        #     for i in range(PLOT_HOP_SIZE):
        #         data_plot[(N_POINTS_X - PLOT_HOP_SIZE) + i] = data_accum[i]

        data_accum = np.array([])

        lines.set_xdata(np.arange(0, len(data)))
        lines.set_ydata(data)

        canvas.draw()

        # for i in range(POINT_TO_PLOT-10):
        #     data_plot[i] = data_plot[i+10]

    root.after(5, plot_data)


def TimerHandler(params):
    global SampleCounter, sample_rate_value
    sampleRate = (SampleCounter / params)
    SampleCounter = 0
    sampleRateReformat = sampleRate/1000
    buff = "%.1f" % sampleRateReformat
    buff = buff + " ksps"
    sample_rate_value.config(text=buff)


# Init GUI
root = tk.Tk()
root.title('Real Time FFT Plotter')
root.configure(background='light blue')
root.geometry("1600x500")  # set the window size

fig = Figure()
fig.set_facecolor('xkcd:tangerine')
ax = fig.add_subplot(111)

ax.set_title('Serial Data')
ax.set_xlabel('Frequency (kHz)')
ax.set_ylabel('A. U.')
ax.set_xlim(0, N_POINTS_X)


ax.set_xticks(np.arange(0, 520, 64))

ax.set_xticklabels(['0','2.7','5.5', '8.2','11','13.7', '16.5','19.2', '22'])



ax.set_ylim(0, N_POINTS_Y)
ax.set_facecolor('xkcd:charcoal')
lines = ax.plot([], [])[0]

canvas = FigureCanvasTkAgg(fig, master=root)  # A tk.DrawingArea.
canvas.get_tk_widget().place(x=10, y=10, width=1580, height=400)
canvas.draw()

# Create controls
root.update()
start = tk.Button(root, text="Start", font=('calbiri', 12), command=lambda: start_acq())
start.place(x=100, y=450)

COMPort = tk.Entry(root)
COMPort.place(x=start.winfo_x() + start.winfo_reqwidth() + 120, y=450 + 5)
COMPort.insert(0, 'COM1')

root.update()
stop = tk.Button(root, text="Stop", font=('calbiri', 12), command=lambda: stop_acq(), state=DISABLED)
stop.place(x=start.winfo_x() + start.winfo_reqwidth() + 150, y=450)

sample_rate_label = tk.Label(root, text="Current Sample Rate").place(x=start.winfo_x() + start.winfo_reqwidth() + 300,y=450)
sample_rate_value = Label(root, text="0.0 ksps")
sample_rate_value.place(x=start.winfo_x() + start.winfo_reqwidth() + 430, y=450)

root.after(1, plot_data)
root.mainloop()
