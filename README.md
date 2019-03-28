<p>
    <img src="./img/udes.jpg?raw=true" height="100" align="left">
    <img src="./img/iglu.jpg?raw=true" height="100" align="center">
    <img src="./img/kth.png?raw=true" height="100" align="right">
</p>

# CLEAR Dataset Generation<br>Compositional Language and<br>Elementary Acoustic Reasoning

We introduced the task of acoustic question answering (AQA) at [NeurIPS VIGIL Workshop 2018](https://nips2018vigil.github.io/static/papers/accepted/16.pdf) <br>
The first version of the dataset can be downloaded via [IEEE Dataport](https://ieee-dataport.org/open-access/clear-dataset-compositional-language-and-elementary-acoustic-reasoning)

The code in this repository will generate acoustic scenes and questions/answers for each of those scenes.<br>

## Overview of the generation process
1. Generation of the scenes definition.
2. Generation of the questions based on the scenes definition.
3. Production of the audio recordings of the scenes (Can also produce spectrograms if option provided)

![Process Overview](img/process_overview.png?raw=true)

If you find this code useful in your research then please cite

```
@inproceedings{abdelnour2018Clear,
  title={CLEAR: A Dataset for Compositional Language and Elementary Acoustic Reasoning},
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
./run_experiment.sh {VERSION_NB}
```

See **Default Arguments** section for a list of the default versions

By default, a folder named `output` will be created at the root of this repository.<br>
All generated files will be outputted in a sub-folder named `{VERSION_NB}` which has the following structure : 

```
- audio : Scene recordings (WAV format) separated by set
    - train
    - val
    - test
- questions : Question definitions (JSON format)
    - CLEAR_train_questions.json
    - CLEAR_val_questions.json
    - CLEAR_test_questions.json
- scenes : Scene definitions (JSON format)
    - CLEAR_train_scenes.json
    - CLEAR_val_scenes.json
    - CLEAR_test_scenes.json
- images : Scene spectrograms (PNG format) separated by set
    - train
    - val
    - test
- arguments : Copy of the arguments used at generation time (If run through run_generation.sh)
- logs : The whole generation process logs (If run through run_generation.sh)
```

## Default Arguments
The folder `arguments` at the root of this repository contains the arguments list for each part of the generation process.

They are divided by version (Simply create a new folder to add a new version with different arguments):
```
    - v1.0.0_1k_scenes_20_inst_per_scene
    - v1.0.0_1k_scenes_40_inst_per_scene
    - v1.0.0_10k_scenes_20_inst_per_scene
    - v1.0.0_10k_scenes_40_inst_per_scene
    - v1.0.0_50k_scenes_20_inst_per_scene
    - v1.0.0_50k_scenes_40_inst_per_scene
```

The versions are named according to the number of scene and question they generate.<br>
For example, the version `v1.0.0_50k_scenes_40_inst_per_scenes` will generate 50 000 scenes and 40 questions per scene for a total of 2 000 000 questions (Which are divided into training, validation and test sets). 

We recommend using the arguments files instead of passing the arguments one by one in the command line for ease of use.

See **Scene Generation**, **Question Generation** and **Scene production** sections for more info on their usage.

## Elementary Sounds
Each scenes is composed by assembling a serie of Elementary Sounds together (randomly sampled).<br>
The elementary sounds have been selected from the [Good-Sound Dataset](https://www.upf.edu/web/mtg/good-sounds) and can be found in the `elementary_sounds` folder of this repository.

In the first version of CLEAR, all elementary sounds are recordings of an instrument playing a single sustained note.

The elementary sounds bank can easily be extended by adding new sounds to the `elementary_sounds` folder and the `elementary_sounds.json` file.This allow to create new scenes with different types of sound (Environmental, speech, etc).

## 1. Scene Generation
To run the scene generation process manually with the default arguments :
```
 python generate_scenes_definition.py @arguments/{VERSION_NB}/generate_scenes_definition.args --output_version_nb {VERSION_NB}
```

The arguments can also be specified in the command line instead of using the argument file.<br>
To see a list of the available arguments, run :
```
 python generate_scenes_definition.py --help
``` 

Once the generation process is done, 3 JSON files (one for each set) will be outputted to `output/{VERSION_NB}scenes`.


## 2. Question Generation
The question generation process is strongly inspired from the [CLEVR dataset](http://cs.stanford.edu/people/jcjohns/clevr/) question generation [code](https://github.com/facebookresearch/clevr-dataset-gen).<br>
The question will be instantiated using the templates in `templates/question_templates`.

To run the question generation manually with the default arguments :

```
 python generate_questions.py @arguments/{VERSION_NB}/generate_{SET_TYPE}_questions.args --output_version_nb {VERSION_NB}
```

This will generate multiple JSON files in `output/{VERSION_NB}/questions/TMP_{SET_TYPE}`.

To merge those files into 1 questions files, run :
```
 python scripts/consolidate_questions.py --set_type {SET_TYPE} --output_version_nb {VERSION_NB}
```

This process has to be ran 3 times : One for each set of scenes (training, validation ,test)

As with previous processes, the arguments can be specified in the command line instead of using the argument file<br>
To see a list of the available arguments, run :
``` 
 python generate_questions.py --help
```

## 3. Scene Production
The last step is to produce the scenes audio recordings from the scene definition files.

To run the scene production manually with the default arguments :
```
 python produce_scenes_audio.py @arguments/{VERSION_NB}/produce_{SET_TYPE}_scenes_audio.args --output_version_nb {VERSION_NB}
```

Audio files will be stored in `output/{VERSION_NB}/audio/{SET_TYPE}`. If the option to generate spectrograms is enabled, they will be stored in `output/{VERSION_NB}/images/{SET_TYPE}`

As with the question generation, this process had to be ran 3 times : One for each set of scenes.

To see a list of the available arguments, run :
```
 python produce_scenes_audio.py --help
```
