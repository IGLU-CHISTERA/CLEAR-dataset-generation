#!/usr/bin/env bash
# Will stop the script on first error
set -e

# Parameters : 
## scene_max_lengths: [50000]
## question_insts_per_scene: [4]
## spectrogram_window_lengths: [1024]
## spectrogram_window_overlap: [0.5]
## Base scene arguments : arguments/base_scene_generation.args
## Base question arguments : arguments/base_question_generation.args
## Base spectrogram arguments : arguments/base_audio_generation.args


# Scene Preparation
mkdir -p output/CLEAR_50k
mkdir -p output/CLEAR_50k/log


# Scene Generation
if [[ ! -e output/CLEAR_50k/scenes ]]; then
if [[ -e output/CLEAR_50k.tar.gz ]]; then
echo "Untaring 'CLEAR_50k.tar.gz'"
pigz -dc output/CLEAR_50k.tar.gz | tar xf - -C output
else
set -x
python generate_scenes_definition.py @arguments/base_scene_generation.args --output_folder output --nb_scene 50000 --output_version_nb CLEAR_50k > output/CLEAR_50k/log/scene_generation.log &
{ set +x; } 2>/dev/null
fi
sleep 0.5
fi
PROCESS_0_PID=$!

wait ${PROCESS_0_PID}

# Question Preparation
mkdir -p output/CLEAR_50k_4_inst
mkdir -p output/CLEAR_50k_4_inst/log
ln -sf ../CLEAR_50k/attributes.json output/CLEAR_50k_4_inst/attributes.json
[[ -e output/CLEAR_50k/scenes ]] && ln -snf ../CLEAR_50k/scenes output/CLEAR_50k_4_inst/scenes


# Question Generation
if [[ ! -e output/CLEAR_50k_4_inst/questions/CLEAR_val_questions.json && ! -e output/CLEAR_50k_4_inst/questions/TMP_val ]]; then
if [[ -e output/CLEAR_50k_4_inst.tar.gz ]]; then
echo "Untaring 'CLEAR_50k_4_inst.tar.gz'"
pigz -dc output/CLEAR_50k_4_inst.tar.gz | tar xf - -C output
else
set -x
python generate_questions.py @arguments/base_question_generation.args --output_folder output --templates_per_scene 4 --output_version_nb CLEAR_50k_4_inst --set_type val > output/CLEAR_50k_4_inst/log/question_generation_val.log &
{ set +x; } 2>/dev/null
fi
sleep 0.5
fi
PROCESS_0_PID=$!

if [[ ! -e output/CLEAR_50k_4_inst/questions/CLEAR_test_questions.json && ! -e output/CLEAR_50k_4_inst/questions/TMP_test ]]; then
if [[ -e output/CLEAR_50k_4_inst.tar.gz ]]; then
echo "Untaring 'CLEAR_50k_4_inst.tar.gz'"
pigz -dc output/CLEAR_50k_4_inst.tar.gz | tar xf - -C output
else
set -x
python generate_questions.py @arguments/base_question_generation.args --output_folder output --templates_per_scene 4 --output_version_nb CLEAR_50k_4_inst --set_type test > output/CLEAR_50k_4_inst/log/question_generation_test.log &
{ set +x; } 2>/dev/null
fi
sleep 0.5
fi
PROCESS_1_PID=$!

if [[ ! -e output/CLEAR_50k_4_inst/questions/CLEAR_train_questions.json && ! -e output/CLEAR_50k_4_inst/questions/TMP_train ]]; then
if [[ -e output/CLEAR_50k_4_inst.tar.gz ]]; then
echo "Untaring 'CLEAR_50k_4_inst.tar.gz'"
pigz -dc output/CLEAR_50k_4_inst.tar.gz | tar xf - -C output
else
set -x
python generate_questions.py @arguments/base_question_generation.args --output_folder output --templates_per_scene 4 --output_version_nb CLEAR_50k_4_inst --set_type train > output/CLEAR_50k_4_inst/log/question_generation_train.log &
{ set +x; } 2>/dev/null
fi
sleep 0.5
fi
PROCESS_2_PID=$!

wait ${PROCESS_0_PID} ${PROCESS_1_PID} ${PROCESS_2_PID}

# Question Consolidation
if [[ ! -e output/CLEAR_50k_4_inst/questions/CLEAR_train_questions.json ]]; then
if [[ -e output/CLEAR_50k_4_inst.tar.gz ]]; then
echo "Untaring 'CLEAR_50k_4_inst.tar.gz'"
pigz -dc output/CLEAR_50k_4_inst.tar.gz | tar xf - -C output
else
set -x
python ./scripts/consolidate_questions.py --output_folder output --tmp_folder_prefix TMP_ --remove_tmp --output_version_nb CLEAR_50k_4_inst --set_type train &
{ set +x; } 2>/dev/null
fi
sleep 0.5
fi
PROCESS_0_PID=$!

if [[ ! -e output/CLEAR_50k_4_inst/questions/CLEAR_val_questions.json ]]; then
if [[ -e output/CLEAR_50k_4_inst.tar.gz ]]; then
echo "Untaring 'CLEAR_50k_4_inst.tar.gz'"
pigz -dc output/CLEAR_50k_4_inst.tar.gz | tar xf - -C output
else
set -x
python ./scripts/consolidate_questions.py --output_folder output --tmp_folder_prefix TMP_ --remove_tmp --output_version_nb CLEAR_50k_4_inst --set_type val &
{ set +x; } 2>/dev/null
fi
sleep 0.5
fi
PROCESS_1_PID=$!

