# CLEAR Dataset
# >> Elementary Sounds Wrapper
#
# Author :      Jerome Abdelnour
# Year :        2018-2019
# Affiliations: Universite de Sherbrooke - Electrical and Computer Engineering faculty
#               KTH Stockholm Royal Institute of Technology
#               IGLU - CHIST-ERA

import json
import os
import numpy as np
from pydub import AudioSegment
from collections import defaultdict
from copy import deepcopy

from timbral_models import timbral_brightness
from utils.audio_processing import get_perceptual_loudness


class Elementary_Sounds:
    """
    Elementary Sounds Wrapper
      - Load the elementary sounds from file
      - Preprocess the sounds
        - Analyse sounds and add new attributes to the definition
      - Give an interface to retrieve sounds
    """

    def __init__(self, folder_path, definition_filename, save_raw_values=False):
        print("Loading Elementary sounds")
        self.folderpath = folder_path

        with open(os.path.join(self.folderpath, definition_filename)) as file:
            self.definition = json.load(file)

        self.notes = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']

        self.sorted_durations = []

        self.nb_sounds = len(self.definition)

        self._preprocess_sounds(save_raw_values)

        self.families_count = {}

        self.id_list = [sound['id'] for sound in self.definition]

        self.id_list_shuffled = self.id_list.copy()

        for sound in self.definition:
            if sound['instrument'] not in self.families_count:
                self.families_count[sound['instrument']] = 1
            else:
                self.families_count[sound['instrument']] += 1

        self.families = self.families_count.keys()
        self.nb_families = len(self.families)

        self.generated_count_by_index = {i: 0 for i in range(self.nb_sounds)}
        self.generated_count_by_families = {fam: 0 for fam in self.families}
        self.gen_index = 0

    def get(self, index):
        # Return copy of element to prevent augmented attribute overwriting
        return deepcopy(self.definition[index])

    def __getitem__(self, item):
        return self.get(item)

    def __len__(self):
        return self.nb_sounds

    def _preprocess_sounds(self, save_raw_values, shuffle_sounds=True):
        """
        Apply some preprocessing on the loaded sounds
          - Calculate the perceptual loudness (ITU-R BS.1770-4 specification) and assign "Loud" or "Quiet" label
          - Calculate perceptual brightness and assign "Bright", "Dark" or None label
          - Retrieve the sound duration
          - Packup the info in the sound dict
        """

        if shuffle_sounds:
            np.random.shuffle(self.definition)

        max_brightness = -9999
        min_brightness = 9999
        max_loudness = -9999
        min_loudness = 9999

        for id, elementary_sound in enumerate(self.definition):
            elementary_sound_filename = os.path.join(self.folderpath, elementary_sound['filename'])
            elementary_sound_audiosegment = AudioSegment.from_wav(elementary_sound_filename)

            elementary_sound['id'] = id

            elementary_sound['duration'] = int(elementary_sound_audiosegment.duration_seconds * 1000)

            perceptual_loudness = get_perceptual_loudness(elementary_sound_audiosegment)
            elementary_sound['raw_loudness'] = perceptual_loudness

            self.sorted_durations.append(elementary_sound['duration'])

            elementary_sound['raw_brightness'] = timbral_brightness(elementary_sound_filename)

            if min_brightness > elementary_sound['raw_brightness']:
                min_brightness = elementary_sound['raw_brightness']

            if max_brightness < elementary_sound['raw_brightness']:
                max_brightness = elementary_sound['raw_brightness']

            if min_loudness > elementary_sound['raw_loudness']:
                min_loudness = elementary_sound['raw_loudness']

            if max_loudness < elementary_sound['raw_loudness']:
                max_loudness = elementary_sound['raw_loudness']

        # Normalize the brightness per instrument and assign the brightness label
        for id, elementary_sound in enumerate(self.definition):
            # Normalize attributes
            normalized_brightness = (elementary_sound['raw_brightness'] - min_brightness) / (max_brightness - min_brightness)
            normalized_loudness = (elementary_sound['raw_loudness'] - min_loudness) / (max_loudness - min_loudness)

            # Assign brightness label
            if normalized_brightness > 0.47:
                elementary_sound['brightness'] = 'bright'
            elif normalized_brightness < 0.42:
                elementary_sound['brightness'] = 'dark'
            else:
                elementary_sound['brightness'] = None

            # Assign loudness label
            if normalized_loudness > 0.62:
                elementary_sound['loudness'] = 'loud'
            elif normalized_loudness < 0.57:
                elementary_sound['loudness'] = 'quiet'
            else:
                elementary_sound['loudness'] = None

            if not save_raw_values:
                # Cleanup unused properties
                del elementary_sound['raw_loudness']
                del elementary_sound['raw_brightness']

        self.sorted_durations = sorted(self.sorted_durations)
        self.half_longest_durations_mean = np.mean(self.sorted_durations[-int(self.nb_sounds/2):])

    def sounds_to_families_count(self, sound_list):
        """
        Return the frequence of each instrument family
        """
        count = {}

        for sound in sound_list:
            family = sound['instrument']
            if family in count:
                count[family] += 1
            else:
                count[family] = 1

        non_empty_families = count.keys()
        non_empty_families_count = len(non_empty_families)

        empty_families = set(self.families) - set(non_empty_families)
        for family in empty_families:
            count[family] = 0

        return count, non_empty_families_count
