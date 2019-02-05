import ujson
from collections import defaultdict
import os
import argparse


parser = argparse.ArgumentParser(fromfile_prefix_chars='@')

parser.add_argument('--results_file_path', default='', type=str,
                    help='')

parser.add_argument('--exp_name', default='', type=str,
                    help='')


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


def load_results(results_path):
  with open(results_path, 'r') as f:
    results = ujson.load(f)

  return results


def get_generated_answer_distribution(results):
  counter = defaultdict(lambda: 0)
  total_answers = len(results)


  for result in results:
    counter[result['generated_answer']] += 1

  distribution = {k: val/total_answers for k,val in counter.items()}

  return distribution


# FIXME : Should use metadata file..
families = {
  'position' : [
    "first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth"
  ],
  'position_global' : [
    "beginning of the scene", "middle of the scene", "end of the scene"
  ],
  'musical_note': [
    "A", "A_Sharp", "B", "C", "C_Sharp", "D", "D_Sharp", "E", "F", "F_Sharp", "G", "G_Sharp"
  ],
  'brightness': [
    "bright", "dark"
  ],
  'loudness': [
    "quiet", "loud"
  ],
  'instrument': [
    "cello", "clarinet", "flute", "trumpet", "violin"
  ]
}

def get_accuracy_per_family(results):

  counter = defaultdict(lambda: {'correct' : 0, 'incorrect': 0})

  for result in results:
    for family, family_values in families.items():
      if result['ground_truth'] in family_values:
        question_family = family

    if result['generated_answer'] == result['ground_truth']:
      counter[question_family]['correct'] += 1
    else:
      counter[question_family]['incorrect'] += 1

  for family, count in counter.items():
    count['accuracy'] = count['correct'] / (count['correct'] + count['incorrect'])

  return counter

def main():
  args = parser.parse_args()

  #result_file = '/home/jerome/dev/test_results.json'
  #result_file = '/home/jerome/dev/aqa-results/test_results/v1.1.0_10k_scenes_40_inst_testrun/test_results.json'

  results = load_results(args.results_file_path)

  accuracies = get_accuracy_per_family(results)

  with open('./analysis/answers_stats_10k_20/%s_test_accuracy_per_family.json' % args.exp_name, 'w') as f:
    ujson.dump(accuracies, f, indent=2)

  print(ujson.dumps(accuracies, indent=2))

  print("Done")


if __name__ == "__main__":
  main()