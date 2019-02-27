import sqlite3
import json
import os
from shutil import copy2 as copyfile
from shutil import rmtree as rmdir







def retrieve_cello_reference_sounds_from_db(cursor):
  cursor.execute("SELECT sounds.instrument, sounds.note, sounds.octave, ratings.mark, takes.microphone, takes.filename from sounds \
                  LEFT JOIN takes on takes.sound_id = sounds.id \
                  LEFT JOIN packs on packs.id = sounds.pack_id \
                  LEFT JOIN ratings on ratings.sound_id = sounds.id \
                  WHERE sounds.octave = 3 \
                  AND sounds.reference = 1 \
                  AND sounds.instrument = 'cello'\
                  AND sounds.klass = 'good-sound' \
                  AND packs.name NOT LIKE '%recordings%' \
                  AND takes.microphone != 'iphone' ")

  return cursor.fetchall()


def retrieve_reference_sounds_from_db_with_joins(cursor):
  cursor.execute("SELECT sounds.instrument, sounds.note, sounds.octave, packs.name, ratings.mark, takes.microphone, takes.filename from sounds \
                  LEFT JOIN takes on takes.sound_id = sounds.id \
                  LEFT JOIN packs on packs.id = sounds.pack_id \
                  LEFT JOIN ratings on ratings.sound_id = sounds.id \
                  WHERE sounds.octave = 4 \
                  AND (ratings.type = 'good-sound' OR ratings.type IS NULL) \
                  AND takes.microphone != 'iphone' \
                  AND packs.name LIKE '%reference' ")

  return cursor.fetchall()

def retrieve_all_sounds_from_db(cursor):
  cursor.execute("SELECT sounds.instrument, sounds.note, sounds.octave, packs.name, ratings.mark, takes.microphone, takes.filename from sounds \
                  LEFT JOIN takes on takes.sound_id = sounds.id \
                  LEFT JOIN packs on packs.id = sounds.pack_id \
                  LEFT JOIN ratings on ratings.sound_id = sounds.id \
                  WHERE sounds.klass = 'good-sound' \
                  AND takes.microphone = 'neumann' ")

  return cursor.fetchall()






    
#################################################
#### NOT REALLY USEFUL
def retrieve_reference_sounds_all_octaves_from_db(cursor):
  cursor.execute("SELECT sounds.instrument, sounds.note, sounds.octave, ratings.mark, takes.microphone, takes.filename from sounds \
                  LEFT JOIN takes on takes.sound_id = sounds.id \
                  LEFT JOIN packs on packs.id = sounds.pack_id \
                  LEFT JOIN ratings on ratings.sound_id = sounds.id \
                  WHERE sounds.reference = 1 \
                  AND sounds.klass = 'good-sound' \
                  AND packs.name NOT LIKE '%recordings%' \
                  AND takes.microphone != 'iphone' ")

  return cursor.fetchall()


def get_note_availability(all_sounds):
  notes_per_octave_per_instrument = {}
  note_count_per_octave_per_instrument = {}

  for sound in all_sounds:
    if sound['instrument'] not in notes_per_octave_per_instrument:
      notes_per_octave_per_instrument[sound['instrument']] = {}

    if sound['octave'] not in notes_per_octave_per_instrument[sound['instrument']]:
      notes_per_octave_per_instrument[sound['instrument']][sound['octave']] = []

    notes_per_octave_per_instrument[sound['instrument']][sound['octave']].append(sound['human_note'])

    notes_per_octave_per_instrument[sound['instrument']][sound['octave']] = sorted(list(set(notes_per_octave_per_instrument[sound['instrument']][sound['octave']])))

    for instrument in notes_per_octave_per_instrument:
      if instrument not in note_count_per_octave_per_instrument:
        note_count_per_octave_per_instrument[instrument] = {}

      for octave in notes_per_octave_per_instrument[instrument]:
        note_count_per_octave_per_instrument[instrument][octave] = len(notes_per_octave_per_instrument[instrument][octave])

  return notes_per_octave_per_instrument, note_count_per_octave_per_instrument



################################################
#### STUFF THAT IS USED
################################################
'''
SQL Handling
'''
def connect_db(database_path):
  connection = sqlite3.connect(database_path)
  return connection.cursor()


def retrieve_CLEAR_elementary_sounds_from_goodsounds_db(database):
  database.execute("SELECT sounds.instrument, sounds.note, sounds.octave, takes.filename from sounds \
                    LEFT JOIN takes on takes.sound_id = sounds.id \
                    LEFT JOIN packs on packs.id = sounds.pack_id \
                    WHERE sounds.octave = 4 \
                    AND sounds.reference = 1 \
                    AND sounds.klass = 'good-sound' \
                    AND packs.name NOT LIKE '%recordings%' \
                    AND takes.microphone = 'akg' ")

  return database.fetchall()


