import re, math, random, os
import ujson

# Constants
_placeholders_to_attribute_reg = re.compile('<([a-zA-Z]+)(\d)?>')


def question_node_shallow_copy(node):
  new_node = {
    'type': node['type'],
    'inputs': node['inputs'],
  }
  if 'side_inputs' in node:
    new_node['side_inputs'] = node['side_inputs']
  return new_node


def placeholders_to_attribute(template_text, metadata):
  correspondences = {}
  # Extracting the placeholders from the text
  matches = re.findall(_placeholders_to_attribute_reg, template_text)

  # FIXME : By iterating over each types, we also iterate over relation. Do we want this ?
  # FIXME : No need to do this every time. This list is read from the metadata and doesn't change
  attribute_correspondences = {metadata['attributes'][t]['placeholder']: t for t in metadata['attributes']}

  for placeholder in matches:
    correspondences['<%s%s>' % (placeholder[0], placeholder[1])] = attribute_correspondences['<%s>' % placeholder[0]]

  return correspondences


def translate_can_be_null_attributes(can_be_null_attributes, param_name_to_attribute):
  '''
  Translate placeholder strings to attribute names and remove duplicate
  '''
  tmp = set()
  for can_be_null_attribute in can_be_null_attributes:
    tmp.add(param_name_to_attribute[can_be_null_attribute])

  return list(tmp)


def write_questions_part_to_file(tmp_folder_path, filename, info_section, questions, index):
  question_program_cleanup(questions)

  tmp_filename = filename.replace(".json", "_%.5d.json" % index)
  tmp_filepath = os.path.join(tmp_folder_path, tmp_filename)

  print("Writing to file %s" % tmp_filepath)

  with open(tmp_filepath, 'w') as f:
    # FIXME : Remove indent parameter. Take more space. Only useful for readability while testing
    ujson.dump({
        'info': info_section,
        'questions': questions,
      }, f, indent=2, sort_keys=True, escape_forward_slashes=False)


# FIXME : The probability should be loaded from config
def replace_optionals(s):
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


def question_program_cleanup(questions):
  # Change "side_inputs" to "value_inputs" in all functions of all functional         # FIXME : Fix this at the same time
  # programs. My original name for these was "side_inputs" but I decided to
  # change the name to "value_inputs" for the public CLEVR release. I should
  # probably go through all question generation code and templates and rename,
  # but that could be tricky and take a while, so instead I'll just do it here.
  # To further complicate things, originally functions without value inputs did
  # not have a "side_inputs" field at all, and I'm pretty sure this fact is used
  # in some of the code above; however in the public CLEVR release all functions
  # have a "value_inputs" field, and it's an empty list for functions that take
  # no value inputs. Again this should probably be refactored, but the quick and
  # dirty solution is to keep the code above as-is, but here make "value_inputs"
  # an empty list for those functions that do not have "side_inputs". Gross.
  for q in questions:
    for f in q['program']:
      if 'side_inputs' in f:
        f['value_inputs'] = f['side_inputs']
        del f['side_inputs']
      else:
        f['value_inputs'] = []

  for q in questions:
    del q['program']  # FIXME : Remove this. We don't include program to improve readability while testing
