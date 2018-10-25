# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import json, os, math
from collections import defaultdict
import random

"""
Utilities for working with function program representations of questions.

Some of the metadata about what question node types are available etc are stored
in a JSON metadata file.
"""


# Handlers for answering questions. Each handler receives the scene structure
# that was output from Blender, the node, and a list of values that were output
# from each of the node's inputs; the handler should return the computed output
# value from this node.

use_last_position_value = False

def scene_handler(scene_struct, inputs, side_inputs):
  # Just return all objects in the scene
  return list(range(len(scene_struct['objects'])))


def make_filter_handler(attribute):
  is_position_attribute = attribute.startswith('position')
  def filter_handler(scene_struct, inputs, side_inputs):
    assert len(inputs) == 1
    assert len(side_inputs) == 1
    value = side_inputs[0]
    output = []
    for idx in inputs[0]:
      if is_position_attribute:
        atr = get_position(attribute, scene_struct, idx)
      else:
        atr = scene_struct['objects'][idx][attribute]
      if value == atr or (type(value) == list and value in atr):
        output.append(idx)
    return output
  return filter_handler


def unique_handler(scene_struct, inputs, side_inputs):
  assert len(inputs) == 1
  if len(inputs[0]) != 1:
    return '__INVALID__'
  return inputs[0][0]


def not_unique_handler(scene_struct, inputs, side_inputs):
  assert len(inputs) == 1
  if len(inputs[0]) == 1:
    return '__INVALID__'
  return inputs[0]


def relate_handler(scene_struct, inputs, side_inputs):
  assert len(inputs) == 1
  assert len(side_inputs) == 1
  relation = side_inputs[0]
  relation_index = scene_struct['_relationships_indexes'][relation]
  return scene_struct['relationships'][relation_index]['indexes'][inputs[0]]
    

def union_handler(scene_struct, inputs, side_inputs):
  assert len(inputs) == 2
  assert len(side_inputs) == 0
  return sorted(list(set(inputs[0]) | set(inputs[1])))


def intersect_handler(scene_struct, inputs, side_inputs):
  assert len(inputs) == 2
  assert len(side_inputs) == 0
  return sorted(list(set(inputs[0]) & set(inputs[1])))


def count_handler(scene_struct, inputs, side_inputs):
  assert len(inputs) == 1
  return len(inputs[0])


def add_handler(scene_struct, inputs, side_inputs):
  assert len(inputs) == 2
  assert len(side_inputs) == 0

  return inputs[0] + inputs[1]


def or_handler(scene_struct, inputs, side_inputs):
  assert len(inputs) == 2
  assert len(side_inputs) == 0

  return inputs[0] or inputs[1]


def make_same_attr_handler(attribute):
  def same_attr_handler(scene_struct, inputs, side_inputs):
    cache_key = '_same_%s' % attribute
    if cache_key not in scene_struct:
      cache = {}
      for i, obj1 in enumerate(scene_struct['objects']):
        same = []
        for j, obj2 in enumerate(scene_struct['objects']):
          if i != j and obj1[attribute] == obj2[attribute]:
            same.append(j)
        cache[i] = same
      scene_struct[cache_key] = cache

    cache = scene_struct[cache_key]
    assert len(inputs) == 1
    assert len(side_inputs) == 0
    return cache[inputs[0]]
  return same_attr_handler


def make_query_handler(attribute):
  def query_handler(scene_struct, inputs, side_inputs):
    assert len(inputs) == 1
    assert len(side_inputs) == 0
    idx = inputs[0]
    obj = scene_struct['objects'][idx]
    assert attribute in obj
    val = obj[attribute]
    if val is None or (type(val) == list and len(val) != 1):
      return '__INVALID__'
    elif type(val) == list and len(val) == 1:
      return val[0]
    else:
      return val
  return query_handler


def exist_handler(scene_struct, inputs, side_inputs):
  assert len(inputs) == 1
  assert len(side_inputs) == 0
  return len(inputs[0]) > 0


def equal_handler(scene_struct, inputs, side_inputs):
  assert len(inputs) == 2
  assert len(side_inputs) == 0
  return inputs[0] == inputs[1]


def less_than_handler(scene_struct, inputs, side_inputs):
  assert len(inputs) == 2
  assert len(side_inputs) == 0
  return inputs[0] < inputs[1]


def greater_than_handler(scene_struct, inputs, side_inputs):
  assert len(inputs) == 2
  assert len(side_inputs) == 0
  return inputs[0] > inputs[1]


def get_absolute_position(scene_struct, idx):
  if idx == len(scene_struct['objects']) - 1 and random.random() > 0.5 and use_last_position_value:   # FIXME : This probability should be parametrable
    return "last"
  else:
    return idx_to_position_str[idx]


