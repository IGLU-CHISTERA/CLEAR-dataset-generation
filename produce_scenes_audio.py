# CLEAR Dataset
# >> Scene audio produce
#
# Author :      Jerome Abdelnour
# Year :        2018-2019
# Affiliations: Universite de Sherbrooke - Electrical and Computer Engineering faculty
#               KTH Stockholm Royal Institute of Technology
#               IGLU - CHIST-ERA


import sys, os ,argparse, random
from multiprocessing import Pool
from shutil import rmtree as rm_dir

import ujson
from pydub import AudioSegment

import matplotlib
# Matplotlib options to reduce memory usage
matplotlib.interactive(False)
matplotlib.use('agg')
import matplotlib.pyplot as plt

from utils.audio_processing import add_reverberation, generate_random_noise
from utils.misc import init_random_seed, pydub_audiosegment_to_float_array, float_array_to_pydub_audiosegment


"""
Arguments definition
"""
parser = argparse.ArgumentParser(fromfile_prefix_chars='@')

# Inputs
parser.add_argument('--elementary_sounds_folder', default='../elementary_sounds', type=str,
                    help='Folder containing all the elementary sounds and the JSON listing them')

parser.add_argument('--elementary_sounds_definition_filename', default='elementary_sounds.json', type=str,
                    help='Filename of the JSON file listing the attributes of the elementary sounds')

# Options
parser.add_argument('--with_background_noise', action='store_true',
                    help='Use this setting to include a background noise in the scenes')
parser.add_argument('--background_noise_gain_range', default="-100,-20", type=str,
                    help='Range for the gain applied to the background noise. '
                         'Should be written as 0,100 for a range from 0 to 100')

parser.add_argument('--with_reverb', action='store_true',
                    help='Use this setting to include ramdom reverberations in the scenes')
parser.add_argument('--reverb_room_scale_range', default="0,100", type=str,
                    help='Range for the reverberation parameter. Should be written as 0,100 for a range from 0 to 100')
parser.add_argument('--reverb_delay_range', default="0,500", type=str,
                    help='Range for the reverberation parameter. Should be written as 0,100 for a range from 0 to 100')

parser.add_argument('--no_audio_files', action='store_true',
                    help='If set, audio file won\'t be produced. '
                         'The --produce_spectrograms switch will also be activated')

parser.add_argument('--produce_spectrograms', action='store_true',
                    help='If set, produce the spectrograms for each scenes')
parser.add_argument('--spectrogram_height', default=480, type=int,
                    help='Height of the generated spectrogram image')
parser.add_argument('--spectrogram_width', default=320, type=int,
                    help='Width of the generated spectrogram image')
parser.add_argument('--spectrogram_window_length', default=1024, type=int,
                    help='Number of samples used in the FFT window')
parser.add_argument('--spectrogram_window_overlap', default=512, type=int,
                    help='Number of samples that are overlapped in the FFT window')

# Outputs
parser.add_argument('--output_folder', default='../output', type=str,
                    help='Folder where the audio and images will be saved')
parser.add_argument('--set_type', default='train', type=str,
                    help="Specify the set type (train/val/test)")
parser.add_argument('--clear_existing_files', action='store_true',
                    help='If set, will delete all files in the output folder before starting the generation.')
parser.add_argument('--output_filename_prefix', default='CLEAR', type=str,
                    help='Prefix used for produced files')
parser.add_argument('--output_version_nb', default='0.1', type=str,
                    help='Version number that will be appended to the produced file')
parser.add_argument('--produce_specific_scenes', default="", type=str,
                    help='Range for the reverberation parameter. Should be written as 0,100 for a range from 0 to 100')

# Misc
parser.add_argument('--random_nb_generator_seed', default=None, type=int,
                    help='Set the random number generator seed to reproduce results')
parser.add_argument('--nb_process', default=4, type=int,
                    help='Number of process allocated for the production')

"""
    Produce audio recording from scene JSON definition
    Can also produce spectrograms of the scene if the correct option is provided
    
        - Load scenes JSON definition from file
        - Calculate random silence duration (Silence between sounds)
        - Concatenate Elementary Sounds (In the order defined by the scene JSON)
        - Generate random white noise and overlay on the scene
        - Apply reverberation effect
        - Write audio scene to file (Either as a WAV file, a spectrogram/PNG or both
        
    The production is distributed across {nb_process} processes
"""

