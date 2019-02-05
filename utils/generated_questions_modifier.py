import json
import re
import os
from collections import OrderedDict


def load_questions(questions_path):
  print("Loading questions from %s" % questions_path)

  with open(questions_path) as f:
    questions = json.load(f, object_pairs_hook=OrderedDict)

  print("Questions Loaded")

  return questions['info'], questions['questions']


def change_question_mark_spacing(questions, use_space):
  new_questions = []

  for question in questions:
    new_questions.append(question)
    have_space = len(re.findall(r'\s\?$', question['question'])) > 0

    if use_space and not have_space:
      new_questions[-1]['question'] = question['question'].replace('?', ' ?')
    elif not use_space and have_space:
      new_questions[-1]['question'] = question['question'].replace(' ?', '?')

  return new_questions

# TODO : Write to file
