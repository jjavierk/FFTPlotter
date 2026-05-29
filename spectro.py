import threading
import tkinter as tk
from tkinter import ttk

import serial
import numpy as np

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


# ============================================================
# Packet / data configuration
# ============================================================

PCK_SIZE = 512

HEADER_A = 0x10
HEADER_B = 0x55
TAILER = 0xAA

SERIAL_BAUDRATE = 115200

N_FREQ_BINS = PCK_SIZE
N_TIME_COLUMNS = 350

DEFAULT_INTENSITY_MIN = 0
DEFAULT_INTENSITY_MAX = 255


# ============================================================
# Globals
# ============================================================

serialInput = None
serial_thread = None
kill_thread = False

latest_fft = np.zeros(PCK_SIZE, dtype=np.uint8)
pck_ready = False

data_lock = threading.Lock()

SampleCounter = 0

spectrogram = np.zeros((N_FREQ_BINS, N_TIME_COLUMNS), dtype=np.float32)


# ============================================================
# Serial receiver thread
# ============================================================

def serial_event():
    global serialInput
    global kill_thread
    global latest_fft
    global pck_ready
    global SampleCounter

    state = 0
    payload = bytearray()

    while not kill_thread:
        try:
            byte_read = serialInput.read(1)

            if len(byte_read) == 0:
                continue

            b = byte_read[0]

            if state == 0:
                # Waiting for first header byte
                if b == HEADER_A:
                    state = 1

            elif state == 1:
                # Waiting for second header byte
                if b == HEADER_B:
                    payload.clear()
                    state = 2
                elif b == HEADER_A:
                    state = 1
                else:
                    state = 0

            elif state == 2:
                # Reading FFT payload
                payload.append(b)

                if len(payload) == PCK_SIZE:
                    state = 3

            elif state == 3:
                # Waiting for tailer
                if b == TAILER:
                    with data_lock:
                        latest_fft = np.frombuffer(bytes(payload), dtype=np.uint8).copy()
                        pck_ready = True
                        SampleCounter += PCK_SIZE

                payload.clear()
                state = 0

        except serial.SerialException:
            break

        except Exception as e:
            print("Serial thread error:", e)
            payload.clear()
            state = 0


# ============================================================
# Acquisition control
# ============================================================

def start_acq():
    global serialInput
    global serial_thread
    global kill_thread

    port_name = com_port_var.get().strip()

    if not port_name:
        status_var.set("No COM port selected.")
        return

    try:
        kill_thread = False

        serialInput = serial.Serial(
            port=port_name,
            baudrate=SERIAL_BAUDRATE,
            timeout=0.1
        )

        serial_thread = threading.Thread(target=serial_event, daemon=True)
        serial_thread.start()

        start_button.config(state=tk.DISABLED)
        stop_button.config(state=tk.NORMAL)

        status_var.set(f"Connected to {port_name} at {SERIAL_BAUDRATE} baud")

    except Exception as e:
        status_var.set(f"Could not open serial port: {e}")


def stop_acq():
    global serialInput
    global kill_thread

    kill_thread = True

    try:
        if serialInput is not None and serialInput.is_open:
            serialInput.close()
    except Exception as e:
        print("Error closing serial port:", e)

    start_button.config(state=tk.NORMAL)
    stop_button.config(state=tk.DISABLED)

    status_var.set("Disconnected")


def clear_spectrogram():
    global spectrogram

    spectrogram[:, :] = 0
    img.set_data(spectrogram)
    canvas.draw_idle()


def on_closing():
    stop_acq()
    root.destroy()


# ============================================================
# GUI update functions
# ============================================================

def plot_data():
    global pck_ready
    global spectrogram

    new_frame_available = False

    with data_lock:
        if pck_ready:
            fft_frame = latest_fft.astype(np.float32)
            pck_ready = False
            new_frame_available = True

    if new_frame_available:
        # Scroll left
        spectrogram[:, :-1] = spectrogram[:, 1:]

        # Add new FFT frame on the right
        spectrogram[:, -1] = fft_frame

        img.set_data(spectrogram)
        canvas.draw_idle()

    root.after(5, plot_data)


def update_sample_rate():
    global SampleCounter

    elapsed = 0.5

    with data_lock:
        sample_rate = SampleCounter / elapsed
        SampleCounter = 0

    sample_rate_k = sample_rate / 1000.0
    sample_rate_var.set(f"{sample_rate_k:.1f} ksps")

    root.after(int(elapsed * 1000), update_sample_rate)


