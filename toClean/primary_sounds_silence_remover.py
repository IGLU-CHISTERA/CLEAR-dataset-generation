from pydub import AudioSegment
from pydub.silence import split_on_silence
import os

cwd = os.path.dirname(os.path.realpath(__file__))

output_folder = os.path.join(cwd, 'primary_sounds_cleaned')
primary_sound_folder = os.path.join(cwd, 'primary_sounds_original')

if not os.path.exists(output_folder):
    os.makedirs(output_folder)
else:
    os.rmdir(output_folder)
    os.makedirs(output_folder)

sounds = [f for f in os.listdir(primary_sound_folder) if os.path.isfile(os.path.join(primary_sound_folder, f)) and f.endswith('.wav')]

for sound in sounds:
    sound_audio_segment = AudioSegment.from_wav(os.path.join(primary_sound_folder, sound))
    non_silent_audio_chunks = split_on_silence(audio_segment=sound_audio_segment, min_silence_len=100,
                                               silence_thresh=-100, keep_silence=5)

    if len(non_silent_audio_chunks) == 1:
        sound_audio_segment = non_silent_audio_chunks[0]
    else:
        print("[ERROR] detected more than one silence.")
        exit(0)

    sound_audio_segment.export(os.path.join(output_folder, sound), format='wav')
