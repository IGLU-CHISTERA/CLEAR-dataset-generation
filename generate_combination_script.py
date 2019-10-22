import argparse
import os
import re
import json

parser = argparse.ArgumentParser()

# TODO : Add background noise & reverb parameters
# TODO : Add help string
parser.add_argument('--scene_max_lengths', default='1000,5000,10000,20000,40000', type=str)
parser.add_argument('--question_insts_per_scene', default='5,10,20,40', type=str)
parser.add_argument('--spectrogram_window_lengths', default='512,1024', type=str)
parser.add_argument('--spectrogram_window_overlap', default='0.50', type=str)


parser.add_argument('--base_scene_args', default='arguments/multi_gen_variable/base_scene_generation.args', type=str,
                    help='Base Arguments for scene generation')
parser.add_argument('--base_question_args', default='arguments/multi_gen_variable/base_question_generation.args',
                    type=str, help='Base Arguments for question generation')
parser.add_argument('--base_spectrogram_args', default='arguments/multi_gen_variable/base_spectrogram_generation.args',
                    type=str, help='Base Arguments for spectrogram generation')
parser.add_argument('--generated_output_folder', default='output', type=str,
                    help='Output path that will be used when generating dataset')
parser.add_argument('--set_to_produce', default='train,val,test', type=str,
                    help='Sets that should be generated (Default : train,val,test)')

parser.add_argument('--output_script_filepath', default='generate.sh', type=str,
                    help='Path to the generated script (That will be used to generate combinations of datasets)')
parser.add_argument('--version_name_prefix', default='v3', type=str,
                    help='Prefix for all generated versions')

parser.add_argument('--python_bin', default='python', type=str,
                    help='Path to the python binary that will be used to generate dataset')
parser.add_argument('--nb_process', default=4, type=int,
                    help='Nb core available for generation')

parser.add_argument('--tar_and_delete', action='store_true',
                    help='Will archive generated files and delete the non compressed version')


def write_script(script, filepath):
    with open(filepath, 'w') as f:
        f.write("#!/usr/bin/env bash\n")
        f.write("# Will stop the script on first error\nset -e\n")
        f.write(script)
        f.write('\necho "All Done !"\n')

    # Make file executable
    os.chmod(filepath, 0o775)


# Commands generation
def get_base_cmd(script_name, base_config_path, output_folder=None, scenes_path=None, set_type=None):
    cmd = f"{script_name} @{base_config_path}"

    if output_folder is not None:
        cmd += f" --output_folder {output_folder}"

    if scenes_path is not None:
        cmd += f" --scenes_json {scenes_path}"

    if set_type is not None:
        cmd += f" --set_type {set_type}"

    return cmd


def generate_scene_commands(base_config_path, base_version_name, output_folder, scene_lengths, script_name='generate_scenes_definition.py'):
    cmds = []
    names = []
    log_paths = []

    base_cmd = get_base_cmd(script_name, base_config_path, output_folder)
    for scene_length in scene_lengths:
        scene_length_in_k = scene_length/1000
        scene_length_in_k = int(scene_length_in_k) if scene_length_in_k.is_integer() else '%.2f' % scene_length_in_k
        version_name = f"{base_version_name}_{scene_length_in_k}k"
        cmds.append(f"{base_cmd} --nb_scene {scene_length} --output_version_nb {version_name}")
        names.append(version_name)
        log_paths.append(f"{output_folder}/{version_name}/log/scene_generation.log")

    return cmds, names, log_paths


def generate_question_commands(base_config_path, base_version_name, output_folder, insts_per_scene, scenes_path=None, script_name='generate_questions.py'):
    cmds = []
    names = []
    log_paths = []

    base_cmd = get_base_cmd(script_name, base_config_path, output_folder, scenes_path)

    for inst_per_scene in insts_per_scene:
        version_name = f"{base_version_name}_{inst_per_scene}_inst"
        cmds.append(f"{base_cmd} --templates_per_scene {inst_per_scene} --output_version_nb {version_name}")
        names.append(version_name)
        log_paths.append(f"{output_folder}/{version_name}/log/question_generation_%s.log")

    return cmds, names, log_paths


