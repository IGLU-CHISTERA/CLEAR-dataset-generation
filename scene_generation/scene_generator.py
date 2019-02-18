import ujson
import random
from shutil import rmtree as rm_dir
import time
import argparse
from itertools import groupby
import os, sys
from collections import defaultdict

from timbral_models import *
from utils.misc import init_random_seed
from scene_generation.elementary_sounds import Elementary_Sounds


"""
Arguments definition
"""
parser = argparse.ArgumentParser(fromfile_prefix_chars='@')

# TODO : Remove unused params

parser.add_argument('--max_nb_scene', default=None, type=int,
                    help='Maximum number of scenes that will be generated.' +
                         'Depending on the scene_length and tree_width, the number of scene generated may be lower.')

parser.add_argument('--scene_length', default=6, type=int,
                    help='Number of elementary sounds in the generated scenes')

parser.add_argument('--tree_width', default=5, type=int,
                    help='Number of node explored at each level of the generation tree')

parser.add_argument('--silence_padding_per_object', default=100, type=int,
                    help='Silence length that will be introduced between the objects')

parser.add_argument('--constraint_min_nb_families', default=3, type=int,
                    help='Minimum number of instrument families required for the scene to be valid')

parser.add_argument('--constraint_min_object_per_family', default=2, type=int,
                    help='Minimum number of object per question family')

parser.add_argument('--constraint_min_nb_families_subject_to_min_object_per_family', default=2, type=int,
                    help='Minimum number of families that must meet the "min_object_per_family" constraint')

parser.add_argument('--constraint_min_ratio_for_attribute', default=0.15, type=float,
                    help='Each scene must contain at least X% of all the values for each attributes')

parser.add_argument('--training_set_ratio', default=0.7, type=float,
                    help='Percentage of generated scenes that are labeled as training.' +
                         'Validation and test sets will contain the rest of the scenes')

parser.add_argument('--random_nb_generator_seed', default=None, type=int,
                    help='Set the random number generator seed to reproduce results')

parser.add_argument('--elementary_sounds_folder', default='../elementary_sounds',
                    help='Folder containing all the elementary sounds and the JSON listing them')

parser.add_argument('--elementary_sounds_definition_filename', default='elementary_sounds.json',
                    help='Filename of the JSON file listing the attributes of the elementary sounds')

parser.add_argument('--metadata_file', default='../metadata.json',
                    help='File containing all the information related to the possible attributes of the objects')

parser.add_argument('--output_folder', default='../output',
                    help='Folder where the generated scenes will be saved')

parser.add_argument('--output_filename_prefix', default='CLEAR', type=str,
                    help='Prefix used for generated scene file')

parser.add_argument('--output_version_nb', default='0.1', type=str,
                    help='Version number that will be appended to the generated scene file')

parser.add_argument('--clear_existing_files', action='store_true',
                    help='If set, will delete all files in the output folder before starting the generation.')


