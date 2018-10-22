import os
import sys
import ujson
from operator import attrgetter
from shutil import copy2 as copyfile
from shutil import rmtree as rmdir

from pydub import AudioSegment
from pydub.silence import split_on_silence

from utils.perceptual_loudness import get_perceptual_loudness


def load_elementary_sounds_definition(elementary_sounds_folder_path, elementary_sounds_definition_filename):
  print("Loading elementary sounds definition")
  elementary_sounds_definition_filepath = os.path.join(elementary_sounds_folder_path, elementary_sounds_definition_filename)
  with open(elementary_sounds_definition_filepath, 'r') as f:
    definition = ujson.load(f)
  return definition


def load_sounds(elementary_sounds_def, elementary_sounds_folder_path):
  print("Loading elementary sounds audio")
  audio_segments = []
  for sound in elementary_sounds_def:
    audio_segment = AudioSegment.from_wav(os.path.join(elementary_sounds_folder_path, sound['filename']))

    audio_segments.append({
      'filename': sound['filename'],
      'audio_segment': audio_segment
    })

  return audio_segments


def remove_silence(audio_segments, silence_thresh, min_silence_duration, begin_end_keep_silence_duration):
  print("Removing silence")
  new_audio_segments = []

  for sound in audio_segments:
    non_silent_audio_chunks = split_on_silence(sound['audio_segment'], min_silence_duration, silence_thresh, begin_end_keep_silence_duration)

    # Sort the non silent part by duration
    non_silent_audio_chunks = sorted(non_silent_audio_chunks, key=attrgetter('duration_seconds'), reverse=True)

    # Use the longest non-silent part
    new_audio_segments.append({
      'filename': sound['filename'],
      'audio_segment': non_silent_audio_chunks[0]
    })

  return new_audio_segments


def amplify_if_perceptual_loudness_in_range(audio_segments, amplification_factor, low_bound, high_bound):
  print("Balancing perceptual loudness")
  new_audio_segments = []

  for sound in audio_segments:
    perceptual_loudness = get_perceptual_loudness(sound['audio_segment'])
    if high_bound > perceptual_loudness > low_bound:
      audio_segment = sound['audio_segment'].apply_gain(amplification_factor)
      print("Amplified '%s'" % sound['filename'])
    else:
      audio_segment = sound['audio_segment']

    new_audio_segments.append({
      'filename': sound['filename'],
      'audio_segment': audio_segment
    })

  return new_audio_segments


def write_audio_segments(audio_segments, output_folder_path, original_folder_path, elementary_sounds_definition_filename):
  print("Writing new elementary sounds audio")
  if os.path.isdir(output_folder_path):
    input(">>> The folder '%s' already exist. \n>>> Press enter to overwrite it. Otherwise CTRL+C" % output_folder_path)
    rmdir(output_folder_path)

  os.mkdir(output_folder_path)

  # Writing all the audio segments
  for sound in audio_segments:
    filepath = os.path.join(output_folder_path, sound['filename'])
    sound['audio_segment'].export(filepath, format='wav')

  # Copy the definition file to the output folder
  old_definition_filepath = os.path.join(original_folder_path, elementary_sounds_definition_filename)
  new_definition_filepath = os.path.join(output_folder_path, elementary_sounds_definition_filename)
  copyfile(old_definition_filepath, new_definition_filepath)


def main():
  # TODO : Add argument parsing for all parameters
  # Paths
  elementary_sounds_folder_path = "/NOBACKUP/jerome/datasets/good-sounds/filtered/akg"
  elementary_sounds_definition_filename = "elementary_sounds.json"
  output_folder_path = "/NOBACKUP/jerome/datasets/good-sounds/filtered_and_preprocessed"

  # Silence removal
  silence_treshold = -50
  min_silence_duration = 100
  begin_end_keep_silence_duration = 100

  # Loudness correction
  amplification_factor = -10.0
  loudness_low_bound = -30.5
  loudness_high_bound = -24.0

  elementary_sounds_def = load_elementary_sounds_definition(elementary_sounds_folder_path,
                                                            elementary_sounds_definition_filename)

  original_audio_segments = load_sounds(elementary_sounds_def, elementary_sounds_folder_path)

  no_silence_audio_segments = remove_silence(original_audio_segments,
                                             silence_treshold,
                                             min_silence_duration,
                                             begin_end_keep_silence_duration)

  amplified_audio_segments = amplify_if_perceptual_loudness_in_range(no_silence_audio_segments,
                                                                     amplification_factor,
                                                                     loudness_low_bound,
                                                                     loudness_high_bound)

  write_audio_segments(amplified_audio_segments,
                       output_folder_path,
                       elementary_sounds_folder_path,
                       elementary_sounds_definition_filename)

  print("All done")


if __name__ == "__main__":
  main()