def generate_consolidation_commands(output_folder, version_names, script_name='./scripts/consolidate_questions.py'):
    cmds = []

    base_cmd = f"{script_name} --output_folder {output_folder} --tmp_folder_prefix TMP_ --remove_tmp"

    for version_name in version_names:
        cmds.append(f"{base_cmd} --output_version_nb {version_name}")

    return cmds


def generate_spectrogram_fft_commands(base_config_path, base_version_name, output_folder, window_lengths,
                                      window_overlaps, scenes_path=None, script_name="produce_scenes_audio.py"):
    cmds = []
    names = []
    log_paths = []

    base_cmd = get_base_cmd(script_name, base_config_path, output_folder, scenes_path)

    combinations = [(l, int(l*o), int(100*o)) for l in window_lengths for o in window_overlaps]

    for window_length, window_overlap, window_overlap_percent in combinations:
        version_name = f"{base_version_name}_{window_length}_win_{window_overlap_percent}_overlap"
        cmds.append(f"{base_cmd} --output_version_nb {version_name} --spectrogram_window_length {window_length} "
                    f"--spectrogram_window_overlap {window_overlap}")
        names.append(version_name)
        log_paths.append(f"{output_folder}/{version_name}/log/spectrogram_fft_%s.log")

    return cmds, names, log_paths


def generate_spectrogram_noise_commands(base_config_path, base_version_name, output_folder, noise_gains,
                                        scenes_path=None, script_name="produce_scenes_audio.py"):
    cmds = []
    names = []
    log_paths = []

    base_cmd = get_base_cmd(script_name, base_config_path, output_folder, scenes_path)

    for label, gain in noise_gains.items():
        version_name = f"{base_version_name}_{label}_noise"
        cmd = f"{base_cmd} --output_version_nb {version_name}"
        if type(gain) is list:
            cmds.append(f"{cmd} --with_background_noise --background_noise_gain_range {gain[0]},{gain[1]}")
        else:
            # No background noise
            cmds.append(f"{cmd} --no_background_noise")

        names.append(version_name)
        log_paths.append(f"{output_folder}/{version_name}/log/spectrogram_noise_%s.log")

    return cmds, names, log_paths


# TODO : Implement this
def generate_spectrogram_reverb_commands(base_config_path, version_name, window_lengths, window_overlaps,
                                         scenes_path=None, script_name="produce_scenes_audio.py"):
    assert True, 'Not Implemented'


def generate_symlink_commands(scene_name, question_names, spectrogram_names, output_folder,
                              attribute_filename='attributes.json'):
    cmds = []
    for question_name in question_names:
        question_suffix = question_name.replace(scene_name, '')

        for spectrogram_name in spectrogram_names:
            cmd = ""
            spectrogram_suffix = spectrogram_name.replace(scene_name, '')

            new_version_name = f"{scene_name}{question_suffix}{spectrogram_suffix}"
            new_version_path = f"{output_folder}/{new_version_name}"

            scene_path = f"../{scene_name}/scenes"
            question_path = f"../{question_name}/questions"
            spectrogram_root_path = f"../{spectrogram_name}"
            spectrogram_real_root_path = f"{output_folder}/{spectrogram_name}"

            #cmd += f'if [[ ! -e {new_version_path} ]];then\n'
            cmd += f"mkdir -p {new_version_path}\n"
            cmd += f"ln -sf ../{scene_name}/{attribute_filename} {new_version_path}/{attribute_filename}\n"
            cmd += f"ln -snf {scene_path} {new_version_path}/scenes\n"
            cmd += f"ln -snf {question_path} {new_version_path}/questions\n"
            cmd += f"[[ -e {spectrogram_real_root_path}/images ]] && ln -snf {spectrogram_root_path}/images {new_version_path}/images\n"
            cmd += f"[[ -e {spectrogram_real_root_path}/audio ]] && ln -snf {spectrogram_root_path}/audio {new_version_path}/audio\n"
            cmd += f"[[ -e {spectrogram_real_root_path}/preprocessed ]] && ln -snf {spectrogram_root_path}/preprocessed {new_version_path}/preprocessed\n"
            #cmd += "fi\n\n"


            cmds.append(cmd)

    return cmds


