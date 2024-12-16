#!/usr/bin/env python3

'''
This script

Expectations:
    
    Centroid CSV file where each centroid has a unique ID named 'NUTS_ID', and its coordinates
    in WGS 84 CRS in columns 'X' and 'Y'.
    
    Edge CSV file with 'ORIGIN' and 'DESTINATION' columns that correspond to IDs in centroid csv 'NUTS_ID', 
    'OD_ID' column that contains the origin and destination IDs joined by an underscore (_), and a 'COUNT'
    column describing the intensity of the flow as integers.
    
'''

from tqdm import tqdm
import pandas as pd
import functions
from numba.core.errors import NumbaDeprecationWarning, NumbaPendingDeprecationWarning
import warnings
import argparse

warnings.simplefilter('ignore', category=NumbaDeprecationWarning)
warnings.simplefilter('ignore', category=NumbaPendingDeprecationWarning)

############################################################################################
# ARGUMENTS AND PARAMETERS
############################################################################################

# initialize argument parser
ap = argparse.ArgumentParser()

# set up arguments
ap.add_argument("-c", "--centroid", required=True,
                help="Path to input CSV file with centroid IDs and coordinates.")

ap.add_argument("-e", "--edges", required=True,
                help="Path to input CSV file with edges between centroids (OD matrix).")

ap.add_argument("-ew", "--edgeweight", default=2, required=False,
                help="Weight for edges, weight = distance^edgeweight. Longer edges have larger weight. Default = 2")

ap.add_argument("-t", "--threshold", default=2, required=False,
                help="Threshold value to specify if edge will be bundled if not. Default = 2. \nIf threshold is 2, edge is not bundled if the bundled version is two times longer or more than original")

ap.add_argument("-o", "--output", required=True,
                help="Path to output geopackage file.")

# parse arguments
args = vars(ap.parse_args())

# read file
centroid_df = pd.read_csv(args['centroid'])
edge_df = pd.read_csv(args['edges'])

ew = args['edgeweight']  # edge weight parameter, weight = distance^d
k = args['threshold']  # if new detour is longer than k times the original line it is not bundled
n = 100  # number of sampling points in Bezier curves
draw_map = True  # Draw map for the underlying data
plot_3d = False  # Plot for use on sphere
smoothing = 2  # Smoothing parameter for Bezier curves
output_option = 1 # Choose drawing output file option

# get nodes and edges from centroids and edges
nodes, edges = functions.get_locations_data(ew, centroid_df, edge_df)

############################################################################################
# MAIN CYCLE
############################################################################################

control_point_lists = []
too_long = 0
no_path = 0
for edge in tqdm(edges, desc="Computing: "):
    if edge.lock:
        continue

    edge.skip = True

    source = nodes[edge.source]
    dest = nodes[edge.destination]

    path = functions.find_shortest_path(source, dest, nodes)

    if len(path) == 0:
        no_path += 1
        edge.skip = False
        continue

    original_edge_distance = source.distance_to(dest)
    new_path_length = sum([e.distance for e in path])

    if new_path_length > k * original_edge_distance:
        too_long += 1
        edge.skip = False
        continue

    for edge_in_path in path:
        edge_in_path.lock = True

    # Get control points for drawing
    control_point_lists.append(functions.get(source, dest, nodes, path, smoothing))
print('Control point lists',control_point_lists[:1])

############################################################################################
# DRAWING
############################################################################################
functions.draw(control_point_lists, nodes, edges, n, plot_3d, draw_map, centroid_df, output_option)

print(f"Out of {len(edges)} edges, {too_long} had too long detour and {no_path} had no alternative path.")