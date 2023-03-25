<p>
    <img src="./img/udes.jpg?raw=true" height="100" align="left">
    <img src="./img/iglu.jpg?raw=true" height="100" align="center">
    <img src="./img/kth.png?raw=true" height="100" align="right">
</p>

# CLEAR Dataset Generation<br>Compositional Language and<br>Elementary Acoustic Reasoning

We introduced the task of acoustic question answering (AQA) at [NeurIPS VIGIL Workshop 2018](https://nips2018vigil.github.io/) in [this paper](https://nips2018vigil.github.io/static/papers/accepted/16.pdf). <br>
The first version of the dataset can be downloaded via [IEEE Dataport](https://ieee-dataport.org/open-access/clear-dataset-compositional-language-and-elementary-acoustic-reasoning).

The code in this repository will generate acoustic scenes and questions/answers for each of those scenes.<br>

## Overview of the generation process
1. Generation of the scenes definition.
2. Generation of the questions based on the scenes definition.
3. Production of the audio recordings of the scenes (Can also produce spectrograms if option provided)

![Process Overview](img/process_overview.png?raw=true)

If you find this code useful in your research then please cite

```
@article{abdelnour2023NAAQA,
  title={{NAAQA}: A Neural Architecture for Acoustic Question Answering},
  author={Abdelnour, Jerome and Rouat, Jean and Salvi, Giampiero},
  journal={IEEE Transactions on Pattern Analysis and Machine Intelligence},
  year={2023},
  pages={4997--5009},
  volume={45},
  number={4}
}
@inproceedings{abdelnour2018Clear,
  title={{CLEAR}: A Dataset for Compositional Language and Elementary Acoustic Reasoning},
  author={Abdelnour, Jerome and Salvi, Giampiero and Rouat, Jean },
  maintitle={NeurIPS},
  booktitle={Visually Grounded Interaction and Language Workshop (VIGIL)},
  year={2018}
}
```

## Installation
This project was written in Python 3 on Ubuntu 18.04<br>
We recommend creating a virtual environment in order to keep clean dependencies<br>
Then, install the dependencies using the requirements.txt file
```
pip install -r requirements.txt
```

## Running the whole generation process
To run the whole generation process with the default configuration simply run
``` 
./generate_CLEAR_dataset.sh
```

By default, a folder named `output` will be created at the root of this repository.<br>
The generated files are separated in different folders :
```
    - CLEAR_50k : Scene definitions (JSON format)
        - CLEAR_train_scenes.json
        - CLEAR_val_scenes.json
        - CLEAR_test_scenes.json

    - CLEAR_50k_4_inst : Question definitions (JSON format)
        - CLEAR_train_questions.json
        - CLEAR_val_questions.json
        - CLEAR_test_questions.

    - CLEAR_50k_audio : Scene recordings (FLAC format) separated by set
        - train
        - val
        - test

    - CLEAR_50k_4_inst_audio : Contains symlinks to the other folders. This link all the parts of the dataset
        - Useful to generate different version of the dataset with more or less scenes/questions without wasting space
```

The generated dataset reside in the folder `output/CLEAR_50k_4_inst_audio`

## Elementary Sounds
Each scenes is composed by assembling a serie of Elementary Sounds together (randomly sampled).<br>
The elementary sounds have been selected from the [Good-Sound Dataset](https://www.upf.edu/web/mtg/good-sounds) and can be found in the `elementary_sounds` folder of this repository.

In the first version of CLEAR, all elementary sounds are recordings of an instrument playing a single sustained note.

The elementary sounds bank can easily be extended by adding new sounds to the `elementary_sounds` folder and the `elementary_sounds.json` file.This allow to create new scenes with different types of sound (Environmental, speech, etc).

## 1. Scene Generation
To run the scene generation process manually with the default arguments :
```
 python generate_scenes_definition.py @arguments/base_scene_generation.args --nb_scene 50000 --output_version_nb CLEAR_50k
```

The arguments can also be specified in the command line instead of using the argument file.<br>
To see a list of the available arguments, run :
```
 python generate_scenes_definition.py --help
``` 

Once the generation process is done, 3 JSON files (one for each set) will be outputted to `output/CLEAR_50k/scenes`.


## 2. Question Generation
The question generation process is strongly inspired from the [CLEVR dataset](http://cs.stanford.edu/people/jcjohns/clevr/) question generation [code](https://github.com/facebookresearch/clevr-dataset-gen).<br>
The question will be instantiated using the templates in `templates/question_templates`.

To run the question generation manually with the default arguments :

```
 python generate_questions.py @arguments/base_question_generation.args --templates_per_scene 4 --output_version_nb CLEAR_50k_4_inst --set_type {train,val,test}
```

This will generate multiple JSON files in `output/CLEAR_50k_4_inst/questions/TMP_{train,val,test}`.

To merge those files into 1 questions files, run :
```
 python scripts/consolidate_questions.py --set_type {train,val,test} --output_version_nb CLEAR_50k_4_inst --remove_tmp
```

This process has to be ran 3 times : One for each set of scenes (training, validation ,test)

As with previous processes, the arguments can be specified in the command line instead of using the argument file<br>
To see a list of the available arguments, run :
``` 
 python generate_questions.py --help
```

## 3. Acoustic Scene Production
The last step is to produce the scenes audio recordings from the scene definition files.

To run the scene production manually with the default arguments :
```
 python produce_scenes_audio.py @arguments/base_audio_generation.args --output_version_nb CLEAR_50k_1024_win_50_overlap --spectrogram_window_length 1024 \
                                                                      --spectrogram_window_overlap 512 --set_type {train,val,test} --nb_process 2
```

Audio files will be stored in `output/CLEAR_50k_1024_win_50_overlap/audio/{train,val,test}`. If the option to generate spectrograms is enabled, they will be stored in `output/CLEAR_50k_1024_win_50_overlap/images/{train,val,test}`

As with the question generation, this process had to be ran 3 times : One for each set of scenes.

To see a list of the available arguments, run :
```
 python produce_scenes_audio.py --help
```
