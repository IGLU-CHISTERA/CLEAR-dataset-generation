import ujson
import os
import re
from question_generation import question_engine as qeng


def initialize_question_engine(metadata_path):
    with open(metadata_path, 'r') as f:
        metadata = ujson.load(f)

    max_scene_length = 10
    instrument_count = {}

    for instrument in metadata['attributes']['instrument']['values']:
      instrument_count[instrument] = max_scene_length

    qeng.instantiate_attributes_handlers(metadata, instrument_count, max_scene_length)

    return metadata


def load_templates(template_dir):
    # Load templates from disk
    # Key is (filename, file_idx)
    num_loaded_templates = 0
    templates = {}
    for fn in os.listdir(template_dir):
        if not fn.endswith('.json'): continue
        with open(os.path.join(template_dir, fn), 'r') as f:
            try:
                template_json = ujson.load(f)
                for i, template in enumerate(template_json):
                    num_loaded_templates += 1
                    key = (fn, i)
                    templates[key] = template

                    # Adding optionals parameters if not present. Remove the need to do null check when accessing
                    optionals_keys = ['constraints', 'can_be_null_attributes']
                    for op_key in optionals_keys:
                        if op_key not in template:
                            template[op_key] = []
            except ValueError:
                print(
                    "[ERROR] Could not load template %s" % fn)  # FIXME : We should probably pause or do something to inform the user. This message will be flooded by the rest of the output. Maybe do a pause before generating ?
    print('Read %d templates from disk' % num_loaded_templates)
    return templates


def load_synonyms(synonyms_path):
    with open(synonyms_path, 'r') as f:
        return ujson.load(f)


def get_number_answers_from_type(metadata, output_type):
    if output_type == 'bool':
       return 2
    elif output_type == 'integer':
        return 11       # FIXME : Do not hardcode the length of the scene (10 object + the possibility of 0 objects)
    else:
        return len(metadata['attributes'][output_type]['values'])


def analyse_templates(templates, metadata):
    node_count_by_type = {}
    templates_stats = {}
    nb_template_total = len(templates.keys())
    for (filename, index), template in templates.items():
        stats = {}
        if filename not in templates_stats:
            templates_stats[filename] = []

        stats['template_filename'] = filename
        stats['is_disabled'] = template['disabled']
        stats['has_note'] = 'note' in template or 'notes' in template
        stats['nb_constraint'] = len(template['constraints'])
        stats['nb_text'] = len(template['text'])
        stats['nb_can_be_null_attributes'] = len(template['can_be_null_attributes'])
        stats['terminal_node_type'] = template['nodes'][-1]['type']
        stats['terminal_node_output_type'] = qeng.functions[stats['terminal_node_type']]['output']
        stats['nb_possible_answer'] = get_number_answers_from_type(metadata, stats['terminal_node_output_type'])

        # Node count
        stats['relation_count'] = 0
        stats['duration_count'] = 0
        stats['random_choose_count'] = 0
        stats['filter_count'] = 0
        stats['query_count'] = 0

        # Analyse nodes
        for node in template['nodes']:
            if 'relate' in node['type']:
                stats['relation_count'] += 1
            elif 'duration' in node['type']:
                stats['duration_count'] += 1
            elif 'filter' in node['type']:
                stats['filter_count'] += 1
            elif 'query' in node['type']:
                stats['query_count'] += 1
            elif 'randomly_choose_one' in node['type']:
                stats['random_choose_count'] += 1

            if node['type'] not in node_count_by_type:
                node_count_by_type[node['type']] = 1
            else:
                node_count_by_type[node['type']] += 1


        # FIXME : Add synonyms counting when it is applied to all the sentene
        # FIXME : Still, we won't have the synonyms for the value. Only the placeholder.
        # FIXME : I guess its a job for the Question Stats script

        # Analyse texts
        tmp_counter = {
            'optionals': [],
            'space_question_mark': [],
            'placeholder': []
        }

        # TODO : Could be interesting to track the occurence of certain word in the text template
        # TODO : Such as "scene"
        for text in template['text']:
            tmp_counter['optionals'].append(("\[\w+\]", text))

            tmp_counter['placeholder'].append(re.findall("<([a-zA-Z])+(\d)?>", text))

            # TODO : Count the number of each type of placeholder

            tmp_counter['space_question_mark'].append(len(re.findall(r'\s\?$', text)))

        # Verify if there is conflict
        placeholder_conflict = not all(x == tmp_counter['placeholder'][0] for x in tmp_counter['placeholder'])
        optional_conflict = not all(x == tmp_counter['optionals'][0] for x in tmp_counter['optionals'])
        space_question_mark_conflict = not all(x == tmp_counter['space_question_mark'][0] for x in tmp_counter['space_question_mark'])

        stats['has_conflict'] = placeholder_conflict or optional_conflict or space_question_mark_conflict

        templates_stats[filename].append(stats)

    return {
        'global' : {
            'nb_template_total': nb_template_total,
            'node_count_per_type': node_count_by_type
        },
        'per_template': templates_stats
    }


def get_template_text(templates):
    return [t['text'] for t in templates.values()]

def main():
    cwd = os.path.dirname(os.path.realpath(__file__))
    # FIXME : Take paths as argument
    template_dir = "question_generation/AQA_templates"
    #template_dir = "question_generation/AQA_templates_PASSING"
    #template_dir = "question_generation/AQA_templates_NOT_PASSING"
    synonyms_path = "question_generation/synonyms.json"
    metadata_path = "metadata.json"

    templates = load_templates(template_dir)

    templates_text = get_template_text(templates)

    with open("./analysis/template_text.json", 'w') as f:
        ujson.dump(templates_text, f, indent=2)

    synonyms = load_synonyms(synonyms_path)
    metadata = initialize_question_engine(metadata_path)

    possible_answers = []

    for attribute_name, attribute_def in metadata['attributes'].items():
      if attribute_name.startswith('relate'):
        continue

      possible_answers += attribute_def['values']

    with open('./all_answers.json', 'w') as f:
      ujson.dump(possible_answers, f, indent=2)

    print('prout')
    #stats = analyse_templates(templates, metadata)

    #print(ujson.dumps(stats, indent=4, sort_keys=True))


if __name__ == "__main__":
    main()