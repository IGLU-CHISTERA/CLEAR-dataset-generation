import ujson
import numpy as np
import os
import argparse
from matplotlib import pyplot as plt

basepath = 'answers_stats_50k_40'

question_types = ['instrument', 'musical_note', 'loudness', 'brightness', 'position_global', 'position']
question_names = {'musical_note': 'note', 'position_global': 'global pos.', 'position': 'relative pos.', 'loudness': 'loudness', 'instrument': 'instrument', 'brightness': 'brightness'}

models = ['1k_scenes_20_inst', '1k_scenes_40_inst', '10k_scenes_20_inst', '10k_scenes_40_inst', '10k_scenes_40_inst_2resblock', '50k_scenes_20_inst', '50k_scenes_40_inst']

data = dict()
for model in models:
    fname = os.path.join(basepath, 'v1.1.0_'+model+'_testrun_test_accuracy_per_family.json')
    with open(fname) as f:
        data[model] = ujson.load(f)

acc = np.zeros((len(models), len(question_types)))
for midx, model in enumerate(models):
    for qtidx, qtype in enumerate(question_types):
        acc[midx,qtidx] = data[model][qtype]['accuracy']

plt.figure(figsize=(6,3))
plt.plot(acc.T*100)
plt.xticks(np.arange(len(question_types)), [question_names[qtype] for qtype in question_types])
plt.legend(models)
plt.ylabel('accuracy (%)')
plt.title('accuracy per question type (FiLM)')
plt.tight_layout()
plt.savefig('accuracy_per_question_family.pdf')
