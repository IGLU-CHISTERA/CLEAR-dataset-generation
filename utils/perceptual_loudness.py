import pyloudnorm
from utils.misc import pydub_audiosegment_to_float_array


def get_perceptual_loudness(pydub_audio_segment):
  # FIXME : The meter should probably not be created everytime
  loudness_meter = pyloudnorm.Meter(pydub_audio_segment.frame_rate, block_size=0.5)  # FIXME : Hardcoded block size

  return loudness_meter.integrated_loudness(pydub_audiosegment_to_float_array(pydub_audio_segment, pydub_audio_segment.sample_width))