def query_absolute_position_handler(scene_struct, inputs, side_inputs):
  assert len(inputs) == 1
  assert len(side_inputs) == 0
  idx = inputs[0]

  return get_absolute_position(scene_struct, idx)


# TODO : Generalize for all attributes
def get_position_instrument(scene_struct, idx, instrument):
  instrument_indexes = scene_struct['instrument_indexes'][instrument]
  relative_position_idx = instrument_indexes.index(idx)

  if relative_position_idx == len(instrument_indexes) - 1 and random.random() > 0.5 and use_last_position_value:  # FIXME : This probability should be parametrable
    return "last"
  # FIXME : Should we enable this ? IF ENABLED, We need to add the instrument alone in metadata values
  elif len(instrument_indexes) == 1 and random.random() > 0.5 and False:  # FIXME : This probability should be parametrable
    return ""   #FIXME : This will create 2 spaces when used to generate the sentence (precompute_filter_options)
  else:
    return idx_to_position_str[relative_position_idx]


# TODO : Generalize for all attributes
def query_position_instrument_handler(scene_struct, inputs, side_inputs):
  assert len(inputs) == 1
  assert len(side_inputs) == 0
  idx = inputs[0]
  instrument = scene_struct['objects'][idx]['instrument']

  return get_position_instrument(scene_struct, idx, instrument)


# FIXME : Could be changed to a one liner. Having an external array with [beginning, middle, end] would
# FIXME : facilitate the metadata enhancement (Right now it seems weird that answers for other position attributes
# FIXME : are not written in the metadata file but the one for position_global are
def get_position_global(scene_struct, idx):
  part_size = math.floor(len(scene_struct['objects']) / 3)
  if idx + 1 < part_size:
    return "beginning"
  elif idx + 1 <= 2 * part_size:
    return "middle"
  else:
    return "end"


def query_position_global_handler(scene_struct, inputs, side_inputs):
  assert len(inputs) == 1
  assert len(side_inputs) == 0
  idx = inputs[0]

  position = get_position_global(scene_struct, idx)

  return position + " of the scene"   # FIXME : Is this really interesting ?


def get_position(attribute_name, scene_struct, obj_idx):
  if attribute_name == 'position':
    return get_absolute_position(scene_struct, obj_idx)
  elif attribute_name == 'position_instrument':  # FIXME : will need to be updated when we generalize the relative attribute
    instrument = scene_struct['objects'][obj_idx]['instrument']
    return get_position_instrument(scene_struct, obj_idx, instrument)
  elif attribute_name == 'position_global':
    return get_position_global(scene_struct, obj_idx)


def filter_longest_duration_handler(scene_struct, inputs, side_inputs):
  assert len(inputs) == 1
  assert len(side_inputs) == 0
  if len(inputs[0]) == 0:
    return '__INVALID__'

  longest = {
    'duration': 0,
    'duration_count': {},
    'index': -1
  }
  for idx in inputs[0]:
    sound_duration = scene_struct['objects'][idx]['duration']

    # Keep track of the longest duration
    if scene_struct['objects'][idx]['duration'] > longest['duration']:
      longest['duration'] = sound_duration

      longest['index'] = idx

    # Keep track of the number of occurence of each duration
    if sound_duration not in longest['duration_count']:
      longest['duration_count'][sound_duration] = 1
    else:
      longest['duration_count'][sound_duration] += 1

  if longest['duration_count'][longest['duration']] > 1:
    # More than one object has the same duration
    return '__INVALID__'

  return longest['index']


def filter_shortest_duration_handler(scene_struct, inputs, side_inputs):
  assert len(inputs) == 1
  assert len(side_inputs) == 0
  if len(inputs[0]) == 0:
    return '__INVALID__'

  shortest = {
    'duration': 99999999,
    'duration_count': {},
    'index': -1
  }
  for idx in inputs[0]:
    sound_duration = scene_struct['objects'][idx]['duration']

    # Keep track of the shortest duration
    if scene_struct['objects'][idx]['duration'] < shortest['duration']:
      shortest['duration'] = sound_duration
      shortest['index'] = idx

    # Keep track of the number of occurence of each duration
    if sound_duration not in shortest['duration_count']:
        shortest['duration_count'][sound_duration] = 1
    else:
        shortest['duration_count'][sound_duration] += 1

  if shortest['duration_count'][shortest['duration']] > 1:
    # More than one object has the same duration
    return '__INVALID__'

  return shortest['index']