def generate_tar_and_delete_commands(scene_name, question_names, spectrogram_names, total_nb_process, delete=True):
    cmds = []
    for question_name in question_names:
        question_suffix = question_name.replace(scene_name, '')

        for spectrogram_name in spectrogram_names:
            cmd = ""
            spectrogram_suffix = spectrogram_name.replace(scene_name, '')

            new_version_name = f"{scene_name}{question_suffix}{spectrogram_suffix}"

            cmd += f"if [[ ! -e {new_version_name}.tar.gz ]];then\n"
            cmd += f'echo "Tarring {new_version_name}.tar.gz"\n'
            cmd += f"tar cf - {new_version_name} | pigz -9 -p {total_nb_process} > {new_version_name}.tar.gz\n"
            cmd += "fi\n"
            cmd += f"if [[ ! -e {scene_name}.tar.gz ]];then\n"
            cmd += f'echo "Tarring {scene_name}.tar.gz"\n'
            cmd += f"tar cf - {scene_name} | pigz -9 -p {total_nb_process} > {scene_name}.tar.gz\n"
            cmd += "fi\n"
            cmd += f"if [[ ! -e {question_name}.tar.gz ]];then\n"
            cmd += f'echo "Tarring {question_name}.tar.gz"\n'
            cmd += f"tar cf - {question_name} | pigz -9 -p {total_nb_process} > {question_name}.tar.gz\n"
            cmd += "fi\n"
            cmd += f"if [[ ! -e {spectrogram_name}.tar.gz ]];then\n"
            cmd += f'echo "Tarring {spectrogram_name}.tar.gz"\n'
            cmd += f"tar cf - {spectrogram_name} | pigz -9 -p {total_nb_process} > {spectrogram_name}.tar.gz\n"
            cmd += "fi\n"

            if delete:
                cmd += "set -x\n"
                cmd += f"rm -rf {scene_name} {question_name} {spectrogram_name} {new_version_name}\n"
                cmd += "{ set +x; } 2>/dev/null\n"

            cmds.append(cmd)

    return cmds


# Script generation
def generate_simple_script(label, cmds):
    script = f"\n# {label}\n"

    for cmd in cmds:
        script += cmd

    return script


def generate_preparation_script(label, new_instance_names, output_folder, directories_to_create=[], directories_to_link=[],
                                attribute_filename='attributes.json'):

    if 'log' not in directories_to_create:
        directories_to_create.append('log')

    script = f"\n# {label}\n"
    regexp = re.compile(r"(.+_[\d,\.]+k)")
    for instance_name in new_instance_names:
        base_inst_name = re.match(regexp, instance_name)[1]
        new_folder_path = f'{output_folder}/{instance_name}'
        #script += f'if [[ ! -e {new_folder_path} ]]; then\n'
        script += f'mkdir -p {new_folder_path}\n'

        for directory in directories_to_create:
            script += f'mkdir -p {new_folder_path}/{directory}\n'

        if base_inst_name != instance_name:
            base_folder_path = f'../{base_inst_name}'
            base_folder_real_path = f'{output_folder}/{base_inst_name}'

            script += f'ln -sf {base_folder_path}/{attribute_filename} {new_folder_path}/{attribute_filename}\n'

            for directory in directories_to_link:
                script += f"[[ -e {base_folder_real_path}/{directory} ]] && " \
                          f"ln -snf {base_folder_path}/{directory} {new_folder_path}/{directory}\n"

        #script += "fi\n"
        script += "\n"

    return script