def update_intensity_from_sliders(_event=None):
    vmin = intensity_min_var.get()
    vmax = intensity_max_var.get()

    if vmax <= vmin:
        vmax = vmin + 1
        intensity_max_var.set(vmax)

    img.set_clim(vmin=vmin, vmax=vmax)

    intensity_label_var.set(f"{vmin:.0f} to {vmax:.0f}")
    canvas.draw_idle()


def update_colormap(_event=None):
    cmap = colormap_var.get()
    img.set_cmap(cmap)
    canvas.draw_idle()


# ============================================================
# GUI
# ============================================================

root = tk.Tk()
root.title("Real-Time FFT Spectrogram")
root.geometry("1650x720")
root.configure(bg="#101820")

style = ttk.Style()
style.theme_use("clam")

style.configure(
    "TFrame",
    background="#101820"
)

style.configure(
    "Panel.TFrame",
    background="#182430",
    relief="flat"
)

style.configure(
    "TLabel",
    background="#101820",
    foreground="#E8EEF2",
    font=("Segoe UI", 10)
)

style.configure(
    "Panel.TLabel",
    background="#182430",
    foreground="#E8EEF2",
    font=("Segoe UI", 10)
)

style.configure(
    "Title.TLabel",
    background="#101820",
    foreground="#FFFFFF",
    font=("Segoe UI", 18, "bold")
)

style.configure(
    "Status.TLabel",
    background="#101820",
    foreground="#AAB7C4",
    font=("Segoe UI", 9)
)

style.configure(
    "TButton",
    font=("Segoe UI", 10),
    padding=6
)

style.configure(
    "TEntry",
    padding=4
)

style.configure(
    "TCombobox",
    padding=4
)


# ============================================================
# Tkinter variables
# ============================================================

com_port_var = tk.StringVar(value="COM1")
sample_rate_var = tk.StringVar(value="0.0 ksps")
status_var = tk.StringVar(value="Disconnected")

intensity_min_var = tk.DoubleVar(value=DEFAULT_INTENSITY_MIN)
intensity_max_var = tk.DoubleVar(value=DEFAULT_INTENSITY_MAX)

intensity_label_var = tk.StringVar(
    value=f"{DEFAULT_INTENSITY_MIN} to {DEFAULT_INTENSITY_MAX}"
)

colormap_var = tk.StringVar(value="inferno")


# ============================================================
# Main layout
# ============================================================

main_frame = ttk.Frame(root)
main_frame.pack(fill=tk.BOTH, expand=True, padx=14, pady=14)

title_label = ttk.Label(
    main_frame,
    text="Real-Time FFT Spectrogram",
    style="Title.TLabel"
)
title_label.pack(anchor="w", pady=(0, 10))


# ============================================================
# Plot frame
# ============================================================

plot_frame = ttk.Frame(main_frame, style="Panel.TFrame")
plot_frame.pack(fill=tk.BOTH, expand=True)


fig = Figure(figsize=(12, 5), dpi=100)
fig.patch.set_facecolor("#182430")

ax = fig.add_subplot(111)
ax.set_facecolor("#0B1117")

img = ax.imshow(
    spectrogram,
    aspect="auto",
    origin="lower",
    interpolation="nearest",
    vmin=DEFAULT_INTENSITY_MIN,
    vmax=DEFAULT_INTENSITY_MAX,
    cmap=colormap_var.get(),
    extent=[0, N_TIME_COLUMNS, 0, N_FREQ_BINS]
)

ax.set_title("FFT Intensity Over Time", color="white", pad=14)
ax.set_xlabel("Time", color="white")
ax.set_ylabel("Frequency (kHz)", color="white")

ax.tick_params(axis="x", colors="white")
ax.tick_params(axis="y", colors="white")

for spine in ax.spines.values():
    spine.set_color("#6C7A89")

ax.set_xlim(0, N_TIME_COLUMNS)
ax.set_ylim(0, N_FREQ_BINS)

ax.set_xticks(np.linspace(0, N_TIME_COLUMNS, 6))
ax.set_xticklabels(["old", "", "", "", "", "new"])

# Same frequency labels as your original code
ax.set_yticks(np.arange(0, 520, 64))
ax.set_yticklabels([
    "0",
    "2.7",
    "5.5",
    "8.2",
    "11",
    "13.7",
    "16.5",
    "19.2",
    "22"
])

cbar = fig.colorbar(img, ax=ax)
cbar.set_label("FFT magnitude / A.U.", color="white")
cbar.ax.yaxis.set_tick_params(color="white")
cbar.outline.set_edgecolor("#6C7A89")

