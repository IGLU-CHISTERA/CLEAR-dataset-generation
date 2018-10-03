import pydub
import sys
from pydub import AudioSegment
from pydub.generators import WhiteNoise as WhiteNoiseGenerator
from pydub.effects import normalize
from pydub.silence import split_on_silence
import os, ujson, argparse, copy
from multiprocessing import Pool
import matplotlib
# Matplotlib options to reduce memory usage
matplotlib.interactive(False)
matplotlib.use('agg')

import matplotlib.pyplot as plt


"""
Arguments definition
"""
parser = argparse.ArgumentParser(fromfile_prefix_chars='@')

parser.add_argument('--output_folder', default='../output', type=str,
                    help='Folder where the audio and images will be saved')

parser.add_argument('--primary_sounds_folder', default='../primary_sounds', type=str,
                    help='Folder containing all the primary sounds and the JSON listing them')

parser.add_argument('--primary_sounds_definition_filename', default='primary_sounds.json', type=str,
                    help='Filename of the JSON file listing the attributes of the primary sounds')

parser.add_argument('--set_type', default='train', type=str,
                    help="Specify the set type (train/val/test)")

parser.add_argument('--spectrogram_height', default=480, type=int,
                    help='Height of the generated spectrogram image')

parser.add_argument('--spectrogram_width', default=320, type=int,
                    help='Width of the generated spectrogram image')

parser.add_argument('--spectrogram_window_length', default=1024, type=int,
                    help='Number of samples used in the FFT window')

parser.add_argument('--spectrogram_window_overlap', default=512, type=int,
                    help='Number of samples that are overlapped in the FFT window')

parser.add_argument('--with_background_noise', action='store_true',
                    help='Use this setting to include a background noise in the scenes')

parser.add_argument('--nb_process', default=4, type=int,
                    help='Number of process allocated for the production')

parser.add_argument('--output_filename_prefix', default='AQA', type=str,
                    help='Prefix used for produced files')

parser.add_argument('--output_version_nb', default='0.1', type=str,
                    help='Version number that will be appended to the produced file')


######################################################################
# This program will read the scene json file                         #
# It will then generate the corresponding audio file & spectrogram   #
######################################################################

# TODO : The audio file must have a fixed length to maintain the same temporal resolution on spectrograms
#        We calculate the scene length by maxNbOfPrimarySoundsInOneScene * longestPrimarySoundLength + maxNbOfPrimarySoundsInOneScene * sleepTimeBetweenSounds + beginSleepTime + endSleepTime
#        Some scenes will require padding. We should pad with silence (Or noise ? Would add more randomness).
#        Instead of padding everything at the end, we should distribute part of the padding between each sounds
#        We should not pad always the same way to reduce bias in data.
#        We should pad or not between each sound according to a certain probability. Then split the rest between beginning and end
# TODO/Investigate : Insert random noise instead of silence between primary sounds

