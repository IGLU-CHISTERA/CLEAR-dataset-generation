# CLEAR Dataset
# >> Question Generator
#
# Author :      Jerome Abdelnour
# Year :        2018-2019
# Affiliations: Universite de Sherbrooke - Electrical and Computer Engineering faculty
#               KTH Stockholm Royal Institute of Technology
#               IGLU - CHIST-ERA
#
# The question generator is based on the CLEVR question generator (github.com/facebookresearch/clevr-dataset-gen)
# The code have been adapted to work with acoustic scenes

# For the original clevr-dataset-gen code
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

"""
Generate synthetic questions and answers for CLEAR acoustic scenes. Input is a single JSON file containing ground-truth 
scene information for all images, and output is one or more JSON files containing generated questions, answers and 
programs. The resulting files should be merged together using ./scripts/consolidate_questions.py to create one single
JSON file.

Questions are generated by expanding templates. Each template contains a single program template and one or more text 
templates. Text templates are composed of placeholders of the form <{NAME}{OCCURENCE}>. (Ex : <I> <I2> <L> <B3>) 
See templates/attributes.json for a complete list of attributes

Program templates may contain special nodes that expand into multiple functions during instantiation; for example a 
"filter" node in a program template will expand into a combination of "filter_size", "filter_color", "filter_material"
and "filter_shape" nodes after instantiation. A "filter_unique" node will expand into some combination of filtering 
nodes followed by a "unique" node.

Templates are instantiated using depth-first search; we are looking for template instantiations where (1) each "unique" 
node actually refers to a single object, (2) constraints in the template are satisfied, and (3) the answer to the 
question passes our rejection sampling heuristics.

To efficiently handle (1) and (2), we keep track of partial evaluations of the program during each step of template 
expansion. This together with the use of composite nodes in program templates (filter_unique, relate_filter_unique) 
allow us to efficiently prune the search space and terminate early when we know that (1) or (2) will be violated.
"""

import argparse, sys, os, random, math
from collections import OrderedDict
from shutil import rmtree as rm_dir
import numpy as np

# Question Engine (Question Answering Mechanism)
import utils.question_engine as qeng

# File handling
from utils.question_helper import load_scenes, load_and_prepare_metadata, load_and_prepare_templates, load_synonyms, \
    write_questions_part_to_file, write_possible_attributes

# Filtering
from utils.question_helper import find_relate_filter_options, find_filter_options, add_empty_filter_options

# Other helpers
from utils.question_helper import validate_constraints, create_reset_counts_fct, replace_optional_words, \
    question_node_shallow_copy

# Misc
from utils.misc import init_random_seed, generate_info_section, get_max_scene_length, save_arguments


# Arguments Definition
parser = argparse.ArgumentParser(fromfile_prefix_chars='@')

# Inputs files
parser.add_argument('--metadata_file', default='templates/attributes.json',
                    help="JSON file listing the available attributes of sounds")
parser.add_argument('--synonyms_json', default='templates/synonyms.json',
                    help="JSON file defining synonyms for parameter values")
parser.add_argument('--template_dir', default='templates/question_templates',
                    help="Directory containing JSON templates for questions")

# Options
# Control the number of questions per scene generated
# Nb question per scene = templates_per_scene * instances_per_template
parser.add_argument('--templates_per_scene', default=20, type=int,
                    help="The number of different templates that should be instantiated for each scene")
parser.add_argument('--instances_per_template', default=1, type=int,
                    help="The number of times each template should be instantiated")
parser.add_argument('--reset_counts_every', default=250, type=int,
                    help="How often to reset template and answer counts. Higher values will result in "
                         "flatter distributions over templates and answers, but will result in longer runtimes.")
parser.add_argument('--instantiation_retry_threshold', default=10000, type=int,
                    help="Maximum number of retry attempt before dropping if didn't reach instances_per_template")
parser.add_argument('--scene_start_idx', default=0, type=int,
                    help="The scene index at which to start generating questions; this allows question generation "
                         "to be split across many workers")
parser.add_argument('--num_scenes', default=0, type=int,
                    help="The number of scenes for which to generate questions. Setting to 0 generates questions for "
                         "all scenes in the input file starting from --scene_start_idx")

# Output paths
parser.add_argument('--output_folder', default='./output',
                    help="Folder where to store the generated questions")
parser.add_argument('--output_filename_prefix', default='CLEAR',
                    help="Prefix for the output file")
parser.add_argument('--output_version_nb', default='0.0.1',
                    help="Identifier of the dataset version.")
