#!/usr/bin/env python3

'''
This script bundles flows between centroids of regional polygons (e.g., NUTS).

Requirements:

Centroid CSV file where each centroid has a unique ID named column, and
its coordinates in WGS 84 CRS in columns 'X' and 'Y'.

Edge CSV file with 'ORIGIN' and 'DESTINATION' columns that correspond to unique 
IDs in centroid csv, 'OD_ID' column that contains the origin and destination
IDs joined by an underscore (_), and a 'COUNT' column describing the intensity
of the flow as integers.

Run the script:
    python bundle_edges.py -c /path/to/centroids.csv -id NUTS_ID -e /path/to/edges.csv -o /path/to/result.gpkg
'''

from tqdm import tqdm
import pandas as pd
import functions
from numba.core.errors import NumbaDeprecationWarning, NumbaPendingDeprecationWarning
import warnings
import argparse

# ignore some warnings for cleanliness
warnings.simplefilter('ignore', category=NumbaDeprecationWarning)
warnings.simplefilter('ignore', category=NumbaPendingDeprecationWarning)

###############################################################################
# ARGUMENTS AND PARAMETERS
###############################################################################

# initialize argument parser
ap = argparse.ArgumentParser()

# set up arguments
ap.add_argument("-c", "--centroid", required=True,
                help="Path to input CSV with centroid IDs and coordinates.")

ap.add_argument("-id", "--identifier", required=True,
                help="The column in centroid CSV that contains unique ID for "
                "the centroid.")

ap.add_argument("-e", "--edges", required=True,
                help="Path to input CSV with edges between centroids.")

ap.add_argument("-ew", "--edgeweight", default=2, required=False,
                help="Weight for edges, weight = distance^edgeweight. Longer "
                "edges have larger weight. Default = 2")

ap.add_argument("-t", "--threshold", default=2, required=False,
                help="Threshold value to specify if edge will be bundled if "
                "not. Default = 2. \nIf threshold is 2, edge is not bundled if"
                " the bundled version is two times longer or more than "
                "original")

ap.add_argument("-o", "--output", required=True,
                help="Path to output geopackage file.")

# parse arguments
args = vars(ap.parse_args())

# read file
centroid_df = pd.read_csv(args['centroid'])
edge_df = pd.read_csv(args['edges'])

# edge weight parameter, weight = distance^d, if new detour is longer than
# k times the original line it is not bundled
ew = args['edgeweight']

# threshold for how long a detour is allowed to be
k = args['threshold']

# assign identifier col and set it as string
id_col = str(args['identifier'])

# number of sampling points in Bezier curves
n = 100

# draw map for the underlying data
draw_map = True

# plot 3d for spheres, legacy code from xpeterk1, NOT IN USE IN THIS TOOL
plot_3d = False

# smoothing parameter for Bezier curves
smoothing = 2

# get nodes and edges from centroids and edges
nodes, edges = functions.get_locations_data(ew, centroid_df, edge_df, id_col)

###############################################################################
# MAIN CYCLE
###############################################################################

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
    control_point_lists.append(functions.get(
        source, dest, nodes, path, smoothing))
print('Control point lists', control_point_lists[:1])

###############################################################################
# DRAWING
###############################################################################
functions.draw(control_point_lists, nodes, edges, n, plot_3d,
               draw_map, centroid_df, output=args['output'], id_col=id_col)

print(f"[INFO] - Out of {len(edges)} edges, {
      too_long} had too long detour and {no_path} had no alternative path.")
print("[INFO] - ... done!")