class AudioSceneProducer:
    def __init__(self,
                 outputFolder,
                 version_nb,
                 spectrogramSettings,
                 withBackgroundNoise,
                 backgroundNoiseGainSetting,
                 withReverb,
                 reverbSettings,
                 produce_audio_files,
                 produce_spectrograms,
                 clear_existing_files,
                 elementarySoundsJsonFilename,
                 elementarySoundFolderPath,
                 setType,
                 outputPrefix):

        # Paths
        self.outputFolder = outputFolder
        self.elementarySoundFolderPath = elementarySoundFolderPath
        self.version_nb = version_nb

        self.outputPrefix = outputPrefix
        self.setType = setType

        self.produce_audio_files = produce_audio_files
        self.produce_spectrograms = produce_spectrograms

        experiment_output_folder = os.path.join(self.outputFolder, self.version_nb)

        # Loading elementary sounds definition from json definition file
        with open(os.path.join(self.elementarySoundFolderPath, elementarySoundsJsonFilename)) as file:
            self.elementarySounds = ujson.load(file)

        # Loading scenes definition
        sceneFilename = '%s_%s_scenes.json' % (self.outputPrefix, self.setType)
        sceneFilepath = os.path.join(experiment_output_folder, 'scenes', sceneFilename)
        with open(sceneFilepath) as scenesJson:
            self.scenes = ujson.load(scenesJson)['scenes']

        self.spectrogramSettings = spectrogramSettings
        self.withBackgroundNoise = withBackgroundNoise
        self.backgroundNoiseGainSetting = backgroundNoiseGainSetting
        self.withReverb = withReverb
        self.reverbSettings = reverbSettings

        root_images_output_folder = os.path.join(experiment_output_folder, 'images')
        root_audio_output_folder = os.path.join(experiment_output_folder, 'audio')

        if not os.path.isdir(experiment_output_folder):
            # This is impossible, if the experiment folder doesn't exist we won't be able to retrieve the scenes
            os.mkdir(experiment_output_folder)

        self.images_output_folder = os.path.join(root_images_output_folder, self.setType)
        self.audio_output_folder = os.path.join(root_audio_output_folder, self.setType)

        if self.produce_audio_files:
            if not os.path.isdir(root_audio_output_folder):
                os.mkdir(root_audio_output_folder)
                os.mkdir(self.audio_output_folder)
            else:
                if not os.path.isdir(self.audio_output_folder):
                    os.mkdir(self.audio_output_folder)
                elif clear_existing_files:
                    rm_dir(self.audio_output_folder)
                    os.mkdir(self.audio_output_folder)

        if self.produce_spectrograms:
            if not os.path.isdir(root_images_output_folder):
                os.mkdir(root_images_output_folder)
                os.mkdir(self.images_output_folder)
            else:
                if not os.path.isdir(self.images_output_folder):
                    os.mkdir(self.images_output_folder)
                elif clear_existing_files:
                    rm_dir(self.images_output_folder)
                    os.mkdir(self.images_output_folder)

        self.currentSceneIndex = -1  # We start at -1 since nextScene() will increment idx at the start of the fct
        self.nbOfLoadedScenes = len(self.scenes)

        if self.nbOfLoadedScenes == 0:
            print("[ERROR] Must have at least 1 scene in '" + sceneFilepath + "'", file=sys.stderr)
            exit(1)

        self.show_status_every = int(self.nbOfLoadedScenes / 10)
        self.show_status_every = self.show_status_every if self.show_status_every > 0 else 1

        # Initialize the list that contain the loaded sounds
        self.loadedSounds = []

    def loadAllElementarySounds(self):
        print("Loading elementary sounds")
        for sound in self.elementarySounds:
            # Creating the audio segment (Suppose WAV format)
            soundFilepath = os.path.join(self.elementarySoundFolderPath, sound['filename'])
            soundAudioSegment = AudioSegment.from_wav(soundFilepath)
            self.loadedSounds.append({
                'name': sound['filename'],
                'audioSegment': soundAudioSegment
            })

        print("Done loading elementary sounds")

    def _getLoadedAudioSegmentByName(self, name):
        filterResult = list(filter(lambda sound: sound['name'] == name, self.loadedSounds))
        if len(filterResult) == 1:
            return filterResult[0]['audioSegment']
        else:
            print('[ERROR] Could not retrieve loaded audio segment \'' + name + '\' from memory.')
            exit(1)

    def produceScene(self, sceneId):
        if sceneId < self.nbOfLoadedScenes:

            scene = self.scenes[sceneId]
            if sceneId % self.show_status_every == 0:
                print('Producing scene ' + str(sceneId), flush=True)

            sceneAudioSegment = self.assembleAudioScene(scene)

            if self.produce_audio_files:
                audioFilename = '%s_%s_%06d.wav' % (self.outputPrefix, self.setType, sceneId)
                sceneAudioSegment.export(os.path.join(self.audio_output_folder, audioFilename),format='wav')

            if self.produce_spectrograms:
                spectrogram = AudioSceneProducer.createSpectrogram(sceneAudioSegment,
                                                                   self.spectrogramSettings['height'],
                                                                   self.spectrogramSettings['width'],
                                                                   self.spectrogramSettings['window_length'],
                                                                   self.spectrogramSettings['window_overlap'])

                imageFilename = '%s_%s_%06d.png' % (self.outputPrefix, self.setType, sceneId)
                spectrogram.savefig(os.path.join(self.images_output_folder, imageFilename),dpi=1)

                AudioSceneProducer.clearSpectrogram(spectrogram)

        else:
            print("[ERROR] The scene specified by id '%d' couln't be found" % sceneId)

    def assembleAudioScene(self, scene):
        sceneAudioSegment = AudioSegment.empty()

        sceneAudioSegment += AudioSegment.silent(duration=scene['silence_before'])
        for sound in scene['objects']:
            newAudioSegment = self._getLoadedAudioSegmentByName(sound['filename'])

            sceneAudioSegment += newAudioSegment

            # Insert a silence padding after the sound
            sceneAudioSegment += AudioSegment.silent(duration=sound['silence_after'])

        if self.withBackgroundNoise:
            gain = random.randrange(self.backgroundNoiseGainSetting['min'], self.backgroundNoiseGainSetting['max'])
            sceneAudioSegment = AudioSceneProducer.overlayBackgroundNoise(sceneAudioSegment, gain)

        if self.withReverb:
            roomScale = random.randrange(self.reverbSettings['roomScale']['min'],
                                         self.reverbSettings['roomScale']['max'])
            delay = random.randrange(self.reverbSettings['delay']['min'], self.reverbSettings['delay']['max'])
            sceneAudioSegment = AudioSceneProducer.applyReverberation(sceneAudioSegment, roomScale, delay)

        # Make sure the everything is in Mono (If stereo, will convert to mono)
        sceneAudioSegment.set_channels(1)

        return sceneAudioSegment

    @staticmethod
    def applyReverberation(audioSegment, roomScale, delay):
        floatArray = pydub_audiosegment_to_float_array(audioSegment, audioSegment.frame_rate, audioSegment.sample_width)

        floatArrayWithReverb = add_reverberation(floatArray, room_scale=roomScale, pre_delay=delay)

        return float_array_to_pydub_audiosegment(floatArrayWithReverb, audioSegment.frame_rate,
                                                 audioSegment.sample_width)

    @staticmethod
    def overlayBackgroundNoise(sceneAudioSegment, noiseGain):
        backgroundNoise = generate_random_noise(sceneAudioSegment.duration_seconds * 1000,
                                                noiseGain,
                                                sceneAudioSegment.frame_width,
                                                sceneAudioSegment.frame_rate)

        sceneAudioSegment = backgroundNoise.overlay(sceneAudioSegment)

        return sceneAudioSegment

    @staticmethod
    def createSpectrogram(sceneAudioSegment, spectrogramHeight, spectrogramWidth, windowLength, windowOverlap):
        # Set figure settings to remove all axis
        spectrogram = plt.figure(frameon=False)
        spectrogram.set_size_inches(spectrogramWidth, spectrogramHeight)
        ax = plt.Axes(spectrogram, [0., 0., 1., 1.])
        ax.set_axis_off()
        spectrogram.add_axes(ax)

        # Generate the spectrogram
        # See https://matplotlib.org/api/_as_gen/matplotlib.pyplot.specgram.html?highlight=matplotlib%20pyplot%20specgram#matplotlib.pyplot.specgram
        Pxx, freqs, bins, im = plt.specgram(x=sceneAudioSegment.get_array_of_samples(), Fs=sceneAudioSegment.frame_rate,
                                            window=matplotlib.mlab.window_hanning,
                                            NFFT=windowLength,
                                            noverlap=windowOverlap,
                                            scale='dB')

        return spectrogram

    @staticmethod
    def clearSpectrogram(spectrogram):
        # Close and Clear the figure
        plt.close(spectrogram)
        spectrogram.clear()


