
import ujson
from itertools import groupby

####### Questions Stats ###############

with open('./output/questions/AQA_V0.0.1_train_questions.json', 'r') as f:
    questions = ujson.load(f)['questions']

questions_by_images = {}

question_answer_count = {}

for question in questions:
    if question['image_filename'] not in questions_by_images:
        questions_by_images[question['image_filename']] = 1
    else:
        questions_by_images[question['image_filename']] += 1

    if question['answer'] not in question_answer_count:
        question_answer_count[question['answer']] = 1
    else:
        question_answer_count[question['answer']] += 1

less_than_30 = {}
for question_id, question_count in questions_by_images.items():
    if question_count < 30 :
        if question_count not in less_than_30:
            less_than_30[question_count] = [question_id]
        else:
            less_than_30[question_count].append(question_id)

nb_less_30 = sum(q < 30 for q in questions_by_images.values())

print(ujson.dumps(questions_by_images, indent=4, sort_keys=True))
print(ujson.dumps(question_answer_count, indent=4, sort_keys=True))

groups = {}
for key, group in groupby(questions_by_images, lambda x : questions_by_images[x]):
    if key not in groups:
        groups[key] = []
    groups[key] += list(group)

print(ujson.dumps(groups, indent=4, sort_keys=True))


####### Scenes Stats ###############

with open('./output/scenes/AQA_V0.1_train_scenes.json', 'r') as f:
    scenes = ujson.load(f)['scenes']

for scene in scenes:
    duration = 0
    duration += scene['silence_before']
    for sound in scene['objects']:
        duration += sound['duration']
        duration += sound['silence_after']

    print("Duration is : %f" % duration)

exit(0)


instrument_family_count = {}
pitch_count = {}
loudness_count = {}

scene_stats = {}

for i, scene in enumerate(scenes):
    scene_stats[i] = {
        'pitch_counts' : {},
        'loudness_counts' : {},
        'instrument_family_counts' : {}
    }


    groups = {}
    for key, group in groupby(scene['objects'], lambda x : x['pitch']):
        if key not in groups:
            groups[key] = []
        groups[key] += list(group)

    for sound in scene['objects']:
        if sound['pitch'] not in scene_stats[i]['pitch_counts']:
            scene_stats[i]['pitch_counts'][sound['pitch']] = 1
        else:
            scene_stats[i]['pitch_counts'][sound['pitch']] += 1

        if sound['loudness'] not in scene_stats[i]['loudness_counts']:
            scene_stats[i]['loudness_counts'][sound['loudness']] = 1
        else:
            scene_stats[i]['loudness_counts'][sound['loudness']] += 1

        if sound['instrument'] not in scene_stats[i]['instrument_family_counts']:
            scene_stats[i]['instrument_family_counts'][sound['instrument']] = 1
        else:
            scene_stats[i]['instrument_family_counts'][sound['instrument']] += 1

pitch_attr_count = {
    'acute' : {},
    'deep' : {}
}
attrs = pitch_attr_count.keys()
for i, scene in scene_stats.items():
    for attr in attrs:
        if scene['pitch_counts'][attr] not in pitch_attr_count[attr]:
            pitch_attr_count[attr][scene['pitch_counts'][attr]] = 1
        else:
            pitch_attr_count[attr][scene['pitch_counts'][attr]] += 1



#print(ujson.dumps(pitch_attr_count, indent=4, sort_keys=True))
#print("-------------------------------")
print(ujson.dumps(scene_stats[0], indent=4, sort_keys=True))
#print("Less than 30 %d" % nb_less_30)


print("Done")