import sqlite3
import json
import os
from operator import attrgetter
from shutil import copy2 as copyfile
from shutil import rmtree as rmdir
import argparse

from pydub import AudioSegment
from pydub.silence import split_on_silence

from utils.audio_processing import get_perceptual_loudness


'''
Arguments definition
'''
parser = argparse.ArgumentParser()

parser.add_argument('--good_sounds_folder', type=str, default="./good-sounds/sounds_files",
                    help='Path to the good-sounds audio folder')

parser.add_argument('--good_sounds_database_filename', type=str, default="./good-sounds/database.sqlite",
                    help='Path to the good-sounds sqlite database')

parser.add_argument('--output_path', type=str, default="./elementary_sounds",
                    help='Path were the extracted elementary sounds will be copied')

parser.add_argument('--output_definition_filename', type=str, default="elementary_sounds.json",
                    help='Filename for the json file that store the attributes of the elementary sounds')


# Preprocessing parameters
# FIXME : Write the help messages
parser.add_argument('--silence_threshold', type=float, default=-50,
                    help='')

parser.add_argument('--min_silence_duration', type=int, default=100,
                    help='')

parser.add_argument('--amplification_factor', type=float, default=-10,
                    help='')

parser.add_argument('--amplification_low_bound', type=float, default=-30.5,
                    help='')

parser.add_argument('--amplification_high_bound', type=float, default=-24.0,
                    help='')


def connect_db(database_path):
  """
  SQL Database connection
  """
  connection = sqlite3.connect(database_path)
  return connection.cursor()


def retrieve_CLEAR_elementary_sounds_infos_from_goodsounds_db(database):
  """
  SQL Query
  """
  database.execute("SELECT sounds.instrument, sounds.note, sounds.octave, takes.filename from sounds \
                    LEFT JOIN takes on takes.sound_id = sounds.id \
                    LEFT JOIN packs on packs.id = sounds.pack_id \
                    WHERE sounds.octave = 4 \
                    AND sounds.reference = 1 \
                    AND sounds.klass = 'good-sound' \
                    AND packs.name NOT LIKE '%recordings%' \
                    AND takes.microphone = 'akg' ")

  return db_rows_to_dict(database.fetchall())


def db_rows_to_dict(results):
  """
  Convert SQL rows to dict
  """
  sounds = []

  for row in results:
    sounds.append({
        'instrument': row[0],
        'note': row[1],
        'octave': row[2],
        'filename': row[3]
      })

  return sounds


def load_sounds_in_memory(sounds, good_sounds_folder):
  """
  Load audio segments into memory
  """
  for sound in sounds:
    audio_segment = AudioSegment.from_wav(os.path.join(good_sounds_folder, sound['filename']))
    sounds['audio_segment'] = audio_segment

  return sounds


def write_sounds_to_files(sounds, output_path, definition_filename):
  """
  Write the audio segments to file and export the definition JSON file
  """

  if os.path.isdir(output_path):
    input(">>> The folder '%s' already exist. \n>>> Press enter to overwrite it. Otherwise CTRL+C" % output_path)
    rmdir(output_path)

  os.mkdir(output_path)

  for sound in sounds:
    new_filename = '%s_%s.wav' % (sound['instrument'], sound['note'])
    sound['audio_segment'].export(os.path.join(output_path, new_filename))
    sound['filename'] = new_filename
    del sound['audio_segment']

  with open(os.path.join(output_path, definition_filename), 'w') as f:
    json.dump(sounds, f, indent=2)

  print("Elementary sounds successfully written in '%s'" % output_path)


def remove_silence(sounds, silence_thresh, min_silence_duration):
  """
  Remove the silence parts of the recordings
  The recordings that we are filtering are sustained note instrumental recordings
  therefore we keep only the longest non silent interval
  """
  for sound in sounds:
    non_silent_audio_chunks = split_on_silence(sound['audio_segment'],
                                               min_silence_duration,
                                               silence_thresh,
                                               100)

    # Sort the non silent part by duration
    non_silent_audio_chunks = sorted(non_silent_audio_chunks, key=attrgetter('duration_seconds'), reverse=True)

    # Use the longest non-silent part
    # (This is suitable only for the recordings of Good-Sounds dataset since they are sustained instrumental notes)
    sound['audio_segment'] = non_silent_audio_chunks[0]

  return sounds


def amplify_if_perceptual_loudness_in_range(sounds, amplification_factor, low_bound, high_bound):
  """
  If the perceptual loudness of the sound is between low_bound and high_bound --> Amplify it by the amplification_factor
  """
  for sound in sounds:
    perceptual_loudness = get_perceptual_loudness(sound['audio_segment'])

    if high_bound > perceptual_loudness > low_bound:
      sounds['audio_segment'] = sound['audio_segment'].apply_gain(amplification_factor)

  return sounds


def main(args):
  database = connect_db(os.path.join(args.good_sounds_folder, args.good_sounds_database_filename))

  # Loading sounds
  CLEAR_elementary_sounds_infos = retrieve_CLEAR_elementary_sounds_infos_from_goodsounds_db(database)
  CLEAR_elementary_sounds = load_sounds_in_memory(CLEAR_elementary_sounds_infos, args.good_sounds_folder)

  # Preprocessing
  # Remove silence parts
  CLEAR_elementary_sounds_preprocessed = remove_silence(CLEAR_elementary_sounds,
                                                        args.silence_threshold,
                                                        args.min_silence_duration)

  # Amplify sounds that are in a certain range of perceptual loudness
  CLEAR_elementary_sounds_preprocessed = amplify_if_perceptual_loudness_in_range(CLEAR_elementary_sounds_preprocessed,
                                                                                 args.amplification_factor,
                                                                                 args.amplification_low_bound,
                                                                                 args.amplification_high_bound)

  # Write to file
  write_sounds_to_files(CLEAR_elementary_sounds_preprocessed, args.output_path, args.output_definition_filename)


if __name__ == "__main__":
  args = parser.parse_args()
  main(args)

