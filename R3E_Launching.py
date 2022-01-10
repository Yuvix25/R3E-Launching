"""
Author: Yuval Rosen.
"""

import os
import mmap
import struct, json
import math
import time
from tkinter import *
from ctypes import windll
from shared_parsing import get_value

# Fix `tk.after` slower when not hovering the window:
timeBeginPeriod = windll.winmm.timeBeginPeriod
timeBeginPeriod(1)


def mmap_io():
    return mmap.mmap(-1, 40960, "Local\\$R3E",  access=mmap.ACCESS_READ)




preferences_file = os.path.join(os.path.dirname(__file__), 'config.json')
preferences = dict()


def save_preferences():
    with open(preferences_file, 'w') as f:
        json.dump(preferences, f, indent=4)

def load_prefrences():
    global preferences
    if os.path.isfile(preferences_file):
        with open(preferences_file, 'r') as f:
            preferences = json.load(f)
    else:
        preferences = {
            'zero_threshold': 0.1,
            'stop_speed': 150,
        }
        save_preferences()
    return preferences


load_prefrences()



def rps_to_rpm(rps):
    return rps * (60 / (2 * math.pi))

def mps_to_kph(mps):
    speed = mps * 3.6
    if speed < preferences['zero_threshold']:
        return 0
    return speed



class GUI:
    def __init__(self):
        self.window = Tk()
        self.window.title("R3E Launching")
        self.window.iconbitmap("timer.ico")
        self.window.geometry("230x130")
        self.window.resizable(width=False, height=False)

        self.window.stop_speed = Label(self.window, text="Stop Speed:")
        self.window.stop_speed.pack()

        vcmd = (self.window.register(self.validate),
                '%d', '%i', '%P', '%s', '%S', '%v', '%V', '%W')
        self.stop_speed_sv = StringVar()
        self.stop_speed_sv.trace('w', lambda name, index, mode, sv=self.stop_speed_sv: self.set_stop_speed(sv))
        self.window.stop_speed_entry = Entry(self.window, textvariable=self.stop_speed_sv, validate='key', validatecommand=vcmd)
        # self.window.entry = Entry(self.window, validate = 'key', validatecommand = vcmd)
        self.window.stop_speed_entry.insert(END, preferences['stop_speed'])
        self.window.stop_speed_entry.pack()


        self.window.current_speed = Label(self.window, text="Current Speed: 0.0 km/h")
        self.window.current_speed.pack()

        self.window.time_label = Label(self.window, text="Time: 0.0s")
        self.window.time_label.pack()

        self.window.last_time_label = Label(self.window, text="Last Time: 0.00s")
        self.window.last_time_label.pack()

        self.window.last_rev_label = Label(self.window, text="Last Revolutions At Launch: 0.0 RPM")
        self.window.last_rev_label.pack()

        self.window.wm_attributes("-topmost", 1)

        self.mmap_file = mmap_io()
        self.measuring = False
        self.measure_start = 0
        self.last_speed = -1
        self.rpm_at_start = -1
        self.run()

        self.window.mainloop()

    def validate(self, action, index, value_if_allowed,
                       prior_value, text, validation_type, trigger_type, widget_name):
        
        if value_if_allowed == "":
            return True
        
        if value_if_allowed:
            try:
                float(value_if_allowed)
                return True
            except ValueError:
                return False
        else:
            return False
        
    def set_stop_speed(self, sv):
        if sv.get() == "":
            return
        preferences['stop_speed'] = float(sv.get())
        save_preferences()

    def set_current_speed_label(self, speed):
        self.window.current_speed.config(text="Current Speed: %.1f km/h" % speed)

    def set_time_label(self, time):
        self.window.time_label.config(text="Time: %.2fs" % time)
    
    def set_last_time_label(self, time):
        self.window.last_time_label.config(text="Last Time: %.3fs" % time)
    
    def set_last_rev_label(self, rpm):
        self.window.last_rev_label.config(text="Last Revolutions At Launch: %.1f RPM" % rpm)

    def run(self):
        self.mmap_file.seek(0)
        raw_data = self.mmap_file.read()

        speed = mps_to_kph(get_value(raw_data, 'CarSpeed'))
        rpm = rps_to_rpm(get_value(raw_data, 'EngineRps'))

        # Another way to get the data:

        # speed = mps_to_kph(struct.unpack("<f", raw_data[1336:1340])[0])
        # rpm = rps_to_rpm(struct.unpack("<f", raw_data[1340:1344])[0])

        if self.last_speed != -1:
            if not self.measuring and speed > 0 and self.last_speed == 0:
                self.measuring = True
                self.measure_start = time.time()
                self.rpm_at_start = rpm
            
            if self.measuring and speed == 0:
                self.measuring = False
                self.measure_start = 0
            
            if speed >= preferences['stop_speed'] and self.measuring:
                self.measuring = False
                self.set_last_time_label(time.time() - self.measure_start)
                self.set_last_rev_label(self.rpm_at_start)
                self.set_time_label(0)
            
            self.set_current_speed_label(speed)
            if self.measuring:
                self.set_time_label(time.time() - self.measure_start)
            else:
                self.set_time_label(0)

        self.last_speed = speed
        self.window.lift()

        self.window.after(5, self.run)


if __name__ == "__main__":
    GUI()
