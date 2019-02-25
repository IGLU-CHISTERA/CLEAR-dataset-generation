import json
import os
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
        print(fn)
        templates[fn] = json.load(f, object_pairs_hook=OrderedDict)
      except ValueError:
        print(
          "[ERROR] Could not load template %s" % fn)  # FIXME : We should probably pause or do something to inform the user. This message will be flooded by the rest of the output. Maybe do a pause before generating ?
      num_loaded_templates += 1
  print('Read %d templates from disk' % num_loaded_templates)
  return templates


def get_text(templates):
  texts_by_filename = {}
  texts = []
  for filename, template_list in templates.items():
    for template in template_list:
      texts_by_filename.setdefault(filename, []).append(template['text'][0])
      texts.append(template['text'][0])

  return texts_by_filename, texts


def main():
  output_path = './output'
  output_version_nb = 'v1.0.0_test_templates'
  template_folder = "./question_generation/CLEAR_templates_ENOUGH_INSTANCES"

  templates = load_templates(template_folder)

  texts_by_filename, texts = get_text(templates)

  with open('template_texts_by_filename.json', 'w') as f:
    json.dump(texts_by_filename, f, indent=2)

  with open('template_texts.json', 'w') as f:
    json.dump(texts, f, indent=2)


if __name__ == "__main__":
  main()