import os
import json
import re
from collections import OrderedDict


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
  print('Read %d templates from disk' % num_loaded_templates)
  return templates


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


def write_templates(templates, template_folder):

  if not os.path.isdir(template_folder):
    os.mkdir(template_folder)
  else:
    print("Folder already exist.. Was it empty ?")  # TODO : Add a prompt to clean the folder

  for filename, template_list in templates.items():

    with open(os.path.join(template_folder, filename), 'w') as f:
      json.dump(template_list, f, indent=2)


if __name__ == "__main__":
  templates = load_templates("question_generation/AQA_templates")

  enabled_templates, disabled_templates = filter_templates_with_notes(templates)

  write_templates(enabled_templates, 'question_generation/AQA_templates_PASSING')
  write_templates(disabled_templates, 'question_generation/AQA_templates_NOT_PASSING')