class Scene_generator:
    # TODO : Rewrite doc string
    """
    Scene generation logic.
    Create a tree of depth 'nb_objects_per_scene' and width 'nb_tree_branch'.
    Each node represent a elementary sound. The tree is instantiated Depth first.
    A scene is composed by taking a end node and going back up until we reach the root node.
    Validation is done at every node insertion in order to remove the combinations that do not respect the constraints.
    """
    def __init__(self, nb_objects_per_scene,
                 nb_tree_branch,
                 silence_padding_per_object,
                 elementary_sounds_folderpath,
                 elementary_sounds_definition_filename,
                 metadata_filepath,
                 version_nb,
                 additional_scenes_multiplier,          # FIXME : Ugly name.. i'm tired..
                 constraint_min_nb_families,
                 constraint_min_objects_per_family,
                 constraint_min_nb_families_subject_to_min_object_per_family,
                 constraint_min_ratio_for_attribute):

        self.nb_objects_per_scene = nb_objects_per_scene

        self.nb_tree_branch = nb_tree_branch

        self.version_nb = version_nb

        self.additional_scenes_multiplier = additional_scenes_multiplier

        with open(metadata_filepath) as metadata:
            self.attributes_values = {key: val['values'] for key, val in ujson.load(metadata)['attributes'].items()}

        self.elementary_sounds = Elementary_Sounds(elementary_sounds_folderpath, elementary_sounds_definition_filename, nb_objects_per_scene)

        # Since the sounds can't repeat themselves in the same scene,
        # The longest scene is the sum of the X longest elementary sounds + some silence padding
        # Where X is the number of objects in the scene
        # Plus the silence
        self.scene_duration = sum(self.elementary_sounds.longest_durations) + silence_padding_per_object * (nb_objects_per_scene + 1)

        # Constraints
        # TODO : Calculate constraints based on nb_object_per_scene ?
        self.constraints = {
            'min_nb_families': constraint_min_nb_families,
            'min_objects_per_family': constraint_min_objects_per_family,
            'min_nb_families_subject_to_min_objects_per_family': constraint_min_nb_families_subject_to_min_object_per_family,
            'min_ratio_for_attribute': constraint_min_ratio_for_attribute
        }

        self.constrained_attributes = ['brightness', 'loudness']     # Attributes on which the 'min_ratio_for_attribute' constraint will be applied

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
        # Shuffling sounds id
        np.random.shuffle(self.elementary_sounds.id_list_shuffled)

        # TODO : Random chance to take different interval than the first NB_Object ? Add more randomness. Necessary ?

        return self.elementary_sounds.id_list_shuffled[:self.nb_objects_per_scene]

    def _validate_scene(self, scene_objects):

        # Validate duration constraint
        total_sound_duration = sum([s['duration'] for s in scene_objects])

        if total_sound_duration >= self.scene_duration:
            return False

        # Validate min_nb_families constraint
        families_count, current_nb_families = self.elementary_sounds.sounds_to_families_count(scene_objects)

        if current_nb_families < self.constraints['min_nb_families']:
            return False

        # Validate that we have the minimum objects per families
        valid_families_count = 0

        for family, count in families_count.items():
            if count >= self.constraints['min_objects_per_family']:
                valid_families_count += 1

        if valid_families_count < self.constraints['min_nb_families_subject_to_min_objects_per_family']:
            return False

        # Validate the attributes distribution
        for constrained_attribute in self.constrained_attributes:
            # Group by the constrained attribute
            groups = {}
            for key, group in groupby(scene_objects, lambda x: x[constrained_attribute]):
                if key not in groups:
                    groups[key] = []
                groups[key] += list(group)

            # Validate distribution
            distribution = [len(group) / self.nb_objects_per_scene for group in groups.values()]

            # FIXME : Having trouble to make this work for both loudness and pitch (Can take 2 or 3 different values)
            # FIXME : Should we really discard if a value is missing ? Still got 30% of the levels to go at this point.
            if min(distribution) <= self.constraints['min_ratio_for_attribute'] or len(distribution) < len(self.attributes_values[constrained_attribute]):
                return False

        return True

    def _generate_scenes(self, start_index, nb_to_generate):

        # TODO : Generate more scenes than necessary and keep only nb_to_generate ? Add more variability

        processed_ids = defaultdict(lambda: False)
        valid_ids = defaultdict(lambda: False)
        scenes_objects = []
        counter = 0

        # Stats
        duplicate_processing = 0
        duplicate_validation = 0
        invalid = 0

        while counter < nb_to_generate:
            scene_id_list = self._generate_scene_id_list()
            hashmap_index = str(scene_id_list)
            scene_objects = self._scene_id_list_to_sound_list(scene_id_list)


            # TODO : Remove duplicate stats
            if not processed_ids[hashmap_index]:
                processed_ids[hashmap_index] = True
                if not valid_ids[hashmap_index] :
                    if self._validate_scene(scene_objects):
                        valid_ids[hashmap_index] = True
                        scenes_objects.append(scene_objects)            # TODO : Make sure this is not to memory hungry. We could also use the keys of preprocessed_ids
                        counter += 1
                    else:
                        invalid += 1
                else:
                    duplicate_validation += 1
            else:
                duplicate_processing += 1

        return scenes_objects

    def _assign_silence_informations(self, scene):
        sounds_duration = sum(sound['duration'] for sound in scene)

        full_padding_duration = self.scene_duration - sounds_duration

        nb_sound = len(scene)

        # Initialize equal silences
        silence_intervals = [full_padding_duration/nb_sound] * nb_sound

        # Randomly modify the silence intervals
        for i in range(nb_sound):
          # Randomly choose a sound
          random_index = random.randint(0, nb_sound-1)
          if silence_intervals[random_index] > 0:
            # Take between 10% and 70% of the silence portion of one sound and add it to another sound
            silence_portion = int(silence_intervals[random_index] * random.randint(10, 70)/100)
            silence_intervals[i] += silence_portion
            silence_intervals[random_index] -= silence_portion

        padded = 0
        scene_reversed = False

        # FIXME : Doing this made sense with the old approach. Now it doesn't really change anything..
        # Reverse the scene order with a probability of 50%
        # This add more randomness to the silence attribution
        if random.random() > 0.5:
          scene.reverse()
          scene_reversed = True

        for i, sound in enumerate(scene):
          sound['silence_after'] = silence_intervals[i]
          padded += sound['silence_after']

        if scene_reversed:
          # Reverse back the scene to the original order
          scene.reverse()

        # The rest of the silence duration should be added in the beginning of the scene
        # We calculate the remaining padding this way to make sure that rounding doesn't affect the result
        return full_padding_duration - padded

    def _generate_info_section(self, set_type):
        return {
                "name": "CLEAR",
                "license": "Creative Commons Attribution (CC-BY 4.0)",
                "version": self.version_nb,
                "split": set_type,
                "date": time.strftime("%x")
            }

    def _generate_relationships(self, scene_composition):
        # FIXME : Those relationships are trivial. Could be moved to question engine (Before & after)
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

        scene_indexes = list(range(0, self.nb_objects_per_scene))

        for i in range(0, self.nb_objects_per_scene):
            if i - 1 >= 0:
                relationships[0]['indexes'].append(relationships[0]['indexes'][i - 1] + [i - 1])

            scene_indexes.remove(i)
            relationships[1]['indexes'].append(list(scene_indexes))

        return relationships

    def generate(self, start_index=0, nb_to_generate=None, training_set_ratio=0.7, shuffle_scenes=True):

        print("Starting Scenes Generation")

        generated_scenes = self._generate_scenes(start_index, nb_to_generate)

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
                scene['split'] = 'train'
                scene['image_index'] = training_index   # TODO : Change this key to "scene_index". Keeping image reference for simplicity
                scene['image_filename'] = "CLEAR_%s_%06d.png" % (scene['split'], training_index)
                training_index += 1
                training_scenes.append(scene)
            elif scene_count < nb_training + nb_valid:
                scene['split'] = 'val'
                scene['image_index'] = valid_index      # TODO : Change this key to "scene_index". Keeping image reference for simplicity
                scene['image_filename'] = "CLEAR_%s_%06d.png" % (scene['split'], valid_index)
                valid_index += 1
                valid_scenes.append(scene)
            else:
                scene['split'] = 'test'
                scene['image_index'] = test_index       # TODO : Change this key to "scene_index". Keeping image reference for simplicity
                scene['image_filename'] = "CLEAR_%s_%06d.png" % (scene['split'], test_index)
                test_index += 1
                test_scenes.append(scene)

            scene_count += 1

        return {
            "train" : {
                "info": self._generate_info_section('train'),
                "scenes": training_scenes
            },
            "val": {
                "info": self._generate_info_section('val'),
                "scenes": valid_scenes
            },
            "test": {
                "info": self._generate_info_section('test'),
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

    # Setting & Saving the random seed
    if args.random_nb_generator_seed is not None:
        init_random_seed(args.random_nb_generator_seed)
    else:
        print("The seed must be specified in the arguments.", file=sys.stderr)
        exit(1)

    scene_generator = Scene_generator(args.scene_length,
                                      args.tree_width,
                                      args.silence_padding_per_object,
                                      args.elementary_sounds_folder,
                                      args.elementary_sounds_definition_filename,
                                      args.metadata_file,
                                      args.output_version_nb,
                                      5,        # FIXME : Take as parameter
                                      args.constraint_min_nb_families,
                                      args.constraint_min_object_per_family,
                                      args.constraint_min_nb_families_subject_to_min_object_per_family,
                                      args.constraint_min_ratio_for_attribute)

    scenes = scene_generator.generate(nb_to_generate=args.max_nb_scene, training_set_ratio=args.training_set_ratio)

    # Write to file
    for set_type, scene_struct in scenes.items():
        scenes_filename = '%s_%s_scenes.json' % (args.output_filename_prefix, set_type)

        scenes_filepath = os.path.join(scenes_output_folder, scenes_filename)

        with open(scenes_filepath, 'w') as f:
            ujson.dump(scene_struct, f, sort_keys=True, escape_forward_slashes=False)

    print('done')