def generate_script_commands(base_config_paths, output_folder, scene_lengths, question_insts_per_scene,
                             spectrogram_window_lengths, spectrogram_window_overlap, background_noise_gains,
                             total_nb_process, prefix='v3'):

    scene_cmds, scene_names, scene_log_paths = generate_scene_commands(base_config_paths['scene'], prefix, output_folder,
                                                                       scene_lengths)

    script = {
        'scene': {
            'cmds': scene_cmds,
            'names': scene_names,
            'log_paths': scene_log_paths
        },
        'question': {
            'cmds': [],
            'names': [],
            'log_paths': [],
            'consolidation': []
        },
        'spectrogram_fft': {
            'cmds': [],
            'names': [],
            'log_paths': []
        },
        'spectrogram_noise': {
            'cmds': [],
            'names': [],
            'log_paths': []
        },
        "symlink": {
            'cmds': []
        },
        "tar_and_delete": {
            'cmds': [f"cd {output_folder}\n"]
        }
    }

    for scene_cmd, scene_name in zip(scene_cmds, scene_names):
        # Question Generation
        tmp_question_cmds, tmp_question_names, tmp_log_paths = generate_question_commands(base_config_paths['question'],
                                                                                          scene_name,
                                                                                          output_folder,
                                                                                          question_insts_per_scene)

        script['question']['cmds'] += tmp_question_cmds
        script['question']['names'] += tmp_question_names
        script['question']['log_paths'] += tmp_log_paths

        # Question Consolidation
        script['question']['consolidation'] += generate_consolidation_commands(output_folder, tmp_question_names)


        # Spectrogram Generation -- FFT
        tmp_spectrogram_fft_cmds, tmp_spectrogram_fft_names, tmp_log_paths = generate_spectrogram_fft_commands(
            base_config_paths['spectrogram'],
            scene_name,
            output_folder,
            spectrogram_window_lengths,
            spectrogram_window_overlap)

        script['spectrogram_fft']['cmds'] += tmp_spectrogram_fft_cmds
        script['spectrogram_fft']['names'] += tmp_spectrogram_fft_names
        script['spectrogram_fft']['log_paths'] += tmp_log_paths

        # Spectrogram Generation -- Background Noise
        tmp_spectrogram_noise_cmds, tmp_spectrogram_noise_names, tmp_log_paths = generate_spectrogram_noise_commands(
            base_config_paths['spectrogram'],
            scene_name,
            output_folder,
            background_noise_gains)

        script['spectrogram_noise']['cmds'] += tmp_spectrogram_noise_cmds
        script['spectrogram_noise']['names'] += tmp_spectrogram_noise_names
        script['spectrogram_noise']['log_paths'] += tmp_log_paths

        script['symlink']['cmds'] += generate_symlink_commands(scene_name, tmp_question_names,
                                                               tmp_spectrogram_fft_names, output_folder)

        script['tar_and_delete']['cmds'] += generate_tar_and_delete_commands(scene_name, tmp_question_names,
                                                                             tmp_spectrogram_fft_names,
                                                                             total_nb_process=total_nb_process)

        # TODO : Add reverb params

    return script


def generate_script_line(cmd, set_type, process_in_use, total_nb_process, nb_process_per_gen, log_path=None,
                         python_bin="python", directory_to_check=None):

    string = ""

    if directory_to_check is not None:
        # This is patchy, there is way more elegant way of retrieving those infos. This is just faster than refactoring...
        reg = re.compile(r'.*--output_folder\s(.[^\s]+).*--output_version_nb\s(.[^\s]+)')
        matches = re.match(reg, cmd)

        output_folder, version_name = matches[1], matches[2]

        path_to_dir = f"{output_folder}/{version_name}/{directory_to_check}"

        if set_type is not None:
            path_to_dir = path_to_dir % set_type

        string += f"if [[ ! -e {path_to_dir} ]]; then\n"

    string += f"if [[ -e {output_folder}/{version_name}.tar.gz ]]; then\n"
    string += f'echo "Untaring \'{version_name}.tar.gz\'"\n'
    string += f"pigz -dc {output_folder}/{version_name}.tar.gz | tar xf - -C {output_folder}\n"
    string += "else\n"

    string += f"set -x\n{python_bin} {cmd}"

    if set_type is not None:
        string += f" --set_type {set_type}"

    if process_in_use < total_nb_process:
        if nb_process_per_gen > 1:
            string += f" --nb_process {nb_process_per_gen}"

        if log_path is not None:
            if '%s' in log_path and set_type is not None:
                log_path = log_path % set_type

            string += f" > {log_path}"

        string += " &\n"
        string += "{ set +x; } 2>/dev/null\n"

        string += "fi\n"

        # This is patchy, avoid race conditions (On folder creation) by not starting all the process at the same time
        string += "sleep 0.5\n"

        if directory_to_check is not None:
            string += "fi\n"

        string += f"PROCESS_{process_in_use}_PID=$!\n"

        process_in_use += nb_process_per_gen

        if process_in_use == total_nb_process:
            string += "\nwait"
            proc_id = 0
            while proc_id < total_nb_process:
                string += " ${PROCESS_%d_PID}" % proc_id
                proc_id += nb_process_per_gen

            process_in_use = 0
            string += "\n"

    string += "\n"

    return string, process_in_use


