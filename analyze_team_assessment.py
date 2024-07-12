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
    TEXT = 'Text'
    DATA = "data"
    ID = 'ID'
    BG_COLOR = "BG Color"
    X = 'Position X'
    Y = 'Position Y'


ID = Field.ID
BG_COLOR = Field.BG_COLOR

stickies_df = pd.read_csv('~/Assessment Findings - All Quotes.csv')
stickies_df.drop(inplace=True, axis='columns', labels=[
    'Sticky type',
    'Border line',
    'Area',
    'Link to',
    'Last Updated By',
    'Last Updated',
    'Tags',
    'Integration Labels'])

# As given, we have color numbers. We'd like these to be
# names and numbers we can relate to (as we don't "see"
# rgb codes).
color_map = {
    '#459C5B': '1-DarkGreen',
    '#AAED92': '2-LightGreen',
    '#FCF281': '3-Yellow',
    '#FFC061': '4-Orange',
    '#E95E5E': '5-DarkRed',
}
stickies_df.replace({BG_COLOR: color_map}, inplace=True)
stickies_df['Disagreement'] = stickies_df[BG_COLOR].str[0]


def distance(left: dict, right: dict) -> float:
    left_x, left_y = left[Field.X], left[Field.Y]
    right_x, right_y = right[Field.X], right[Field.Y]
    return sqrt((left_x - right_x) ** 2 + (left_y - right_y) ** 2)


stickies_list = list(stickies_df.to_dict(orient='records'))
raw_distances = [
    (distance(left, right), left[ID], right[ID])
    for left, right in combinations(stickies_list, 2)
]
distances = sorted(raw_distances, key=lambda x: x[0])

# My idea is that we
# a. add all stickies to a graph as nodes
graph = nx.Graph()
for sticky in stickies_list:
    graph.add_node(sticky[ID], data=sticky)

# b. add edges, shortest-distance-first, until there are no unconnected nodes
for dist, left, right in distances:
    graph.add_edge(left, right)
    unconnected_nodes = [node_id for node_id, connections in graph.degree if connections == 0]
    if len(unconnected_nodes) == 0:
        break

# c. Show all connected groups.
scoring = []
for number, group in enumerate(nx.connected_components(graph)):
    sticky_group = [graph.nodes[id][Field.DATA] for id in group]

    population = len(sticky_group)

    # Analyze based on sticky note background colors
    backgrounds = [note[Field.BG_COLOR] for note in sticky_group]
    darkgreen = backgrounds.count('1-DarkGreen')
    lightgreen = backgrounds.count('2-LightGreen')
    yellow = backgrounds.count('3-Yellow')
    orange = backgrounds.count('4-Orange')
    darkred = backgrounds.count('5-DarkRed')

    # Calculate score
    score = ((darkred * 0) + (orange * 25) + (yellow * 50) + (lightgreen * 75) + (darkgreen * 100)) // population

    # Overt sentiment analysis
    positive = int((lightgreen + darkgreen) / population * 100)
    neutral = int(yellow / population * 100)
    negative = int((darkred + orange) / population * 100)

    combined_text = ". ".join(note[Field.TEXT].rstrip('.')
                             for note in sticky_group
                             if isinstance(note[Field.TEXT], str)
                             )

    # Use TextBlob to analyze combined text of all comments
    discussion = TextBlob(combined_text)

    # Report...
    print(f"Group #{number}")
    print(f"   {population} total responses")
    print(f"   Score: {score}")
    print(f"   +{positive}% {neutral}% -{negative}%")
    print(f"   Topics: {discussion.noun_phrases}")
    print(f"   Sentiment: {discussion.sentiment_assessments}")
    group_members_by_color = sorted(sticky_group, key=lambda x: x[BG_COLOR])
    for sticky in group_members_by_color:
        mural_id = sticky[ID]
        x = sticky[Field.X]
        y = sticky[Field.Y]
        mural_color = sticky[Field.BG_COLOR]
        text = sticky[Field.TEXT]
        print(f"   {mural_id}, ({x}, {y}), {mural_color}, \"{text}\"")
    print("\n")

    scoring.append( [number,score])

for(group_number, score) in scoring:
    print(f"{group_number}: {score}")

# d. Push group assignment back into the df
