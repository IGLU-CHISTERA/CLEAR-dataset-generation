# CLEAR Dataset
# >> Scene Generator
#
# Author :      Jerome Abdelnour
# Year :        2018-2019
# Affiliations: Universite de Sherbrooke - Electrical and Computer Engineering faculty
#               KTH Stockholm Royal Institute of Technology
#               IGLU - CHIST-ERA

import argparse, os, sys, random
from shutil import rmtree as rm_dir
from itertools import groupby
from collections import defaultdict

import ujson
import numpy as np

from utils.misc import init_random_seed, generate_info_section, save_arguments
from utils.elementary_sounds import Elementary_Sounds

# Arguments definition
parser = argparse.ArgumentParser(fromfile_prefix_chars='@')

# Input
parser.add_argument('--elementary_sounds_folder', default='./elementary_sounds',
                    help='Folder containing all the elementary sounds and the JSON listing them')
parser.add_argument('--elementary_sounds_definition_filename', default='elementary_sounds.json',
                    help='Filename of the JSON file listing the attributes of the elementary sounds')

parser.add_argument('--metadata_file', default='templates/attributes.json',
                    help='File containing all the information related to the possible attributes of the objects')

# Options
parser.add_argument('--min_scene_length', default=3, type=int,
                    help='Minimum number of elementary sounds in each scene')
parser.add_argument('--max_scene_length', default=10, type=int,
                    help='Maximum number of elementary sounds in each scene')
parser.add_argument('--nb_scene', default=None, type=int,
                    help='Number of scenes that will be generated.')

parser.add_argument('--silence_padding_per_object', default=100, type=int,
                    help='Silence length that will be introduced between the objects (in ms)')

# Constraints
parser.add_argument('--constraint_min_nb_families', default=3, type=int,
                    help='Minimum number of instrument families required for the scene to be valid')
parser.add_argument('--constraint_min_object_per_family', default=2, type=int,
                    help='Minimum number of object per question family')
parser.add_argument('--constraint_min_nb_families_subject_to_min_object_per_family', default=2, type=int,
                    help='Minimum number of families that must meet the "min_object_per_family" constraint')
parser.add_argument('--constraint_min_ratio_for_attribute', default=0.15, type=float,
                    help='Each scene must contain at least X%% of all the values for each attributes')

# Output
parser.add_argument('--training_set_ratio', default=0.7, type=float,
                    help='Percentage of generated scenes that are labeled as training.' +
                         'Validation and test sets will contain the rest of the scenes')
parser.add_argument('--output_folder', default='./output',
                    help='Folder where the generated scenes will be saved')
parser.add_argument('--output_filename_prefix', default='CLEAR', type=str,
                    help='Prefix used for generated scene file')
parser.add_argument('--output_version_nb', default='0.1', type=str,
                    help='Version number that will be appended to the generated scene file')
parser.add_argument('--clear_existing_files', action='store_true',
                    help='If set, will delete all files in the output folder before starting the generation.')

# Misc
parser.add_argument('--random_nb_generator_seed', default=None, type=int,
                    help='Set the random number generator seed to reproduce results')


