import json
from scene_generation.scene_generator import Primary_sounds
import pydub


def main():
  elementary_sound_folder = '/NOBACKUP/jerome/datasets/good-sounds/filtered/akg'
  elementary_sound_definition_filename = 'elementary_sounds.json'

  print("Loading primary sounds")
  elementary_sounds = Primary_sounds(elementary_sound_folder, elementary_sound_definition_filename, 10)
  print("Primary sounds loaded")

  count_per_instrument = {}

  for sound in elementary_sounds.definition:
    if sound['instrument'] not in count_per_instrument:
      count_per_instrument[sound['instrument']] = {
        'above' : 0,
        'below' : 0
      }

    if sound['perceptual_loudness'] < -25:
      count_per_instrument[sound['instrument']]['below'] += 1
    else:
      count_per_instrument[sound['instrument']]['above'] += 1

  print(json.dumps(count_per_instrument, indent=2))

  nb_below_25db = sum(1 for e in elementary_sounds.definition if e['perceptual_loudness'] < -25)
  nb_above_25db = len(elementary_sounds.definition) - nb_below_25db

  print("Below -25db : %d --- Above -25db : %d" % (nb_below_25db, nb_above_25db))

  exit(0)


  amplification_range = [-5.0, -10.0, -15.0, -20.0, -25.0, -30.0]

  perceptual_loudness_per_amplification = {}

  for sound in elementary_sounds.definition:
    audioSegment = sound['audio_segment']

    if sound['instrument'] not in perceptual_loudness_per_amplification:
      print("New instrument : %s" % sound['instrument'])
      perceptual_loudness_per_amplification[sound['instrument']] = {}

    if sound['filename'] not in perceptual_loudness_per_amplification[sound['instrument']]:
      perceptual_loudness_per_amplification[sound['instrument']][sound['filename']] = {0.0: sound['perceptual_loudness']}

    for amplification in amplification_range:
      amplified_segment = audioSegment.apply_gain(amplification)
      perceptual_loudness_per_amplification[sound['instrument']][sound['filename']][amplification] = elementary_sounds._get_perceptual_loudness(amplified_segment)

  print(json.dumps(perceptual_loudness_per_amplification, indent=2, sort_keys=True))


if __name__ == '__main__':
  main()