"""
Try to give an analysis of topics from a downloaded mural,
where the download is a set of sticky notes with text,
color, and position.
"""
import csv
import itertools
import sys
from dataclasses import dataclass, asdict
from enum import StrEnum
from itertools import combinations
from math import sqrt
import logging

logger = logging.getLogger(__name__)


import networkx as nx
import pandas as pd


@dataclass
class Analysis:
    team_name: str
    topic: str
    population: int
    score: int
    red_text: str
    yellow_text: str
    green_text: str


class Field(StrEnum):
    """ Field names for the sticky notes DF from Mural"""
    TEXT = 'Text'
    DATA = "data"
    ID = 'ID'
    BG_COLOR = "BG Color"
    X = 'Position X'
    Y = 'Position Y'


def drop_unused_columns(raw_df):
    result_df = raw_df.drop(axis='columns', labels=[
        'Sticky type',
        'Border line',
        'Area',
        'Link to',
        'Last Updated By',
        'Last Updated',
        'Tags',
        'Integration Labels'])
    return result_df


def replace_rgb_codes_with_names(input_df):
    # As given, we have color numbers. We'd like these to be
    # names and numbers we can relate to (as we don't "see"
    # rgb codes).
    color_map = {
        '#459C5B': '1-DarkGreen',
        '#AAED92': '2-LightGreen',
        '#FCF281': '3-Yellow',
        '#FFC061': '4-Orange',
        '#E95E5E': '5-DarkRed',
        '#86E6D9': 'Team-Label',
        '#FFFFFF': 'Topic-Label'
    }
    out_df = input_df.replace({Field.BG_COLOR: color_map})
    out_df['Disagreement'] = out_df[Field.BG_COLOR].str[0]
    return out_df


def distance(left: dict, right: dict) -> float:
    left_x, left_y = left[Field.X], left[Field.Y]
    right_x, right_y = right[Field.X], right[Field.Y]
    return sqrt((left_x - right_x) ** 2 + (left_y - right_y) ** 2)


def build_connection_graph(df):
    stickies_list = list(df.to_dict(orient='records'))
    label_texts = ['Team-Label', 'Topic-Label']
    labels_only = [x for x in stickies_list if x[Field.BG_COLOR] in label_texts]
    notes_only = [x for x in stickies_list if x[Field.BG_COLOR] not in label_texts]
    label_ids = {item[Field.ID] for item in labels_only}

    graph = nx.Graph()

    # First mate labels to nearest notes
    label_proximity = [(distance(label, note), label, note)
                       for (label, note) in itertools.product(labels_only, notes_only)]
    label_proximity = sorted(label_proximity, key=lambda x: x[0])
    labels_connected = set()
    for (_, label, note) in label_proximity:
        label_id = label[Field.ID]
        if label_id in labels_connected:
            continue
        labels_connected.add(label_id)

        graph.add_node(label_id, data=label)
        graph.add_edge(label_id, note[Field.ID], kind='labeling')

        if len(labels_connected) == len(labels_only):
            break

    # Mate notes to nearest other
    for sticky in notes_only:
        graph.add_node(sticky[Field.ID], data=sticky)

    raw_ticket_proximity = [
        (distance(left, right), left[Field.ID], right[Field.ID])
        for left, right in combinations(notes_only, r=2)
    ]
    sorted_ticket_proximity = sorted(raw_ticket_proximity)

    for _, left_id, right_id in sorted_ticket_proximity:
        graph.add_edge(left_id, right_id, kind='proximity')
        fewest_connections = min(value for key, value in graph.degree if key not in label_ids)
        if fewest_connections == 2:
            break
    return graph


def collect_text(sticky_group):
    text_fields = (note[Field.TEXT].rstrip('.') for note in sticky_group if isinstance(note[Field.TEXT], str))
    return ". ".join(text_fields)


def main(filename: str):
    stickies_df = pd.read_csv(filename)
    stickies_df = drop_unused_columns(stickies_df)
    stickies_df = replace_rgb_codes_with_names(stickies_df)
    graph = build_connection_graph(stickies_df)

    analyses = []

    groups = list(nx.connected_components(graph))
    for number, group in enumerate(groups):
        sticky_group = [graph.nodes[node_id]['data'] for node_id in group]

        team_name = topic = ""
        extra_names = []
        extra_topics = []
        try:
            [team_name, *extra_names] = [node[Field.TEXT] for node in sticky_group if
                                         node[Field.BG_COLOR] == 'Team-Label']
        except ValueError:
            logger.warning("Group {number} missing a team name label")
            team_name = "no team name attached"

        try:
            [topic, *extra_topics] = [node[Field.TEXT] for node in sticky_group if
                                      node[Field.BG_COLOR] == 'Topic-Label']
        except ValueError:
            logger.warning(f"Group {number} missing a topic")
            topic = "no topic attached."

        if extra_names or extra_topics:
            logger.warning(f"too many labels for: {team_name} {extra_names}, {topic} {extra_topics}")

        sticky_group = [sticky
                        for sticky in sticky_group
                        if 'Label' not in sticky[Field.BG_COLOR]
                        ]
        population = len(sticky_group)

        # Analyze based on sticky note background colors
        backgrounds = [note[Field.BG_COLOR] for note in sticky_group]
        darkgreen = backgrounds.count('1-DarkGreen')
        lightgreen = backgrounds.count('2-LightGreen')
        yellow = backgrounds.count('3-Yellow')
        orange = backgrounds.count('4-Orange')
        darkred = backgrounds.count('5-DarkRed')
        score = ((darkred * 0) + (orange * 25) + (yellow * 50) + (lightgreen * 75) + (darkgreen * 100)) // population

        positive_colors = ['1-DarkGreen', '2-LightGreen']
        negative_colors = ['4-Orange', '5-Darkred']
        positive_text = collect_text(x for x in sticky_group if x[Field.BG_COLOR] in positive_colors)
        neutral_text = collect_text(x for x in sticky_group if x[Field.BG_COLOR] == '3-Yellow')
        negative_text = collect_text(x for x in sticky_group if x[Field.BG_COLOR] in negative_colors)

        analyses.append(Analysis(
            team_name=team_name,
            topic=topic,
            population=population,
            score=score,
            red_text=negative_text,
            yellow_text=neutral_text,
            green_text=positive_text
        ))

    writer = csv.DictWriter(sys.stdout,
                            ['team_name', 'topic', 'score', 'population', 'green_text', 'yellow_text', 'red_text'])
    writer.writeheader()
    writer.writerows(asdict(x) for x in analyses)

if __name__ == '__main__':
    main('FullMap.csv')