def make_count_different_handler(attribute):
  def count_different_handler(scene_struct, inputs, side_inputs):
    assert len(inputs) == 1
    assert len(side_inputs) == 0

    counter = set()

    for idx in inputs[0]:
      counter.add(scene_struct['objects'][idx][attribute])

    return len(counter)
  return count_different_handler


functions = {
  'scene': {
    'handler': scene_handler,
    'output': 'object_set'
  },
  'unique': {
    'handler': unique_handler,
    'output': 'object'
  },
  'not_unique': {
    'handler': not_unique_handler,
    'output': 'object'
  },
  'relate': {
    'handler': relate_handler,
    'output': 'object_set'
  },
  'union': {
    'handler': union_handler,
    'output': 'object_set'
  },
  'or': {
    'handler': or_handler,
    'output': "bool"
  },
  'intersect': {
    'handler': intersect_handler,
    'output': 'object_set'
  },
  'count': {
    'handler': count_handler,
    'output': 'integer'
  },
  'add': {
    'handler': add_handler,
    'output': 'integer'
  },
  'exist': {
    'handler': exist_handler,
    'output': 'bool'
  },
  'equal_integer': {
    'handler': equal_handler,
    'output': 'bool'
  },
  'equal_object': {
    'handler': equal_handler,
    'output': 'bool'
  },
  'less_than': {
    'handler': less_than_handler,
    'output': 'bool'
  },
  'greater_than': {
    'handler': greater_than_handler,
    'output': 'bool'
  },
  'filter_longest_duration': {
    'handler': filter_longest_duration_handler,
    'output': 'object'
  },
  'filter_shortest_duration': {
    'handler': filter_shortest_duration_handler,
    'output': 'object'
  },
  'query_position': {
    'handler': query_absolute_position_handler,
    'output': "position"
  },
  'query_position_instrument': {
    'handler': query_position_instrument_handler,
    'output': "position_instrument"
  },
  'query_position_global': {
    'handler': query_position_global_handler,
    'output': "position_global"
  },
  # The following functions can't be called directly.
  # They are intermediate functions that are expanded in a combination of other functions
  'filter': {
    'handler': None,
    'output': 'object_set'
  },
  'filter_exist': {
    'handler': None,
    'output': 'bool'
  },
  'filter_count': {
    'handler': None,
    'output': 'integer'
  },
  'filter_unique': {
    'handler': None,
    'output': 'object'
  },
  'filter_not_unique': {
    'handler': None,
    'output': 'object'
  },
  'relate_filter': {
    'handler': None,
    'output': 'object_set'
  },
  'relate_filter_unique': {
    'handler': None,
    'output': 'object'
  },
  'relate_filter_not_unique': {
    'handler': None,
    'output': 'object'
  },
  'relate_filter_count': {
    'handler': None,
    'output': 'integer'
  },
  'relate_filter_exist': {
    'handler': None,
    'output': 'bool'
  }
}

functions_to_be_expanded = [name for name, definition in functions.items() if definition['handler'] is None]

# FIXME : This won't work if the scene is longer than 11
idx_to_position_str = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth", "eleventh"]
def add_positions_to_metadata(metadata, instrument_count, max_scene_length):
  # Adding values for position absolute
  position_absolute_answers = []
  for i in range(max_scene_length):
    position_absolute_answers.append(idx_to_position_str[i] + ' sound')

  if use_last_position_value:
    position_absolute_answers.append('last sound')

  metadata['attributes']['position']['values'] = position_absolute_answers

  # Adding values for position_instrument           # FIXME : Generalize this
  position_instrument_answers = []
  for instrument, count in instrument_count.items():
    for i in range(count):
      position_instrument_answers.append(idx_to_position_str[i] + ' ' + instrument)

      if use_last_position_value:
        position_instrument_answers.append('last ' + instrument)

  metadata['attributes']['position_instrument']['values'] = position_instrument_answers


def instantiate_attributes_handlers(metadata, instrument_count, max_scene_length):
  add_positions_to_metadata(metadata, instrument_count, max_scene_length)

  for attribute_name in metadata['attributes'].keys():

    # Relations are defined separately
    if attribute_name.startswith('relate'):
      continue

    # Filter handler
    functions['filter_' + attribute_name] = {
      'handler': make_filter_handler(attribute_name),
      'output': 'object_set'
    }

    # Those positions handlers are defined separately (Or not needed)
    if not attribute_name.startswith('position'):
      # Equal handler
      functions['equal_' + attribute_name] = {
        'handler': equal_handler,
        'output': 'bool'
      }

      # Same handler
      functions['same_' + attribute_name] = {
        'handler': make_same_attr_handler(attribute_name),
        'output': 'object_set'
      }

      # Query handler
      functions['query_' + attribute_name] = {
        'handler': make_query_handler(attribute_name),
        'output': attribute_name
      }

      # Count different handler
      functions['count_different_' + attribute_name] = {
        'handler': make_count_different_handler(attribute_name),
        'output': 'integer'
      }