for label in cbar.ax.get_yticklabels():
    label.set_color("white")

fig.tight_layout()

canvas = FigureCanvasTkAgg(fig, master=plot_frame)
canvas_widget = canvas.get_tk_widget()
canvas_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
canvas.draw()


# ============================================================
# Control panel
# ============================================================

control_frame = ttk.Frame(main_frame, style="Panel.TFrame")
control_frame.pack(fill=tk.X, pady=(12, 0), ipady=8)


# -----------------------------
# Row 0: connection controls
# -----------------------------

ttk.Label(
    control_frame,
    text="COM port:",
    style="Panel.TLabel"
).grid(row=0, column=0, padx=(14, 6), pady=8, sticky="w")

com_entry = ttk.Entry(
    control_frame,
    width=12,
    textvariable=com_port_var
)
com_entry.grid(row=0, column=1, padx=6, pady=8, sticky="w")

start_button = ttk.Button(
    control_frame,
    text="Start",
    command=start_acq
)
start_button.grid(row=0, column=2, padx=6, pady=8)

stop_button = ttk.Button(
    control_frame,
    text="Stop",
    command=stop_acq,
    state=tk.DISABLED
)
stop_button.grid(row=0, column=3, padx=6, pady=8)

clear_button = ttk.Button(
    control_frame,
    text="Clear",
    command=clear_spectrogram
)
clear_button.grid(row=0, column=4, padx=6, pady=8)

ttk.Label(
    control_frame,
    text="Sample rate:",
    style="Panel.TLabel"
).grid(row=0, column=5, padx=(30, 6), pady=8, sticky="e")

ttk.Label(
    control_frame,
    textvariable=sample_rate_var,
    style="Panel.TLabel"
).grid(row=0, column=6, padx=6, pady=8, sticky="w")


# -----------------------------
# Row 1: intensity controls
# -----------------------------

ttk.Label(
    control_frame,
    text="Min intensity:",
    style="Panel.TLabel"
).grid(row=1, column=0, padx=(14, 6), pady=8, sticky="w")

intensity_min_slider = ttk.Scale(
    control_frame,
    from_=0,
    to=255,
    orient=tk.HORIZONTAL,
    variable=intensity_min_var,
    command=update_intensity_from_sliders,
    length=240
)
intensity_min_slider.grid(
    row=1,
    column=1,
    columnspan=3,
    padx=6,
    pady=8,
    sticky="we"
)

ttk.Label(
    control_frame,
    text="Max intensity:",
    style="Panel.TLabel"
).grid(row=1, column=4, padx=(30, 6), pady=8, sticky="w")

intensity_max_slider = ttk.Scale(
    control_frame,
    from_=1,
    to=255,
    orient=tk.HORIZONTAL,
    variable=intensity_max_var,
    command=update_intensity_from_sliders,
    length=240
)
intensity_max_slider.grid(
    row=1,
    column=5,
    columnspan=3,
    padx=6,
    pady=8,
    sticky="we"
)

ttk.Label(
    control_frame,
    textvariable=intensity_label_var,
    style="Panel.TLabel"
).grid(row=1, column=8, padx=(20, 10), pady=8, sticky="w")


# -----------------------------
# Row 2: colormap and status
# -----------------------------

ttk.Label(
    control_frame,
    text="Colormap:",
    style="Panel.TLabel"
).grid(row=2, column=0, padx=(14, 6), pady=8, sticky="w")

colormap_box = ttk.Combobox(
    control_frame,
    textvariable=colormap_var,
    values=[
        "inferno",
        "plasma",
        "viridis",
        "magma",
        "cividis",
        "turbo",
        "jet",
        "hot"
    ],
    state="readonly",
    width=14
)
colormap_box.grid(row=2, column=1, padx=6, pady=8, sticky="w")
colormap_box.bind("<<ComboboxSelected>>", update_colormap)

ttk.Label(
    control_frame,
    textvariable=status_var,
    style="Panel.TLabel"
).grid(row=2, column=2, columnspan=6, padx=20, pady=8, sticky="w")


# Make selected columns stretch nicely
control_frame.columnconfigure(1, weight=1)
control_frame.columnconfigure(5, weight=1)


# ============================================================
# Start update loops
# ============================================================

root.after(5, plot_data)
root.after(500, update_sample_rate)

root.protocol("WM_DELETE_WINDOW", on_closing)
root.mainloop()