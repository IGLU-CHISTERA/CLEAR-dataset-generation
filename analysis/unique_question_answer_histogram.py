import ujson
from collections import defaultdict
import json
import os
import copy
import matplotlib
import argparse
from questions_stats import load_questions
import numpy as np
# Matplotlib options to reduce memory usage
#matplotlib.interactive(False)
#matplotlib.use('agg')

import matplotlib.pyplot as plt

parser = argparse.ArgumentParser(fromfile_prefix_chars='@')

parser.add_argument('--output_folder', default='../output', type=str,
                    help='Folder where the audio and images are located')
parser.add_argument('--output_version_nb', type=str,
                    help='Version number to analyse')


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

if __name__ == "__main__":
  args = parser.parse_args()
  # args = parser.parse_args(['--output_version_nb', 'v1.0.0_50k_scenes'])
  questions_path = os.path.join(args.output_folder, args.output_version_nb, 'questions')

  questions = dict()
  questions['training'], questions['validation'], questions['test'] = load_questions(questions_path)
  print("Question loaded")

  question_text_with_answer_list = dict()
  question_text_with_asswer_duplicate_count = dict()
  counts = dict()
  maxOccurrence = 0
  for subset in questions.keys():
    question_text_with_answer_list[subset] = get_question_text_with_answer_list(questions[subset])
    question_text_with_asswer_duplicate_count[subset] = get_question_text_with_answer_duplicate_count(question_text_with_answer_list[subset])
    counts[subset] = np.array(list(question_text_with_asswer_duplicate_count[subset].values()))
    maxOccurrence = max(counts[subset].max(), maxOccurrence)
  # plotting
  bins = np.arange(0.5, maxOccurrence+1.5)
  h=dict()
  bar_width=0.2
  bar_shift = {'training': 0.5-bar_width, 'validation': 0.5, 'test': 0.5+bar_width}
  for subset in questions.keys():
    h[subset], be = np.histogram(counts[subset], bins, density=True)
  # Collect data in matrix
  N = 20
  hplot = np.zeros((N+1, 3))
  f = plt.figure(figsize=(8,4))
  for idx, subset in enumerate(['training', 'validation', 'test']):
    hplot[:N,idx] = h[subset][:N]
    hplot[N,idx] = h[subset][N:].sum()
    plt.bar(bins[:21]+bar_shift[subset], hplot[:,idx], width=bar_width, align='center', label=subset)
  #plt.xlim([0,20])
  plt.xticks(np.arange(1,N+2), [str(i) for i in range(1,N+1)]+['>'+str(N)])
  plt.title('Unique Questions/Answer')
  plt.xlabel('number of repetitions')
  plt.ylabel('frequency')
  plt.legend()
  plt.savefig('unique_question_answer_histogram_'+args.output_version_nb+'.pdf')
  
