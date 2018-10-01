#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
ROOTDIR="${DIR}/.."
OLDDIR=$PWD

EXPERIMENT_NAME=$1
if [ "${EXPERIMENT_NAME: -1}" = "/" ]; then
    EXPERIMENT_NAME="${EXPERIMENT_NAME:: -1}"
fi
EXPERIMENT_DIR="${DIR}/${EXPERIMENT_NAME}"
LOG_DIR="${EXPERIMENT_DIR}/log"

OUTPUT_DIR=$(grep output_folder ${EXPERIMENT_DIR}/scene_generator.args | awk -F '=' '{print $2}')

# TODO : This script must be run in the virtual environment. Figure a way to make sure we are in the environment ?

if [ ! -d "${LOG_DIR}" ]; then
  mkdir "${LOG_DIR}"
fi

# Will stop the script on first error
set -e

cd ${ROOTDIR}
echo "-----------------------------------------------------------------------------------------------------------"
echo "    AQA Dataset Generation"
echo "-----------------------------------------------------------------------------------------------------------"
echo "[NOTE] This script should be run inside the virtual environment associated with Aqa-Dataset-Gen project"
echo "[NOTE] The output of each process can be found in the log folder of the experiment"
echo "[NOTE] Stopping this script will not stop the background process."
echo "[NOTE] Make sure all the process are stopped if CTRL+C on this script"
echo "-----------------------------------------------------------------------------------------------------------"

## Generate the scenes
echo "Generating scenes..."
python ./scene_generation/scene_generator.py @${EXPERIMENT_DIR}/scene_generator.args --output_version_nb ${EXPERIMENT_NAME} > "${LOG_DIR}/scene_generation.log"
echo -e "Scene generation Done\n"

## Question Generation
echo 'Starting Training Question Generation...'
python ./question_generation/generate_questions.py @${EXPERIMENT_DIR}/train_question_generator.args --output_version_nb ${EXPERIMENT_NAME} > "${LOG_DIR}/train_question_generation.log" &
TRAINING_QUESTION_GENERATION_PID=$!

echo 'Starting Validation Question Generation...'
python ./question_generation/generate_questions.py @${EXPERIMENT_DIR}/val_question_generator.args --output_version_nb ${EXPERIMENT_NAME} > "${LOG_DIR}/val_question_generation.log" &
VAL_QUESTION_GENERATION_PID=$!

echo 'Starting Test Question Generation...'
python ./question_generation/generate_questions.py @${EXPERIMENT_DIR}/test_question_generator.args --output_version_nb ${EXPERIMENT_NAME} > "${LOG_DIR}/test_question_generation.log" &
TEST_QUESTION_GENERATION_PID=$!

# Wait for process to finish
wait $TRAINING_QUESTION_GENERATION_PID $VAL_QUESTION_GENERATION_PID $TEST_QUESTION_GENERATION_PID

echo -e "Question generation done\n"

# Consolidate results
echo "Consolidating questions json..."
# Training questions
python ./utils/consolidate_questions.py --set_type train --output_folder ${OUTPUT_DIR} --output_version_nb ${EXPERIMENT_NAME} --remove_tmp > "${LOG_DIR}/train_question_consolidation.log"

# Validation questions
python ./utils/consolidate_questions.py --set_type val  --output_folder ${OUTPUT_DIR} --output_version_nb ${EXPERIMENT_NAME} --remove_tmp > "${LOG_DIR}/val_question_consolidation.log"

# Test questions
python ./utils/consolidate_questions.py --set_type test --output_folder ${OUTPUT_DIR} --output_version_nb ${EXPERIMENT_NAME} --remove_tmp > "${LOG_DIR}/test_question_consolidation.log"

echo -e "Question consolidation Done\n"

# Scene production
echo "Starting scene production..."
python ./scene_generation/produce_scenes.py @${EXPERIMENT_DIR}/train_scene_producer.args --output_version_nb ${EXPERIMENT_NAME} > "${LOG_DIR}/train_scene_production.log" &
TRAIN_SCENE_PRODUCTION_PID=$!

python ./scene_generation/produce_scenes.py @${EXPERIMENT_DIR}/val_scene_producer.args --output_version_nb ${EXPERIMENT_NAME} > "${LOG_DIR}/val_scene_production.log" &
VAL_SCENE_PRODUCTION_PID=$!

python ./scene_generation/produce_scenes.py @${EXPERIMENT_DIR}/test_scene_producer.args --output_version_nb ${EXPERIMENT_NAME} > "${LOG_DIR}/test_scene_production.log" &
TEST_SCENE_PRODUCTION_PID=$!

wait $TRAIN_SCENE_PRODUCTION_PID $VAL_SCENE_PRODUCTION_PID $TEST_SCENE_PRODUCTION_PID

echo -e "Scene production done\n"