parser.add_argument('--set_type', default='train', type=str,
                    help="Specify the set type (train/val/test)")
parser.add_argument('--clear_existing_files', action='store_true',
                    help='Will delete all files in {output_folder}/{output_version_nb} before starting the generation.')
parser.add_argument('--write_to_file_every', default=2500, type=int,
                    help="The number of questions that will be written to each temporary files. "
                         "(We are doing this to reduce the amount of memory used)")

# Misc
parser.add_argument('--random_nb_generator_seed', default=None, type=int,
                    help='Set the random number generator seed to reproduce results')
parser.add_argument('--verbose', action='store_true',
                    help="Print more verbose output")


def generate_and_write_questions_to_file(scenes, templates, metadata, synonyms,
                                         questions_info, output_folder, output_filename):
    """
    Wrapper around the question instantiation
        - Launch question instantiation for each scene
        - Create appropriate JSON structure
        - Write questions to file
            - Questions are written to temporary smaller JSON files.in order to keep memory usage low
            - ./scripts/consolidate_questions.py should be run afterwards to merge all questions in 1 file
    """

    # Helper function
    reset_counts = create_reset_counts_fct(templates, metadata, metadata['max_scene_length'])

    # Initialisation
    questions = []
    question_index = 0
    file_written = 0
    scene_count = 0
    nb_scenes = len(scenes)
    print_msg_every = int(nb_scenes*0.1)

    for i, scene in enumerate(scenes):
        if i % print_msg_every == 0:
            print('starting scene %s (%d / %d)' % (scene['scene_filename'], i + 1, nb_scenes), flush=True)

        if scene_count % args.reset_counts_every == 0:
            template_counts, template_answer_counts = reset_counts()
        scene_count += 1

        # Order templates by the number of questions we have so far for those
        # templates. This is a simple heuristic to give a flat distribution over templates.
        # We shuffle the templates before sorting to ensure variability when the counts are equals
        templates_items = list(templates.items())
        np.random.shuffle(templates_items)
        templates_items = sorted(templates_items,
                                 key=lambda x: template_counts[x[0]])

        num_instantiated = 0
        for (template_fn, template_idx), template in templates_items:
            if 'disabled' in template and template['disabled']:
                continue

            #print('    trying template ', template_fn, template_idx, flush=True)

            question_texts, programs, answers = instantiate_template(
                scene,
                template,
                metadata,
                template_answer_counts[(template_fn, template_idx)],
                synonyms,
                reset_threshold=args.instantiation_retry_threshold,
                max_instances=args.instances_per_template,
                verbose=args.verbose)

            for question_text, program, answer in zip(question_texts, programs, answers):
                questions.append({
                    'scene_filename': scene['scene_filename'],
                    'scene_index': scene['scene_index'],
                    'question': question_text,
                    'program': program,
                    'answer': answer,
                    'template_index': '%s-%d' % (template_fn, template_idx),
                    'question_index': question_index,
                })
                question_index += 1

            if len(question_texts) > 0:
                # Template have been instantiated at least 1 time
                num_instantiated += 1
                template_counts[(template_fn, template_idx)] += 1
            elif args.verbose:
                print('Could not generate any question for template "%s-%d" on scene "%s"' %
                      (template_fn, template_idx, scene['scene_filename']))

            if num_instantiated >= args.templates_per_scene:
                # We have instantiated enough template for this scene
                break

        if question_index != 0 and question_index % args.write_to_file_every == 0:
            write_questions_part_to_file(output_folder, output_filename, questions_info, questions, file_written)
            file_written += 1
            questions = []

        if "_filter_options" in scene:
            # Clear filter options for this scene. We won't be needing them anymore
            del scene['_filter_options']

    if len(questions) > 0 or file_written == 0:
        # Write the rest of the questions
        # If no file were written and we have 0 questions,
        # we still want an output file with no questions (Otherwise it will break the pipeline)
        write_questions_part_to_file(output_folder, output_filename, questions_info, questions, file_written)


