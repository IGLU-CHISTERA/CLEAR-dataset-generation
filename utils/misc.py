# CLEAR Dataset
# >> Generic Helper functions
#
# Author :      Jerome Abdelnour
# Year :        2018-2019
# Affiliations: Universite de Sherbrooke - Electrical and Computer Engineering faculty
#               KTH Stockholm Royal Institute of Technology
#               IGLU - CHIST-ERA

import os
import numpy as np
from array import array
from pydub import AudioSegment
from pydub.utils import get_array_type
import random
import time
import json


def init_random_seed(seed):
    """
    Random Seed Management
    """
    random.seed(seed)
    np.random.seed(seed)


def save_arguments(args, folder_path, filename):
    """
    Arguments saving
    """
    if not os.path.isdir(folder_path):
        os.mkdir(folder_path)

    with open(f"{folder_path}/{filename}", 'w') as f:
        json.dump(args, f, indent=2)


'''
Format conversion
'''
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

    NOTE : This will only work for mono audio segment because of the way data is ordered in a pydub audio segment
    NOTE : See https://groups.google.com/d/msg/librosa/XWae4PdbXuk/4LjHK3d4BAAJ for a fix
    """

    bit_depth = 8 * n_bytes

    # Invert the scale of the data
    scale = 1. / float(1 << (bit_depth - 1))

    # Construct the format string
    fmt = '<i{:d}'.format(n_bytes)

    np_arr = np.frombuffer(audio_segment._data, fmt)

    scaled = np.multiply(np_arr, scale, dtype=from_pydub_bit_depth_to_np_type[bit_depth])

    return scaled


def float_array_to_pydub_audiosegment(float_array, frame_rate, n_bytes):
    bit_depth = 8 * n_bytes
    # Revert the scale of the data
    scale = float(1 << ((bit_depth) - 1))

    scaled = np.multiply(scale, float_array).astype(to_pydub_bit_depth_to_np_type[bit_depth])

    return AudioSegment(scaled.tobytes(),
                        frame_rate=frame_rate,
                        sample_width=n_bytes,
                        channels=1)


def get_max_scene_length(scenes):
  return np.max([len(scene['objects']) for scene in scenes])


def generate_info_section(set_type, version_nb):
    return {
            "name": "CLEAR",
            "license": "Creative Commons Attribution (CC-BY 4.0)",
            "version": version_nb,
            "set_type": set_type,
            "date": time.strftime("%x")
        }





