import ujson
import numpy as np
import os
import argparse
from matplotlib import pyplot as plt


parser = argparse.ArgumentParser(fromfile_prefix_chars='@')

parser.add_argument('--output_folder', default='../output', type=str,
                    help='Folder where the audio and images are located')
parser.add_argument('--output_version_nb', type=str,
                    help='Version number to analyse')


def scene2primary_sound_ids(scenes, n_objects=10):
    """ Return an array of object ids per each scene
    (we assume a fixed number of objects per scene) """
    n_scenes = len(scenes)
    primary_sound_ids = np.zeros((n_scenes, n_objects), dtype=int)
    for scene_idx, scene in enumerate(scenes):
        for obj_idx, obj in enumerate(scene['objects']):
            primary_sound_ids[scene_idx, obj_idx] = obj['id']
    return primary_sound_ids

if __name__ == "__main__":
    args = parser.parse_args()
    # args = parser.parse_args(['--output_version_nb', 'v1.0.0_50k_scenes'])
    scene_path = os.path.join(args.output_folder, args.output_version_nb, 'scenes')

    subsets = ['training', 'validation', 'test']
    paths = {'training': 'train', 'validation': 'val', 'test': 'test'}

    scenes = dict()
    for subset in subsets:
        fname = os.path.join(scene_path, 'AQA_'+paths[subset]+'_scenes.json')
        with open(fname) as f:
            scenes[subset] = ujson.load(f)['scenes']
    print("Scenes loaded")

    primary_sounds_ids = dict()
    for subset in subsets:
        primary_sounds_ids[subset] = scene2primary_sound_ids(scenes[subset])

    # plotting
    fig, axs = plt.subplots(len(subsets), 1, figsize=(24,14))
    for subset_idx, subset in enumerate(subsets):
        axs[subset_idx].hist(primary_sounds_ids[subset], bins=np.arange(0.5, 56.5))
        axs[subset_idx].set_title('distribution of primary sounds: '+subset)
    plt.savefig('primary_sounds_distribution_'+args.output_version_nb+'.pdf')
    
