import os
import ujson
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


def load_all_tmp_json(folder_path):
  info_section = None
  questions = []
  for fn in os.listdir(folder_path):
    if not fn.endswith('.json'): continue
    with open(os.path.join(folder_path, fn), 'r') as f:
      try:
        file_content = ujson.load(f)
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
    ujson.dump(data, f, indent=2, sort_keys=True, escape_forward_slashes=False)


def main():
  args = parser.parse_args()
  question_folder_path = os.path.join(args.output_folder, args.output_version_nb, 'questions')
  tmp_folder_path = os.path.join(question_folder_path, args.tmp_folder_prefix + args.set_type)
  output_question_filename = "%s_%s_questions.json" % (args.output_filename_prefix, args.set_type)
  output_question_filepath = os.path.join(question_folder_path, output_question_filename)

  print("Consolidating json part file in folder '%s'" % tmp_folder_path)

  consolidated_data = load_all_tmp_json(tmp_folder_path)
  write_to_file(output_question_filepath, consolidated_data)

  if args.remove_tmp:
    shutil.rmtree(tmp_folder_path)

  print("Finished")


if __name__ == "__main__":
  main()

