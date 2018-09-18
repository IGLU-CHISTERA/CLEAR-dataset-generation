#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
ROOTDIR="${DIR}/.."
OLDDIR=$PWD

experiment_name=$1
experiment_dir="${DIR}/${experiment_name}"
log_dir="${experiment_dir}/log"

# TODO : This script must be run in the virtual environment. Figure a way to make sure we are in the environment ?

if [ ! -d "${log_dir}" ]; then
  mkdir "${log_dir}"
fi

# Will stop the script on first error
set -e

cd $ROOTDIR

echo "-----------------------------------------------------------------------------------------------------------"
echo "[NOTE] This script should be run inside the virtual environment associated with Aqa-Dataset-Gen project"
echo "[NOTE] The output of each process can be found in the log folder of the experiment"
echo "[NOTE] Stopping this script will not stop the background process."
echo "[NOTE] Make sure all the process are stopped if CTRL+C on this script"
echo "-----------------------------------------------------------------------------------------------------------"

## Generate the scenes
echo "Generating scenes..."
python ./scene_generation/scene_generator.py @${experiment_dir}/scene_generator.args > "${log_dir}/scene_generation.log"
echo -e "Scene generation Done\n"

## Question Generation
echo 'Starting Training Question Generation...'
python ./question_generation/generate_questions.py @${experiment_dir}/train_question_generator.args > "${log_dir}/train_question_generation.log" &
TRAINING_QUESTION_GENERATION_PID=$!

echo 'Starting Validation Question Generation...'
python ./question_generation/generate_questions.py @${experiment_dir}/val_question_generator.args > "${log_dir}/val_question_generation.log" &
VAL_QUESTION_GENERATION_PID=$!

echo 'Starting Test Question Generation...'
python ./question_generation/generate_questions.py @${experiment_dir}/test_question_generator.args > "${log_dir}/test_question_generation.log" &
TEST_QUESTION_GENERATION_PID=$!

# Wait for process to finish
wait $TRAINING_QUESTION_GENERATION_PID $VAL_QUESTION_GENERATION_PID $TEST_QUESTION_GENERATION_PID

echo -e "Question generation done\n"

# Consolidate results
echo "Consolidating questions json..."
# Training questions
OUTPUT_FILEPATH=$( grep 'output_questions_file' ${experiment_dir}/train_question_generator.args | awk -F '=' '{print $2}')
python ./utils/consolidate_questions.py --remove_tmp --json_file_path ${OUTPUT_FILEPATH} > "${log_dir}/train_question_consolidation.log"

# Validation questions
OUTPUT_FILEPATH=$( grep 'output_questions_file' ${experiment_dir}/val_question_generator.args | awk -F '=' '{print $2}')
python ./utils/consolidate_questions.py --remove_tmp --json_file_path ${OUTPUT_FILEPATH} > "${log_dir}/val_question_consolidation.log"

# Test questions
OUTPUT_FILEPATH=$( grep 'output_questions_file' ${experiment_dir}/test_question_generator.args | awk -F '=' '{print $2}')
python ./utils/consolidate_questions.py --remove_tmp --json_file_path ${OUTPUT_FILEPATH} > "${log_dir}/test_question_consolidation.log"

echo -e "Question consolidation Done\n"

# Scene production
echo "Starting scene production..."
python ./scene_generation/produce_scenes.py @${experiment_dir}/train_scene_producer.args > "${log_dir}/train_scene_production.log" &
TRAIN_SCENE_PRODUCTION_PID=$!

python ./scene_generation/produce_scenes.py @${experiment_dir}/val_scene_producer.args > "${log_dir}/val_scene_production.log" &
VAL_SCENE_PRODUCTION_PID=$!

python ./scene_generation/produce_scenes.py @${experiment_dir}/test_scene_producer.args > "${log_dir}/test_scene_production.log" &
TEST_SCENE_PRODUCTION_PID=$!

echo -e "Scene production done\n"
