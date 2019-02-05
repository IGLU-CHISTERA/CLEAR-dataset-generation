import numpy as np
import holoviews as hv
import holoviews.plotting.bokeh
import pandas as pd
from utils.question_classifier import load_questions_with_program_beautified, get_all_question_type_percent, get_all_template_type_percent, load_templates
from analysis.answers_distribution import get_answer_distribution, get_answer_distribution_per_family
from analysis.scenes_stats import load_scenes, get_scene_distributions


renderer = hv.renderer('bokeh')

questions_path = "/home/jerome/dev/datasets-remote/v2.0.0_50k_scenes_40_inst-titan01/questions"
template_path = 'question_generation/AQA_templates'

training_questions, val_questions, test_questions = load_questions_with_program_beautified(questions_path, template_path)
templates = load_templates(template_path)
train_scenes, val_scenes, test_scenes = load_scenes('/home/jerome/dev/datasets-remote/v2.0.0_50k_scenes_40_inst-titan01/scenes')

all_scenes = train_scenes + val_scenes + test_scenes

training_questions_type_percent = get_all_question_type_percent(training_questions)
training_questions_type_percent = {k: {'Frequency' : v, 'set': 'train'} for k,v in training_questions_type_percent.items()}
val_questions_type_percent = get_all_question_type_percent(val_questions)
val_questions_type_percent = {k: {'Frequency' : v, 'set': 'validation'} for k,v in val_questions_type_percent.items()}
test_questions_type_percent = get_all_question_type_percent(test_questions)
test_questions_type_percent = {k: {'Frequency' : v, 'set': 'test'} for k,v in test_questions_type_percent.items()}

all_questions = training_questions + val_questions + test_questions

all_questions_type_percent = get_all_question_type_percent(all_questions)

all_questions_type_percent_DF = pd.DataFrame.from_dict(all_questions_type_percent, orient='index', columns=['Frequency'])
all_questions_type_percent_DF.index.name = 'Type'
all_questions_type_percent_DF = all_questions_type_percent_DF.sort_values('Type')

training_questions_type_percent_DF = pd.DataFrame.from_dict(training_questions_type_percent, orient='index', columns=['Frequency', 'set'])
training_questions_type_percent_DF.index.name = 'Type'
val_questions_type_percent_DF = pd.DataFrame.from_dict(val_questions_type_percent, orient='index', columns=['Frequency','set'])
val_questions_type_percent_DF.index.name = 'Type'
test_questions_type_percent_DF = pd.DataFrame.from_dict(test_questions_type_percent, orient='index', columns=['Frequency','set'])
test_questions_type_percent_DF.index.name = 'Type'

all_questions_type_percent_DF = all_questions_type_percent_DF.sort_values('Type')

counter, answer_distribution_by_family = get_answer_distribution_per_family(all_questions)

prepared_for_DF = []

for answer_fam, counters in answer_distribution_by_family.items():
  for counter_name, counter_value in counters.items():
    prepared_for_DF.append({'value': counter_name, 'frequency': counter_value, 'family': answer_fam})

answer_distribution_by_family_DF = pd.DataFrame(prepared_for_DF, columns=['value', 'family', 'frequency'])

answer_distribution_by_family_bar_graph = hv.Bars(answer_distribution_by_family_DF, ['family','value'], 'frequency', label="Answer distribution by family")

renderer.save(answer_distribution_by_family_bar_graph,'out')

print("Done")