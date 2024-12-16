#!/usr/bin/env python3

'''
This script hosts functions used in edge bundling, most are original from https://github.com/xpeterk1/edge-path-bundling
However, some we have changed to improve modularity and user convenience
'''

import numpy as np
import pandas as pd
import geopandas as gpd
from model import Edge, Node
from typing import List
import heapq
from numba import jit
from shapely.geometry import Point, LineString
import matplotlib.pyplot as plt
from tqdm import tqdm

# function for
def split(points, smoothing):
    p = points
    # for each level of smoothing, insert new control point in the middle of all points already in the array
    # loop starts from 1 => smoothing level of 1 keeps only node points
    for smooth in range(1, smoothing):
        new_points = []
        for i in range(len(p) - 1):
            new_point = np.divide(p[i] + p[i + 1], 2.0)
            new_points.append(p[i])
            new_points.append(new_point)
        new_points.append(p[-1])
        p = new_points
    return p

# funtiong to retrieve flows
def get(source, dest, nodes, path, smoothing):
    control_points = []
    current_node = source
    for edge_in_path in path:
        control_points.append(np.array([current_node.longitude, current_node.latitude]))

        other_node_id = edge_in_path.destination if edge_in_path.source == current_node.id else edge_in_path.source
        current_node = nodes[other_node_id]
    
    control_points.append(np.array([dest.longitude, dest.latitude]))
    return split(control_points, smoothing)

# funtion to create a mapping between unique locations and unique integer IDs
def create_ids(dataframe, id_col):
        
    # Create a object of unique locations (union of ORIGIN and DESTINATION)
    unique_locations = dataframe.drop_duplicates(subset=[id_col])

    # Create a mapping between unique locations and consecutive integers
    location_mapping = dict(zip(unique_locations[id_col], range(1, len(unique_locations) + 1)))
        
    return location_mapping

# load locations and prepare them for edge bundling
def get_locations_data(edgeweight, centroid_csv, edge_df):
    """
    Read in centroids and edges between centroids, and process them so they're ready for edge-path bundling.
    """
    
    # Load data into dataframes
    nodes_list = centroid_csv
    edges_list = edge_df

    nodes = {}
    edges = []
    
    #nodes_list['id'] = nodes_list.reset_index().index + 1 
    node_ids = create_ids(nodes_list)

    # Load nodes into dict. Maps ID -> Node instance
    for index, row in nodes_list.iterrows():
        idx = node_ids[row['NUTS_ID']]
        name = row['NUTS_ID']
        lat = row['Y']
        long = row['X']
        nodes[idx] = Node(idx, long, lat, name)

    # Load edges to list
    for index, row in edges_list.iterrows():
        so = node_ids[row['ORIGIN']]
        dest = node_ids[row['DESTINATION']]
        od_id = row['OD_ID']
        count = row['COUNT']
        edges.append(Edge(source=so, destination=dest, od_id=od_id, count=count))
    
    # set iterator for edge removal
    calc_r = 0

    # Assign edges to nodes
    for edge in edges:

        # eliminate edges without nodes
        if edge.destination not in nodes or edge.source not in nodes:
            calc_r += 1
            edges.remove(edge)

        source = nodes[edge.source]
        dest = nodes[edge.destination]
        distance = source.distance_to(dest)

        edge.distance = distance
        edge.weight = pow(distance, edgeweight)

        source.edges.append(edge)
        dest.edges.append(edge)
    
    # print removed edges
    print('Total number of edges removed: ' + str(calc_r))

    # iterator for removed nodes
    calc_n = 0
    
    # Eliminate nodes without edges
    to_remove = [node.id for node in nodes.values() if len(node.edges) == 0]
    for key in to_remove:
        calc_n += 1
        del nodes[key]
    
    # print removed node count
    print('Nodes removed: '+str(calc_n))
    
    # print nodes values
    print(nodes.values())

    # Sort edges inside nodes in ascending order
    for node in nodes.values():
        node.edges.sort(key=lambda x: x.distance)

    # Sort edges
    edges.sort(key=lambda x: x.weight, reverse=True)
    print(edges[0].source)
    print(edges[0].destination)
    print(edges[0].od_id)
    print('Origin node name: ' + str(nodes[edges[0].source].name) + ' , origin node id: ' + str(nodes[edges[0].source].id) + '\nDestination node name: ' + str(nodes[edges[0].destination].name) + ', dest origin id: ' + str(nodes[edges[0].destination].id))
    return nodes, edges

