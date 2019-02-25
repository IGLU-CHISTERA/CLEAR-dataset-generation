import plotly
import plotly.graph_objs as go
from plotly.offline import iplot
import plotly.io as pio


from utils.question_classifier import load_questions_with_program_beautified, get_all_question_type_percent, load_templates, get_all_template_type_percent
from analysis.answers_distribution import get_answer_distribution, get_answer_distribution_per_family, get_answer_distribution_per_family_patched, get_answer_distribution_per_family_patched_second
from analysis.scenes_stats import get_scene_distributions, load_scenes_beautified

families_colors = {
  'Brightness': "#E377C2",
  'Count': "#1F77B4",
  'Instrument': "#17BECF",
  'Loudness': '#2CA02C',
  'Musical Note': '#8C564B',
  'Position': '#D62728',
  'Position Global': '#BCBD22',
  'Yes/No': '#FF7F0E'
}

def get_answer_distribution_bar_graph(questions, show_legend=True):
  counter, answer_distribution_by_family = get_answer_distribution_per_family(questions)

  bars = []

  for family, value_freq in answer_distribution_by_family.items():
    x = []
    y = []

    the_iterator = list(value_freq.items())
    the_iterator.sort(key=lambda x: x[0])

    for value, freq in the_iterator:
      x.append(value)
      y.append(freq)

    bars.append(go.Bar(
      x=x,
      y=y,
      name=family,
      showlegend=show_legend,
      marker={
        'color': families_colors[family],
        'line': {
          'color': "#000000",
          'width': 0.5
        }
      })
    )

  bars.sort(key=lambda x:x['name'])

  # Moving the yes/no category before.. SUPER HACKISH.. Looks better this way
  yes_no_bar = bars.pop()
  bars.insert(4, yes_no_bar)

  return bars

def graph_answer_distribution_by_family_subplots(training_questions, validation_questions, test_questions, filename):
  print("Starting...")

  training_bars = get_answer_distribution_bar_graph(training_questions, show_legend=True)
  validation_bars = get_answer_distribution_bar_graph(validation_questions, show_legend=False)
  test_bars = get_answer_distribution_bar_graph(test_questions, show_legend=False)


  layout = go.Layout(barmode='group',
                     font={
                       'size':10
                     },
                     autosize=False,
                     margin={'r':0, 'l':0, 'b': 120,'t':0, 'pad':4},
                     yaxis={
                       'title': 'Frequency',
                       'range': [0, 0.08]
                     },
                     yaxis2={
                       'title': 'Frequency',
                       'range': [0, 0.08]
                     },
                     yaxis3={
                       'title': 'Frequency',
                       'range': [0, 0.08]
                     },
                     legend={'x':-.1, 'y':1.2, 'orientation': 'h'})

  fig = plotly.tools.make_subplots(rows=3, cols=1, subplot_titles=('Training', 'Validation', 'Test'))

  for i in range(len(training_bars)):
    fig.append_trace(training_bars[i], 1, 1)
    fig.append_trace(validation_bars[i], 2, 1)
    fig.append_trace(test_bars[i], 3, 1)

  fig.update({'layout':layout})

  plotly.offline.plot(fig, filename=filename + '.html')
  pio.write_image(fig, filename + '.pdf', scale=1, width=650, height=800)


def graph_all_answer_distribution_by_family(questions, filename):
  print("Starting...")
  counter, answer_distribution_by_family = get_answer_distribution_per_family(questions)

  bars = []

  count = 0

  for family, value_freq in answer_distribution_by_family.items():
    x = []
    y = []

    the_iterator = list(value_freq.items())
    the_iterator.sort(key=lambda x: x[0])

    for value, freq in the_iterator:
      x.append(value)
      y.append(freq)
      count += freq

    bars.append(go.Bar(
      x=x,
      y=y,
      name=family,
      marker={
        'line': {
          'color': "#000000",
          'width': 0.5
        }
      })
    )

  layout = go.Layout(barmode='group',
                     autosize=False,
                     margin={'r':0, 'l':0, 'b': 90,'t':0, 'pad':4},
                     yaxis={
                       'title': 'Frequency',
                       'showgrid': True,
                       'gridwidth':2,
                       'range': [0, 0.08]},
                     legend={'x':-.1, 'y':1.2, 'orientation': 'h'})
  layout.font.size=10
  fig = go.Figure(data=bars, layout=layout)

  plotly.offline.plot(fig, filename=filename + '.html')
  pio.write_image(fig, filename + '.pdf', scale=1, width=650, height=400)