soundsColumns = ['id', 'instrument', 'note', 'octave', 'dynamics', 'recorded_at', 'location',
                'player', 'bow_velocity', 'bridge_position', 'string', 'csv_file', 'csv_id',
                'pack_filename', 'pack_id', 'attack', 'decay', 'sustain', 'release', 'offset',
                'reference', 'klass', 'comments', 'semitone', 'pitch_reference']


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


'''
Filtering
'''


def overwrite_folder(folder_path):
  if os.path.isdir(folder_path):
    input(">>> The folder '%s' already exist. \n>>> Press enter to overwrite it. Otherwise CTRL+C" % folder_path)
    rmdir(folder_path)

  os.mkdir(folder_path)


def create_folder_if_doesnt_exist(folder_path):
  if not os.path.isdir(folder_path):
    os.mkdir(folder_path)


def copy_sounds_file(sounds, dataset_root_path, destination_path, definition_filename):
  overwrite_folder(destination_path)

  print("Starting to copy files in '%s'" % destination_path)
  for sound in sounds:
    new_filename = '%s_%s_%s.wav' % (sound['instrument'], sound['human_note'], sound['source_microphone'])

    copyfile(os.path.join(dataset_root_path, sound['filename']), os.path.join(destination_path, new_filename))

    sound['filename'] = new_filename

  with open(os.path.join(destination_path, definition_filename), 'w') as f:
    json.dump(sounds, f, indent=2)

  print("Finished copying files")


def copy_sounds_file_separate_microphone(sounds, dataset_root_path, destination_path, definition_filename):
  overwrite_folder(destination_path)
  definitions_by_microphone = {}

  print("Starting to copy files in '%s'" % destination_path)
  for sound in sounds:
    new_filename = '%s_%s_%s.wav' % (sound['instrument'], sound['human_note'], sound['source_microphone'])
    microphone_folder = os.path.join(destination_path, sound['source_microphone'])
    create_folder_if_doesnt_exist(microphone_folder)

    copyfile(os.path.join(dataset_root_path, sound['filename']), os.path.join(microphone_folder, new_filename))

    sound['filename'] = new_filename

    if sound['source_microphone'] not in definitions_by_microphone:
      definitions_by_microphone[sound['source_microphone']] = []

    definitions_by_microphone[sound['source_microphone']].append(sound)

  for microphone, sounds_def in definitions_by_microphone.items():
    definition_path = os.path.join(destination_path, microphone, definition_filename)

    with open(definition_path, 'w') as f:
      json.dump(sounds_def, f, indent=2)

  print("Finished copying files")


def copy_sounds_file_separate_folders_per_instrument(sounds, dataset_root_path, destination_path, definition_filename):
  overwrite_folder(destination_path)

  print("Starting to copy files in '%s'" % destination_path)
  for sound in sounds:
    new_filename = '%s_%s.wav' % (sound['instrument'], sound['human_note'])

    instrument_folder = os.path.join(destination_path, sound['instrument'])
    create_folder_if_doesnt_exist(instrument_folder)

    source_folder = os.path.join(instrument_folder, sound['source_microphone'])
    create_folder_if_doesnt_exist(source_folder)

    copyfile(os.path.join(dataset_root_path, sound['filename']), os.path.join(source_folder, new_filename))

  print("Finished copying files")


def main():
  good_sounds_dataset_root_path = '.'
  output_path = 'filtered'
  good_sounds_db_path = 'database.sqlite'
  database = connect_db(good_sounds_db_path)

  allSounds = retrieve_reference_sounds_all_octaves_from_db(cursor)
  allSounds = db_rows_to_dict(allSounds)

  notes_availability, note_count = get_note_availability(allSounds)

  print("Note count per instrument per octave")
  print(json.dumps(notes_availability, indent=2))

  sounds = retrieve_reference_sounds_fourth_octave_from_db(cursor)
  sounds = db_rows_to_dict(sounds)

  #copy_sounds_file_separate_folders_per_instrument(sounds, good_sounds_dataset_root_path, 'filtered_separated_per_instrument', 'elementary_sounds.json')

  #copy_sounds_file_separate_microphone(sounds, good_sounds_dataset_root_path, output_path, 'elementary_sounds.json')

  print("All done")

if __name__ == "__main__":
  main()