if [[ ! -e output/CLEAR_50k_4_inst/questions/CLEAR_test_questions.json ]]; then
if [[ -e output/CLEAR_50k_4_inst.tar.gz ]]; then
echo "Untaring 'CLEAR_50k_4_inst.tar.gz'"
pigz -dc output/CLEAR_50k_4_inst.tar.gz | tar xf - -C output
else
set -x
python ./scripts/consolidate_questions.py --output_folder output --tmp_folder_prefix TMP_ --remove_tmp --output_version_nb CLEAR_50k_4_inst --set_type test &
{ set +x; } 2>/dev/null
fi
sleep 0.5
fi
PROCESS_2_PID=$!

wait ${PROCESS_0_PID} ${PROCESS_1_PID} ${PROCESS_2_PID}

# Spectrogram FFT Preparation
mkdir -p output/CLEAR_50k_1024_win_50_overlap
mkdir -p output/CLEAR_50k_1024_win_50_overlap/preprocessed
mkdir -p output/CLEAR_50k_1024_win_50_overlap/log
ln -sf ../CLEAR_50k/attributes.json output/CLEAR_50k_1024_win_50_overlap/attributes.json
[[ -e output/CLEAR_50k/scenes ]] && ln -snf ../CLEAR_50k/scenes output/CLEAR_50k_1024_win_50_overlap/scenes


# Spectrogram Generation
if [[ ! -e output/CLEAR_50k_1024_win_50_overlap/images/val ]]; then
if [[ -e output/CLEAR_50k_1024_win_50_overlap.tar.gz ]]; then
echo "Untaring 'CLEAR_50k_1024_win_50_overlap.tar.gz'"
pigz -dc output/CLEAR_50k_1024_win_50_overlap.tar.gz | tar xf - -C output
else
set -x
python produce_scenes_audio.py @arguments/base_audio_generation.args --output_folder output --output_version_nb CLEAR_50k_1024_win_50_overlap --spectrogram_window_length 1024 --spectrogram_window_overlap 512 --set_type val --nb_process 2 > output/CLEAR_50k_1024_win_50_overlap/log/spectrogram_fft_val.log &
{ set +x; } 2>/dev/null
fi
sleep 0.5
fi
PROCESS_0_PID=$!

if [[ ! -e output/CLEAR_50k_1024_win_50_overlap/images/test ]]; then
if [[ -e output/CLEAR_50k_1024_win_50_overlap.tar.gz ]]; then
echo "Untaring 'CLEAR_50k_1024_win_50_overlap.tar.gz'"
pigz -dc output/CLEAR_50k_1024_win_50_overlap.tar.gz | tar xf - -C output
else
set -x
python produce_scenes_audio.py @arguments/base_audio_generation.args --output_folder output --output_version_nb CLEAR_50k_1024_win_50_overlap --spectrogram_window_length 1024 --spectrogram_window_overlap 512 --set_type test --nb_process 2 > output/CLEAR_50k_1024_win_50_overlap/log/spectrogram_fft_test.log &
{ set +x; } 2>/dev/null
fi
sleep 0.5
fi
PROCESS_2_PID=$!

wait ${PROCESS_0_PID} ${PROCESS_2_PID}

if [[ ! -e output/CLEAR_50k_1024_win_50_overlap/images/train ]]; then
if [[ -e output/CLEAR_50k_1024_win_50_overlap.tar.gz ]]; then
echo "Untaring 'CLEAR_50k_1024_win_50_overlap.tar.gz'"
pigz -dc output/CLEAR_50k_1024_win_50_overlap.tar.gz | tar xf - -C output
else
set -x
python produce_scenes_audio.py @arguments/base_audio_generation.args --output_folder output --output_version_nb CLEAR_50k_1024_win_50_overlap --spectrogram_window_length 1024 --spectrogram_window_overlap 512 --set_type train --nb_process 4 > output/CLEAR_50k_1024_win_50_overlap/log/spectrogram_fft_train.log &
{ set +x; } 2>/dev/null
fi
sleep 0.5
fi
PROCESS_0_PID=$!

wait ${PROCESS_0_PID}


# Linking versions together
mkdir -p output/CLEAR_50k_4_inst_1024_win_50_overlap
ln -sf ../CLEAR_50k/attributes.json output/CLEAR_50k_4_inst_1024_win_50_overlap/attributes.json
ln -snf ../CLEAR_50k/scenes output/CLEAR_50k_4_inst_1024_win_50_overlap/scenes
ln -snf ../CLEAR_50k_4_inst/questions output/CLEAR_50k_4_inst_1024_win_50_overlap/questions
[[ -e output/CLEAR_50k_1024_win_50_overlap/images ]] && ln -snf ../CLEAR_50k_1024_win_50_overlap/images output/CLEAR_50k_4_inst_1024_win_50_overlap/images
[[ -e output/CLEAR_50k_1024_win_50_overlap/audio ]] && ln -snf ../CLEAR_50k_1024_win_50_overlap/audio output/CLEAR_50k_4_inst_1024_win_50_overlap/audio
[[ -e output/CLEAR_50k_1024_win_50_overlap/preprocessed ]] && ln -snf ../CLEAR_50k_1024_win_50_overlap/preprocessed output/CLEAR_50k_4_inst_1024_win_50_overlap/preprocessed

echo "All Done !"
