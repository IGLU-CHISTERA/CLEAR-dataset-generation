import os
import ujson
import random
from datetime import datetime


class Node:
    def __init__(self, parent, level, sound_id, overlapping_last=False):
        self.childs = []
        self.level = level
        self.sound_id = sound_id
        self.overlapping_last = overlapping_last
        self.parent = parent

    def add_child(self, sound_id):
        new_child = Node(self, self.level+1, sound_id)
        self.childs.append(new_child)
        return new_child

    def get_childs_ids(self):
        ids = []

        for child in self.childs:
            ids.append(child.sound_id)

        return ids


class Primary_sounds:
    def __init__(self, definition_filepath):
        filepath = os.path.join(os.path.dirname(os.path.realpath(__file__)), definition_filepath)
        with open(filepath) as primary_sounds_definition:
            self.definition = ujson.load(primary_sounds_definition)

        self.nb_sounds = len(self.definition)

        self.families_count = {}

        for sound in self.definition:
            if sound['instrument_family_str'] not in self.families_count:
                self.families_count[sound['instrument_family_str']] = 1
            else:
                self.families_count[sound['instrument_family_str']] += 1

        self.families = self.families_count.keys()
        self.nb_families = len(self.families)

        self.generated_count_by_index = {i: 0 for i in range(self.nb_sounds)}
        self.generated_count_by_families = {fam: 0 for fam in self.families}
        self.gen_index = 0

    def ids_to_families_count(self, id_list):
        count = {}

        for id in id_list:
            family = self.definition[id]['instrument_family_str']
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

    def next_id(self, state, siblings):
        # TODO : Do some checking based on the state to minimize same items (Instead of handling it later on in scenes constraints)
        # TODO : Try to minimize the reuse of the same sound (Even same category sound ?)
        #self.gen_index = (self.gen_index + 1) % self.nb_sounds
        self.gen_index = random.randint(0, self.nb_sounds - 1)

        state_and_siblings = list(set(state + siblings))

        # Prevent from using a sound that is already in the state or is another child of the parent node
        while self.gen_index in state_and_siblings:
            #self.gen_index = (self.gen_index + 1) % self.nb_sounds
            self.gen_index = random.randint(0, self.nb_sounds - 1)

        # Keeping track of the nb of occurence
        self.generated_count_by_index[self.gen_index] += 1
        self.generated_count_by_families[self.definition[self.gen_index]['instrument_family_str']] += 1

        return self.gen_index


class Scene_generator:
    def __init__(self, primary_sounds_definition_filepath, nb_objects_per_scene, nb_tree_branch=None):
        self.nb_objects_per_scene = nb_objects_per_scene
        if nb_tree_branch:
            self.nb_tree_branch = nb_tree_branch
        else:
            self.nb_tree_branch = self.nb_objects_per_scene

        self.primary_sounds = Primary_sounds(primary_sounds_definition_filepath)

        # Constraints
        # TODO : Take those as parameter or calculate them based on nb_object_per_scene
        self.constraints = {
            'min_nb_families' : 5,
            'min_objects_per_family': 2,
            'min_nb_families_subject_to_min_objects_per_family' : 2
        }

    def validate_final(self, state):
        # TODO : Validate final state before adding this scene to the repository
        # TODO : Validate all the constraints ? (Maybe not necessary to reverify the intermediate)
        # TODO : Constraints :
        # TODO :        - X differents instrument families
        # TODO :        - X uniquely filterable objects for {set} of attributes
        # TODO :        - X objects per instrument families. For at least X instument families
        # TODO :        - SOME CONSTRAINTS ON OVERLAPPING

        # Validate that we have enough instrument families
        families_count, nb_families = self.primary_sounds.ids_to_families_count(state)
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
        families_count, current_nb_families = self.primary_sounds.ids_to_families_count(state)

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

        validated_families = {
            'valid' : [],
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
            return False
        else:
            # Calculating the probability that this tree will lead to a valid combination
            prob = 0
            for (family, count) in validated_families['invalid']:
                nb_other_sounds_same_family = self.primary_sounds.families_count[family] - count
                nb_missing_sounds = self.constraints['min_objects_per_family'] - count

                prob += nb_other_sounds_same_family/self.primary_sounds.nb_sounds ** nb_missing_sounds

        return True

    def generate(self, start_index= 0, nb_to_generate=None, root_node=None):
        if not root_node:
            # FIXME : The process won't include the root node in the scene composition. Will cause problem when distributing part of the tree in different processes
            root_node = Node(None, -1, -1)      # Root of the tree

        next_node = root_node
        state = []
        generated_scenes = []

        # FIXME : Remove this, debugging purpose
        self.stats = {
            'levels' : {},
            'nbValid': 0,
            'nbMissingFamilies' : 0
        }

        continue_work = True

        while continue_work:
            current_node = next_node
            #print("Node %d" % current_node.sound_id)
            #print(state)
            #print("-"*10)

            # Depth first instantiation of tree
            if current_node.level < self.nb_objects_per_scene - 1:
                # Not reached the bottom yet.

                if len(current_node.childs) < self.nb_tree_branch:
                    # Add a new child
                    new_sound_id = self.primary_sounds.next_id(state, [c.sound_id for c in current_node.childs])
                    state.append(new_sound_id)
                    # TODO : random Chance of overlapping
                    next_node = current_node.add_child(new_sound_id)
                else:
                    # Go up one level
                    next_node = current_node.parent
                    if next_node is None:
                        # We reached the root node. The tree has been completely instantiated
                        continue_work = False
                        break
                    else:
                        state.pop()

                if not self.validate_intermediate(state, next_node.level):
                    next_node = current_node
                    state.pop()

                # TODO : Update the state
                # TODO : To intermediary validation. If validation fail, we need to mark the branch as unfit (Simply go up ?)

            else:
                # Reached the bottom of the tree

                if self.validate_final(state):
                    # TODO : dump scene to file instead of creating a list of all scenes possible
                    # TODO : We can then collect all the file at the end of the process
                    # TODO : Do this in another process ? --> 1 process for tree instantiation that feed a mailbox and 1 process that empty the mailbox and write to file
                    self.stats['nbValid'] += 1
                    scene_index = start_index

                    if nb_to_generate and scene_index >= nb_to_generate:
                        # Reached the limit of scene to generate,
                        continue_work = False
                        break
                    start_index += 1

                    generated_scenes.append(list(state))

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
        print(self.stats['levels'])
        print(self.stats['nbMissingFamilies'])
        cnt = 0
        for i in self.stats['levels'].values():
            cnt += i

        cnt += self.stats['nbMissingFamilies']

        print("Total skipped : %d" %cnt)

        return generated_scenes


if __name__ == '__main__':
    # TODO : Parameters handling
    # TODO : seed handling
    #random.seed(4543525235253235)

    scene_generator = Scene_generator('../primary_sounds/primary_sounds.json', 10, 3)
    before = datetime.now()
    scenes = scene_generator.generate()
    skt = set([tuple(i) for i in scenes])
    print("Set len : %d" % len(skt))
    timing = datetime.now() - before

    print("Took %f" % timing.seconds)
    print('done')
