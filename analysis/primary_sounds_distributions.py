import ujson
import json
import numpy as np
import os
import argparse
from matplotlib import pyplot as plt
import matplotlib
# Matplotlib options to reduce memory usage
#matplotlib.interactive(True)
#matplotlib.use('agg')



parser = argparse.ArgumentParser(fromfile_prefix_chars='@')

parser.add_argument('--output_folder', default='../output', type=str,
                    help='Folder where the audio and images are located')
parser.add_argument('--output_version_nb', type=str,
                    help='Version number to analyse')


def get_primary_sounds_unique_count(primary_sounds_definition_path):
    with open(primary_sounds_definition_path, 'r') as f:
        primary_sounds = ujson.load(f)

    return len(primary_sounds)


def scene2primary_sound_ids(scenes, n_objects=10):
    """ Return an array of object ids per each scene
    (we assume a fixed number of objects per scene) """
    n_scenes = len(scenes)
    primary_sound_ids = np.zeros((n_scenes, n_objects), dtype=int)
    for scene_idx, scene in enumerate(scenes):
        for obj_idx, obj in enumerate(scene['objects']):
            primary_sound_ids[scene_idx, obj_idx] = obj['id']
    return primary_sound_ids


def scene2primary_sound_position(scenes, n_primary_sounds):
    """ Return an array of object ids per each scene
    (we assume a fixed number of objects per scene) """
    n_scenes = len(scenes)
    primary_sound_pos = np.ones((n_scenes, n_primary_sounds), dtype=int) * -1
    for scene_idx, scene in enumerate(scenes):
        for obj_pos, obj in enumerate(scene['objects']):
            primary_sound_pos[scene_idx, obj['id']] = obj_pos
    return primary_sound_pos


def load_scenes(scene_path, subsets):
    scenes = dict()
    for subset in subsets:
        fname = os.path.join(scene_path, 'CLEAR_' + subset + '_scenes.json')
        with open(fname) as f:
            scenes[subset] = ujson.load(f)['scenes']
    print("Scenes loaded")
    return scenes


def get_n_max_with_index(list_value, nb):
    n_max_vals = sorted(list_value)[-nb:]

    max_with_index = []
    idx_processed = []

    for val in n_max_vals:
        indexes = np.where(list_value == val)[0]
        if len(indexes) > 1:
            for id in indexes:
                if id not in idx_processed:
                    idx = id
                    break
        else:
            idx = indexes[0]
        idx_processed.append(idx)
        max_with_index.append(str((idx, val)))

    return max_with_index


def plot_distribution_hist_pos_per_id(data, subsets, output_version_nb, save_fig=True):
    fig, axs = plt.subplots(len(subsets), 1, figsize=(24, 14))
    max_freq_per_pos = {}
    for subset_idx, subset in enumerate(subsets):
        n, bins, patches = axs[subset_idx].hist(data[subset], bins=np.arange(0.5, 56.5), density=True, label=['pos ' + str(p) for p in range(1, 11)])
        axs[subset_idx].set_title('distribution of primary sounds: ' + subset)
        axs[subset_idx].set_xticks(range(0, 55))
        axs[subset_idx].set_xlabel('primary object id')
        axs[subset_idx].legend()

        max_freq_per_pos[subset] = {}

        for pos, freq in enumerate(n):
            max_freq_per_pos[subset][pos] = get_n_max_with_index(freq, 5)

    print("Saving to file")
    with open('max_freq_per_pos_%s.json' % output_version_nb, 'w') as f:
        json.dump(max_freq_per_pos, f, indent=4)
    print("File saved")


    if save_fig:
        plt.savefig('primary_sounds_distribution_' + output_version_nb + '.pdf')
    else:
        plt.show()


def plot_distribution_hist_id_per_pos(data, subsets, save_fig=True):
    fig, axs = plt.subplots(len(subsets), 1, figsize=(24, 14))
    for subset_idx, subset in enumerate(subsets):
        n, bins, patches = axs[subset_idx].hist(data[subset],  bins=np.arange(-0.5, 10.5), density=False)
        axs[subset_idx].set_title('distribution of primary sounds: ' + subset)
        #axs[subset_idx].set_xticks(range(0, 10))
        axs[subset_idx].set_xlabel('Position')
        axs[subset_idx].legend()

    if save_fig:
        plt.savefig('primary_sounds_distribution_' + args.output_version_nb + '.pdf')
    else:
        plt.show()


if __name__ == "__main__":
    args = parser.parse_args()
    # args = parser.parse_args(['--output_version_nb', 'v1.0.0_50k_scenes'])
    scene_path = os.path.join(args.output_folder, args.output_version_nb, 'scenes')
    primary_sounds_definition_path = './elementary_sounds/elementary_sounds.json'

    subsets = ['train', 'val', 'test']

    nb_primary_sounds = get_primary_sounds_unique_count(primary_sounds_definition_path)

    scenes = load_scenes(scene_path, subsets)

    primary_sounds_ids = dict()
    for subset in subsets:
        #primary_sounds_ids[subset] = scene2primary_sound_ids(scenes[subset])
        primary_sounds_ids[subset] = scene2primary_sound_position(scenes[subset], nb_primary_sounds)

    # plotting
    #plot_distribution_hist_pos_per_id(primary_sounds_ids, subsets, args.output_version_nb, save_fig=False)
    plot_distribution_hist_id_per_pos(primary_sounds_ids, subsets, save_fig=True)
    print("Done")
    
