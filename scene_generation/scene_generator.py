from pydub import AudioSegment
import copy
import ujson
import random
import time
import argparse
from itertools import groupby
import os, sys
from collections import defaultdict

from timbral_models import *

from utils.perceptual_loudness import get_perceptual_loudness


"""
Arguments definition
"""
parser = argparse.ArgumentParser(fromfile_prefix_chars='@')

parser.add_argument('--max_nb_scene', default=None, type=int,
                    help='Maximum number of scenes that will be generated.' +
                         'Depending on the scene_length and tree_width, the number of scene generated may be lower.')

parser.add_argument('--scene_length', default=6, type=int,
                    help='Number of primary sounds in the generated scenes')

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

parser.add_argument('--primary_sounds_folder', default='../primary_sounds',
                    help='Folder containing all the primary sounds and the JSON listing them')

parser.add_argument('--primary_sounds_definition_filename', default='primary_sounds.json',
                    help='Filename of the JSON file listing the attributes of the primary sounds')

parser.add_argument('--metadata_file', default='../metadata.json',
                    help='File containing all the information related to the possible attributes of the objects')

parser.add_argument('--output_folder', default='../output',
                    help='Folder where the generated scenes will be saved')

parser.add_argument('--output_filename_prefix', default='AQA', type=str,
                    help='Prefix used for generated scene file')

parser.add_argument('--output_version_nb', default='0.1', type=str,
                    help='Version number that will be appended to the generated scene file')


class Node:
    """
    Node object used in tree generation
    """
    def __init__(self, parent, level, sound, overlapping_last=False):
        self.childs = []
        self.level = level
        self.sound = sound
        self.overlapping_last = overlapping_last
        self.parent = parent

    def add_child(self, sound):
        new_child = Node(self, self.level+1, sound)
        self.childs.append(new_child)
        return new_child

    def get_childs_ids(self):
        return [child.sound['id'] for child in self.childs]

    def get_childs_definitions(self):
        return [child.sound for child in self.childs]


