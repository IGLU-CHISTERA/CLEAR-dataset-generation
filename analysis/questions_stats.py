import ujson
from collections import defaultdict
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

  return training_questions, validation_questions, test_questions


def determine_question_family(program):
  program_types = [p['type'] for p in program]
  last_node_type = program_types[-1]

  # TODO : Check for special nodes

  return last_node_type


def do_analyse_questions(questions):
  # TODO : Attributes to check
  #   How many of each templates are generated

  print("Analysing questions...")

  questions_stats = []

  nb_question = len(questions)

  for question in questions:
    answer_count = {}
    word_count = {}
    template_count = {}
    node_count = {}
    question_family_count = {}

    # Special nodes
    # Question type -- Last node ---> Should make sure that the last node really represent the question
    # Max length of question

    if question['answer'] not in answer_count:
      answer_count[question['answer']] = 1
    else:
      answer_count[question['answer']] += 1

    if question['template_filename'] not in template_count:
      template_count[question['template_filename']] = 1
    else:
      template_count[question['template_filename']] += 1

    for word in question['question'].split(' '):
      if word not in word_count:
        word_count[word] = 1
      else:
        word_count[word] += 1

    for node in question['program']:
      if node['type'] not in node_count:
        node_count[node['type']] = 1
      else:
        node_count[node['type']] += 1

    question_family = determine_question_family(question['program'])

    if question_family not in question_family_count:
      question_family_count[question_family] = 1
    else:
      question_family_count[question_family] += 1

    questions_stats.append({
      'answer_count': answer_count,
      'question_length': len(question['question']),
      'word_count': word_count,
      'template_count': template_count,
      'node_count': node_count,
      'question_family_count': question_family_count
    })

  avg_stats = {
    'answer_count': {},
    'question_length': 0,
    'word_count': {},
    'template_count': {},
    'node_count': {},
    'question_family_count': {}
  }

  # Global count for all scenes
  for count_type, count_values in avg_stats.items():
    for question_stats in questions_stats:
      if type(count_values) is dict:
        for key, val in question_stats[count_type].items():
          if key not in avg_stats[count_type]:
            avg_stats[count_type][key] = val
          else:
            avg_stats[count_type][key] += val
      elif type(count_values) is int:
        avg_stats[count_type] += question_stats[count_type]

  total_count = copy.deepcopy(avg_stats)

  # We don't want to keep track of the total number of word
  del total_count['question_length']

  # Additional stats
  total_count['nb_diff_answers'] = len(total_count['answer_count'].keys())
  print(total_count['nb_diff_answers'])

  # Calculate average
  for count_key, count_values in avg_stats.items():
    if type(count_values) is dict:
      for key, val in count_values.items():
        avg_stats[count_key][key] = val/nb_question
    elif type(count_values) is int:
      avg_stats[count_key] /= nb_question

  return total_count, avg_stats


def analyse_questions(output_folder, set_type, scenes):
  # Analyse the scenes
  total_count, avg_stats = do_analyse_questions(scenes)

  # Create output folder structure
  stats_folder_path = os.path.join(output_folder, 'stats')
  if not os.path.isdir(stats_folder_path):
    os.mkdir(stats_folder_path)

  set_stats_folder_path = os.path.join(stats_folder_path, set_type)
  if not os.path.isdir(set_stats_folder_path):
    os.mkdir(set_stats_folder_path)

  scenes_stats_folder_path = os.path.join(set_stats_folder_path, 'questions')
  if not os.path.isdir(scenes_stats_folder_path):
    os.mkdir(scenes_stats_folder_path)

  # Save result to file
  write_stats_to_file(scenes_stats_folder_path, set_type, total_count, avg_stats)
  save_piechart(scenes_stats_folder_path, avg_stats)


