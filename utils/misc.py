import numpy as np
from array import array
from pydub import AudioSegment
from pydub.utils import get_array_type
import random
import re, os
import time
import ujson

'''
Random Seed Management
'''
def init_random_seed(seed):
  random.seed(seed)
  np.random.seed(seed)


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



## QUESTION SUTFF

def question_node_shallow_copy(node):
  new_node = {
    'type': node['type'],
    'inputs': node['inputs'],
  }
  if 'value_inputs' in node:
    new_node['value_inputs'] = node['value_inputs']
  else:
    new_node['value_inputs'] = []

  return new_node


def write_questions_part_to_file(tmp_folder_path, filename, info_section, questions, index):
  tmp_filename = filename.replace(".json", "_%.5d.json" % index)
  tmp_filepath = os.path.join(tmp_folder_path, tmp_filename)

  print("Writing to file %s" % tmp_filepath)

  with open(tmp_filepath, 'w') as f:
    ujson.dump({
        'info': info_section,
        'questions': questions,
      }, f, indent=2, sort_keys=True, escape_forward_slashes=False)


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