class Scene_generator:
    """
    Scene generation logic.
    Will load all sounds in {elementary_sounds_folder} and randomly sample {scene_length} sounds from the whole set.
    The chosen sounds will be submitted to various constraints (See arguments definition for more information).
    If the scene satisfy the constraints, it will be added to the generated scenes up until we got {max_nb_scene}.

    The generated scenes will be splitted in 3 sets (training, validation, test) according to {training_set_ratio}.
    The rest of the scenes will be evenly splitted into validation and test sets.
    """
    def __init__(self, min_nb_objects_per_scene,
                 max_nb_objects_per_scene,
                 silence_padding_per_object,
                 elementary_sounds_folderpath,
                 elementary_sounds_definition_filename,
                 metadata_filepath,
                 version_nb,
                 constraint_min_nb_families,
                 constraint_min_objects_per_family,
                 constraint_min_nb_families_subject_to_min_object_per_family,
                 constraint_min_ratio_for_attribute):

        self.version_nb = version_nb

        with open(metadata_filepath) as metadata:
            self.attributes_values = {key: val['values'] for key, val in ujson.load(metadata)['attributes'].items()}

        self.elementary_sounds = Elementary_Sounds(elementary_sounds_folderpath, elementary_sounds_definition_filename)

        self.nb_objects_per_scene = {
            'min': min_nb_objects_per_scene,
            'max': max_nb_objects_per_scene
        }

        get_duration = lambda n: self.elementary_sounds.half_longest_durations_mean*n + silence_padding_per_object*(n+1)
        self.scene_duration = {
            'min': int(get_duration(self.nb_objects_per_scene['min'])),
            'max': int(get_duration(self.nb_objects_per_scene['max']))
        }

        self.silence_padding_per_object = silence_padding_per_object

        # Constraints
        self.constraints = {
            'min_nb_families': constraint_min_nb_families,
            'min_objects_per_family': constraint_min_objects_per_family,
            'min_nb_families_subject_to_min_objects_per_family': constraint_min_nb_families_subject_to_min_object_per_family,
            'min_ratio_for_attribute': constraint_min_ratio_for_attribute
        }

        # Attributes on which the 'min_ratio_for_attribute' constraint will be applied
        self.constrained_attributes = ['brightness', 'loudness']

        # Stats
        self.stats = {
            'levels': {},
            'nbValid': 0,
            'nbMissingFamilies': 0,
            'nbMissingObjectPerFam': 0,
            'attribute_constraint': {}
        }

    def _scene_id_list_to_sound_list(self, scene_id_list):
        return [self.elementary_sounds.definition[idx] for idx in scene_id_list]

    def _generate_scene_id_list(self):
        # Shuffle all sounds and pick the first 'nb_objects_per_scene' as the scene
        np.random.shuffle(self.elementary_sounds.id_list_shuffled)

        nb_sound = np.random.randint(self.nb_objects_per_scene['min'], self.nb_objects_per_scene['max'] + 1)

        return self.elementary_sounds.id_list_shuffled[:nb_sound]

    def _validate_scene(self, scene_objects):
        nb_object_in_scene = len(scene_objects)

        # Validate duration constraint
        total_sound_duration = sum([s['duration'] for s in scene_objects])

        if self.scene_duration['min'] <= total_sound_duration >= self.scene_duration['max']:
            return False

        # Validate min_nb_families constraint
        families_count, current_nb_families = self.elementary_sounds.sounds_to_families_count(scene_objects)

        if current_nb_families < self.constraints['min_nb_families']:
            return False

        # Validate that we have the minimum objects per families
        valid_families_count = sum([1 for family, count in families_count.items()
                                    if count >= self.constraints['min_objects_per_family']])

        if valid_families_count < self.constraints['min_nb_families_subject_to_min_objects_per_family']:
            return False

        # Validate the attributes distribution
        for constrained_attribute in self.constrained_attributes:
            # Group by the constrained attribute
            groups = defaultdict(lambda : [])

            for scene_object in scene_objects:
                attribute = scene_object[constrained_attribute]

                groups[attribute].append(scene_object)

            # Must have at least 1 occurence of each attribute (Without counting None values)
            nb_vals_except_none = len(set(groups.keys()) - {None})
            if nb_vals_except_none < len(self.attributes_values[constrained_attribute]):
                return False

            # Verify that the frequencies validate the constraints
            for key, group in groups.items():
                if len(group)/nb_object_in_scene <= self.constraints['min_ratio_for_attribute']:     # FIXME : nb_object
                    return False

        return True

    def _generate_scenes(self, nb_to_generate):
        processed_ids = defaultdict(lambda: False)
        valid_ids = defaultdict(lambda: False)
        scenes = []
        counter = 0

        while counter < nb_to_generate:
            scene_id_list = self._generate_scene_id_list()
            hashmap_index = str(scene_id_list)
            scene_objects = self._scene_id_list_to_sound_list(scene_id_list)

            if not processed_ids[hashmap_index]:
                processed_ids[hashmap_index] = True
                if not valid_ids[hashmap_index]:
                    if self._validate_scene(scene_objects):
                        valid_ids[hashmap_index] = True
                        scenes.append(scene_objects)
                        counter += 1

        return scenes

    def _assign_silence_informations(self, scene):
        nb_sound = len(scene)
        sounds_duration = sum(sound['duration'] for sound in scene)

        # Add between 5% and 20% of the sound duration as silence padding
        full_padding_duration = self.silence_padding_per_object*nb_sound + sounds_duration * random.randint(5, 20)/100

        # Initialize equal silences
        silence_intervals = [int((full_padding_duration * random.randint(80, 99)/100)/nb_sound) for i in range(nb_sound)]

        # Randomly modify the silence intervals
        for i in range(nb_sound):

          # Randomly choose a sound
          random_index = random.randint(0, nb_sound - 1)
          while random_index == i:
            random_index = random.randint(0, nb_sound - 1)

          if silence_intervals[random_index] > 0:
            # Take between 10% and 50% of the silence portion of one sound and add it to another sound
            silence_portion = int(silence_intervals[random_index] * random.randint(1, 50)/100)
            silence_intervals[i] += silence_portion
            silence_intervals[random_index] -= silence_portion

        random.shuffle(silence_intervals)

        for i, sound in enumerate(scene):
          sound['silence_after'] = silence_intervals[i]

        # The rest of the silence duration should be added in the beginning of the scene
        silence_before = int(full_padding_duration - sum(silence_intervals))

        return silence_before

    def _generate_relationships(self, scene_composition):
        # TODO : Those relationships are trivial. Could be moved to question engine (Before & after)
        relationships = [
            {
                'type': 'before',
                'indexes': [
                    []
                ]
            },
            {
                'type': 'after',
                'indexes': []
            }
        ]

        nb_object = len(scene_composition)
        scene_indexes = list(range(0, nb_object))   # NOTE : Would not work with variable scene length

        for i in range(0, nb_object):
            if i - 1 >= 0:
                relationships[0]['indexes'].append(relationships[0]['indexes'][i - 1] + [i - 1])

            scene_indexes.remove(i)
            relationships[1]['indexes'].append(list(scene_indexes))

        return relationships

    def generate(self, nb_to_generate, training_set_ratio=0.7, shuffle_scenes=True):

        print("Starting Scenes Generation")

        generated_scenes = self._generate_scenes(nb_to_generate)

        print("Generated %d scenes" % len(generated_scenes))

        if shuffle_scenes:
            np.random.shuffle(generated_scenes)

        # Separating train, valid and test sets
        nb_scene = len(generated_scenes)
        nb_training = round(nb_scene*training_set_ratio)
        valid_and_test_ratio = (1.0 - training_set_ratio) / 2
        nb_valid = round(nb_scene*valid_and_test_ratio)
        nb_test = nb_scene - nb_training - nb_valid

        training_scenes = []
        valid_scenes = []
        test_scenes = []

        training_index = 0
        valid_index = 0
        test_index = 0

        scene_count = 0
        for generated_scene in generated_scenes:
            silence_before = self._assign_silence_informations(generated_scene)

            scene = {
                "silence_before": silence_before,
                "objects": generated_scene,
                "relationships": self._generate_relationships(generated_scene)
            }

            if scene_count < nb_training:
                scene['scene_index'] = '%.6d' % training_index
                scene['scene_filename'] = "CLEAR_train_%06d.wav" % training_index
                training_index += 1
                training_scenes.append(scene)

            elif scene_count < nb_training + nb_valid:
                scene['scene_index'] = '%.6d' % valid_index
                scene['scene_filename'] = "CLEAR_val_%06d.wav" % valid_index
                valid_index += 1
                valid_scenes.append(scene)

            else:
                scene['scene_index'] = '%.6d' % test_index
                scene['scene_filename'] = "CLEAR_test_%06d.wav" % test_index
                test_index += 1
                test_scenes.append(scene)

            scene_count += 1

        return {
            "train" : {
                "info": generate_info_section('train', self.version_nb),
                "scenes": training_scenes
            },
            "val": {
                "info": generate_info_section('val', self.version_nb),
                "scenes": valid_scenes
            },
            "test": {
                "info": generate_info_section('test', self.version_nb),
                "scenes": test_scenes
            }
        }