def write_stats_to_file(output_folder, set_type, total_count, avg_count):
  stats_file_path = os.path.join(output_folder, '%s_questions_stats.json' % set_type)

  with open(stats_file_path, 'w') as f:
    ujson.dump({
      'avg_per_question_count' : avg_count,
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
      int_values[attribute] = count_by_values # TODO : Save those somewhere. Table ?


def get_instantiated_template_name_list(questions):
  template_list = set()
  for question in questions:
    template_list.add(question['template_filename'])

  return template_list


def get_question_text_list(questions):
  question_list = []
  for question in questions:
    question_list.append(question['question'])

  return question_list


def get_question_text_duplicate_count(questions_text):
  counter = defaultdict(lambda: 0)

  for question_text in questions_text:
    counter[question_text] += 1

  return counter

def get_question_text_with_answer_list(questions):
  question_with_answer = []

  for question in questions:
    question_with_answer.append((question['question'], question['answer']))

  return question_with_answer


def get_question_text_with_answer_duplicate_count(questions_with_answers):
  counter = defaultdict(lambda : 0)

  for question_answer in questions_with_answers:
    counter[question_answer] += 1

  return counter


def get_difference_between_sets(training_questions, validation_questions, test_questions, result_filepath):
  analysis_result = {
    'total_question_count': {},
    'template_differences': {},
    'questions_text_differences': {},
    'questions_text_duplicate': {},
    'questions_text_answer_differences': {},
    'questions_text_answer_duplicate': {}
  }

  analysis_result['total_question_count']['nb_train_questions'] = len(training_questions)
  analysis_result['total_question_count']['nb_val_questions'] = len(validation_questions)
  analysis_result['total_question_count']['nb_test_questions'] = len(test_questions)

  # Verify what templates are unique to each set {train, val, test}
  training_instantiated_templates = get_instantiated_template_name_list(training_questions)
  validation_instantiated_templates = get_instantiated_template_name_list(validation_questions)
  test_instantiated_templates = get_instantiated_template_name_list(test_questions)

  templates_in_train_only = training_instantiated_templates - validation_instantiated_templates - test_instantiated_templates
  templates_in_train_not_test = training_instantiated_templates - test_instantiated_templates
  templates_in_train_not_val = training_instantiated_templates - validation_instantiated_templates
  templates_in_test_only = test_instantiated_templates - training_instantiated_templates - validation_instantiated_templates
  templates_in_test_not_train = test_instantiated_templates - training_instantiated_templates
  templates_in_test_not_val = test_instantiated_templates - validation_instantiated_templates
  templates_in_val_only = validation_instantiated_templates - training_instantiated_templates - test_instantiated_templates
  templates_in_val_not_train = validation_instantiated_templates - training_instantiated_templates
  templates_in_val_not_test = validation_instantiated_templates - test_instantiated_templates

  analysis_result['template_differences']['nb_templates_in_train_only'] = len(templates_in_train_only)
  analysis_result['template_differences']['nb_templates_in_train_not_test'] = len(templates_in_train_not_test)
  analysis_result['template_differences']['nb_templates_in_train_not_val'] = len(templates_in_train_not_val)
  analysis_result['template_differences']['nb_templates_in_test_only'] = len(templates_in_test_only)
  analysis_result['template_differences']['nb_templates_in_test_not_train'] = len(templates_in_test_not_train)
  analysis_result['template_differences']['nb_templates_in_test_not_val'] = len(templates_in_test_not_val)
  analysis_result['template_differences']['nb_templates_in_val_only'] = len(templates_in_val_only)
  analysis_result['template_differences']['nb_templates_in_val_not_train'] = len(templates_in_val_not_train)
  analysis_result['template_differences']['nb_templates_in_val_not_test'] = len(templates_in_val_not_test)

  # Verify what questions are unique to each set
  training_questions_text = get_question_text_list(training_questions)
  validation_questions_text = get_question_text_list(validation_questions)
  test_questions_text = get_question_text_list(test_questions)

  training_questions_text_duplicate_count_per_text = get_question_text_duplicate_count(training_questions_text)
  validation_questions_text_duplicate_count_per_text = get_question_text_duplicate_count(validation_questions_text)
  test_questions_text_duplicate_count_per_text = get_question_text_duplicate_count(test_questions_text)

  unique_training_questions_text = set(training_questions_text)
  unique_validation_questions_text = set(validation_questions_text)
  unique_test_questions_text = set(test_questions_text)

  nb_unique_training_questions_text = len(unique_training_questions_text)
  nb_unique_validation_questions_text = len(unique_validation_questions_text)
  nb_unique_test_questions_text = len(unique_test_questions_text)

  analysis_result['questions_text_duplicate']['training_total_duplicated_questions_text'] = len(training_questions_text) - nb_unique_training_questions_text
  analysis_result['questions_text_duplicate']['validation_total_duplicated_questions_text'] = len(validation_questions_text) - nb_unique_validation_questions_text
  analysis_result['questions_text_duplicate']['test_total_duplicated_questions_text'] = len(test_questions_text) - nb_unique_test_questions_text

  questions_in_train_only = unique_training_questions_text - unique_test_questions_text - unique_validation_questions_text
  questions_in_train_not_test = unique_training_questions_text - unique_test_questions_text
  questions_in_train_not_val = unique_training_questions_text - unique_validation_questions_text
  questions_in_test_only = unique_test_questions_text - unique_training_questions_text - unique_validation_questions_text
  questions_in_test_not_train = unique_test_questions_text - unique_training_questions_text
  questions_in_test_not_val = unique_test_questions_text - unique_validation_questions_text
  questions_in_val_only = unique_validation_questions_text - unique_training_questions_text - unique_test_questions_text
  questions_in_val_not_train = unique_validation_questions_text - unique_training_questions_text
  questions_in_val_not_test = unique_validation_questions_text - unique_test_questions_text

  analysis_result['questions_text_differences']['nb_questions_in_train_only'] = len(questions_in_train_only)
  analysis_result['questions_text_differences']['nb_questions_in_train_not_test'] = len(questions_in_train_not_test)
  analysis_result['questions_text_differences']['nb_questions_in_train_not_val'] = len(questions_in_train_not_val)
  analysis_result['questions_text_differences']['nb_questions_in_test_only'] = len(questions_in_test_only)
  analysis_result['questions_text_differences']['nb_questions_in_test_not_train'] = len(questions_in_test_not_train)
  analysis_result['questions_text_differences']['nb_questions_in_test_not_val'] = len(questions_in_test_not_val)
  analysis_result['questions_text_differences']['nb_questions_in_val_only'] = len(questions_in_val_only)
  analysis_result['questions_text_differences']['nb_questions_in_val_not_train'] = len(questions_in_val_not_train)
  analysis_result['questions_text_differences']['nb_questions_in_val_not_test'] = len(questions_in_val_not_test)

  # Verify what (Question, Answer) are unique to each set
  training_questions_text_answer = get_question_text_with_answer_list(training_questions)
  validation_questions_text_answer = get_question_text_with_answer_list(validation_questions)
  test_questions_text_answer = get_question_text_with_answer_list(test_questions)

  training_questions_text_answer_duplicate_count_per_text_answer = get_question_text_duplicate_count(training_questions_text_answer)
  validation_questions_text_answer_duplicate_count_per_text_answer = get_question_text_duplicate_count(validation_questions_text_answer)
  test_questions_text_answer_duplicate_count_per_text_answer = get_question_text_duplicate_count(test_questions_text_answer)

  unique_training_questions_text_answer = set(training_questions_text_answer)
  unique_validation_questions_text_answer = set(validation_questions_text_answer)
  unique_test_questions_text_answer = set(test_questions_text_answer)

  analysis_result['questions_text_answer_duplicate']['training_total_duplicated_questions_text_answer'] = len(training_questions_text_answer) - len(unique_training_questions_text_answer)
  analysis_result['questions_text_answer_duplicate']['validation_total_duplicated_questions_text_answer'] = len(validation_questions_text_answer) - len(unique_validation_questions_text_answer)
  analysis_result['questions_text_answer_duplicate']['test_total_duplicated_questions_text_answer'] = len(test_questions_text_answer) - len(unique_test_questions_text_answer)

  questions_answer_in_train_only = unique_training_questions_text_answer - unique_test_questions_text_answer - unique_validation_questions_text_answer
  questions_answer_in_train_not_test = unique_training_questions_text_answer - unique_test_questions_text_answer
  questions_answer_in_train_not_val = unique_training_questions_text_answer - unique_validation_questions_text_answer
  questions_answer_in_test_only = unique_test_questions_text_answer - unique_training_questions_text_answer - unique_validation_questions_text_answer
  questions_answer_in_test_not_train = unique_test_questions_text_answer - unique_training_questions_text_answer
  questions_answer_in_test_not_val = unique_test_questions_text_answer - unique_validation_questions_text_answer
  questions_answer_in_val_only = unique_validation_questions_text_answer - unique_training_questions_text_answer - unique_test_questions_text_answer
  questions_answer_in_val_not_train = unique_validation_questions_text_answer - unique_training_questions_text_answer
  questions_answer_in_val_not_test = unique_validation_questions_text_answer - unique_test_questions_text_answer

  analysis_result['questions_text_answer_differences']['nb_questions_answer_in_train_only'] = len(questions_answer_in_train_only)
  analysis_result['questions_text_answer_differences']['nb_questions_answer_in_train_not_test'] = len(questions_answer_in_train_not_test)
  analysis_result['questions_text_answer_differences']['nb_questions_answer_in_train_not_val'] = len(questions_answer_in_train_not_val)
  analysis_result['questions_text_answer_differences']['nb_questions_answer_in_test_only'] = len(questions_answer_in_test_only)
  analysis_result['questions_text_answer_differences']['nb_questions_answer_in_test_not_train'] = len(questions_answer_in_test_not_train)
  analysis_result['questions_text_answer_differences']['nb_questions_answer_in_test_not_val'] = len(questions_answer_in_test_not_val)
  analysis_result['questions_text_answer_differences']['nb_questions_answer_in_val_only'] = len(questions_answer_in_val_only)
  analysis_result['questions_text_answer_differences']['nb_questions_answer_in_val_not_train'] = len(questions_answer_in_val_not_train)
  analysis_result['questions_text_answer_differences']['nb_questions_answer_in_val_not_test'] = len(questions_answer_in_val_not_test)

  with open(result_filepath, 'w') as f:
    ujson.dump(analysis_result, f, indent=2, sort_keys=True)

  print("Done analysing difference between set. To see results, set breakpoint here.")


if __name__ == "__main__":
  args = parser.parse_args()
  output_path = "./%s/%s" % (args.output_folder, args.output_version_nb)
  scenes_path = os.path.join(output_path, 'scenes')

  questions_path = os.path.join(output_path, 'questions')

  # Load scenes
  training_questions, validation_questions, test_questions = load_questions(questions_path)
  print("Question loaded")

  # Get differences between sets
  get_difference_between_sets(training_questions, validation_questions, test_questions, './differences_between_sets.json')

  # Analyze scenes for each set
  #analyse_questions(output_path, 'train', training_questions)
  print("Training questions analyzed")

  #analyse_questions(output_path, 'val', validation_questions)
  print("Validation questions analyzed")

  #analyse_questions(output_path, 'test', test_questions)
  print("Test questions analyzed")

  print("Analysis finished. See %s/stats for infos" % output_path)
