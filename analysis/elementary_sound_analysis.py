import ujson
import numpy as np
import pandas as pd
import holoviews as hv
hv.extension('bokeh')

from scene_generation.scene_generator import Primary_sounds

def load_elementary_sounds_definition(elementary_sounds_definition_filepath):
  with open(elementary_sounds_definition_filepath, 'r') as f:
    definition = ujson.load(f)
  return definition


def main():
  primary_sounds_folderpath = '/NOBACKUP/jerome/datasets/good-sounds/filtered/akg'
  primary_sounds_definition_filename = 'elementary_sounds.json'

  print("Reading files")
  elementary_sounds = Primary_sounds(primary_sounds_folderpath, primary_sounds_definition_filename, 10)

  print("File readed")

  #dataframe = pd.DataFrame.from_dict(elementary_sounds.definition)

  # Setting up renderer
  #renderer = hv.renderer('bokeh')
  #print(renderer)

  #scatter = hv.Scatter(dataframe, 'instrument', 'duration')
  #renderer.server_doc(scatter)
  print("Done")


if __name__ == "__main__":
  main()