def get_all_question_type_percent_sorted(questions):
  training_questions_type_percent = get_all_question_type_percent(questions)

  items = list(training_questions_type_percent.items())

  items.sort(key=lambda x: x[0])

  # FIXME : REMOVE THIS... SUPER HACKISH.. Look better this way

  counts = items.pop(1)

  items.append(counts)

  return [x[0] for x in items], [y[1] for y in items]


def graph_generated_question_type_distribution(training_questions, val_questions, test_questions, filename):
  training_x, training_y = get_all_question_type_percent_sorted(training_questions)
  val_x, val_y = get_all_question_type_percent_sorted(val_questions)
  test_x, test_y = get_all_question_type_percent_sorted(test_questions)

  train_bar_graph = go.Bar(
    x=training_x,
    y=training_y,
    marker={
      'color': '#2CA02C',
      'line': {
        'color': "#000000",
        'width': 0.5
      }
    },
    name='Training'
  )

  val_bar_graph = go.Bar(
    x=val_x,
    y=val_y,
    marker={
      'color': '#1F77B4',
      'line': {
        'color': "#000000",
        'width': 0.5
      }
    },
    name='Validation'
  )

  test_bar_graph = go.Bar(
    x=test_x,
    y=test_y,
    marker={
      'color': '#FF7F11',
      'line': {
        'color': "#000000",
        'width': 0.5
      }
    },
    name='Test'
  )

  layout = go.Layout(font={
                       'size':10
                     },
                     autosize=False,
                     margin={'r':50, 'l':50, 'b': 120,'t':50, 'pad':4},
                     xaxis={
                       'tickangle': 90
                     },
                     yaxis={
                       'visible': True,
                       'title': 'Frequency',
                       'showgrid': True,
                       'gridwidth': 2,
                       #'range': [0, 0.08]
                     },
                     showlegend=True,
                     legend={'x': -.1, 'y': 1.2, 'orientation': 'h'})

  fig = go.Figure(data=[train_bar_graph, val_bar_graph, test_bar_graph], layout=layout)

  fig.update({'layout': layout})

  plotly.offline.plot(fig, filename=filename + '.html')
  pio.write_image(fig, filename + '.pdf', scale=1, width=600, height=600)


def graph_generated_question_type_distribution_bck(training_questions, val_questions, test_questions, filename):
  training_x, training_y = get_all_question_type_percent_sorted(training_questions)
  val_x, val_y = get_all_question_type_percent_sorted(val_questions)
  test_x, test_y = get_all_question_type_percent_sorted(test_questions)

  train_bar_graph = go.Bar(
    x=training_x,
    y=training_y,
    marker={
      'color': '#8F33FF',
      'line': {
        'color': "#000000",
        'width': 0.5
      }
    }
  )

  val_bar_graph = go.Bar(
    x=val_x,
    y=val_y,
    marker={
      'color': '#FF545B',
      'line': {
        'color': "#000000",
        'width': 0.5
      }
    }
  )

  test_bar_graph = go.Bar(
    x=test_x,
    y=test_y,
    marker={
      'color': '#24FF6F',
      'line': {
        'color': "#000000",
        'width': 0.5
      }
    }
  )

  layout = go.Layout(
    title="<b>Question Type Distribution</b>",
    font={
                       'size':10
                     },
                     autosize=False,
                     margin={'r':50, 'l':50, 'b': 80,'t':50, 'pad':4},
                     yaxis={
                       'visible': True,
                       'title': 'Frequency',
                       'showgrid': True,
                       'gridwidth': 2,
                       #'range': [0, 0.08]
                     },
                    yaxis2={
                      'visible': True,
                      'title': 'Frequency',
                      'showgrid': True,
                      'gridwidth': 2,
                      # 'range': [0, 0.08]
                    },
                    yaxis3={
                      'visible': True,
                      'title': 'Frequency',
                      'showgrid': True,
                      'gridwidth': 2,
                      # 'range': [0, 0.08]
                    },
                     showlegend=False)

  fig = plotly.tools.make_subplots(rows=3, cols=1, subplot_titles=('Training', 'Validation', 'Test'))

  fig.append_trace(train_bar_graph, 1, 1)
  fig.append_trace(val_bar_graph, 2, 1)
  fig.append_trace(test_bar_graph, 3, 1)

  fig.update({'layout': layout})

  plotly.offline.plot(fig, filename=filename + '.html')
  pio.write_image(fig, filename + '.pdf', scale=1, width=600, height=700)



