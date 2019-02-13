import os
import numpy as np
from array import array
from pydub import AudioSegment
from pydub.utils import get_min_max_value, get_frame_width, get_array_type, db_to_float
import ujson
import random
from shutil import copy2 as copyfile

# TODO : Rename this file to data processing (Or something like that. Misc is too generic)
from_pydub_bit_depth_to_np_type = {
  16 : np.float32,
  32 : np.float64
}

to_pydub_bit_depth_to_np_type = {
  16 : np.int16,
  32 : np.int32
}

def pydub_audiosegment_to_float_array(audio_segment, frame_rate, n_bytes):
    """Convert an integer buffer to floating point values.
    This is primarily useful when loading integer-valued wav data
    into numpy arrays.

    Taken from https://librosa.github.io/librosa/_modules/librosa/util/utils.html#buf_to_float

    FIXME : This will only work for mono audio segment because of the way data is ordered in a pydub audio segment
    FIXME : See https://groups.google.com/d/msg/librosa/XWae4PdbXuk/4LjHK3d4BAAJ for a fix
    """

    bit_depth = 8 * n_bytes

    raw_data = audio_segment.get_array_of_samples()

    # Invert the scale of the data
    scale = 1. / float(1 << (bit_depth - 1))

    # Construct the format string
    fmt = '<i{:d}'.format(n_bytes)

    # Rescale and format the data buffer
    return scale * np.frombuffer(raw_data, fmt).astype(from_pydub_bit_depth_to_np_type[bit_depth])


def float_array_to_pydub_audiosegment(float_array, frame_rate, n_bytes):
    bit_depth = 8 * n_bytes
    # Revert the scale of the data
    scale = float(1 << ((bit_depth) - 1))

    scaled = np.multiply(scale, float_array)

    array_of_samples = array(get_array_type(bit_depth), scaled.astype(to_pydub_bit_depth_to_np_type[bit_depth]))

    return AudioSegment(array_of_samples,
                        frame_rate=frame_rate,
                        sample_width=n_bytes,
                        channels=1)


def init_random_seed(seed, version_nb, seed_save_path):
  random.seed(seed)
  np.random.seed(seed)

  with open(seed_save_path, 'w') as f:
    ujson.dump({
      'seed': seed,
      'version_nb': version_nb
    }, f, indent=2)


def generate_random_noise(duration, gain, frame_width, sample_rate):
  bit_depth = 8 * frame_width
  minval, maxval = get_min_max_value(bit_depth)
  sample_width = get_frame_width(bit_depth)
  array_type = get_array_type(bit_depth)

  gain = db_to_float(gain)
  sample_count = int(sample_rate * (duration / 1000.0))

  data = ((np.random.rand(sample_count, 1) * 2) - 1.0) * maxval * gain
  data = array(array_type, data)

  try:
    data = data.tobytes()
  except:
    data = data.tostring()

  return AudioSegment(data=data, metadata={
    "channels": 1,
    "sample_width": sample_width,
    "frame_rate": sample_rate,
    "frame_width": sample_width,
  })
