#!/usr/bin/env python
# vim: set fileencoding=utf-8 :
# Elie Khoury <Elie.Khoury@idiap.ch>
#
# Copyright (C) 2012-2013 Idiap Research Institute, Martigny, Switzerland
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

"""{4Hz modulation energy and energy}-based voice activity detection for speaker recognition"""

import numpy,math
import bob
import os
import time
from .. import utils


class MOD_4HZ:
  """Extracts Modulation of the Energy at 4Hz features"""
  def __init__(self, config):
    self.m_config = config
 

  def voice_activity_detection(self, energy_array, mod_4hz):
    #########################
    ## Initialisation part ##
    #########################
    #index = self.m_config.energy_mask
    max_iterations = self.m_config.max_iterations
    alpha = self.m_config.alpha
    
    useMod4Hz = self.m_config.useMod4Hz
    
    n_samples = len(energy_array)
    
    ratio_for_threshold = 5
    
    threshold = numpy.max(energy_array) - numpy.log((100./ratio_for_threshold) * (100./ratio_for_threshold))

    energy = energy_array
    
    label = numpy.array(numpy.zeros(n_samples), dtype=numpy.int16)

    for i in range(n_samples):
      if ( energy[i] > threshold and mod_4hz[i] > 0.9 ):
        label[i]=1
              
    # If speech part less then 10 seconds and less than the half of the segment duration, try to find speech with more risk 
    if  numpy.sum(label) < 2000 and float(numpy.sum(label)) / float(len(label)) < 0.5:
      #print "TRY WITH MORE RISK 1..."
      for i in range(n_samples):
        if ( energy[i] > threshold and mod_4hz[i] > 0.5 ):
          label[i]=1

    if  numpy.sum(label) < 2000 and float(numpy.sum(label)) / float(len(label)) < 0.5:
      #print "TRY WITH MORE RISK 2..."
      for i in range(n_samples):
        if ( energy[i] > threshold and mod_4hz[i] > 0.2 ):
          label[i]=1

    if  numpy.sum(label) < 2000 and float(numpy.sum(label)) / float(len(label)) < 0.5: # This is special for short segments (less than 2s)...
      #print "TRY WITH MORE RISK 3..."
      if (len(energy) < 200 ) or (numpy.sum(label) == 0) or (numpy.mean(label)<0.025):
        for i in range(n_samples):
          if ( energy[i] > threshold ):
            label[i]=1

    return label 
  
  def averaging(self, list_1s_shift):

    len_list=len(list_1s_shift)
    sample_level_value = numpy.array(numpy.zeros(len_list, dtype=numpy.float))
    
    sample_level_value[0]=numpy.array(list_1s_shift[0])
    for j in range(2, numpy.min([len_list, 100])):
      sample_level_value[j-1]=((j-1.0)/j)*sample_level_value[j-2] +(1.0/j)*numpy.array(list_1s_shift[j-1])
    for j in range(numpy.min([len_list, 100]), len_list-100 +1):
      sample_level_value[j-1]=numpy.array(numpy.mean(list_1s_shift[j-100:j]))
    sample_level_value[len_list-1] = list_1s_shift[len_list -1]
    for j in range(2, numpy.min([len_list, 100]) + 1):
      sample_level_value[len_list-j]=((j-1.0)/j)*sample_level_value[len_list+1-j] +(1.0/j)*numpy.array(list_1s_shift[len_list-j])
    return sample_level_value


  
  def pass_band_filtering(self, energy_bands, fs):
    order = 2
    Nyq = float(fs/2)
    Wo = float(4/Nyq)
    Wn = [(Wo - 0.5/Nyq), Wo + 0.5/Nyq]
    import scipy.signal
    b, a = scipy.signal.butter(order, Wn, btype='band')

    res = scipy.signal.lfilter(b, a, energy_bands)
    return res.T
  
    
  def modulation_4hz(self, filtering_res, rate_wavsample):
    fs = rate_wavsample[0]
    win_length = int (fs * self.m_config.win_length_ms / 1000)
    win_shift = int (fs * self.m_config.win_shift_ms / 1000)
       
    Energy = filtering_res.sum(axis=0)
    mean_Energy = numpy.mean(Energy)
    
    win_size = int (2.0 ** math.ceil(math.log(win_length) / math.log(2)))
    n_frames = 1 + (rate_wavsample[1].shape[0] - win_length) / win_shift
    range_modulation = int(fs/win_shift) # This corresponds to 1 sec 
    res = numpy.zeros(n_frames)
    if n_frames < range_modulation:
      return res
    for w in range(0,n_frames-range_modulation):
      E_range=Energy[w:w+range_modulation-1] # computes the modulation every 10 ms 
      if (E_range<1.).any():
        res[w] = 0
      else:
        E_range = E_range/mean_Energy 
        res[w] = numpy.var(E_range)
    res[n_frames-range_modulation:n_frames] = res[n_frames-range_modulation-1] 
    return res 
  
  def mod_4hz(self, input_file):
    """Computes and returns the 4Hz modulation energy features for the given input wave file"""
    
    print "Input file : ", input_file
    rate_wavsample = utils.read(input_file)
    
    # Feature extraction
    
    # Set parameters
    wl = self.m_config.win_length_ms
    ws = self.m_config.win_shift_ms
    nf = self.m_config.n_filters
    nc = self.m_config.n_ceps

    f_min = self.m_config.f_min
    f_max = self.m_config.f_max
    dw = self.m_config.delta_win
    pre = self.m_config.pre_emphasis_coef

    c = bob.ap.Spectrogram(rate_wavsample[0], wl, ws, nf, f_min, f_max, pre)
    
    c.energy_filter=True
    c.log_filter=False
    c.energy_bands=True

    energy_bands = c(rate_wavsample[1])

    filtering_res = self.pass_band_filtering(energy_bands, rate_wavsample[0])
    mod_4hz = self.modulation_4hz(filtering_res, rate_wavsample)
    mod_4hz = self.averaging(mod_4hz)
    base_filename = os.path.splitext(os.path.basename(input_file))[0]
    e = bob.ap.Energy(rate_wavsample[0], wl, ws)
    energy_array = e(rate_wavsample[1])

    labels = self.voice_activity_detection(energy_array, mod_4hz)

    labels = utils.smoothing(labels,10) # discard isolated speech less than 100ms
    
    return labels
    
  
  def __call__(self, input_file, output_file, annotations = None):
    """labels speech (1) and non-speech (0) parts for the given input wave file using 4Hz modulation energy and energy"""
    
    labels = self.mod_4hz(input_file)
    print numpy.sum(labels)
    
    bob.io.save(labels, output_file)
    