def get_template_type_percent_sorted(templates):
  training_questions_type_percent = get_all_template_type_percent(templates)

  items = list(training_questions_type_percent.items())

  items.sort(key=lambda x: x[0])

  # FIXME : REMOVE THIS... SUPER HACKISH.. Look better this way

  counts = items.pop(1)

  items.append(counts)

  return [x[0] for x in items], [y[1] for y in items]


def graph_template_type_distribution(templates, filename):
  templates_x, templates_y = get_template_type_percent_sorted(templates)

  bar_graph = go.Bar(
    x=templates_x,
    y=templates_y,
    marker={
      'color': '#FF8670',
      'line': {
        'color': "#000000",
        'width': 0.5
      }
    }
  )

  layout = go.Layout(font={
                       'size':10
                     },
                     title="<b style='background-color:red'>Template Type Distribution</b>",
                     autosize=False,
                     margin={'r':50, 'l':50, 'b': 120,'t':50, 'pad':4},
                     yaxis={
                       'visible': True,
                       'title': 'Frequency',
                       'showgrid': True,
                       'gridwidth': 2,
                       #'range': [0, 0.08]
                     },
                     xaxis={
                       'tickangle': 90
                     },
                     showlegend=False)

  fig = go.Figure(data=[bar_graph], layout=layout)

  plotly.offline.plot(fig, filename=filename + '.html')
  pio.write_image(fig, filename + '.pdf', scale=1, width=650, height=350)

def get_scene_distribution_bar_graph(scenes, color, name):
  instrument_dist, brightness_dist, loudness_dist, note_dist = get_scene_distributions(scenes)

  # Instrument
  items = list(instrument_dist.items())
  items.sort(key=lambda x:x[0])

  x = [j[0] for j in items]
  y = [i[1] for i in items]

  instrument_dist_bar_graph = go.Bar(
    x=x,
    y=y,
    marker={
      'color': color,
      'line': {
        'color': "#000000",
        'width': 0.5
      }
    },
    showlegend=True,
    name=name
  )

  # Brightness
  items = list(brightness_dist.items())
  items.sort(key=lambda x: x[0] if x[0] is not None else 'zzz')

  x = [j[0] for j in items]
  y = [i[1] for i in items]

  brightness_dist_bar_graph = go.Bar(
    x=x,
    y=y,
    marker={
      'color': color,
      'line': {
        'color': "#000000",
        'width': 0.5
      }
    },
    showlegend=False
  )

  # Loudness
  items = list(loudness_dist.items())
  items.sort(key=lambda x: x[0])

  x = [j[0] for j in items]
  y = [i[1] for i in items]

  loudness_dist_bar_graph = go.Bar(
    x=x,
    y=y,
    marker={
      'color': color,
      'line': {
        'color': "#000000",
        'width': 0.5
      }
    },
    showlegend=False
  )

  # Note
  items = list(note_dist.items())
  items.sort(key=lambda x: x[0])

  x = [j[0] for j in items]
  y = [i[1] for i in items]

  note_dist_bar_graph = go.Bar(
    x=x,
    y=y,
    marker={
      'color': color,
      'line': {
        'color': "#000000",
        'width': 0.5
      }
    },
    showlegend=False
  )

  return [instrument_dist_bar_graph, brightness_dist_bar_graph, loudness_dist_bar_graph, note_dist_bar_graph]