class Primary_sounds:
    """
    Primary sounds generator.
    Load the primary sounds from file, preprocess them and give an interface to retrieve sounds
    """
    def __init__(self, folder_path, definition_filename, nb_objects_per_scene):
        print("Loading Elementary sounds")
        self.folderpath = folder_path

        with open(os.path.join(self.folderpath, definition_filename)) as primary_sounds_definition:
            self.definition = ujson.load(primary_sounds_definition)

        self.notes = [ 'C', 'Db', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B' ]

        self.longest_durations = []

        self.nb_sounds = len(self.definition)

        self._preprocess_sounds(nb_objects_per_scene)

        self.families_count = {}

        for sound in self.definition:
            if sound['instrument'] not in self.families_count:
                self.families_count[sound['instrument']] = 1
            else:
                self.families_count[sound['instrument']] += 1

        self.families = self.families_count.keys()
        self.nb_families = len(self.families)

        self.generated_count_by_index = {i: 0 for i in range(self.nb_sounds)}
        self.generated_count_by_families = {fam: 0 for fam in self.families}
        self.gen_index = 0

    def _midi_to_note(self, midi_value):
        return self.notes[midi_value % 12]

    def _preprocess_sounds(self, nb_objects_per_scene, shuffle_primary_sounds=True):

        if shuffle_primary_sounds:
            random.shuffle(self.definition)

        # Store max and min brightness for each instrument. Used for brightness normalization
        brightness_per_instrument = defaultdict(lambda: {'max': 0, 'min': 9999})

        for id, primary_sound in enumerate(self.definition):
            primary_sound_filename = os.path.join(self.folderpath, primary_sound['filename'])
            primary_sound_audiosegment = AudioSegment.from_wav(primary_sound_filename)

            primary_sound['id'] = id

            primary_sound['duration'] = int(primary_sound_audiosegment.duration_seconds * 1000)

            # FIXME : The perceptual loudness threshold should not be hardcoded
            perceptual_loudness = get_perceptual_loudness(primary_sound_audiosegment)
            primary_sound['loudness'] = 'quiet' if perceptual_loudness < -27 else 'loud'

            self.longest_durations.append(primary_sound['duration'])

            primary_sound['int_brightness'] = timbral_brightness(primary_sound_filename)

            if primary_sound['int_brightness'] > brightness_per_instrument[primary_sound['instrument']]['max']:
                brightness_per_instrument[primary_sound['instrument']]['max'] = primary_sound['int_brightness']
            elif primary_sound['int_brightness'] < brightness_per_instrument[primary_sound['instrument']]['min']:
                brightness_per_instrument[primary_sound['instrument']]['min'] = primary_sound['int_brightness']

        # Normalize the brightness per instrument and assign the brightness label
        for id, primary_sound in enumerate(self.definition):
          max_brightness = brightness_per_instrument[primary_sound['instrument']]['max']
          min_brightness = brightness_per_instrument[primary_sound['instrument']]['min']
          cur_brightness = primary_sound['int_brightness']

          # Normalize brightness per instrument
          primary_sound['rel_brightness'] = (cur_brightness - min_brightness) / (max_brightness - min_brightness)

          # Assign brightness label
          if primary_sound['rel_brightness'] > 0.6:     # FIXME : The brightness threshold should not be hardcoded
            primary_sound['brightness'] = 'bright'
          elif primary_sound['rel_brightness'] < 0.4:   # FIXME : The brightness threshold should not be hardcoded
            primary_sound['brightness'] = 'dark'
          else:
            primary_sound['brightness'] = None

          # Cleanup unused properties
          del primary_sound['int_brightness']
          del primary_sound['rel_brightness']

        # Remove the 20% longest sounds.
        # Use the sum of the duration of the next 'nb_objects_per_scene' as the scene total duration
        twenty_percent_index = int(self.nb_sounds * 0.20)
        sorted_durations = sorted(self.longest_durations, reverse=True)
        self.longest_durations = sorted_durations[twenty_percent_index:twenty_percent_index+nb_objects_per_scene]

    def sounds_to_families_count(self, sound_list):
        count = {}

        for sound in sound_list:
            family = sound['instrument']
            if family in count:
                count[family] += 1
            else:
                count[family] = 1

        non_empty_families = count.keys()
        non_empty_families_count = len(non_empty_families)

        empty_families = set(self.families) - set(non_empty_families)
        for family in empty_families:
            count[family] = 0

        return count, non_empty_families_count

    def get(self, index):
        return self.definition[index]

    def next(self, state, siblings_ids):
        # TODO : Do some checking based on the state to minimize same items (Instead of handling it later on in scenes constraints)
        # TODO : Try to minimize the reuse of the same sound (Even same category sound ?)
        #self.gen_index = (self.gen_index + 1) % self.nb_sounds
        self.gen_index = random.randint(0, self.nb_sounds - 1)

        state_ids = [s['id'] for s in state]

        state_and_siblings = list(set(state_ids + siblings_ids))

        # Prevent from using a sound that is already in the state or is another child of the parent node
        while self.gen_index in state_and_siblings:
            self.gen_index = random.randint(0, self.nb_sounds - 1)

        # TODO : Do something with this information
        # Keeping track of the nb of occurence
        self.generated_count_by_index[self.gen_index] += 1
        self.generated_count_by_families[self.definition[self.gen_index]['instrument']] += 1

        return copy.deepcopy(self.definition[self.gen_index])


class Scene_generator:
    """
    Scene generation logic.
    Create a tree of depth 'nb_objects_per_scene' and width 'nb_tree_branch'.
    Each node represent a primary sound. The tree is instantiated Depth first.
    A scene is composed by taking a end node and going back up until we reach the root node.
    Validation is done at every node insertion in order to remove the combinations that do not respect the constraints.
    """
    def __init__(self, nb_objects_per_scene,
                 nb_tree_branch,
                 silence_padding_per_object,
                 primary_sounds_folderpath,
                 primary_sounds_definition_filename,
                 metadata_filepath,
                 version_nb,
                 constraint_min_nb_families,
                 constraint_min_objects_per_family,
                 constraint_min_nb_families_subject_to_min_object_per_family,
                 constraint_min_ratio_for_attribute):

        self.nb_objects_per_scene = nb_objects_per_scene

        self.nb_tree_branch = nb_tree_branch

        self.version_nb = version_nb

        with open(metadata_filepath) as metadata:
            self.attributes_values = {key: val['values'] for key, val in ujson.load(metadata)['attributes'].items()}

        self.primary_sounds = Primary_sounds(primary_sounds_folderpath, primary_sounds_definition_filename, nb_objects_per_scene)

        # Since the sounds can't repeat themselves in the same scene,
        # The longest scene is the sum of the X longest primary sounds.
        # Where X is the number of objects in the scene
        # Plus the silence
        self.scene_duration = sum(self.primary_sounds.longest_durations) + silence_padding_per_object * (nb_objects_per_scene + 1)

        # Constraints
        # TODO : Calculate constraints based on nb_object_per_scene ?
        self.constraints = {
            'min_nb_families': constraint_min_nb_families,
            'min_objects_per_family': constraint_min_objects_per_family,
            'min_nb_families_subject_to_min_objects_per_family': constraint_min_nb_families_subject_to_min_object_per_family,
            'min_ratio_for_attribute': constraint_min_ratio_for_attribute
        }

        self.constrained_attributes = ['brightness', 'loudness']     # Attributes on which the 'min_ratio_for_attribute' constraint will be applied

    def validate_final(self, state):
        # TODO : Validate final state before adding this scene to the repository
        # TODO : Validate all the constraints ? (Maybe not necessary to reverify the intermediate)
        # TODO : Constraints :
        # TODO :        - X differents instrument families
        # TODO :        - X uniquely filterable objects for {set} of attributes
        # TODO :        - X objects per instrument families. For at least X instument families
        # TODO :        - SOME CONSTRAINTS ON OVERLAPPING

        total_sound_duration = sum([s['duration'] for s in state])

        if total_sound_duration >= self.scene_duration:
          return False

        # Validate that we have enough instrument families
        families_count, nb_families = self.primary_sounds.sounds_to_families_count(state)
        if nb_families < self.constraints['min_nb_families']:
            print("Constraint NB_FAMILY not met")
            return False

        # Validate that we have enough objects per instrument families
        nb_families_meet_requirements = 0
        for count in families_count.values():
            if count >= self.constraints['min_objects_per_family']:
                nb_families_meet_requirements += 1

            # FIXME : Is this really usefull ? We save couple of iteration to the expense of a if every iteration
            if nb_families_meet_requirements >= self.constraints['min_nb_families_subject_to_min_objects_per_family']:
                break

        if nb_families_meet_requirements < self.constraints['min_nb_families_subject_to_min_objects_per_family']:
            print("Constraint NB_OBJECT_PER_FAMILIES not met")
            return False

        return True

    def validate_intermediate(self, state, current_level):
        # TODO : Validate intermediate state. The handling should be different depending on the level
        # TODO : Based on the current composition and the current level, we can calculate the probability that an eventual branch respect all the constraints
        # TODO :    EX :  We need 3 different instrument families. We are at level 3 on 4 and we only have <guitar> sounds. Its impossible to satisfy the constraint with the remaining branches

        # TODO : Only validate if we have more than XXX level to go ?? No need to validate if we are on the 1/4 of the scene composition
        nb_level_to_go = self.nb_objects_per_scene - current_level - 1
        families_count, current_nb_families = self.primary_sounds.sounds_to_families_count(state)

        # CONSTRAINT VALIDATION : min_nb_families
        if current_nb_families < self.constraints['min_nb_families']:
            missing_nb_families = self.constraints['min_nb_families'] - current_nb_families

            # TODO : Calculate prob that we will reach valid combination

            if missing_nb_families > nb_level_to_go:
                if current_level not in self.stats['levels']:
                    self.stats['levels'][current_level] = 1
                else:
                    self.stats['levels'][current_level] += 1
                print("Intermediate constraint not met. %d levels to go and %d missing families" % (nb_level_to_go, missing_nb_families))
                return False

        # CONSTRAINT VALIDATION : min_objects_per_family && min_nb_families_subject_to_min_objects_per_family
        validated_families = {
            'valid': [],
            'invalid': []
        }
        for family, count in families_count.items():
            if count >= self.constraints['min_objects_per_family']:
                validation_status = 'valid'
            else:
                validation_status = 'invalid'
            validated_families[validation_status].append((family, count))

        nb_valid_families = len(validated_families['valid'])
        nb_missing_families = self.constraints['min_nb_families_subject_to_min_objects_per_family'] - nb_valid_families

        # TODO : Calculate probability

        if nb_missing_families > nb_level_to_go:
            self.stats['nbMissingFamilies'] += 1
            if current_level not in self.stats['levels']:
                self.stats['levels'][current_level] = 1
            else:
                self.stats['levels'][current_level] += 1
            return False
        else:
            # Calculating the probability that this tree will lead to a valid combination
            if nb_missing_families * self.constraints['min_objects_per_family'] > nb_level_to_go:
                self.stats['nbMissingObjectPerFam'] += 1
                if current_level not in self.stats['levels']:
                    self.stats['levels'][current_level] = 1
                else:
                    self.stats['levels'][current_level] += 1
                return False

            # TODO : Probabilist approach
            '''
            prob = 0
            for (family, count) in validated_families['invalid']:
                nb_other_sounds_same_family = self.primary_sounds.families_count[family] - count
                nb_missing_sounds = self.constraints['min_objects_per_family'] - count

                prob += (nb_other_sounds_same_family/self.primary_sounds.nb_sounds ** nb_missing_sounds) * (((self.primary_sounds.nb_sounds - nb_missing_sounds)/self.primary_sounds.nb_sounds) ** (nb_level_to_go - nb_missing_sounds))

            print("Prob is %f" %prob)
            if prob < 0.2:
                self.stats['nbMissingObjectPerFam'] += 1
                if current_level not in self.stats['levels']:
                    self.stats['levels'][current_level] = 1
                else:
                    self.stats['levels'][current_level] += 1
                return False
            '''

        # CONSTRAINT VALIDATION : attribute_distribution_min
        if nb_level_to_go <= round(self.constraints['min_ratio_for_attribute']*self.nb_objects_per_scene):

            for constrained_attribute in self.constrained_attributes:
                # Group by the constrained attribute
                groups = {}
                for key, group in groupby(state, lambda x: x[constrained_attribute]):
                    if key not in groups:
                        groups[key] = []
                    groups[key] += list(group)

                # Validate distribution
                distribution = [len(group)/self.nb_objects_per_scene for group in groups.values()]

                # FIXME : Having trouble to make this work for both loudness and pitch (Can take 2 or 3 different values)
                # FIXME : Should we really discard if a value is missing ? Still got 30% of the levels to go at this point.
                if min(distribution) <= self.constraints['min_ratio_for_attribute'] or len(distribution) < len(self.attributes_values[constrained_attribute]):
                    if current_level not in self.stats['attribute_constraint']:
                        self.stats['attribute_constraint'][current_level] = 1
                    else:
                        self.stats['attribute_constraint'][current_level] += 1
                    return False

        return True

    def _get_random_loudness(self):
        high_bound = len(self.attributes_values['loudness']) - 1

        return self.attributes_values['loudness'][random.randint(0, high_bound)]

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

    def _generate_scenes(self, start_index= 0, nb_to_generate=None, root_node=None):
        if not root_node:
            # FIXME : The process won't include the root node in the scene composition. Will cause problem when distributing part of the tree in different processes
            root_node = Node(None, -1, {})      # Root of the tree

        next_node = root_node
        state = []
        generated_scenes = []

        # FIXME : Remove this, debugging purpose
        self.stats = {
            'levels' : {},
            'nbValid': 0,
            'nbMissingFamilies' : 0,
            'nbMissingObjectPerFam' : 0,
            'attribute_constraint' : {}
        }

        print("Starting Scenes Generation")

        continue_work = True

        while continue_work:
            current_node = next_node

            # Depth first instantiation of tree
            if current_node.level < self.nb_objects_per_scene - 1:
                # Not reached the bottom yet.

                if len(current_node.childs) < self.nb_tree_branch:
                    # Add a new child
                    new_sound = self.primary_sounds.next(state, current_node.get_childs_ids())

                    # Randomly assign a loudness level to the new sound
                    new_sound['loudness'] = self._get_random_loudness()

                    state.append(new_sound)
                    # TODO : random Chance of overlapping
                    next_node = current_node.add_child(new_sound)

                    if not self.validate_intermediate(state, next_node.level):
                        next_node = current_node
                        if len(state) > 0:
                            state.pop()
                else:
                    # Go up one level
                    next_node = current_node.parent
                    if next_node is None:
                        # We reached the root node. The tree has been completely instantiated
                        continue_work = False
                        break
                    elif len(state) > 0:            # FIXME : Unecessary check. If parent is not none then the state is not empty
                        state.pop()

            else:
                # Reached the bottom of the tree

                if self.validate_final(state):
                    # TODO : dump scene to file instead of creating a list of all scenes possible
                    # TODO : We can then collect all the file at the end of the process
                    # TODO : Do this in another process ? --> 1 process for tree instantiation that feed a mailbox and 1 process that empty the mailbox and write to file
                    scene_index = start_index

                    if nb_to_generate and scene_index >= nb_to_generate:
                        # Reached the limit of scene to generate,
                        continue_work = False
                        break
                    self.stats['nbValid'] += 1
                    start_index += 1

                    generated_scenes.append(copy.deepcopy(state))

                # Going up in the tree
                next_node = current_node.parent     # FIXME : This will fail in the case we have a depth of 1 because the None check is in the while (Not really a use cas.. we can ignore)
                state.pop()
                while len(next_node.childs) >= self.nb_tree_branch:
                    next_node = next_node.parent
                    if next_node is None:
                        # We reached the root node. The tree has been completely instantiated
                        continue_work = False
                        break
                    else:
                        # Update the state
                        state.pop()

        print("Nb valid : %d" % self.stats['nbValid'])
        print("Stats")
        print(ujson.dumps(self.stats, indent=4))
        cnt = 0
        for i in self.stats['levels'].values():
            cnt += i

        cnt += self.stats['nbMissingFamilies']

        print("Total skipped : %d" %cnt)

        return generated_scenes

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
        # TODO : Add more relationships
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

        print("Starting scenes generation")

        generated_scenes = self._generate_scenes(start_index, nb_to_generate, None)

        if shuffle_scenes:
            random.shuffle(generated_scenes)

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
                scene['image_filename'] = "AQA_%s_%06d.png" % (scene['split'], training_index)
                training_index += 1
                training_scenes.append(scene)
            elif scene_count < nb_training + nb_valid:
                scene['split'] = 'val'
                scene['image_index'] = valid_index      # TODO : Change this key to "scene_index". Keeping image reference for simplicity
                scene['image_filename'] = "AQA_%s_%06d.png" % (scene['split'], valid_index)
                valid_index += 1
                valid_scenes.append(scene)
            else:
                scene['split'] = 'test'
                scene['image_index'] = test_index       # TODO : Change this key to "scene_index". Keeping image reference for simplicity
                scene['image_filename'] = "AQA_%s_%06d.png" % (scene['split'], test_index)
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
    else:
      print("This experiment have already been run. Please bump the version number or delete the previous output.",
            file=sys.stderr)
      exit(1)

    # Setting & Saving the random seed
    if args.random_nb_generator_seed is not None:
      random.seed(args.random_nb_generator_seed)

      random_seed_save_filepath = os.path.join(scenes_output_folder, 'scene_generator_random_seed.json')

      with open(random_seed_save_filepath, 'w') as f:
        ujson.dump({
          'seed': args.random_nb_generator_seed,
          'version_nb': args.output_version_nb
        }, f, indent=2)

    scene_generator = Scene_generator(args.scene_length,
                                      args.tree_width,
                                      args.silence_padding_per_object,
                                      args.primary_sounds_folder,
                                      args.primary_sounds_definition_filename,
                                      args.metadata_file,
                                      args.output_version_nb,
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
