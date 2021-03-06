#!/usr/bin/env python

import spear

preprocessor = spear.preprocessing.Energy

# Cepstral parameters
win_length_ms = 20
win_shift_ms = 10

# VAD parameters
alpha = 2
max_iterations = 10
smoothing_window = 10 # This corresponds to 100ms