def graph_scene_distribution(training_scenes, val_scenes, test_scenes, filename):
  train_bars = get_scene_distribution_bar_graph(training_scenes, '#2CA02C', 'Training')
  val_bars = get_scene_distribution_bar_graph(val_scenes, '#1F77B4', 'Validation')
  test_bars = get_scene_distribution_bar_graph(test_scenes, '#FF7F11', 'Test')

  layout = go.Layout(
    barmode='group',
    font={'size':22},
    titlefont={'size': 32},
    autosize=False,
    margin={'r': 50, 'l': 50, 'b': 80, 't': 50, 'pad': 4},
    xaxis={
      'tickangle': 90
    },
    xaxis2={
      'tickangle': 90
    },
    xaxis3={
      'tickangle': 90
    },
    xaxis4={
      'tickangle': 90
    },
    yaxis={
      'visible': True,
      'title': 'Frequency',
      'showgrid': True,
      'gridwidth': 2,
      # 'range': [0, 0.08]
    },
    yaxis2={
      'visible': True,
      'title': 'Frequency',
      'showgrid': True,
      'gridwidth': 2,
      # 'range': [0, 0.08]
    },
    yaxis3={
      'visible': True,
      'title': 'Frequency',
      'showgrid': True,
      'gridwidth': 2,
      # 'range': [0, 0.08]
    },
    yaxis4={
      'visible': True,
      'title': 'Frequency',
      'showgrid': True,
      'gridwidth': 2,
      # 'range': [0, 0.08]
    },
    showlegend=True,
    legend={
      'x': -.1,
      'y': 1.2,
      'orientation': 'h'
    }
  )

  fig = plotly.tools.make_subplots(rows=2, cols=2, subplot_titles=('<b>Instrument Distribution</b>', '<b>Brightness Distribution</b>', '<b>Loudness Distribution</b>', '<b>Note Distribution</b>'), horizontal_spacing=0.15)

  fig.append_trace(train_bars[0], 1, 1)
  fig.append_trace(val_bars[0], 1, 1)
  fig.append_trace(test_bars[0], 1, 1)

  fig.append_trace(train_bars[1], 1, 2)
  fig.append_trace(val_bars[1], 1, 2)
  fig.append_trace(test_bars[1], 1, 2)

  fig.append_trace(train_bars[2], 2, 1)
  fig.append_trace(val_bars[2], 2, 1)
  fig.append_trace(test_bars[2], 2, 1)

  fig.append_trace(train_bars[3], 2, 2)
  fig.append_trace(val_bars[3], 2, 2)
  fig.append_trace(test_bars[3], 2, 2)

  fig.update({'layout': layout})

  for i in fig['layout']['annotations']:
    i['font'] = dict(size=28)

  plotly.offline.plot(fig, filename=filename + '.html')
  pio.write_image(fig, filename + '.pdf', scale=1, width=900, height=800)


def main():
  questions_path = "/home/jerome/dev/datasets-remote/v2.0.0_50k_scenes_40_inst-titan01/questions"
  scene_path = '/home/jerome/dev/datasets-remote/v2.0.0_50k_scenes_40_inst-titan01/scenes'
  template_path = 'question_generation/CLEAR_templates'

  training_questions, val_questions, test_questions = load_questions_with_program_beautified(questions_path, template_path)
  train_scenes, val_scenes, test_scenes = load_scenes_beautified(scene_path)
  templates = load_templates(template_path)

  all_scenes = train_scenes + val_scenes + test_scenes
  all_questions = training_questions + val_questions + test_questions

  # Graphing
  graph_answer_distribution_by_family_subplots(training_questions, val_questions, test_questions, 'answer_dist_by_family')

  graph_generated_question_type_distribution(training_questions, val_questions, test_questions, 'generated_question_type_dist')

  graph_template_type_distribution(templates, 'templates_type_dist')

  graph_scene_distribution(train_scenes, val_scenes, test_scenes, 'scene_dist')




if __name__ == "__main__":
  main()