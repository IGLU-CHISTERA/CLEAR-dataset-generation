# CLEAR Dataset
# >> Audio Processing Helpers
#
# Author :      Jerome Abdelnour
# Year :        2018-2019
# Affiliations: Universite de Sherbrooke - Electrical and Computer Engineering faculty
#               KTH Stockholm Royal Institute of Technology
#               IGLU - CHIST-ERA

from array import array
from pydub import AudioSegment
import numpy as np
import pyloudnorm
from pysndfx import AudioEffectsChain
from pydub.utils import get_min_max_value, get_frame_width, get_array_type, db_to_float
from utils.misc import pydub_audiosegment_to_float_array


def get_perceptual_loudness(pydub_audio_segment):
  loudness_meter = pyloudnorm.Meter(pydub_audio_segment.frame_rate, block_size=0.5)

  sound_float_array = pydub_audiosegment_to_float_array(pydub_audio_segment,
                                                        pydub_audio_segment.frame_rate,
                                                        pydub_audio_segment.sample_width)

  return loudness_meter.integrated_loudness(sound_float_array)


def generate_random_noise(duration, gain, frame_width, sample_rate):
  bit_depth = 8 * frame_width
  minval, maxval = get_min_max_value(bit_depth)
  sample_width = get_frame_width(bit_depth)
  array_type = get_array_type(bit_depth)

  gain = db_to_float(gain)
  sample_count = int(sample_rate * (duration / 1000.0))

  data = ((np.random.rand(sample_count, 1) * 2) - 1.0) * maxval * gain

  return AudioSegment(data=data.astype(array_type).tobytes(), metadata={
    "channels": 1,
    "sample_width": sample_width,
    "frame_rate": sample_rate,
    "frame_width": sample_width,
  })


def add_reverberation(sound,
                        reverberance=100,
                        hf_damping=50,
                        room_scale=50,
                        stereo_depth=100,
                        pre_delay=20,
                        wet_gain=0,
                        wet_only=False):
  transformer = (
    AudioEffectsChain().
    reverb(reverberance=reverberance,
           hf_damping=hf_damping,
           room_scale=room_scale,
           stereo_depth=stereo_depth,
           pre_delay=pre_delay,
           wet_gain=wet_gain,
           wet_only=wet_only)
  )

  return transformer(sound)