def mainPool():
    args = parser.parse_args()

    # If not producing audio, we will produce spectrograms
    if args.no_audio_files and not args.produce_spectrograms:
        args.produce_spectrograms = True

    # Preparing settings
    reverbRoomScaleRange = args.reverb_room_scale_range.split(',')
    reverbDelayRange = args.reverb_delay_range.split(',')
    reverbSettings = {
        'roomScale': {
            'min': int(reverbRoomScaleRange[0]),
            'max': int(reverbRoomScaleRange[1])
        },
        'delay': {
            'min': int(reverbDelayRange[0]),
            'max': int(reverbDelayRange[1])
        }
    }

    backgroundNoiseGainRange = args.background_noise_gain_range.split(',')
    backgroundNoiseGainSetting = {
        'min': int(backgroundNoiseGainRange[0]),
        'max': int(backgroundNoiseGainRange[1])
    }

    # Creating the producer
    producer = AudioSceneProducer(outputFolder=args.output_folder,
                                  version_nb=args.output_version_nb,
                                  elementarySoundsJsonFilename=args.elementary_sounds_definition_filename,
                                  elementarySoundFolderPath=args.elementary_sounds_folder,
                                  setType=args.set_type,
                                  outputPrefix=args.output_filename_prefix,
                                  produce_audio_files=not args.no_audio_files,
                                  produce_spectrograms=args.produce_spectrograms,
                                  clear_existing_files=args.clear_existing_files,
                                  withBackgroundNoise=args.with_background_noise,
                                  backgroundNoiseGainSetting=backgroundNoiseGainSetting,
                                  withReverb=args.with_reverb,
                                  reverbSettings=reverbSettings,
                                  spectrogramSettings={
                                      'height': args.spectrogram_height,
                                      'width': args.spectrogram_width,
                                      'window_length': args.spectrogram_window_length,
                                      'window_overlap': args.spectrogram_window_overlap,
                                  })

    # Setting & Saving the random seed
    if args.random_nb_generator_seed is not None:
        init_random_seed(args.random_nb_generator_seed)
    else:
        print("The seed must be specified in the arguments.", file=sys.stderr)
        exit(1)

    # Setting ids of scenes to produce
    if args.produce_specific_scenes == '':
        idList = list(range(producer.nbOfLoadedScenes))
    else:
        bounds = [int(x) for x in args.produce_specific_scenes.split(",")]
        if len(bounds) != 2 or bounds[0] > bounds[1]:
            print("Invalid scenes interval. Must be specified as X,Y where X is the low bound and Y the high bound.",
                  file=sys.stderr)
            exit(1)

        bounds[1] = bounds[1] if bounds[1] < producer.nbOfLoadedScenes else producer.nbOfLoadedScenes
        idList = list(range(bounds[0], bounds[1]))

    # Load and preprocess all elementary sounds into memory
    producer.loadAllElementarySounds()
    
    nb_generated = len(idList)
    while len(idList) > 0:

        # Create process pool
        pool = Pool(processes=args.nb_process)

        # We batch the scenes and close the pool everytime to avoid memory leak (not the most elegant fix) #FIXME : Wait for the pool queue to empty instead. See stack overflow
        nbToProcess = args.nb_process * 100     # TODO : Take the multiplier in parameter (For now, value of 100 take about 8 GB of RAM)
        toProcess = idList[:nbToProcess]
        idList = idList[nbToProcess:]
        # Start the production
        pool.map(producer.produceScene, toProcess)

        pool.close()
        pool.join()

    print("Job Done !")
    if args.produce_spectrograms:
        print(">>> Produced %d spectrograms." % nb_generated)

    if not args.no_audio_files:
        print(">>> Produced %d audio files." % nb_generated)


if __name__ == '__main__':
    mainPool()