def get_filter_key(attr_keys, scene_struct, obj_idx):
  obj = scene_struct['objects'][obj_idx]
  position_keys = [k for k in attr_keys if k.startswith('position')]

  attr_to_keys = {}
  # Retrieve value for position keys
  for position_key in position_keys:
    attr_to_keys[position_key] = get_position(position_key, scene_struct, obj_idx)

  # Retrieve values for the other keys
  attr_keys_without_position = list(set(attr_keys) - set(position_keys))
  for attr_key in attr_keys_without_position:
    attr_to_keys[attr_key] = obj[attr_key]

  # Sort the filter_key according to the order of attr_keys
  keys = list(attr_to_keys.keys())
  values = list(attr_to_keys.values())

  filter_key = sorted(values, key=lambda x: attr_keys.index(keys[values.index(x)]))

  return tuple(filter_key)


def answer_question(question, metadata, scene_struct, all_outputs=False,
                    cache_outputs=True):
  """
  Use structured scene information to answer a structured question. Most of the
  heavy lifting is done by the execute handlers defined above.

  We cache node outputs in the node itself; this gives a nontrivial speedup
  when we want to answer many questions that share nodes on the same scene
  (such as during question-generation DFS). This will NOT work if the same
  nodes are executed on different scenes.
  """
  all_input_types, all_output_types = [], []
  node_outputs = []
  for node in question['nodes']:
    if cache_outputs and '_output' in node:
      node_output = node['_output']
    else:
      node_type = node['type']
      msg = 'Could not find handler for "%s"' % node_type
      assert node_type in functions, msg
      handler = functions[node_type]['handler']
      node_inputs = [node_outputs[idx] for idx in node['inputs']]
      side_inputs = node.get('side_inputs', [])
      node_output = handler(scene_struct, node_inputs, side_inputs)
      if cache_outputs:
        node['_output'] = node_output
    node_outputs.append(node_output)
    if node_output == '__INVALID__':
      break

  if all_outputs:
    return node_outputs
  else:
    return node_outputs[-1]


def insert_scene_node(nodes, idx):
  # First make a shallow-ish copy of the input
  new_nodes = []
  for node in nodes:
    new_node = {
      'type': node['type'],
      'inputs': node['inputs'],
    }
    if 'side_inputs' in node:
      new_node['side_inputs'] = node['side_inputs']
    new_nodes.append(new_node)

  # Replace the specified index with a scene node
  new_nodes[idx] = {'type': 'scene', 'inputs': []}

  # Search backwards from the last node to see which nodes are actually used
  output_used = [False] * len(new_nodes)
  idxs_to_check = [len(new_nodes) - 1]
  while idxs_to_check:
    cur_idx = idxs_to_check.pop()
    output_used[cur_idx] = True
    idxs_to_check.extend(new_nodes[cur_idx]['inputs'])

  # Iterate through nodes, keeping only those whose output is used;
  # at the same time build up a mapping from old idxs to new idxs
  old_idx_to_new_idx = {}
  new_nodes_trimmed = []
  for old_idx, node in enumerate(new_nodes):
    if output_used[old_idx]:
      new_idx = len(new_nodes_trimmed)
      new_nodes_trimmed.append(node)
      old_idx_to_new_idx[old_idx] = new_idx

  # Finally go through the list of trimmed nodes and change the inputs
  for node in new_nodes_trimmed:
    new_inputs = []
    for old_idx in node['inputs']:
      new_inputs.append(old_idx_to_new_idx[old_idx])
    node['inputs'] = new_inputs

  return new_nodes_trimmed


def is_degenerate(question, metadata, scene_struct, answer=None, verbose=False):
  """
  A question is degenerate if replacing any of its relate nodes with a scene
  node results in a question with the same answer.
  """
  if answer is None:
    answer = answer_question(question, metadata, scene_struct)

  for idx, node in enumerate(question['nodes']):
    if node['type'] == 'relate':
      new_question = {
        'nodes': insert_scene_node(question['nodes'], idx)
      }
      new_answer = answer_question(new_question, metadata, scene_struct)
      if verbose:
        print('here is truncated question:')
        for i, n in enumerate(new_question['nodes']):
          name = n['type']
          if 'side_inputs' in n:
            name = '%s[%s]' % (name, n['side_inputs'][0])
          print(i, name, n['_output'])
        print('new answer is: ', new_answer)

      if new_answer == answer:
        return True

  return False