def generate_script(label, cmds, total_nb_process, set_types=None, log_paths=None, multiple_process_per_gen=False,
                    longer_set_type=None, python_bin="python", directory_to_check=None):
    if set_types is None:
        set_types = [None]
    elif longer_set_type is not None:
        set_types = list(set(set_types) - {longer_set_type})

    if log_paths is None:
        log_paths = [None]*len(cmds)

    if not multiple_process_per_gen:
        nb_process_per_gen = 1
    else:
        nb_set_to_gen = len(set_types)
        nb_process_per_gen = int(total_nb_process / nb_set_to_gen)
        total_nb_process = nb_process_per_gen * nb_set_to_gen       # Round to multiple of nb_process_per_gen

    if total_nb_process == 1:
        total_nb_process = 0    # Disable the background process instantiation if only 1 process, side effect : Disable file log

    process_in_use = 0

    script = f"\n# {label}\n"

    for cmd, log_path in zip(cmds, log_paths):
        for set_type in set_types:
            line, process_in_use = generate_script_line(cmd, set_type, process_in_use, total_nb_process,
                                                        nb_process_per_gen, log_path, python_bin, directory_to_check)

            script += line

    # We split generation so that all the "longer process" will be bundled together to optimize multicore handling
    if longer_set_type is not None:
        if multiple_process_per_gen:
            longer_set_nb_process_per_gen = total_nb_process
        else:
            longer_set_nb_process_per_gen = nb_process_per_gen

        for cmd, log_path in zip(cmds, log_paths):
            line, process_in_use = generate_script_line(cmd, longer_set_type, process_in_use, total_nb_process,
                                                        longer_set_nb_process_per_gen, log_path, python_bin,
                                                        directory_to_check)

            script += line

    if process_in_use != 0:
        script += "wait"
        proc_id = 0
        while proc_id < process_in_use:
            script += " ${PROCESS_%d_PID}" % proc_id
            proc_id += nb_process_per_gen

        script += "\n"

    return script


def arg_str_to_type_list(arg_str, dtype=int, separator=','):
    return [dtype(a) for a in arg_str.split(separator)]


