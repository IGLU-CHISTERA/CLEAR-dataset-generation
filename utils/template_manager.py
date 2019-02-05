import os
import json
import ujson
import re
from collections import OrderedDict, defaultdict


def load_templates(template_dir):
  # Load templates from disk
  # Key is (filename, file_idx)
  num_loaded_templates = 0
  templates = {}
  for fn in os.listdir(template_dir):
    if not fn.endswith('.json'): continue
    with open(os.path.join(template_dir, fn), 'r') as f:
      try:
        templates[fn] = json.load(f, object_pairs_hook=OrderedDict)
      except ValueError:
        print(
          "[ERROR] Could not load template %s" % fn)  # FIXME : We should probably pause or do something to inform the user. This message will be flooded by the rest of the output. Maybe do a pause before generating ?
      num_loaded_templates += 1
  print('Read %d templates from disk' % num_loaded_templates)
  return templates


def load_questions(questions_path):
  print("Loading questions from %s" % questions_path)

  with open(questions_path) as f:
    questions = ujson.load(f)['questions']

  print("Questions Loaded")

  return questions


def load_scenes(scenes_path):
  print("Loading scenes from %s" % scenes_path)

  with open(scenes_path) as f:
    scenes = ujson.load(f)['scenes']

  print("Scenes Loaded")

  return scenes


def filter_templates_with_notes(templates_by_filename):
  enabled_templates = {}
  disabled_templates = {}
  for filename, templates in templates_by_filename.items():
    enabled_templates[filename] = []
    disabled_templates[filename] = []
    for template in templates:
      enabled = True
      if 'note' in template:
        # FIXME : Do not hardcode the "on 70"
        if 'on 70' in template['note']:
          matches = re.search(".*[\s,\.](\d+)\son\s70", template['note'])
          if matches is None :
            # FIXME : Should not happen. Fix the note in templates
            enabled = False
          else:
            nb_of_answers = int(matches.group(1))
            if nb_of_answers < 0.6*70:
              enabled = False
        else:
          enabled = False

      if enabled:
        template['disabled'] = False
        enabled_templates[filename].append(template)
      else:
        template['disabled'] = True
        disabled_templates[filename].append(template)

  return enabled_templates, disabled_templates


def filter_percussion_templates(templates_by_filename):

  non_percussion_templates = {}
  percussion_templates = {}

  reg = re.compile('<([a-zA-Z]+)(\d)?>')

  for filename, templates in templates_by_filename.items():
    non_percussion_templates[filename] = []
    percussion_templates[filename] = []
    for template in templates:
      matches = re.findall(reg, template['text'][0])
      matches = [m[0] for m in matches]

      if "PE" in matches:
        percussion_templates[filename].append(template)
      else:
        non_percussion_templates[filename].append(template)

  return non_percussion_templates, percussion_templates


def get_all_placeholders(templates_by_filename):

  placeholders = set()

  reg = re.compile('<([a-zA-Z]+)(\d)?>')

  for filename, templates in templates_by_filename.items():
    for template in templates:
      matches = re.findall(reg, template['text'][0])
      matches = [m[0] for m in matches]

      placeholders.update(matches)

  return placeholders


def enable_all(templates):
  for filename, templates_list in templates.items():
    for template in templates_list:
      template['disabled'] = False

  print("Enabled all templates")


def remove_all_notes(templates):
  for filename, templates_list in templates.items():
    for template in templates_list:
      if 'note' in template:
        del template['note']

  print("Removed all notes from templates")


def filter_by_occurence(templates, version_nb, minimum_ratio):
  filtered_templates = {}
  rejected_templates = {}
  for filename, templates_list in templates.items():
    for template in templates_list:
      if 'instantiation' in template:
        if template['instantiation'][version_nb]['ratio'] >= minimum_ratio:
          filtered_templates.setdefault(filename, []).append(template)
        else:
          rejected_templates.setdefault(filename, []).append(template)

  return filtered_templates, rejected_templates


def get_all_last_node_type(templates_by_filename):

  node_types = set()

  for filename, templates in templates_by_filename.items():
    for template in templates:

      node_types.add(template['nodes'][-1]['type'])

  return node_types


def write_templates(templates, template_folder):

  if not os.path.isdir(template_folder):
    os.mkdir(template_folder)
  else:
    print("Folder already exist.. Was it empty ?")  # TODO : Add a prompt to clean the folder

  for filename, template_list in templates.items():

    with open(os.path.join(template_folder, filename), 'w') as f:
      json.dump(template_list, f, indent=2)


