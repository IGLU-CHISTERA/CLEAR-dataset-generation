#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
OLDDIR=$PWD
CURRENT_DATE_TIME=$(date +'%d-%m-%Y_%Hh%M')

# Init timer
SECONDS=0

EXPERIMENT_NAME=$1
if [[ "${EXPERIMENT_NAME: -1}" = "/" ]]; then
    EXPERIMENT_NAME="${EXPERIMENT_NAME:: -1}"
fi
EXPERIMENT_DIR="${DIR}/arguments/${EXPERIMENT_NAME}"

# TODO : Supply another way to provide the output path
# Output dir must be specified in scene_generator.args (May be omitted from other args file, we will use the extracted one)
REL_OUTPUT_DIR=$(grep output_folder ${EXPERIMENT_DIR}/scene_generator.args | awk -F '=' '{print $2}')
OUTPUT_DIR="${DIR}/${REL_OUTPUT_DIR}"
EXPERIMENT_OUTPUT_DIR="${OUTPUT_DIR}/${EXPERIMENT_NAME}"
ARGUMENTS_COPY_DIR="${EXPERIMENT_OUTPUT_DIR}/arguments"
LOG_DIR="${EXPERIMENT_OUTPUT_DIR}/logs"

# Creating all necessary folders
if [[ ! -d "${OUTPUT_DIR}" ]]; then
  echo "Output directory '${OUTPUT_DIR}' did not exist. Creating output directory."
  mkdir "${OUTPUT_DIR}"
fi

if [[ ! -d "${EXPERIMENT_OUTPUT_DIR}" ]]; then
  mkdir "${EXPERIMENT_OUTPUT_DIR}"
fi

if [[ ! -d "${ARGUMENTS_COPY_DIR}" ]]; then
  mkdir "${ARGUMENTS_COPY_DIR}"
fi

if [[ ! -d "${LOG_DIR}" ]]; then
  mkdir "${LOG_DIR}"
fi

# Will stop the script on first error
set -e

echo "-----------------------------------------------------------------------------------------------------------"
echo "    CLEAR Dataset Generation  --- Version : ${EXPERIMENT_NAME}  ---  `date +"%d/%m/%Y %H:%M"`"
echo "-----------------------------------------------------------------------------------------------------------"
echo "[NOTE] This script should be run inside the virtual environment associated with CLEAR-Dataset-Geneneration project"
echo "[NOTE] The output of each process can be found in the log folder"
echo "[NOTE] Stopping this script will not stop the background process."
echo "[NOTE] Make sure all the process are stopped if CTRL+C on this script"
echo "-----------------------------------------------------------------------------------------------------------"

## Generate the scenes
echo ">> Generating scenes..."
python generate_scenes_definition.py @${EXPERIMENT_DIR}/scene_generator.args --output_version_nb ${EXPERIMENT_NAME} > "${LOG_DIR}/${CURRENT_DATE_TIME}_scene_generation.log"
echo -e ">> Scene generation Done\n"

# Scene production
echo ">> Starting scene production..."
python produce_scenes_audio.py @${EXPERIMENT_DIR}/train_scene_producer.args --output_version_nb ${EXPERIMENT_NAME} > "${LOG_DIR}/${CURRENT_DATE_TIME}_train_scene_production.log" &
TRAIN_SCENE_PRODUCTION_PID=$!

# Sleep to let the first script create the folders and avoid race condition
sleep 1

python produce_scenes_audio.py @${EXPERIMENT_DIR}/val_scene_producer.args --output_version_nb ${EXPERIMENT_NAME} > "${LOG_DIR}/${CURRENT_DATE_TIME}_val_scene_production.log" &
VAL_SCENE_PRODUCTION_PID=$!

python produce_scenes_audio.py @${EXPERIMENT_DIR}/test_scene_producer.args --output_version_nb ${EXPERIMENT_NAME} > "${LOG_DIR}/${CURRENT_DATE_TIME}_test_scene_production.log" &
TEST_SCENE_PRODUCTION_PID=$!

## Question Generation
echo '>>> Starting Question Generation...'
python generate_questions.py @${EXPERIMENT_DIR}/train_question_generator.args --output_version_nb ${EXPERIMENT_NAME} > "${LOG_DIR}/${CURRENT_DATE_TIME}_train_question_generation.log" &
TRAINING_QUESTION_GENERATION_PID=$!
# Sleep to let the first script create the folders and avoid race condition
sleep 1

python generate_questions.py @${EXPERIMENT_DIR}/val_question_generator.args --output_version_nb ${EXPERIMENT_NAME} > "${LOG_DIR}/${CURRENT_DATE_TIME}_val_question_generation.log" &
VAL_QUESTION_GENERATION_PID=$!

python generate_questions.py @${EXPERIMENT_DIR}/test_question_generator.args --output_version_nb ${EXPERIMENT_NAME} > "${LOG_DIR}/${CURRENT_DATE_TIME}_test_question_generation.log" &
TEST_QUESTION_GENERATION_PID=$!

# Wait for process to finish
wait ${TRAINING_QUESTION_GENERATION_PID} ${VAL_QUESTION_GENERATION_PID} ${TEST_QUESTION_GENERATION_PID}

echo -e ">>> Question generation done\n"

# Consolidate results
echo ">>> Consolidating questions json..."
# Training questions
python ./scripts/consolidate_questions.py --set_type train --output_folder ${OUTPUT_DIR} --output_version_nb ${EXPERIMENT_NAME} --tmp_folder_prefix TMP_ --remove_tmp > "${LOG_DIR}/${CURRENT_DATE_TIME}_train_question_consolidation.log"

# Validation questions
python ./scripts/consolidate_questions.py --set_type val  --output_folder ${OUTPUT_DIR} --output_version_nb ${EXPERIMENT_NAME} --tmp_folder_prefix TMP_ --remove_tmp > "${LOG_DIR}/${CURRENT_DATE_TIME}_val_question_consolidation.log"

# Test questions
python ./scripts/consolidate_questions.py --set_type test --output_folder ${OUTPUT_DIR} --output_version_nb ${EXPERIMENT_NAME} --tmp_folder_prefix TMP_ --remove_tmp > "${LOG_DIR}/${CURRENT_DATE_TIME}_test_question_consolidation.log"

echo -e ">>> Question consolidation Done\n"

echo ">>> Copying generation arguments to output folder..."

if [[ -d "${ARGUMENTS_COPY_DIR}" ]]; then
  rm -rf "${ARGUMENTS_COPY_DIR}"
fi

mkdir ${ARGUMENTS_COPY_DIR}

cp ${EXPERIMENT_DIR}/*.args ${ARGUMENTS_COPY_DIR}

echo -e ">>> Arguments copy Done\n"

echo -e ">> Waiting for scene production..\n"
wait ${TRAIN_SCENE_PRODUCTION_PID} ${VAL_SCENE_PRODUCTION_PID} ${TEST_SCENE_PRODUCTION_PID}

echo -e ">> Scene production done\n"

DURATION=$SECONDS
HOURS=$((${DURATION} / 3600))
SECONDS_REMAINDER=$((${DURATION} % 3600))
MINUTES=$((SECONDS_REMAINDER / 60))
echo "Full generation : ${HOURS} hours ${MINUTES} min" > "${LOG_DIR}/${CURRENT_DATE_TIME}_duration.timing"