if __name__ == '__main__':
    args = parser.parse_args()

    experiment_output_folder = os.path.join(args.output_folder, args.output_version_nb)
    scenes_output_folder = os.path.join(experiment_output_folder, 'scenes')

    if not os.path.isdir(experiment_output_folder):
        os.mkdir(experiment_output_folder)

    if not os.path.isdir(scenes_output_folder):
        os.mkdir(scenes_output_folder)
    elif args.clear_existing_files:
        rm_dir(scenes_output_folder)
        os.mkdir(scenes_output_folder)
    else:
        print("This experiment have already been run. Please bump the version number or delete the previous output.",
            file=sys.stderr)
        exit(1)
        # Save arguments
        save_arguments(args, f"{args.output_folder}/{args.output_version_nb}/arguments",
                       'generate_scenes_definition.args')

    # Setting & Saving the random seed
    if args.random_nb_generator_seed is not None:
        init_random_seed(args.random_nb_generator_seed)
    else:
        print("The seed must be specified in the arguments.", file=sys.stderr)
        exit(1)

    scene_generator = Scene_generator(args.min_scene_length,
                                      args.max_scene_length,
                                      args.silence_padding_per_object,
                                      args.elementary_sounds_folder,
                                      args.elementary_sounds_definition_filename,
                                      args.metadata_file,
                                      args.output_version_nb,
                                      args.constraint_min_nb_families,
                                      args.constraint_min_object_per_family,
                                      args.constraint_min_nb_families_subject_to_min_object_per_family,
                                      args.constraint_min_ratio_for_attribute)

    scenes = scene_generator.generate(nb_to_generate=args.nb_scene, training_set_ratio=args.training_set_ratio)

    # Write to file
    for set_type, scene_struct in scenes.items():
        scenes_filename = '%s_%s_scenes.json' % (args.output_filename_prefix, set_type)

        scenes_filepath = os.path.join(scenes_output_folder, scenes_filename)

        with open(scenes_filepath, 'w') as f:
            ujson.dump(scene_struct, f, indent=2, sort_keys=True, escape_forward_slashes=False)

    print('done')
