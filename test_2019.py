#!/usr/bin/python
# ############################################################
# python class that runs experiments and save data
# author  Federico Corradi - federico.corradi@inilabs.com
# author  Diederik Paul Moeys - diederikmoeys@live.com
# update 2019 by
# author Germain Haessig - germain@ini.uzh.ch
# ############################################################
from __future__ import division
import numpy as np
import matplotlib
from pylab import *
import time, os
import shutil
import caer_communication
import signal

import gpio_usb

def exit_gracefully(signal, frame):
    sources.close()


signal.signal(signal.SIGINT, exit_gracefully)

sources = gpio_usb.gpio_usb()

sources.set_dc_voltage(0.1)

freq = 1
amp = 0.1
offset = 0
sources.set_square(freq, amp, offset)
