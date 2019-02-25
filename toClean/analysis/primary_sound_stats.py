import soundfile
import pyloudnorm as pyln
import os
import json
from pydub import AudioSegment
import numpy as np
import utils



cwd = os.path.dirname(os.path.realpath(__file__))

primary_sound_folder = os.path.join(cwd, 'primary_sounds')

sounds = [f for f in os.listdir(primary_sound_folder) if os.path.isfile(os.path.join(primary_sound_folder, f)) and f.endswith('.wav')]

loudnessLevels = {}


for sound in sounds:
    data, rate = soundfile.read(os.path.join(primary_sound_folder, sound))
    print(sound)
    meter = pyln.Meter(rate, block_size=0.35)
    loudnessLevels[sound] = {
        'duration' : data.size / rate,
        'level': meter.integrated_loudness(data)
    }

print("Done")
print(json.dumps(loudnessLevels, indent=4, sort_keys=True))
