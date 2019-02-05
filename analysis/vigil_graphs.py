from matplotlib import pyplot as plt
import numpy as np
import pandas as pd

from utils.question_classifier import load_questions_with_program_beautified, get_all_question_type_percent, load_templates, get_all_template_type_percent
from analysis.answers_distribution import get_answer_distribution, get_answer_distribution_per_family_patched, get_answer_distribution_per_family_patched_second
from analysis.scenes_stats import load_scenes   # TODO : Put all the helpers in the same file


def get_question_type_percent(questions):
  questions_type_percent = get_all_question_type_percent(questions)
  questions_type_percent = {k: {'Frequency': v, 'set': 'train'} for k, v in questions_type_percent.items()}

  questions_type_percent_DF = pd.DataFrame.from_dict(questions_type_percent, orient='index',
                                                              columns=['Frequency', 'set'])
  questions_type_percent_DF.index.name = 'Type'

  questions_type_percent_DF = questions_type_percent_DF.sort_values('Type')

  return questions_type_percent_DF


def graph_generated_question_type_distribution(questions):
  questions_type_percent_DF = get_question_type_percent(questions)

                                                # TODO : Subplot each set to show differences
  questions_type_percent_DF.plot(kind='bar', title='Generated question type distribution')    # TODO : Make sure labels have enough space


def graph_template_type_distribution(templates):
  templates_type_percent = get_all_template_type_percent(templates)

  template_type_percent_DF = pd.DataFrame.from_dict(templates_type_percent, orient='index', columns=['Frequency'])
  template_type_percent_DF.index.name = 'Type'
  template_type_percent_DF = template_type_percent_DF.sort_values('Type')

  template_type_percent_DF.plot(kind='bar', title='Templates type distribution')


def graph_answer_distribution(questions):
  answer_distribution = get_answer_distribution(questions)
  answer_distribution_DF = pd.DataFrame.from_dict(answer_distribution, orient='index', columns=['Frequency'])
  answer_distribution_DF.index = answer_distribution_DF.index.map(str)
  answer_distribution_DF.index.name = 'Answer'

  answer_distribution_DF.plot(kind='bar', title='Answer distribution')

def graph_answer_distribution_by_family(questions):
  answer_distribution_by_family = get_answer_distribution_per_family_patched(questions)

  answer_distribution_by_family_DF = pd.DataFrame.from_dict(answer_distribution_by_family, orient='index', columns=['family', 'frequency'])
  answer_distribution_by_family_DF.index = answer_distribution_by_family_DF.index.map(str)
  answer_distribution_by_family_DF.index.name = 'Answer'

  print(answer_distribution_by_family_DF)

  t = answer_distribution_by_family_DF.groupby(by=['family'])

  count = 0
  for a in t:

    print(a)
    a.plot(kind='bar', title='Test plot %d' % count)
    count+=1

  #t.plot(kind='bar', title='test groupby')

  #answer_distribution_by_family_DF.plot(table=True)

  answer_distribution_by_family_DF.plot(kind='bar', title='Answer distribution by family')


def graph_answer_distribution_by_family_second(questions):
  answer_distribution_by_family = np.array(get_answer_distribution_per_family_patched_second(questions))

  fig = plt.figure()

  space = 0.3

  conditions = np.unique(answer_distribution_by_family[:, 1])


def main():
  questions_path = "/home/jerome/dev/datasets-remote/v2.0.0_50k_scenes_40_inst-titan01/questions"
  scene_path = '/home/jerome/dev/datasets-remote/v2.0.0_50k_scenes_40_inst-titan01/scenes'
  template_path = 'question_generation/AQA_templates'

  training_questions, val_questions, test_questions = load_questions_with_program_beautified(questions_path, template_path)
  #train_scenes, val_scenes, test_scenes = load_scenes(scene_path)
  templates = load_templates(template_path)

  #all_scenes = train_scenes + val_scenes + test_scenes
  all_questions = training_questions + val_questions + test_questions

  # Graphing
  #graph_generated_question_type_distribution(all_questions)

  #graph_template_type_distribution(templates)

  #graph_answer_distribution(all_questions)

  graph_answer_distribution_by_family(all_questions)


  # Showing all graphs
  plt.show()





if __name__ == "__main__":
  main()