def main(args):
    base_config_paths = {
        'scene': args.base_scene_args,
        'question': args.base_question_args,
        'spectrogram': args.base_spectrogram_args
    }

    set_types = args.set_to_produce.split(',')

    scene_max_lengths = arg_str_to_type_list(args.scene_max_lengths, dtype=int)
    question_insts_per_scene = arg_str_to_type_list(args.question_insts_per_scene, dtype=int)
    spectrogram_window_lengths = arg_str_to_type_list(args.spectrogram_window_lengths, dtype=int)
    spectrogram_window_overlap = arg_str_to_type_list(args.spectrogram_window_overlap, dtype=float)
    background_noise_gains = {
        'NO' : 'NO',
        'small' : [-90, -80],
        'medium': [-70, -50],
        'large' : [-40, -10],
        'extra' : [-10, -5]
    }

    # Exp 1:
    #       - See impact of the number of scenes
    #scene_lengths = [1000, 2000, 5000, 10000, 15000, 20000, 30000, 40000, 50000]
    #question_insts_per_scene = [1, 2, 5, 10, 20, 30, 40]
    #spectrogram_window_lengths = [512, 1024]
    #spectrogram_window_overlap = [0.50]

    # Exp 2:
    #       - See impact of number of questions
    #       - Note : Should also include 1 insts_per_scene from Exp1 in result analysis
    #scene_lengths = [1000, 5000, 10000, 20000, 30000]
    #question_insts_per_scene = [2, 5, 10, 20, 40]
    #spectrogram_window_lengths = [1024]
    #spectrogram_window_overlap = [0.50]

    # Exp 3:
    #       - See impact of fft windows
    #scene_lengths = [10000]       # FIXME : Choose those !
    #question_insts_per_scene = [20]   # FIXME : Choose those !
    #spectrogram_window_lengths = [1024]
    #spectrogram_window_overlap = [0.50]

    if args.version_name_prefix[-1] == "_":
        args.version_name_prefix = args.version_name_prefix[:-1]

    # TODO : Add Reverb
    script = generate_script_commands(base_config_paths, args.generated_output_folder, scene_max_lengths,
                                      question_insts_per_scene, spectrogram_window_lengths,
                                      spectrogram_window_overlap, background_noise_gains, args.nb_process,
                                      args.version_name_prefix)

    # Scene Generation Script
    scene_preparation_script = generate_preparation_script("Scene Preparation", script['scene']['names'], args.generated_output_folder)
    scene_gen_script = generate_script("Scene Generation", script['scene']['cmds'], args.nb_process,
                                       log_paths=script['scene']['log_paths'], directory_to_check='scenes',
                                       python_bin=args.python_bin)

    question_preparation_script = generate_preparation_script('Question Preparation', script['question']['names'],
                                                              args.generated_output_folder, directories_to_link=['scenes'])

    # Question Generation Script
    question_gen_script = generate_script(f"Question Generation", script['question']['cmds'],
                                          args.nb_process, set_types, script['question']['log_paths'],
                                          longer_set_type='train',
                                          directory_to_check='questions/CLEAR_%s_questions.json', python_bin=args.python_bin)

    # Question Consolidation
    question_consolidation_script = generate_script(f"Question Consolidation", script['question']['consolidation'],
                                                    args.nb_process, set_types, python_bin=args.python_bin,
                                                    directory_to_check='questions/CLEAR_%s_questions.json')

    spectrogram_fft_preparation_script = generate_preparation_script('Spectrogram FFT Preparation',
                                                                     script['spectrogram_fft']['names'], args.generated_output_folder,
                                                                     directories_to_create=['preprocessed'],
                                                                     directories_to_link=['scenes'])

    # Spectrogram Generation Scripts
    spectrogram_fft_gen_script = generate_script("Spectrogram Generation", script['spectrogram_fft']['cmds'],
                                                 args.nb_process, set_types, script['spectrogram_fft']['log_paths'],
                                                 directory_to_check="images/%s",
                                                 longer_set_type='train', multiple_process_per_gen=True,
                                                 python_bin=args.python_bin)

    symlink_script = generate_simple_script("Linking versions together", script['symlink']['cmds'])

    if args.tar_and_delete:
        tar_and_delete_script = generate_simple_script("Tar and Delete", script['tar_and_delete']['cmds'])
    else:
        tar_and_delete_script = ""

    full_script = scene_preparation_script + scene_gen_script + question_preparation_script + question_gen_script + \
                  question_consolidation_script + spectrogram_fft_preparation_script + spectrogram_fft_gen_script + \
                  symlink_script + tar_and_delete_script

    comment_string = "\n# Parameters : \n"
    comment_string += f'## scene_max_lengths: {scene_max_lengths}\n'
    comment_string += f'## question_insts_per_scene: {question_insts_per_scene}\n'
    comment_string += f'## spectrogram_window_lengths: {spectrogram_window_lengths}\n'
    comment_string += f'## spectrogram_window_overlap: {spectrogram_window_overlap}\n'
    comment_string += f'## Base scene arguments : {base_config_paths["scene"]}\n'
    comment_string += f'## Base question arguments : {base_config_paths["question"]}\n'
    comment_string += f'## Base spectrogram arguments : {base_config_paths["spectrogram"]}\n\n'

    write_script(comment_string + full_script, args.output_script_filepath)

    print(comment_string)
    print("Script written to '%s'" % args.output_script_filepath)


if __name__ == "__main__":
    args = parser.parse_args()
    main(args)
