#!/usr/bin/env python3

'''
This script has the slightly modified model.py file from:
https://github.com/xpeterk1/edge-path-bundling/blob/main/Edge%20Path%20Bundling%20Python/model.py
'''

import math

# instantiate the Edge class and its attributes


class Edge:

    def __init__(self, source, destination, od_id, count):
        self.source = source
        self.destination = destination
        self.od_id = od_id
        self.count = count
        self.distance = -1
        self.weight = -1
        self.skip = False
        self.lock = False

# instantiate the Node class and its attributes


class Node:

    def __init__(self, id, longitude, latitude, name):
        self.id = id
        self.longitude = longitude
        self.latitude = latitude
        self.name = name
        self.edges = []

        # dijkstra related attributes
        self.distance = -1
        self.visited = False
        self.previous = None
        self.previous_edge = None

    def distance_to(self, other) -> float:
        return math.sqrt(pow(other.longitude - self.longitude, 2) +
                         pow(other.latitude - self.latitude, 2))

    def __lt__(self, other):
        return self.id < other.id

    def __gt__(self, other):
        return self.id > other.id

    def __le__(self, other):
        return self.id <= other.id

    def __ge__(self, other):
        return self.id >= other.id
