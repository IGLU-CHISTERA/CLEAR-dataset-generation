import ujson
import json
import os
import copy
import matplotlib
import argparse
# Matplotlib options to reduce memory usage
matplotlib.interactive(False)
matplotlib.use('agg')

import matplotlib.pyplot as plt


parser = argparse.ArgumentParser(fromfile_prefix_chars='@')

parser.add_argument('--output_folder', default='../output', type=str,
                    help='Folder where the audio and images are located')
parser.add_argument('--output_version_nb', type=str,
                    help='Version number to analyse')


def load_scenes(scenes_path):
  filename = "AQA_%s_scenes.json"
  training_scenes_path = os.path.join(scenes_path, filename % 'train')
  validation_scenes_path = os.path.join(scenes_path, filename % 'val')
  test_scenes_path = os.path.join(scenes_path, filename % 'test')

  with open(training_scenes_path) as f:
    training_scenes = ujson.load(f)['scenes']

  with open(validation_scenes_path) as f:
    validation_scenes = ujson.load(f)['scenes']

  with open(test_scenes_path) as f:
    test_scenes = ujson.load(f)['scenes']

  return training_scenes, validation_scenes, test_scenes


def do_analyse_scenes(scenes):

  scenes_stats = []

  # Count attributes for each scene
  for scene in scenes:
    instrument_count = {}
    musical_note_count = {}
    brightness_count = {}
    loudness_count = {}
    percussive_count = {}
    distortion_count = {}
    silence_count = {
      'silence': scene['silence_before'],
      'sound': 0
    }

    for obj in scene['objects']:
      silence_count['silence'] += obj['silence_after']
      silence_count['sound'] += obj['duration']

      if obj['instrument'] not in instrument_count:
        instrument_count[obj['instrument']] = 1
      else:
        instrument_count[obj['instrument']] += 1

      if obj['human_note'] not in musical_note_count:
        musical_note_count[obj['human_note']] = 1
      else:
        musical_note_count[obj['human_note']] += 1

      if obj['brightness'] not in brightness_count:
        brightness_count[obj['brightness']] = 1
      else:
        brightness_count[obj['brightness']] += 1

      if obj['loudness'] not in loudness_count:
        loudness_count[obj['loudness']] = 1
      else:
        loudness_count[obj['loudness']] += 1

      if obj['percussion'] not in percussive_count:
        percussive_count[obj['percussion']] = 1
      else:
        percussive_count[obj['percussion']] += 1

      if obj['distortion'] not in distortion_count:
        distortion_count[obj['distortion']] = 1
      else:
        distortion_count[obj['distortion']] += 1

    scenes_stats.append({
      'instrument_count': instrument_count,
      'musical_note_count': musical_note_count,
      'brightness_count': brightness_count,
      'loudness_count': loudness_count,
      'percussive_count': percussive_count,
      'distortion_count': distortion_count,
      'silence': silence_count,
      'nb_different_instrument': len(instrument_count.keys())
    })

  avg_stats = {
    'instrument_count': {},
    'musical_note_count': {},
    'brightness_count': {},
    'loudness_count': {},
    'percussive_count': {},
    'distortion_count': {},
    'silence': {},
    'nb_different_instrument': 0
  }

  # Global count for all scenes
  for count_type, count_values in avg_stats.items():
    for scene_stats in scenes_stats:
      if type(count_values) is dict:
        for key, val in scene_stats[count_type].items():
          if key not in avg_stats[count_type]:
            avg_stats[count_type][key] = val
          else:
            avg_stats[count_type][key] += val
      elif type(count_values) is int:
        avg_stats[count_type] += scene_stats[count_type]

  total_count = copy.deepcopy(avg_stats)

  # Calculate average
  nb_scenes = len(scenes_stats)
  for count_key, count_values in avg_stats.items():
    if type(count_values) is dict:
      for key, val in count_values.items():
        avg_stats[count_key][key] = val/nb_scenes
    elif type(count_values) is int:
      avg_stats[count_key] /= nb_scenes

  return total_count, avg_stats


def analyse_scenes(output_folder, set_type, scenes):
  # Analyse the scenes
  total_count, avg_stats = do_analyse_scenes(scenes)

  # Create output folder structure
  stats_folder_path = os.path.join(output_folder, 'stats')
  if not os.path.isdir(stats_folder_path):
    os.mkdir(stats_folder_path)

  set_stats_folder_path = os.path.join(stats_folder_path, set_type)
  if not os.path.isdir(set_stats_folder_path):
    os.mkdir(set_stats_folder_path)

  scenes_stats_folder_path = os.path.join(set_stats_folder_path, 'scenes')
  if not os.path.isdir(scenes_stats_folder_path):
    os.mkdir(scenes_stats_folder_path)

  # Save result to file
  write_stats_to_file(scenes_stats_folder_path, set_type, total_count, avg_stats)
  save_piechart(scenes_stats_folder_path, avg_stats)


def write_stats_to_file(output_folder, set_type, total_count, avg_count):
  stats_file_path = os.path.join(output_folder, '%s_scenes_stats.json' % set_type)

  with open(stats_file_path, 'w') as f:
    ujson.dump({
      'avg_per_scene_count' : avg_count,
      'total_count': total_count
    }, f, indent=2)


def save_piechart(output_path, counts_by_attributes):

  int_values = {}

  for attribute, count_by_values in counts_by_attributes.items():
    if type(count_by_values) is dict:
      filename = attribute + ".png"
      output_filepath = os.path.join(output_path, filename)
      figure = plt.figure(frameon=False)
      plt.pie(count_by_values.values(), labels=count_by_values.keys(), autopct='%1.1f%%')
      plt.axis('equal')
      plt.tight_layout()
      figure.savefig(output_filepath)
      plt.close(figure)
      figure.clear()
    elif type(count_by_values) is int or type(count_by_values) is float:
      int_values[attribute] = count_by_values

  # TODO : Save those somewhere. Table ?
  print(ujson.dumps(int_values, indent=2))


if __name__ == "__main__":
  args = parser.parse_args()
  output_path = "./%s/%s" % (args.output_folder, args.output_version_nb)
  scenes_path = os.path.join(output_path, 'scenes')

  # Load scenes
  training_scenes, validation_scenes, test_scenes = load_scenes(scenes_path)
  print("Scenes loaded")

  # Analyze scenes for each set
  analyse_scenes(output_path, 'train', training_scenes)
  print("Training scenes analyzed")

  analyse_scenes(output_path, 'val', validation_scenes)
  print("Validation scenes analyzed")

  analyse_scenes(output_path, 'test', test_scenes)
  print("Test scenes analyzed")

  print("Analysis finished. See %s/stats for infos" % output_path)