def harmonize_question_mark_spacing(templates, use_space):
  invalid_count = 0
  for filename, file_templates in templates.items():
    for template in file_templates:
      for i, text in enumerate(template['text']):
        have_space = len(re.findall(r'\s\?$', text)) > 0

        if use_space and not have_space:
          template['text'][i] = text.replace('?', ' ?')
          invalid_count += 1
        elif not use_space and have_space:
          template['text'][i] = text.replace(' ?', '?')
          invalid_count += 1

  print("Modified %d templates text. Use_space = %s" % (invalid_count, use_space))


def get_question_occurence_by_template(questions):
  occurence_by_template = {}
  for question in questions:
    separator_index = question['template_filename'].find('.json')
    template_filename = question['template_filename'][:separator_index+5]
    template_index = question['template_filename'][separator_index+6:]

    if template_filename not in occurence_by_template:
      occurence_by_template[template_filename] = {}

    if template_index not in occurence_by_template[template_filename]:
      occurence_by_template[template_filename][template_index] = 0

    occurence_by_template[template_filename][template_index] += 1

  return occurence_by_template


def add_occurence_note_to_templates(templates, occurence_by_template, max_instance_per_template, version_nb):
  for filename, template_list in templates.items():
    for i, template in enumerate(template_list):
      index = str(i)
      if filename in occurence_by_template and index in occurence_by_template[filename]:
        nb_instance = occurence_by_template[filename][index]
      else:
        nb_instance = 0

      template_list[i].setdefault('instantiation', {})[version_nb] = {
        'instances': nb_instance,
        'max': max_instance_per_template,
        'ratio': float('%.2f' % (nb_instance / max_instance_per_template))
      }

  return templates


if __name__ == "__main__":
  # FIXME : Should be able to chose between train, val and test sets
  # TODO : Take those as parameters
  question_filename = "AQA_%s_questions.json"
  scenes_filename = "AQA_%s_scenes.json"
  output_path = './output'
  output_version_nb = 'v1.0.0_test_templates'
  template_folder = "./question_generation/AQA_templates_ALL_ENABLED"
  output_folder = os.path.join(output_path, output_version_nb)
  question_folder = os.path.join(output_folder, 'questions')
  scene_folder = os.path.join(output_folder, 'scenes')
  training_question_path = os.path.join(question_folder, question_filename % 'train')
  training_scene_path = os.path.join(scene_folder, scenes_filename % 'train')
  val_question_path = os.path.join(question_folder, question_filename % 'val')
  val_scene_path = os.path.join(scene_folder, scenes_filename % 'val')
  test_question_path = os.path.join(question_folder, question_filename % 'test')
  test_scene_path = os.path.join(scene_folder, scenes_filename % 'test')
  instances_per_template = 1

  # Loading templates
  templates = load_templates(template_folder)

  # Loading questions
  #training_questions = load_questions(training_question_path)
  test_questions = load_questions(test_question_path)
  val_questions = load_questions(val_question_path)

  # Loading scenes
  training_scenes = load_scenes(training_scene_path)
  test_scenes = load_scenes(test_scene_path)
  val_scenes = load_scenes(val_scene_path)

  max_question_instance_per_template_train = len(training_scenes) * instances_per_template
  max_question_instance_per_template_test = len(test_scenes) * instances_per_template
  max_question_instance_per_template_val = len(val_scenes) * instances_per_template

  # Make sure all templates use the same spacing convention (Either have a space before the question mark or not)
  harmonize_question_mark_spacing(templates, use_space=True)

  # Remove notes from templates
  remove_all_notes(templates)

  #enable_all(templates)

  #write_templates(templates, 'question_generation/AQA_templates_ALL_ENABLED')


  # Calculate the nb of occurence for each templates
  occurence_by_template = get_question_occurence_by_template(test_questions)
  templates_with_instantiation_stats = add_occurence_note_to_templates(templates,
                                                                       occurence_by_template,
                                                                       max_question_instance_per_template_test,
                                                                       output_version_nb)

  accepted_templates, rejected_templates = filter_by_occurence(templates_with_instantiation_stats,
                                                               output_version_nb,
                                                               minimum_ratio=0.6)

  write_templates(accepted_templates, 'question_generation/AQA_templates_ENOUGH_INSTANCES')
  write_templates(rejected_templates, 'question_generation/AQA_templates_NOT_ENOUGH_INSTANCES')


  #write_templates(templates_with_instantiation_stats, 'question_generation/AQA_templates_WITH_STATS')

  #node_types = get_all_last_node_type(templates)

  #placeholders = get_all_placeholders(templates)

  #non_percussion_templates, percussion_templates = filter_percussion_templates(templates)

  #write_templates(non_percussion_templates, 'question_generation/AQA_templates_NO_PERCUSSION')
  #enabled_templates, disabled_templates = filter_templates_with_notes(templates)

  #write_templates(enabled_templates, 'question_generation/AQA_templates_PASSING')
  #write_templates(disabled_templates, 'question_generation/AQA_templates_NOT_PASSING')

  print("Done")
