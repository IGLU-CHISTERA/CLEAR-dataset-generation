import os
import ujson
from collections import defaultdict

from analysis.template_stats import load_templates


def replace_sharp_from_questions(questions):
  for question in questions:
    question['question'] = question['question'].replace('_Sharp', "#").capitalize()
    if type(question['answer']) is str:
      question['answer'] = question['answer'].replace('_Sharp', '#').title()


# FIXME : This should probably be in here. The loading of the question should be done in the script using this classifier
def load_questions(questions_path):
  print("Loading questions...")
  filename = "CLEAR_%s_questions.json"
  training_question_path = os.path.join(questions_path, filename % 'train')
  validation_questions_path = os.path.join(questions_path, filename % 'val')
  test_questions_path = os.path.join(questions_path, filename % 'test')

  with open(training_question_path) as f:
    training_questions = ujson.load(f)['questions']

  print("Loaded training questions")

  with open(validation_questions_path) as f:
    validation_questions = ujson.load(f)['questions']

  print("Loaded validation questions")

  with open(test_questions_path) as f:
    test_questions = ujson.load(f)['questions']
  print("Loaded test questions")

  return training_questions, validation_questions, test_questions


def add_question_program_from_template(questions, templates):

  for question in questions:
    template_key = question['template_filename'].split('-')
    template_key = (template_key[0], int(template_key[1]))
    question['program'] = templates[template_key]['nodes']

  return questions


special_ending_nodes_correspondence = {
  'add': 'count',
  'relate_filter_count': 'count',
  'filter_count': 'count',
  'count_different_instrument': 'count',
  'or':  'exist',
  'relate_filter_exist': 'exist',
  'filter_exist': 'exist',
  'equal_integer': 'compare_integer',
  'greater_than': 'compare_integer',
  'less_than': 'compare_integer',
  'query_position': 'query_position_absolute',
  'query_human_note': 'query_musical_note'

}

special_intermediary_nodes_correspondence = {
  'duration': ['filter_longest_duration', 'filter_shortest_duration'],
  'relation': ['relate_filter', 'relate_filter_unique', 'relate_filter_not_unique', 'relate_filter_count', 'relate_filter_exist']
}


def get_question_type(question_nodes):
  last_node_type = question_nodes[-1]['type']

  if last_node_type in special_ending_nodes_correspondence:
    last_node_type = special_ending_nodes_correspondence[last_node_type]

  return last_node_type.title().replace('_', ' ')


def get_all_question_type_count(questions, node_key='program'):
  counter = defaultdict(lambda : 0)

  for question in questions:
    question_type = get_question_type(question[node_key])
    counter[question_type] += 1

  return counter


def get_all_question_type_percent(questions, node_key='program'):
  counter = get_all_question_type_count(questions, node_key)

  nb_questions = len(questions)
  counter = {k : v/nb_questions for k, v in counter.items()}

  return counter


def get_all_last_node_type(questions):

  node_types = set()

  for question in questions:
    node_types.add(question['program'][-1]['type'])

  return node_types


def get_all_node_type(questions):

  node_types = set()

  for question in questions:
    nodes = [n['type'] for n in question['program']]
    node_types.update(nodes)

  return node_types


def get_all_template_type_percent(templates):
  return get_all_question_type_percent(list(templates.values()), node_key='nodes')


def load_questions_with_program_beautified(questions_path, templates_path):
  training_questions, validation_questions, test_questions = load_questions_with_program(questions_path, templates_path)

  replace_sharp_from_questions(training_questions)
  replace_sharp_from_questions(validation_questions)
  replace_sharp_from_questions(test_questions)

  return training_questions, validation_questions, test_questions


def load_questions_with_program(questions_path, templates_path):
  # Load questions
  training_questions, validation_questions, test_questions = load_questions(questions_path)

  # Load templates
  templates = load_templates(templates_path)

  # Add program from template for each questions
  training_questions = add_question_program_from_template(training_questions, templates)
  validation_questions = add_question_program_from_template(validation_questions, templates)
  test_questions = add_question_program_from_template(test_questions, templates)

  return training_questions, validation_questions, test_questions


if __name__ == "__main__":
  version_nb = 'v0.2.1_10000_scenes'
  output_folder = os.path.join('./output', version_nb)

  output_folder = '/home/jerome/datasets/AQA_REMOTE/v2.0.0_50k_scenes_40_inst-titan01'

  questions_path = os.path.join(output_folder, 'questions')

  template_path = 'question_generation/CLEAR_templates'

  training_questions, validation_questions, test_questions = load_questions_with_program(questions_path, template_path)

  templates = load_templates(template_path)

  template_type_percent = get_all_template_type_percent(templates)

  # Questions type
  training_questions_types = get_all_question_type_percent(training_questions)
  validation_questions_types = get_all_question_type_percent(validation_questions)
  test_questions_types = get_all_question_type_percent(test_questions)

  all_questions = training_questions + validation_questions + test_questions
  all_questions_types = get_all_question_type_percent(all_questions)

  last_node_types = get_all_last_node_type(all_questions)

  all_node_types = get_all_node_type(all_questions)

  print("done")