# function to find shortest path
def find_shortest_path(source: Node, dest: Node, nodes) -> List[Edge]:
    # reset nodes
    for node in nodes.values():
        node.distance = 99999999999999
        node.visited = False
        node.previous = None
        node.previous_edge = None

    source.distance = 0
    queue = []
    heapq.heappush(queue, (source.distance, source))

    while not len(queue) == 0:
        next_node = heapq.heappop(queue)[1]
        next_node.visited = True

        for edge in next_node.edges:
            if edge.skip:
                continue

            other_id = edge.destination if edge.source == next_node.id else edge.source
            other = nodes[other_id]

            current_distance = next_node.distance + edge.weight

            if current_distance < other.distance:
                other.distance = current_distance
                other.previous = next_node
                other.previous_edge = edge
                heapq.heappush(queue, (other.distance, other))
                
        # Already found the destination, no need to continue with the search
        if next_node == dest:
            break
        
    # extract path
    path = []
    
    node = dest
    while node.previous is not None:
        path.append(node.previous_edge)
        node = node.previous
        
    path.reverse()
    return path


# function to draw the bezier curves
def draw(control_points, nodes, edges, n, use_3d, draw_map, centroid_df, output):

    if draw_map:
        
        # assign nodes
        nodes_list = centroid_df
        
        # Get geometry list from nodes
        geometry = [Point(xy) for xy in zip(nodes_list['X'], nodes_list['Y'])]
        
        geo_df = gpd.GeoDataFrame(nodes_list, crs='epsg:4326', geometry=geometry)
        #testaan miltä näyttää koordinaatit orig/dest-sovitusta varten 1
        print('\nNODE_LIST ALKU \n',geo_df.head())
        
    else:
        plt.gcf().set_dpi(300)
        
    if use_3d: # not supported
        print('[INFO] - 3D not supported, check original repo by xpeterk1 for 3D functionality!')
        print('[INFO] - Exiting...')
        exit
    else:
        # create and bezier curves
        bezier_polygons = []
        for controlPoints in tqdm(control_points, desc="Drawing curves: "):
            polygon = create_bezier_polygon(controlPoints, n)  # returns list of 2d vectors
            bezier_polygons.append(polygon)
        
        # create a list for the first and last points of each bezier line
        cp_list = []
        
        # append points to list
        for poly in bezier_polygons:
            cp_list.append(np.array([poly[0], poly[-1]]))
        
        # create a dataframe from control points to create origin and destination coordinate points
        cp_df = pd.DataFrame(columns=['orig', 'dest'])
        
        # loop over control points list
        for cp in cp_list:
            
            # add values to df
            cp_df = cp_df.append({'orig': cp[0], 'dest': cp[1]}, ignore_index=True)
        
        # adding an index column to the OD dataframe
        cp_df['id'] = cp_df.index
        
        # adding orig_nuts and dest_nuts ID's for control_points for later on happening join
        for index, poly in cp_df.iterrows():
            for _, centroid in geo_df.iterrows():
                if (poly['orig'][0] == centroid['X']) and (poly['orig'][1] == centroid['Y']):
                    cp_df.at[index, 'orig_nuts'] = centroid['NUTS_ID']
        
        for index, poly in cp_df.iterrows():
            for _, centroid in geo_df.iterrows():
                if (poly['dest'][0] == centroid['X']) and (poly['dest'][1] == centroid['Y']):
                    cp_df.at[index, 'dest_nuts'] = centroid['NUTS_ID']
        
        # create list of bezier linestrings
        lines = []
        for poly in bezier_polygons:
            a = LineString(poly)
            lines.append(a)
        
        # create dataframe and geodataframe for bezier lines
        lines_df = pd.DataFrame(lines, columns=['geometry'])
        lines_gdf = gpd.GeoDataFrame(lines_df, crs='epsg:4326', geometry='geometry')
        
        # adding an index column to the lines dataframe
        lines_gdf['id'] = lines_gdf.index
        
        # merging orig_nuts and dest_nuts to lines_gdf
        merged_lines_gdf = lines_gdf.merge(cp_df[['id','orig_nuts','dest_nuts']], on='id', how='left')
        
        # generate od ids
        merged_lines_gdf['OD_ID'] = merged_lines_gdf['orig_nuts'] + '_' + merged_lines_gdf['dest_nuts']
        
        # empty list for dataframes
        straight_edges = []
        
        # draw lines without detour or with detour that was too long
        for edge in tqdm(edges, desc="Drawing lines: "):
            if edge.skip:
                continue
            
            # get nodes
            o = nodes[edge.source]
            d = nodes[edge.destination]
            
            # get names of nodes
            o_name = o.name
            d_name = d.name
                        
            # get count of flow for edge connecting the nodes
            count = edge.count
            
            # generate geometry for the edge
            line = LineString([Point([o.longitude, o.latitude]), Point([d.longitude, d.latitude])])
            
            # create dataframe
            straight_df = pd.DataFrame(columns=['orig_nuts', 'dest_nuts', 'OD_ID', 'COUNT', 'geometry'])
            
            # add row
            straight_df = straight_df.append({'orig_nuts': o_name,
                                              'dest_nuts': d_name,
                                              'OD_ID': o_name + '_' + d_name,
                                              'COUNT': count,
                                              'geometry': line}, ignore_index=True)
                    
            # add to list
            straight_edges.append(straight_df)
            
        # concatenate list to dataframe
        straights = pd.concat(straight_edges)
        
        # add orig and dest nuts
        straights['orig_nuts'] = straights['OD_ID'].apply(lambda x: x.split('_')[0])
        straights['dest_nuts'] = straights['OD_ID'].apply(lambda x: x.split('_')[1])
        
        # create geodataframe of straight lines
        straights = gpd.GeoDataFrame(straights, crs='epsg:4326', geometry='geometry')
        
        #testaan miltä näyttää koordinaatit orig/dest-sovitusta varten 2
        print('\nPRINTING straights head \n',straights.head(n=2))
        
        # get results
        results = merged_lines_gdf.append(straights, ignore_index=True)
        
        # save
        results.to_file(output, driver='GPKG')

# Check if we have enough control points
@jit(nopython=True)
def eval_bezier(control_points, t):
    '''
    # arguments: list of 2D-np.array, float
    # return list
    '''
    
    if len(control_points) < 2:
        return np.zeros(2)
    
    if t < 0 or t > 1:
        return np.zeros(2)
    if t == 0:
        return control_points[0]
    if t == 1:
        return control_points[-1]
    
    # Calculate the intermediate points
    points = control_points
    while len(points) > 1:
        intermediate_points = []
        for i in range(len(points)-1):
            p = (1 - t) * points[i] + t * points[i+1]
            intermediate_points.append(p)
        points = intermediate_points
    return points[0]


# create bezier polygon
@jit(nopython=True)
def create_bezier_polygon(control_points, n):
    '''
    # n = number of points to approximate curve
    # arguments: list of 2d-np.arrays , int
    # returns: list of 2d np.arrays (points) on the bezier curve
    '''
    
    if n < 2:
        return [control_points[0], control_points[-1]]
    points = []
    for i in range(n):
        points.append(eval_bezier(control_points, i/n))
    points.append(control_points[-1])
    return points