def instantiate_template(scene_struct, template, metadata, answer_counts,
                         synonyms, max_instances=None, reset_threshold=0, verbose=False):
    """
    Instantiate the template based on the content of a scene.
    We will try to instantiate the template {max_instances} times.
    """
    # Initialisation
    states = []
    final_states = []

    # Helper function that reset the the process if we haven't reached the generation threshold
    def reset_states_if_needed(current_states):
        if reset_states_if_needed.reset_counter < reset_threshold:
            if len(current_states) == 0:
                initial_state = {
                    'nodes': [question_node_shallow_copy(template['nodes'][0])],
                    'vals': {},
                    'input_map': {0: 0},
                    'next_template_node': 1,
                }
                current_states = [initial_state]
                reset_states_if_needed.reset_counter += 1
        else:
            if verbose: print("--> Retried %d times. Could only instantiate %d on %d. Giving up on this template" % (
            reset_threshold, len(final_states), max_instances))
            current_states = []

        return current_states

    # Counter to keep track of the number of reset
    reset_states_if_needed.reset_counter = -1

    # Build the root node of the tree
    states = reset_states_if_needed(states)

    # Traverse the tree of states to instantiate the template (Depth First)
    while states:
        state = states.pop()

        # Check that the current state produce a valid answer
        q = {'nodes': state['nodes']}
        outputs = qeng.answer_question(q, metadata, scene_struct, all_outputs=True)
        answer = outputs[-1]

        if answer == '__INVALID__':
            if verbose: print("Skipping due to invalid answer")
            states = reset_states_if_needed(states)
            continue

        if not validate_constraints(template, state, outputs, template['_param_name_to_attribute'], verbose):
            states = reset_states_if_needed(states)
            continue

        # We have already checked to make sure the answer is valid, so if we have
        # processed all the nodes in the template then the current state is a valid
        # question, so add it if it passes our rejection sampling tests.
        if state['next_template_node'] == len(template['nodes']):
            # Use our rejection sampling heuristics to decide whether we should
            # keep this template instantiation
            cur_answer_count = answer_counts[answer]
            answer_counts_sorted = sorted(answer_counts.values())
            median_count = answer_counts_sorted[len(answer_counts_sorted) // 2]
            median_count = max(median_count, 5)

            nb_answers = len(answer_counts_sorted)
            idx = max(int(math.floor(nb_answers * 0.15)), 2)

            if cur_answer_count > 1.1 * answer_counts_sorted[-idx]:
                if verbose: print('skipping due to second count')
                states = reset_states_if_needed(states)
                continue
            if cur_answer_count > 5.0 * median_count:
                if verbose: print('skipping due to median')
                states = reset_states_if_needed(states)
                continue

            # If the template contains a raw relate node then we need to check for degeneracy at the end
            has_relate = any(n['type'] == 'relate' for n in template['nodes'])

            if has_relate:
                degen = qeng.is_degenerate(q, metadata, scene_struct, answer=answer,
                                           verbose=verbose)
                if degen:
                    if verbose: print("Skipping, question is degenerate")
                    continue

            answer_counts[answer] += 1
            state['answer'] = answer
            final_states.append(state)

            if max_instances is not None and len(final_states) == max_instances:
                if verbose: print('Breaking out, we got enough instances')
                break
            else:
                states = reset_states_if_needed(states)

            if verbose: print("Added a state to final_states")
            continue

        # Otherwise fetch the next node from the template
        # Make a shallow copy so cached _outputs don't leak ... this is very nasty
        next_node = template['nodes'][state['next_template_node']]
        next_node = question_node_shallow_copy(next_node)

        if next_node['type'] in qeng.functions_to_be_expanded:

            params_in_node = sorted([template['_param_name_to_attribute'][i] for i in next_node['value_inputs']])

            if next_node['type'].startswith('relate_filter'):
                unique = (next_node['type'] == 'relate_filter_unique')
                not_unique = (next_node['type'] == 'relate_filter_not_unique')
                include_zero = (
                            next_node['type'] == 'relate_filter_count' or next_node['type'] == 'relate_filter_exist')

                filter_options = find_relate_filter_options(answer, scene_struct, params_in_node,
                                                            template['_can_be_null_attributes'], unique=unique,
                                                            include_zero=include_zero, not_unique=not_unique)

            else:
                filter_options = find_filter_options(answer, scene_struct, params_in_node,
                                                     template['_can_be_null_attributes'])

                if next_node['type'] == 'filter':
                    # Remove null filter
                    filter_options.pop((None,) * len(params_in_node), None)

                if next_node['type'] == 'filter_unique':
                    single_filter_options = OrderedDict()

                    # Get rid of all filter options that don't result in a single object
                    for k, v in filter_options.items():
                        if len(v) == 1:
                            single_filter_options[k] = v

                    filter_options = single_filter_options
                elif next_node['type'] == 'filter_not_unique':
                    multiple_filter_options = OrderedDict()
                    # Get rid of all filter options that don't result in more than one object
                    for k, v in filter_options.items():
                        if len(v) > 1:
                            multiple_filter_options[k] = v
                    filter_options = multiple_filter_options
                else:

                    # Add some filter options that do NOT correspond to the scene
                    if next_node['type'] == 'filter_exist':
                        # For filter_exist we want an equal number that do and don't
                        num_to_add = len(filter_options)
                    elif next_node['type'] == 'filter_count':
                        # For filter_count add empty filters equal to the number of singletons
                        num_to_add = sum(1 for k, v in filter_options.items() if len(v) == 1)
                    else:
                        num_to_add = 0

                    add_empty_filter_options(filter_options, metadata, template['_can_be_null_attributes'],
                                             params_in_node, num_to_add)

            # The filter options keys are sorted before being shuffled to control the randomness (ensure reproducibility)
            # This ensure that for the same seed of the random number generator, the same output will be produced
            filter_option_keys = sorted(filter_options.keys(), key=lambda x: x[0] if x[0] is not None else '')

            np.random.shuffle(filter_option_keys)
            for k in filter_option_keys:
                new_nodes = []
                cur_next_vals = {l: v for l, v in state['vals'].items()}
                next_input = state['input_map'][next_node['inputs'][0]]
                filter_value_inputs = sorted(next_node['value_inputs'],
                                             key=lambda param: template['_param_name_to_attribute'][param])

                if next_node['type'].startswith('relate'):
                    param_name = next_node['value_inputs'][0]  # The first value_input has to be a relate
                    filter_value_inputs = sorted(next_node['value_inputs'][1:],
                                                 key=lambda param: template['_param_name_to_attribute'][param])
                    param_val = k[0]  # Relation value
                    k = k[1]  # Other attributes filter
                    new_nodes.append({
                        'type': 'relate',
                        'inputs': [next_input],
                        'value_inputs': [param_val],
                    })
                    cur_next_vals[param_name] = param_val
                    next_input = len(state['nodes']) + len(new_nodes) - 1

                for param_name, param_val in zip(filter_value_inputs, k):
                    param_type = template['_param_name_to_attribute'][param_name]
                    filter_type = 'filter_%s' % param_type

                    if param_val is not None:
                        new_nodes.append({
                            'type': filter_type,
                            'inputs': [next_input],
                            'value_inputs': [param_val],
                        })
                        cur_next_vals[param_name] = param_val
                        next_input = len(state['nodes']) + len(new_nodes) - 1
                    else:
                        param_val = ''
                        cur_next_vals[param_name] = param_val

                input_map = {k: v for k, v in state['input_map'].items()}
                extra_type = None
                if next_node['type'].endswith('not_unique'):
                    extra_type = 'not_unique'
                elif next_node['type'].endswith('unique'):
                    extra_type = 'unique'
                elif next_node['type'].endswith('count'):
                    extra_type = 'count'
                elif next_node['type'].endswith('exist'):
                    extra_type = 'exist'

                if extra_type is not None:
                    new_nodes.append({
                        'type': extra_type,
                        'inputs': [input_map[next_node['inputs'][0]] + len(new_nodes)],
                        'value_inputs': []
                    })

                input_map[state['next_template_node']] = len(state['nodes']) + len(new_nodes) - 1
                states.append({
                    'nodes': state['nodes'] + new_nodes,
                    'vals': cur_next_vals,
                    'input_map': input_map,
                    'next_template_node': state['next_template_node'] + 1,
                })

        elif 'value_inputs' in next_node and next_node['value_inputs']:
            # If the next node has template parameters, expand them out
            # TODO: Generalize this to work for nodes with more than one side input
            assert len(next_node['value_inputs']) == 1, 'NOT IMPLEMENTED'

            # Use metadata to figure out domain of valid values for this parameter.
            # Iterate over the values in a random order; then it is safe to bail
            # from the DFS as soon as we find the desired number of valid template
            # instantiations.
            param_name = next_node['value_inputs'][0]
            param_type = template['_param_name_to_attribute'][param_name]
            param_vals = metadata['attributes'][param_type]['values'][:]
            np.random.shuffle(param_vals)
            for val in param_vals:
                input_map = {k: v for k, v in state['input_map'].items()}
                input_map[state['next_template_node']] = len(state['nodes'])
                cur_next_node = {
                    'type': next_node['type'],
                    'inputs': [input_map[idx] for idx in next_node['inputs']],
                    'value_inputs': [val],
                }
                cur_next_vals = {k: v for k, v in state['vals'].items()}
                cur_next_vals[param_name] = val

                states.append({
                    'nodes': state['nodes'] + [cur_next_node],
                    'vals': cur_next_vals,
                    'input_map': input_map,
                    'next_template_node': state['next_template_node'] + 1,
                })
        else:
            input_map = {k: v for k, v in state['input_map'].items()}
            input_map[state['next_template_node']] = len(state['nodes'])
            next_node = {
                'type': next_node['type'],
                'inputs': [input_map[idx] for idx in next_node['inputs']],
                'value_inputs': []
            }
            states.append({
                'nodes': state['nodes'] + [next_node],
                'vals': state['vals'],
                'input_map': input_map,
                'next_template_node': state['next_template_node'] + 1,
            })

    # Actually instantiate the template with the solutions we've found
    return instantiate_texts_from_solutions(template, synonyms, final_states)


bool_to_yes_no = ['no', 'yes']
def instantiate_texts_from_solutions(template, synonyms, final_states):
    """
    Translate the validated final_states to textual instantiation of the question
    """
    # Actually instantiate the template with the solutions we've found
    text_questions, structured_questions, answers = [], [], []
    for state in final_states:
        structured_questions.append(state['nodes'])

        # Translating True/False values to yes/no
        if type(state['answer']) is bool:
            state['answer'] = bool_to_yes_no[state['answer']]

        answers.append(state['answer'])
        text = random.choice(template['text'])
        for name, val in state['vals'].items():
            if val in synonyms:
                val = random.choice(synonyms[val])
            text = text.replace(name, val)
            text = ' '.join(text.split())
        text = replace_optional_words(text)
        text = ' '.join(text.split())
        text_questions.append(text)

    return text_questions, structured_questions, answers


def main(args):
    # Paths definition from arguments
    experiment_output_folder = os.path.join(args.output_folder, args.output_version_nb)
    questions_output_folder = os.path.join(experiment_output_folder, 'questions')
    tmp_output_folder = os.path.join(questions_output_folder, 'TMP_%s' % args.set_type)
    questions_filename = '%s_%s_questions.json' % (args.output_filename_prefix, args.set_type)
    questions_output_filepath = os.path.join(questions_output_folder, questions_filename)
    scene_filepath = os.path.join(experiment_output_folder, 'scenes',
                                  '%s_%s_scenes.json' % (args.output_filename_prefix, args.set_type))

    # Setting the random seed from arguments
    if args.random_nb_generator_seed is not None:
        init_random_seed(args.random_nb_generator_seed)
    else:
        print("The seed must be specified in the arguments.", file=sys.stderr)
        exit(1)

    # Folder structure creation
    if not os.path.isdir(experiment_output_folder):
        os.mkdir(experiment_output_folder)

    if not os.path.isdir(questions_output_folder):
        os.mkdir(questions_output_folder)

    # Save arguments
    save_arguments(args, f"{experiment_output_folder}/arguments", f"produce_scenes_audio_{args.set_type}.args")

    question_file_exist = os.path.isfile(questions_output_filepath)
    if question_file_exist and args.clear_existing_files:
        os.remove(questions_output_filepath)
    elif question_file_exist:
        assert False, "This experiment have already been run. Please bump the version number or delete the previous output."

    # Create tmp folder to store questions (separated in small files)
    if not os.path.isdir(tmp_output_folder):
        os.mkdir(tmp_output_folder)
    elif args.clear_existing_files:
        rm_dir(tmp_output_folder)
        os.mkdir(tmp_output_folder)
    else:
        assert False, "Directory %s already exist. Please change the experiment name" % tmp_output_folder

    # Load templates, scenes, metadata and synonyms from file
    scenes, scene_info = load_scenes(scene_filepath, args.scene_start_idx, args.num_scenes)
    metadata = load_and_prepare_metadata(args.metadata_file, scenes)
    templates = load_and_prepare_templates(args.template_dir, metadata)
    synonyms = load_synonyms(args.synonyms_json)

    # Create question info section
    questions_info = generate_info_section(args.set_type, args.output_version_nb)

    # Start question generation
    generate_and_write_questions_to_file(scenes,
                                         templates,
                                         metadata,
                                         synonyms,
                                         questions_info,
                                         tmp_output_folder,
                                         questions_filename)

    write_possible_attributes(metadata, os.path.join(experiment_output_folder, 'attributes.json'))

    print(">> Questions generation done !")
    print(">> Questions have been written in multiple files in '%s'." % tmp_output_folder)
    print(">> Run ./scripts/consolidate_questions.py to merge them into one file.")


if __name__ == '__main__':
    args = parser.parse_args()
    main(args)
