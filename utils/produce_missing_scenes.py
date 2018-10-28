import os
import re
import subprocess


def get_missing_scene_ids(generated_dataset_path, expected_nb_scenes):

  img_files = [f for f in os.listdir(generated_dataset_path) if os.path.isfile(os.path.join(generated_dataset_path, f)) and f.endswith('.png')]

  id_reg = re.compile('\w+_(\d\d\d\d\d\d).png')

  img_ids = set([int(re.findall(id_reg, filename)[0]) for filename in img_files])

  expected_ids = set(range(0,expected_nb_scenes))

  missing_ids = expected_ids - img_ids

  return missing_ids


def get_nb_scenes(scene_generator_args_path):
  with open(scene_generator_args_path, 'r') as f:
    full_content = f.read()

  scene_nb_reg = re.compile('--max_nb_scene=(\d+)\n')
  total_nb_scenes = int(re.findall(scene_nb_reg, full_content)[0])

  training_ratio_reg = re.compile('--training_set_ratio=(\d\.\d+)\n')
  training_ratio = float(re.findall(training_ratio_reg, full_content)[0])

  nb_training = round(total_nb_scenes * training_ratio)
  valid_and_test_ratio = (1.0 - training_ratio) / 2
  nb_valid = round(total_nb_scenes * valid_and_test_ratio)
  nb_test = total_nb_scenes - nb_training - nb_valid

  return nb_training, nb_valid, nb_test


def run_producer(args_filepath, experiment_name, missing_ids):
  command = "python ./scene_generation/produce_scenes.py @%s --output_version_nb %s --produce_specific_scenes %s"
  ids_str = [str(id) for id in missing_ids]
  command = command % (args_filepath, experiment_name, ','.join(ids_str))
  subprocess.run(command.split(' '))


def main():
  output_path = './output'
  experiments_path = './experiments'
  experiment_name = 'v1.1.0_1k_scenes_20_inst'

  experiment_output_path = os.path.join(output_path, experiment_name)
  experiment_path = os.path.join(experiments_path, experiment_name)

  scene_experiment_config = os.path.join(experiment_path, 'scene_generator.args')
  producer_experiment_config = os.path.join(experiment_path, '%s_scene_producer.args')

  train_producer_experiment_config = producer_experiment_config % 'train'
  val_producer_experiment_config = producer_experiment_config % 'val'
  test_producer_experiment_config = producer_experiment_config % 'test'

  img_output_path = os.path.join(experiment_output_path, 'images')

  train_img_output_path = os.path.join(img_output_path, 'train')
  val_img_output_path = os.path.join(img_output_path, 'val')
  test_img_output_path = os.path.join(img_output_path, 'test')

  nb_train, nb_valid, nb_test = get_nb_scenes(scene_experiment_config)

  train_id_missing = get_missing_scene_ids(train_img_output_path, nb_train)
  val_id_missing = get_missing_scene_ids(val_img_output_path, nb_valid)
  test_id_missing = get_missing_scene_ids(test_img_output_path, nb_test)

  print("Found %d files missing" % (len(train_id_missing) + len(val_id_missing) + len(test_id_missing)))

  if len(train_id_missing) > 0:
    run_producer(train_producer_experiment_config, experiment_name, train_id_missing)

  if len(val_id_missing) > 0:
    run_producer(val_producer_experiment_config, experiment_name, val_id_missing)

  if len(test_id_missing) > 0:
    run_producer(test_producer_experiment_config, experiment_name, test_id_missing)

  print("Done")


if __name__ == "__main__":
  main()