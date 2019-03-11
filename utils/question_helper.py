import re, random, os, copy
from collections import OrderedDict
from functools import reduce
from itertools import groupby

import ujson
import numpy as np
import utils.question_engine as qeng


'''
  Tree Filtering functions
'''
def precompute_filter_options(scene_struct, attr_keys, can_be_null_attributes):
  # Keys are tuples (size, color, shape, material) (where some may be None)
  # and values are lists of object idxs that match the filter criterion
  attribute_map = OrderedDict()

  # Precompute masks
  masks = []
  for i in range(2 ** len(attr_keys)):
    mask = []
    for j in range(len(attr_keys)):
      mask.append((i // (2 ** j)) % 2)
    masks.append(mask)

  np.random.shuffle(masks)

  for object_idx, obj in enumerate(scene_struct['objects']):
    key = qeng.get_filter_key(attr_keys, scene_struct, object_idx)

    for mask in masks:
      masked_key = []
      for a, b in zip(key, mask):
        if b == 1:
          masked_key.append(a)
        else:
          masked_key.append(None)
      masked_key = tuple(masked_key)
      if masked_key not in attribute_map:
        attribute_map[masked_key] = set()
      attribute_map[masked_key].add(object_idx)

  # Keep only filters with Null values for allowed attributes
  deleted_keys = set()
  for key in list(attribute_map.keys()):
    for i, val in enumerate(key):
      if val is None and attr_keys[i] not in can_be_null_attributes and key not in deleted_keys:
          deleted_keys.add(key)
          del attribute_map[key]

  # FIXME : Generalize this
  # FIXME : Make sure this will hold when there is more positional attributes
  # Removing position attribute if there is only one occurrence of the instrument
  if "position_instrument" in attr_keys:
    keys_by_instrument = OrderedDict()
    for instrument, key in groupby(attribute_map.keys(), lambda x: x[0]):
      if instrument not in keys_by_instrument:
        keys_by_instrument[instrument] = []
      keys_by_instrument[instrument] += list(key)

    for instrument, keys in keys_by_instrument.items():
      if len(keys) == 1:
        # Only have 1 object, we remove the position attribute
        attribute_map[(instrument, None)] = attribute_map[keys[0]]
        del attribute_map[keys[0]]

  if '_filter_options' not in scene_struct:
    scene_struct['_filter_options'] = {}

  scene_struct['_filter_options'][tuple(attr_keys)] = attribute_map


def find_filter_options(object_idxs, scene_struct, attr, can_be_null_attributes):
  # Keys are tuples (size, color, shape, material) (where some may be None)
  # and values are lists of object idxs that match the filter criterion
  filter_key = tuple(attr)

  if '_filter_options' not in scene_struct or filter_key not in scene_struct['_filter_options']:
    precompute_filter_options(scene_struct, attr, can_be_null_attributes)

  attribute_map = OrderedDict()
  object_idxs = set(object_idxs)
  for k, vs in scene_struct['_filter_options'][filter_key].items():
    attribute_map[k] = sorted(list(object_idxs & vs))
  return attribute_map


def add_empty_filter_options(attribute_map, metadata, can_be_null_attributes, attr_keys, num_to_add):
  '''
  Add some filtering criterion that do NOT correspond to objects
  '''

  attr_vals = []
  for key in attr_keys:
    vals = metadata['attributes'][key]['values']
    if key in can_be_null_attributes:
         vals.append(None)

    attr_vals.append(vals)

  attr_vals_len = list(map(lambda x: len(x), attr_vals))

  if len(attr_vals) > 1:
    max_nb_filter = reduce(lambda x, y: x * y, attr_vals_len)
  else:
    max_nb_filter = attr_vals_len[0]

  target_size = min(len(attribute_map) + num_to_add, max_nb_filter)

  while len(attribute_map) < target_size:
    k = tuple(random.choice(v) for v in attr_vals)
    if k not in attribute_map:
      attribute_map[k] = []


def find_relate_filter_options(object_idx, scene_struct, attr, can_be_null_attributes,
                               unique=False, include_zero=False, not_unique=False, trivial_frac=0.1):
  options = OrderedDict()

  attr = [a for a in attr if not a.startswith('relate')]
  filter_key = tuple(attr)

  if '_filter_options' not in scene_struct or filter_key not in scene_struct['_filter_options']:
    precompute_filter_options(scene_struct, attr, can_be_null_attributes)

  nb_filters = len(scene_struct['_filter_options'][filter_key].keys()) * len(scene_struct['relationships'])
  nb_trivial = int(round(nb_filters * trivial_frac / (1 - trivial_frac)))

  # TODO/VERIFY : Will probably have to change the definition of "trivial"
  # TODO_ORIG: Right now this is only looking for nontrivial combinations; in some
  # cases I may want to add trivial combinations, either where the intersection
  # is empty or where the intersection is equal to the filtering output.
  trivial_options_keys = []
  non_trivial_options_keys = []
  all_options = {}

  for relationship in scene_struct['relationships']:
    relationship_index = scene_struct['_relationships_indexes'][relationship['type']]
    related = set(scene_struct['relationships'][relationship_index]['indexes'][object_idx])
    if len(related) == 0:
      # If no relation, the object is the first (No before relations) or the last (No after relations)
      continue
    for filters, filtered in scene_struct['_filter_options'][filter_key].items():
      intersection = related & filtered
      trivial = (intersection == filtered)
      if unique and len(intersection) != 1:
        continue
      if not_unique and len(intersection) <= 1:
        continue
      if not include_zero and len(intersection) == 0:
        continue

      key = (relationship['type'], filters)
      if trivial:
        trivial_options_keys.append(key)
      else:
        non_trivial_options_keys.append(key)
      all_options[key] = sorted(list(intersection))

  np.random.shuffle(trivial_options_keys)
  options_to_keep = non_trivial_options_keys + trivial_options_keys[:nb_trivial]

  # FIXME : Looping a second time is really ineficient.. We do it to make sure that we keep the same order in the dict to ensure reproducibility
  for relationship in scene_struct['relationships']:
    for filters, filtered in scene_struct['_filter_options'][filter_key].items():
      key = (relationship['type'], filters)
      if key in options_to_keep:
        options[key] = all_options[key]

  return options


'''
  Misc
'''
# Constants
_placeholders_to_attribute_reg = re.compile('<([a-zA-Z]+)(\d)?>')


def placeholders_to_attribute(template_text, metadata):
  correspondences = {}
  # Extracting the placeholders from the text
  matches = re.findall(_placeholders_to_attribute_reg, template_text)

  attribute_correspondences = {metadata['attributes'][t]['placeholder']: t for t in metadata['attributes']}

  for placeholder in matches:
    correspondences['<%s%s>' % (placeholder[0], placeholder[1])] = attribute_correspondences['<%s>' % placeholder[0]]

  return correspondences


def translate_can_be_null_attributes(can_be_null_attributes, param_name_to_attribute):
  """
  Translate placeholder strings to attribute names and remove duplicate
  Ex : can_be_null_attributes = ['<I>', '<I2>', '<HN>', '<HN2>', '<HN3>']
  """
  tmp = set()
  for can_be_null_attribute in can_be_null_attributes:
    tmp.add(param_name_to_attribute[can_be_null_attribute])

  return list(tmp)


'''
  File loading & Preprocessing 
'''
def load_and_prepare_templates(template_dir, metadata):
  # Load templates from disk
  # Key is (filename, file_idx)

  num_loaded_templates = 0
  templates = OrderedDict()
  for fn in os.listdir(template_dir):
    if not fn.endswith('.json'): continue
    with open(os.path.join(template_dir, fn), 'r') as f:
      try:
        template_json = ujson.load(f)
        for i, template in enumerate(template_json):
          num_loaded_templates += 1
          key = (fn, i)

          # Create index from placeholder string to attribute string (Ex : <I1> --> Instrument)
          template['_param_name_to_attribute'] = placeholders_to_attribute(template['text'][0], metadata)

          # Adding optionals parameters if not present. Remove the need to do null check when accessing
          optionals_keys = ['constraints', 'can_be_null_attributes']
          for op_key in optionals_keys:
            if op_key not in template:
              template[op_key] = []

          # Remove duplicated can_be_null_attributes (<I> and <I2> will result in 'instrument', 'instrument'.
          # We only want to keep the attribute name not the identifier)
          template['_can_be_null_attributes'] = translate_can_be_null_attributes(template['can_be_null_attributes'],
                                                                                 template['_param_name_to_attribute'])

          templates[key] = template
      except ValueError:
        print("[ERROR] Could not load template %s" % fn)
  print('Read %d templates from disk' % num_loaded_templates)

  return templates


def load_scenes(scene_filepath, start_idx, nb_scenes_to_gen):
  # Read file containing input scenes
  with open(scene_filepath, 'r') as f:
    scene_data = ujson.load(f)
    scenes = scene_data['scenes']
    nb_scenes_loaded = len(scenes)
    scene_info = scene_data['info']

  if nb_scenes_to_gen > 0:
    end = start_idx + nb_scenes_to_gen
    end = end if end < nb_scenes_loaded else nb_scenes_loaded
    scenes = scenes[start_idx:end]
  else:
    scenes = scenes[start_idx:]

  print('Read %d scenes from disk' % len(scenes))

  return scenes, scene_info


def load_and_prepare_metadata(metadata_filepath, scenes):
  # Loading metadata
  with open(metadata_filepath, 'r') as f:
    metadata = ujson.load(f)

  # To initialize the metadata, we first need to know how many instruments each scene contains
  instrument_count_empty = {}
  instrument_indexes_empty = {}

  for instrument in metadata['attributes']['instrument']['values']:
    instrument_count_empty[instrument] = 0
    instrument_indexes_empty[instrument] = []

  instrument_count = dict(instrument_count_empty)

  max_scene_length = 0
  for scene in scenes:
    # Keep track of the maximum number of objects across all scenes
    scene_length = len(scene['objects'])
    if scene_length > max_scene_length:
      max_scene_length = scene_length

    # Keep track of the indexes for each instrument
    instrument_indexes = copy.deepcopy(instrument_indexes_empty)
    for i, obj in enumerate(scene['objects']):
      instrument_indexes[obj['instrument']].append(i)

    # TODO : Generalize this for all attributes
    # Insert the instrument indexes in the scene definition
    # (Will be used for relative positioning. Increased performance compared to doing the search everytime)
    scene['instrument_indexes'] = instrument_indexes

    # Retrieve the maximum number of occurence for each instruments
    for instrument, index_list in instrument_indexes.items():
      count = len(index_list)
      if count > instrument_count[instrument]:
        instrument_count[instrument] = count

    # Insert reference from relation label (Ex: before, after, ..) to index in scene['relationships']
    # Again for performance. Faster than searching in the dict every time
    scene['_relationships_indexes'] = {}
    for i, relation_data in enumerate(scene['relationships']):
      scene['_relationships_indexes'][relation_data['type']] = i

  # Instantiate the question engine attributes handlers
  qeng.instantiate_attributes_handlers(metadata, instrument_count, max_scene_length)

  return metadata


def load_synonyms(synonyms_filepath):
  # Read synonyms file
  with open(synonyms_filepath, 'r') as f:
    return ujson.load(f)


def create_reset_counts_fct(templates, metadata, max_scene_length):
  """
  Create a helper function that is used to reset the answer counts
  """
  def reset_counts():
    # Maps a template (filename, index) to the number of questions we have
    # so far using that template
    template_counts = {}
    # Maps a template (filename, index) to a dict mapping the answer to the
    # number of questions so far of that template type with that answer
    template_answer_counts = {}
    for key, template in templates.items():
      template_counts[key] = 0
      last_node = template['nodes'][-1]['type']
      output_type = qeng.functions[last_node]['output']

      if output_type == 'bool':
        answers = [True, False]
      elif output_type == 'integer':
        answers = list(range(0, max_scene_length + 1))      # FIXME : This won't hold if the scenes have different length
      else:
        answers = metadata['attributes'][output_type]['values']

      template_answer_counts[key] = {}
      for a in answers:
        template_answer_counts[key][a] = 0
    return template_counts, template_answer_counts

  return reset_counts


# FIXME : The probability should be loaded from config
def replace_optional_words(s):
  """
  Each substring of s that is surrounded in square brackets is treated as
  optional and is removed with probability 0.5. For example the string

  "A [aa] B [bb]"

  could become any of

  "A aa B bb"
  "A  B bb"
  "A aa B "
  "A  B "

  with probability 1/4.
  """
  pat = re.compile(r'\[([^\[]*)\]')

  while True:
    match = re.search(pat, s)
    if not match:
      break
    i0 = match.start()
    i1 = match.end()
    if random.random() > 0.5:
      s = s[:i0] + match.groups()[0] + s[i1:]
    else:
      s = s[:i0] + s[i1:]
  return s


# TODO : Adapt other_heuristic
def replace_other_word_if_needed(text, param_vals):
  """
  Post-processing heuristic to handle the word "other"
  """
  if ' other ' not in text and ' another ' not in text:
    return text
  target_keys = {
    '<Z>',  '<C>',  '<M>',  '<S>',        # FIXME : Hardcoded string placeholder
    '<Z2>', '<C2>', '<M2>', '<S2>',
  }
  if param_vals.keys() != target_keys:
    return text
  key_pairs = [
    ('<Z>', '<Z2>'),                      # FIXME : Hardcoded string placeholder
    ('<C>', '<C2>'),
    ('<M>', '<M2>'),
    ('<S>', '<S2>'),
  ]
  remove_other = False
  for k1, k2 in key_pairs:
    v1 = param_vals.get(k1, None)
    v2 = param_vals.get(k2, None)
    if v1 != '' and v2 != '' and v1 != v2:
      print('other has got to go! %s = %s but %s = %s'
            % (k1, v1, k2, v2))
      remove_other = True
      break
  if remove_other:
    if ' other ' in text:
      text = text.replace(' other ', ' ')
    if ' another ' in text:
      text = text.replace(' another ', ' a ')
  return text


def validate_constraints(template, state, outputs, param_name_to_attribute, verbose):
  """
  Validate that the current state comply with the template constraints
  """
  for constraint in template['constraints']:
    if constraint['type'] == 'NEQ':
      p1, p2 = constraint['params']
      v1, v2 = state['vals'].get(p1), state['vals'].get(p2)
      if v1 is not None and v2 is not None and v1 == v2:
        if verbose:
          print('skipping due to NEQ constraint')
          print(constraint)
          print(state['vals'])
        return False
    elif constraint['type'] == 'NULL':
      p = constraint['params'][0]
      p_type = param_name_to_attribute[p]
      v = state['vals'].get(p)
      if v is not None:
        skip = False
        if p_type == 'instrument' and v != 'thing': skip = True  # FIXME : Hardcoded stuff here
        if p_type != 'instrument' and v != '': skip = True
        if skip:
          if verbose:
            print('skipping due to NULL constraint')
            print(constraint)
            print(state['vals'])
          return False
    elif constraint['type'] == 'NOT_NULL':
      p = constraint['params'][0]
      p_type = param_name_to_attribute[p]
      v = state['vals'].get(p)
      if v is not None and (v == '' or v == 'thing'):
        skip = True  # FIXME : Ugly
        if skip:
          if verbose:
            print('skipping due to NOT NULL constraint')
            print(constraint)
            print(state['vals'])
          return False
    elif constraint['type'] == 'OUT_NEQ':
      i, j = constraint['params']
      i = state['input_map'].get(i, None)
      j = state['input_map'].get(j, None)
      if i is not None and j is not None and outputs[i] == outputs[j]:
        if verbose:
          print('skipping due to OUT_NEQ constraint')
        return False
    else:
      assert False, 'Unrecognized constraint type "%s"' % constraint['type']

  return True