# FIXME : We should probably clear previously generated audio & images before generating. (We may end up with samples from another run otherwise)
# TODO : Add more comments
# FIXME : Take sample rate as parameter. If primary sounds have a lower sample freq, upscale ?
class AudioSceneProducer:
    def __init__(self,
                 outputFolder,
                 version_nb,
                 spectrogramSettings,
                 withBackgroundNoise,
                 primarySoundsJsonFilename,
                 primarySoundFolderPath,
                 setType,
                 outputPrefix):

        # Paths
        self.outputFolder = outputFolder
        self.primarySoundFolderPath = primarySoundFolderPath
        self.version_nb = version_nb

        self.outputPrefix = outputPrefix
        self.setType = setType

        # Loading primary sounds definition from 'primarySounds.json'
        with open(os.path.join(self.primarySoundFolderPath, primarySoundsJsonFilename)) as primarySoundJson:
            self.primarySounds = ujson.load(primarySoundJson)

        # Loading scenes definition
        sceneFilename = '%s_%s_scenes.json' % (self.outputPrefix, self.setType)
        sceneFilepath = os.path.join(self.outputFolder, self.version_nb, 'scenes', sceneFilename)
        with open(sceneFilepath) as scenesJson:
            self.scenes = ujson.load(scenesJson)['scenes']

        self.spectrogramSettings = spectrogramSettings
        self.withBackgroundNoise = withBackgroundNoise


        experiment_output_folder = os.path.join(self.outputFolder, self.version_nb)
        self.images_output_folder = os.path.join(experiment_output_folder, 'images')
        self.audio_output_folder = os.path.join(experiment_output_folder, 'audio')

        if not os.path.isdir(experiment_output_folder):
            os.mkdir(experiment_output_folder)

        if not os.path.isdir(self.images_output_folder):
            os.mkdir(self.images_output_folder)

        if not os.path.isdir(self.audio_output_folder):
            os.mkdir(self.audio_output_folder)

        self.images_output_folder = os.path.join(self.images_output_folder, self.setType)
        self.audio_output_folder = os.path.join(self.audio_output_folder, self.setType)

        if os.path.isdir(self.images_output_folder) or os.path.isdir(self.audio_output_folder):
            print("This experiment have already been run. Please bump the version number or delete the previous output.", file=sys.stderr)
            exit(1)
        else:
            os.mkdir(self.audio_output_folder)
            os.mkdir(self.images_output_folder)

        self.currentSceneIndex = -1  # We start at -1 since nextScene() will increment idx at the start of the fct
        self.nbOfLoadedScenes = len(self.scenes)

        if self.nbOfLoadedScenes == 0:
            print("[ERROR] Must have at least 1 scene in '"+sceneFilepath+"'")
            exit(1)     # FIXME : Should probably raise an exception here instead

        # TODO : Add other default sounds such as random noise and other continuous sounds
        self.defaultLoadedSounds = [
            {
                'name': '-SILENCE-',
                'audioSegment': AudioSegment.silent(duration=100)      # 100 ms of silence      # FIXME : Should specify the sample rate
            }
        ]

        # Creating a copy of the default sound list
        self.loadedSounds = copy.deepcopy(self.defaultLoadedSounds)

    def _loadAllPrimarySounds(self):
        for sound in self.primarySounds:
            # Creating the audio segment (Suppose WAV format)
            soundFilepath = os.path.join(self.primarySoundFolderPath, sound['filename'])
            soundAudioSegment = AudioSegment.from_wav(soundFilepath)
            self.loadedSounds.append({
                'name': sound['filename'],
                'audioSegment': soundAudioSegment
            })

        print("Done loading primary sounds")

    def _getLoadedAudioSegmentByName(self, name):
        filterResult = list(filter(lambda sound: sound['name'] == name, self.loadedSounds))
        if len(filterResult) == 1:
            return filterResult[0]['audioSegment']
        else:
            print('[ERROR] Could not retrieve loaded audio segment \'' + name + '\' from memory.')
            exit(0)  # FIXME : Should probably raise an exception here instead

    def produceScene(self, sceneId):
        if sceneId < self.nbOfLoadedScenes:

            scene = self.scenes[sceneId]
            print('Producing scene ' + str(sceneId))
            sceneAudioSegment = AudioSegment.empty()

            sceneAudioSegment += AudioSegment.silent(duration=scene['silence_before'])
            for sound in scene['objects']:
                newAudioSegment = self._getLoadedAudioSegmentByName(sound['filename'])

                sceneAudioSegment += newAudioSegment

                # Insert a silence padding after the sound
                sceneAudioSegment += AudioSegment.silent(duration=sound['silence_after'])

            # FIXME : Background noise should probably constant ? The scene duration is constant so no need to regen everytime
            if self.withBackgroundNoise:
                backgroundNoise = WhiteNoiseGenerator(sample_rate=sceneAudioSegment.frame_rate).to_audio_segment(sceneAudioSegment.duration_seconds*1000)

                sceneAudioSegment = backgroundNoise.overlay(sceneAudioSegment, gain_during_overlay=-60)

            # Make sure the everything is in Mono (If stereo, will convert to mono)
            sceneAudioSegment.set_channels(1)

            # FIXME : Create the setType folder if doesnt exist
            sceneAudioSegment.export(os.path.join(self.audio_output_folder, '%s_%s_%06d.wav' % (self.outputPrefix, self.setType, sceneId)), format='wav')

            # Set figure settings to remove all axis
            spectrogram = plt.figure(frameon=False)
            spectrogram.set_size_inches(self.spectrogramSettings['height'], self.spectrogramSettings['width'])
            ax = plt.Axes(spectrogram, [0., 0., 1., 1.])
            ax.set_axis_off()
            spectrogram.add_axes(ax)

            # Generate the spectrogram
            # See https://matplotlib.org/api/_as_gen/matplotlib.pyplot.specgram.html?highlight=matplotlib%20pyplot%20specgram#matplotlib.pyplot.specgram
            # TODO : Use essentia to generate spectrogram, mfcc, etc ?
            Pxx, freqs, bins, im = plt.specgram(x=sceneAudioSegment.get_array_of_samples(), Fs=sceneAudioSegment.frame_rate,
                         window=matplotlib.mlab.window_hanning,
                         NFFT=self.spectrogramSettings['window_length'], noverlap=self.spectrogramSettings['window_overlap'], mode='magnitude', scale='dB')

            # FIXME : Create the setType folder if doesnt exist
            spectrogram.savefig(os.path.join(self.images_output_folder, '%s_%s_%06d.png' % (self.outputPrefix, self.setType, sceneId)), dpi=1)

            # Close and Clear the figure
            plt.close(spectrogram)
            spectrogram.clear()

        else:
            print("[ERROR] The scene specified by id '%d' couln't be found" % sceneId)

def mainPool():
    args = parser.parse_args()

    producer = AudioSceneProducer(outputFolder=args.output_folder,
                                  version_nb= args.output_version_nb,
                                  primarySoundsJsonFilename=args.primary_sounds_definition_filename,
                                  primarySoundFolderPath=args.primary_sounds_folder,
                                  setType=args.set_type,
                                  outputPrefix=args.output_filename_prefix,
                                  withBackgroundNoise=args.with_background_noise,
                                  spectrogramSettings={
                                      'height': args.spectrogram_height,
                                      'width': args.spectrogram_width,
                                      'window_length': args.spectrogram_window_length,
                                      'window_overlap': args.spectrogram_window_overlap,
                                  })

    idList = list(range(producer.nbOfLoadedScenes))

    # FIXME : The definition of the threads should be done inside the class

    # FIXME : Each process should load their composition sound instead of loading everything in memory here
    producer._loadAllPrimarySounds()

    # FIXME : All the process should probably not work from the same object attributes
    nbProcess = args.nb_process

    pool = Pool(processes=nbProcess)
    pool.map(producer.produceScene, idList)

    print("Job Done !")


if __name__ == '__main__':
    mainPool()
