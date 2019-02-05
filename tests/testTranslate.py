from utils.misc import float_array_to_pydub_audiosegment, pydub_audiosegment_to_float_array
from pydub import AudioSegment
from pydub.generators import WhiteNoise as WhiteNoiseGenerator
from utils.misc import generate_random_noise
from time import time


def main():
  testSound = AudioSegment.from_wav('/home/jerome/dev/Aqa-Dataset-Gen/elementary_sounds_16_bits/violin_F_akg.wav')
  #testSound = AudioSegment.from_wav('/home/jerome/dev/Aqa-Dataset-Gen/elementary_sounds/violin_F_akg.wav')
  orig = testSound.get_array_of_samples()
  before = time()
  for i in range(10):
    float_array = pydub_audiosegment_to_float_array(testSound, testSound.frame_rate, testSound.sample_width)

    reconstructedSegment = float_array_to_pydub_audiosegment(float_array, testSound.frame_rate, testSound.sample_width)

    reconstructed = reconstructedSegment.get_array_of_samples()

    #backgroundNoise = WhiteNoiseGenerator(sample_rate=testSound.frame_rate). \
    #  to_audio_segment(testSound.duration_seconds * 1000)

    #whiteNoise = generate_random_noise(testSound.duration_seconds * 1000, -20, testSound.frame_width, testSound.frame_rate)

    #new_overlayed = whiteNoise.overlay(testSound)
    print("Reconstructed")

  print("Took %f " % (time() - before))
  print("Done")



if __name__ == "__main__":
  main()