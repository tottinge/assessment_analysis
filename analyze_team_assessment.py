"""
Try to give an analysis of topics from a downloaded mural,
where the download is a set of sticky notes with text,
color, and position.
"""
from enum import StrEnum
from itertools import combinations
from math import sqrt

import networkx as nx
import pandas as pd
from textblob import TextBlob


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
    raw_distances = [
        (distance(left, right), left[Field.ID], right[Field.ID])
        for left, right in combinations(stickies_list, 2)
    ]
    distances = sorted(raw_distances, key=lambda node: node[0])
    graph = nx.Graph()
    for sticky in stickies_list:
        graph.add_node(sticky[Field.ID], data=sticky)
    for dist, left, right in distances:
        graph.add_edge(left, right)
        least_connections = min(dict(graph.degree).values())
        if least_connections == 2:
            break
    return graph


def check_sentiment(sticky_group):
    text_fields = (note[Field.TEXT].rstrip('.') for note in sticky_group if isinstance(note[Field.TEXT], str))
    combined_text = ". ".join(text_fields)
    discussion = TextBlob(combined_text)
    return discussion


def generate_group_id(sticky_group, number) -> str:
    group_id: str = ""
    try:
        [team_name] = [node[Field.TEXT] for node in sticky_group if node[Field.BG_COLOR] == 'Team-Label']
        [topic] = [node[Field.TEXT] for node in sticky_group if node[Field.BG_COLOR] == 'Topic-Label']
        group_id = f'{team_name}-{topic}'
    except ValueError:
        group_id = f"Group #{number}"
        print(f"NO ID GENERATED FOR {group_id}")
        for sticky in sticky_group:
            print("...\t", sticky[Field.BG_COLOR], sticky[Field.ID], sticky[Field.TEXT])
    return group_id


def main(filename: str):
    stickies_df = pd.read_csv(filename)
    stickies_df = drop_unused_columns(stickies_df)
    stickies_df = replace_rgb_codes_with_names(stickies_df)
    graph = build_connection_graph(stickies_df)
    # c. Show all connected groups.
    scoring = []
    groups = list(nx.connected_components(graph))
    for number, group in enumerate(groups):
        sticky_group = [graph.nodes[node_id][Field.DATA] for node_id in group]
        group_id = generate_group_id(sticky_group, number)
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
        positive_discussion = check_sentiment( x for x in sticky_group if x[Field.BG_COLOR] in positive_colors)
        negative_discussion = check_sentiment( x for x in sticky_group if x[Field.BG_COLOR] in negative_colors)

        print(f"Group {group_id}")
        print(f"   {population} total responses")
        print(f"   Score: {score}")
        print(f"   Positive Topics: {positive_discussion.noun_phrases}")
        print(f"   Negative Topics: {negative_discussion.noun_phrases}")
        group_members_by_color = sorted(sticky_group, key=lambda member: member[Field.BG_COLOR])
        for sticky in group_members_by_color:
            mural_color = sticky[Field.BG_COLOR]
            text = sticky[Field.TEXT]
            print(f"   {mural_color}, \"{text}\"")
        print("\n")

        scoring.append([group_id, score])
    for (group_id, score) in scoring:
        print(f"{group_id}: {score}")


if __name__ == '__main__':
    main('PartialMap.csv')
