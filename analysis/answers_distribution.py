import ujson
from collections import defaultdict
import os
import argparse

from utils.question_classifier import load_questions_with_program_beautified


parser = argparse.ArgumentParser(fromfile_prefix_chars='@')

parser.add_argument('--output_folder', default='../output', type=str,
                    help='Folder where the audio and images are located')
parser.add_argument('--output_version_nb', type=str,
                    help='Version number to analyse')


# FIXME : Should use metadata file..
families = {
  'position' : [
    "first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth"
  ],
  'position_global' : [
    "beginning of the scene", "middle of the scene", "end of the scene"
  ],
  'musical_note': [
    "a", "a#", 'b', 'c', 'c#', 'd', "d#", "e", 'f', 'f#', 'g', 'g#'
  ],
  'brightness': [
    "bright", "dark"
  ],
  'loudness': [
    "quiet", "loud"
  ],
  'instrument': [
    "cello", "clarinet", "flute", "trumpet", "violin"
  ],
  'count' : [
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
  ],
  'yes/no': [
    'yes', 'no'
  ]
}


def load_questions(questions_path):
  print("Loading questions...")
  filename = "AQA_%s_questions.json"
  training_question_path = os.path.join(questions_path, filename % 'train')
  validation_questions_path = os.path.join(questions_path, filename % 'val')
  test_questions_path = os.path.join(questions_path, filename % 'test')

  with open(training_question_path) as f:
    training_questions = ujson.load(f)['questions']

  print("Loaded training")

  with open(validation_questions_path) as f:
    validation_questions = ujson.load(f)['questions']

  print("Loaded val")

  with open(test_questions_path) as f:
    test_questions = ujson.load(f)['questions']

  print("Loaded test")

  return training_questions, validation_questions, test_questions

def get_answer_families_correspondance():
  correspondance = {}
  for family, family_values in families.items():
    for value in family_values:
      correspondance[value] = family

  return correspondance

def get_answer_distribution_per_family(questions):
  answer_family_correspondance = get_answer_families_correspondance()
  counter = defaultdict(lambda: 0)
  count_per_answer_per_family = {}
  nb_question = len(questions)

  for question in questions:
    answer = question['answer'].lower() if type(question['answer']) is str else question['answer']
    family = answer_family_correspondance[answer]
    counter[family] += 1
    count_per_answer_per_family.setdefault(family, defaultdict(lambda : 0))[str(question['answer'])] += 1

  freq_per_answer_per_family = {}
  for family, family_vals in count_per_answer_per_family.items():
    for key, value in family_vals.items():
      freq_per_answer_per_family.setdefault(family.replace('_', " ").title(), {})[key] = value / nb_question

  # FIXME : REMOVE THIS.. SUPER HACKISH
  if len(freq_per_answer_per_family['Count'].keys()) < 10:
    freq_per_answer_per_family['Count']['9'] = 0

  return counter, freq_per_answer_per_family


def get_answer_distribution_per_family2(questions):
  individual_per_family = {}
  counter = defaultdict(lambda: 0)
  total_question = len(questions)

  for question in questions:
    for family, family_values in families.items():
      answer = question['answer'].lower() if type(question['answer']) is str else question['answer']
      if answer in family_values:
        counter[family] += 1
        individual_per_family.setdefault(family, defaultdict(lambda : 0))[str(question['answer'])] += 1
        break

  ind_per_family = {}
  for family, family_vals in individual_per_family.items():
    for key, value in family_vals.items():
      ind_per_family.setdefault(family, {})[key] = value/total_question

  return counter, ind_per_family

def get_answer_distribution_per_family_patched(questions):
  counter, answer_distribution_by_family = get_answer_distribution_per_family(questions)
  prepared_for_DF = {}
  for family, value_frequency in answer_distribution_by_family.items():
    for value, freq in value_frequency.items():
      prepared_for_DF[value] = {'family': family, 'frequency': freq}

  return prepared_for_DF

def get_answer_distribution_per_family_patched_second(questions):
  counter, answer_distribution_by_family = get_answer_distribution_per_family(questions)
  prepared_for_DF = []
  for family, value_frequency in answer_distribution_by_family.items():
    for value, freq in value_frequency.items():
      prepared_for_DF.append([value, family, freq])

  return prepared_for_DF

def get_answer_distribution(questions):
  counter = defaultdict(lambda: 0)
  total_question = len(questions)


  for question in questions:
    counter[question['answer']] += 1

  distribution = {k: val/total_question for k,val in counter.items()}

  return distribution


def main():
  #args = parser.parse_args()
  template_path = 'question_generation/AQA_templates'
  question_path = "/home/jerome/dev/film-aqa/data/v1.1.0_1k_scenes_20_inst/questions"
  experiment_name = "v2.0.0_50k_scenes_40_inst"
  question_path = "/home/jerome/dev/datasets-remote/%s/questions" % experiment_name
  question_path = "/home/jerome/dev/datasets-remote/%s-titan01/questions" %experiment_name

  train_questions, val_questions, test_questions = load_questions_with_program_beautified(question_path, template_path)


  get_answer_distribution_per_family(train_questions)

  exit(0)

  train_dist = get_answer_distribution(train_questions)
  val_dist = get_answer_distribution(val_questions)
  test_dist = get_answer_distribution(test_questions)

  with open('./analysis/questions_stats/%s_train_answer_dist.json' % experiment_name, 'w') as f:
    ujson.dump(train_dist, f, indent=2)

  with open('./analysis/questions_stats/%s_val_answer_dist.json' % experiment_name, 'w') as f:
    ujson.dump(val_dist, f, indent=2)

  with open('./analysis/questions_stats/%s_test_answer_dist.json' % experiment_name, 'w') as f:
    ujson.dump(test_dist, f, indent=2)

  print(ujson.dumps(test_dist, indent=2))

  print("Done")


if __name__ == "__main__":
  main()