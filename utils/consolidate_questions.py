import os
import ujson
import argparse
import shutil


parser = argparse.ArgumentParser(fromfile_prefix_chars='@')
parser.add_argument('--json_file_path', default='./output/questions/AQA_V0.1.1_train_questions.json',
    help="Name of the final output file")
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
        print("[ERROR] Could not load question file %s" % fn)    # FIXME : We should probably pause or do something to inform the user. This message will be flooded by the rest of the output. Maybe do a pause before generating ?

  questions = sorted(questions, key=lambda x: x['question_index'])

  return {
        'info': info_section,
        'questions': questions,
      }


def write_to_file(filepath, data):
  with open(filepath, 'w') as f:
    # FIXME : Remove indent parameter. Take more space. Only useful for readability while testing
    ujson.dump(data, f, indent=2, sort_keys=True, escape_forward_slashes=False)


def main():
  args = parser.parse_args()
  tmp_folder_path = args.json_file_path.replace(".json", "_TMP")

  print("Consolidating json part file in folder '%s'" % tmp_folder_path)

  consolidated_data = load_all_tmp_json(tmp_folder_path)
  write_to_file(args.json_file_path, consolidated_data)

  if args.remove_tmp:
    shutil.rmtree(tmp_folder_path)

  print("Finished")


if __name__ == "__main__":
  main()

