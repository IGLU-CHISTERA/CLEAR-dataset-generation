import time
import itertools
import ujson
import os
from pydub import AudioSegment


# TODO : distribute the scene creation (Create a json for each scene and merge them together at the end)
# FIXME : Current implementation is really slow for more than 4 primary sounds per scene. A threaded implementation would be best
class Scene_generator:
    def __init__(self, nb_sound_per_scene=5,
                 primary_sounds_folder=None,
                 primary_sounds_definition_filename="primary_sounds.json",
                 output_folder=None,
                 set_type = "train"):

        self.set_type = set_type

        if not output_folder:
            self.output_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "output")
        else:
            self.output_folder = output_folder

        self.sound_output_folder = os.path.join(self.output_folder, 'scenes')

        if not primary_sounds_folder:
            self.primary_sounds_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "primary_sounds")
        else:
            self.primary_sounds_folder = primary_sounds_folder

        self.primary_sounds_definition_filepath = os.path.join(self.primary_sounds_folder, primary_sounds_definition_filename)

        with open(self.primary_sounds_definition_filepath) as primary_sounds_definition:
            self.primary_sounds_definition = ujson.load(primary_sounds_definition)

        self.nb_primary_sound = len(self.primary_sounds_definition)

        # Make sure we have enough primary sounds for the number of sound per scene
        self.nb_sound_per_scene = nb_sound_per_scene if nb_sound_per_scene <= self.nb_primary_sound else self.nb_primary_sound

        self.preprocess_primary_sounds()

    def preprocess_primary_sounds(self):
        for primary_sound in self.primary_sounds_definition:
            primary_sound_filename = os.path.join(self.primary_sounds_folder, primary_sound['note_str']) + ".wav"
            primary_sound_audiosegment = AudioSegment.from_wav(primary_sound_filename)

            # Use str attributes and remove the numerical representation
            for key in list(primary_sound.keys()):
                if key.endswith('_str'):
                    primary_sound[key[:-4]] = primary_sound[key]
                    del primary_sound[key]

            # Remove sample_rate attribute
            if 'sample_rate' in primary_sound:
                del primary_sound['sample_rate']

            # TODO : Add more sound analysis here. The added attributes should be used in the scene generation
            primary_sound['duration'] = int(primary_sound_audiosegment.duration_seconds * 1000)
            primary_sound['rms'] = primary_sound_audiosegment.rms

    def generate_info_section(self):
        return {
                "name": "AQA-V0.1",
                "license": "Creative Commons Attribution (CC-BY 4.0)",
                "version": "0.1",
                "split": self.set_type,
                "date": time.strftime("%x")
            }

    def generate_relationships(self, scene_composition):
        # FIXME : Those relationships are trivial. Could be moved to question engine (Before & after)
        # TODO : Add more relationships
        relationships = {
            'before': [],
            'after': []
        }

        scene_indexes = list(range(0, self.nb_sound_per_scene))

        for i in range(0, self.nb_sound_per_scene):
            if i - 1 >= 0:
                relationships['before'].append(relationships['before'][i - 1] + [i - 1])

            scene_indexes.remove(i)
            relationships['after'].append(list(scene_indexes))

        return relationships



    # FIXME: full_scene_duration value
    def generate_scenes_definition(self, min_instrument_family_per_scene=2, full_scene_duration= 5000, scene_start_id=0):
        # TODO : Make sure we have different instruments in the scene

        # Generate all possible permurations of the primary sounds
        index_permutations = itertools.permutations(range(0, self.nb_primary_sound), self.nb_sound_per_scene)

        scene_index = scene_start_id
        scenes = []

        for scene_composition_indexes in index_permutations:
            scene_composition = []
            instruments = {}
            skip_scene = False
            for idx in scene_composition_indexes:
                sound_definition = self.primary_sounds_definition[idx]

                # Count occurence of each instrument families
                if sound_definition['instrument_family'] in instruments:
                    instruments[sound_definition['instrument_family']] += 1
                else:
                    instruments[sound_definition['instrument_family']] = 1

                scene_composition.append(sound_definition)

            if len(instruments.keys()) < min_instrument_family_per_scene or scene_index > 100:          # FIXME : Remove scene limit
                # Not enough sound family
                print("Skipping")
                continue

            scenes.append({
                "split": self.set_type,
                "objects": scene_composition,
                "relationships": self.generate_relationships(scene_composition),            # TODO : Implement relationships
                "image_index": scene_index,     # TODO : Change this key to "scene_index". Keeping image reference for simplicity
                "image_filename": "AQA_%s_%06d.png" % (self.set_type, scene_index)
            })

            scene_index += 1

        return {
            "info" : self.generate_info_section(),
            "scenes": scenes
        }


def main():

    scene_generator = Scene_generator()
    startTime = time.time()
    scenes = scene_generator.generate_scenes_definition()
    elapsed = time.time() - startTime

    print("Generated %d scenes in %d secs" % (len(scenes['scenes']), elapsed))

    with open('../output/testScenes.json', 'w') as outputFile:
        ujson.dump(scenes, outputFile)
    print('done')

    #print(ujson.dumps(scene_generator.primary_sounds_definition, indent=4))


if __name__ == "__main__":
    main()