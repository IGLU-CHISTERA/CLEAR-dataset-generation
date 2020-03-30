# CLEAR Dataset
# >> Questions file consolidator
#
# Author :      Jerome Abdelnour
# Year :        2018-2019
# Affiliations: Universite de Sherbrooke - Electrical and Computer Engineering faculty
#               KTH Stockholm Royal Institute of Technology
#               IGLU - CHIST-ERA

"""
This script will merge temporary questions files (questions are written to multiple file to reduce memory usage)
into a single file.
"""


import os
import json
import argparse
import shutil


parser = argparse.ArgumentParser(fromfile_prefix_chars='@')
parser.add_argument('--output_folder', default='./output',
    help="Folder containing the generated question files")
parser.add_argument('--output_version_nb', default='0.0.1',
    help="Identifier of the dataset version.")
parser.add_argument('--tmp_folder_prefix', default='TMP_',
    help="Prefix for the temporary output folder")
parser.add_argument('--set_type', default='train', type=str,
    help="Specify the set type (train/val/test)")
parser.add_argument('--output_filename_prefix', default='CLEAR',
    help="Prefix for the output file")
parser.add_argument('--remove_tmp', action="store_true",
    help="Will delete the tmp folder after consolidation")


# Old approach (Load everything in memory)
def load_all_tmp_json(folder_path):
  info_section = None
  questions = []
  for fn in os.listdir(folder_path):
    if not fn.endswith('.json'): continue
    with open(os.path.join(folder_path, fn), 'r') as f:
      try:
        file_content = json.load(f)
        questions += file_content['questions']

        if info_section is None:
          info_section = file_content['info']
      except ValueError:
        print("[ERROR] Could not load question file %s" % fn)

  questions = sorted(questions, key=lambda x: x['question_index'])

  return {
        'info': info_section,
        'questions': questions,
      }


def write_to_file(filepath, data):
  with open(filepath, 'w') as f:
    json.dump(data, f, indent=2, sort_keys=True, escape_forward_slashes=False)


# New approach, stream writing to file
def stream_write(output_filepath, tmp_folder_path, indent=2):
    with open(output_filepath, 'wb+') as f:

        info_section = None

        file_ext = '.json'
        filenames = [fn for fn in os.listdir(tmp_folder_path) if fn.endswith(file_ext)]
        # Sort files according to index (Ex : CLEAR_train_XXXX.json where XXXX is the index)
        filenames = sorted(filenames, key=lambda fn: int(fn[fn.rfind('_')+1:-len(file_ext)]))

        for fn in filenames:
            with open(os.path.join(tmp_folder_path, fn), 'rb') as tmp_f:
                try:
                    file_content = json.load(tmp_f)

                    if info_section is None:
                        info_section = file_content['info']

                        # Beginning of file
                        f.write(bytes('{\n', encoding='utf8'))
                        f.write(bytes(f'{" "*indent}"info": {to_json_string(info_section, indent=indent, indent_level=1)},\n', encoding='utf8'))
                        f.write(bytes(f'{" "*indent}"questions": [\n', encoding='utf8'))

                    for question in file_content['questions']:
                        f.write(bytes(to_json_string(question, indent=indent, indent_level=2), encoding='utf8'))
                        f.write(bytes(',\n', encoding='utf8'))
                        
                except ValueError:
                    print("[ERROR] Could not load question file %s" % fn)

        # Remove last ','
        f.seek(-2, 2)
        f.truncate()
        f.write(bytes("\n", encoding='utf8'))

        # Close array & object
        f.write(bytes(f'{" " * indent}]\n', encoding='utf8'))
        f.write(bytes('}\n', encoding='utf8'))


def to_json_string(dict_obj, indent=2, indent_level=0):
    json_string = json.dumps(dict_obj, indent=indent, escape_forward_slashes=False)

    if indent_level > 0:
        json_string_lines = json_string.split('\n')
        new_lines = []

        for line in json_string_lines:
            new_line = line
            for i in range(indent_level):
                new_line = " " * indent + new_line

            new_lines.append(new_line)

        json_string = '\n'.join(new_lines)

    return json_string

def main():
  args = parser.parse_args()
  question_folder_path = os.path.join(args.output_folder, args.output_version_nb, 'questions')
  tmp_folder_path = os.path.join(question_folder_path, args.tmp_folder_prefix + args.set_type)
  output_question_filename = "%s_%s_questions.json" % (args.output_filename_prefix, args.set_type)
  output_question_filepath = os.path.join(question_folder_path, output_question_filename)

  if os.path.exists(tmp_folder_path):

      stream_write(output_question_filepath, tmp_folder_path)

      #consolidated_data = load_all_tmp_json(tmp_folder_path)
      #write_to_file(output_question_filepath, consolidated_data)

      if args.remove_tmp:
        shutil.rmtree(tmp_folder_path)

      print("Consolidated json part file in folder '%s'" % tmp_folder_path)


if __name__ == "__main__":
  main()

