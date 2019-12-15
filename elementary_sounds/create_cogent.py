import json
import random
from collections import defaultdict

# Set seed
random.seed(42)

# Load all elementary sounds
with open('elementary_sounds.json') as f:
    elementary_sounds = json.load(f)

# Group by instruments
by_instr = defaultdict(list)
for s in elementary_sounds:
    by_instr[s['instrument']].append(s)

# Randomly sample N sounds of each instrument
N = 4
cogent = [[], []]
for instr, sounds in by_instr.items():
    # FIXME : Random sampling doesn't ensure that all the attributes are present in either of the cogent versions
    sampled = random.sample(sounds, N)
    sampled_ids = [s['filename'] for s in sampled]

    cogent[0] += sampled
    others = [s for s in sounds if s['filename'] not in sampled_ids]
    cogent[1] += others

with open('elementary_sounds_cogent_train.json', 'w') as f:
    json.dump(cogent[1], f)

with open('elementary_sounds_cogent_eval.json', 'w') as f:
    json.dump(cogent[0], f)

