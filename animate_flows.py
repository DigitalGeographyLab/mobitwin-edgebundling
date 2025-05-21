#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar 28 15:27:50 2025

@author: waeiski
"""

import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import contextily as ctx
import numpy as np
from matplotlib.colors import Normalize

# configure file paths
GPKG_PATH = "/path/to/geopackage.gpkg"   # Path to your GPKG file
OUTPUT_GIF_PATH = "/path/to/output.gif"  # Output GIF filename

# column names (adjust if different in your files) ---
GPKG_ORIGIN_ID_COL = 'orig_id'
GPKG_DEST_ID_COL = 'dest_id'
CSV_ORIGIN_ID_COL = 'orig_id'
CSV_DEST_ID_COL = 'dest_id'
CSV_COUNT_COL = 'COUNT'

# animation and style parameters ---
TOP_PERCENTILE_THRESHOLD = 0.95  # top 5% for moving dots
NUM_FRAMES = 120                 # number of frames in the animation loop
FPS = 30                         # frames per second for the output GIF
BASEMAP_SOURCE = ctx.providers.CartoDB.DarkMatter  # basemap style
FLOW_COLORMAP = 'viridis'        # colormap for line intensity
DOT_COLOR = 'lightcyan'          # color of the moving dots
DOT_SIZE = 2                     # size of the moving dots
MIN_LINEWIDTH = 0.5              # minimum linewidth for flows
MAX_LINEWIDTH = 1.5              # maximum linewidth for flows
MIN_ALPHA = 0.15                 # minimum alpha (transparency) for flows
MAX_ALPHA = 0.9                  # maximum alpha for flows (scaled by count)
GLOW_EFFECT_MULTIPLIER = 2.3     # for top 5%, draw slightly thicker base line


# main flow animation function
def create_flow_animation():
    print("1. Loading data...")
    try:
        gdf_lines = gpd.read_file(GPKG_PATH)
        gdf_lines = gdf_lines[[GPKG_ORIGIN_ID_COL,
                               GPKG_DEST_ID_COL,
                               'geometry']]
        df_flows = gpd.read_file(GPKG_PATH)
        df_flows = df_flows[[GPKG_ORIGIN_ID_COL, GPKG_DEST_ID_COL,
                             CSV_COUNT_COL]]
    except Exception as e:
        print(f"Error loading input files: {e}")
        return

    print(f"   Loaded {len(gdf_lines)} lines from GeoPackage.")
    print(f"   Loaded {len(df_flows)} flows from CSV.")

    # set up list of columns that must be in the data
    required_gpkg_cols = [GPKG_ORIGIN_ID_COL, GPKG_DEST_ID_COL, 'geometry']

    # validate the data
    if not all(col in gdf_lines.columns for col in required_gpkg_cols):
        print(f"Error: GPKG missing required columns: {required_gpkg_cols}")
        return

    # another list of required columns for the csv data
    required_csv_cols = [CSV_ORIGIN_ID_COL, CSV_DEST_ID_COL, CSV_COUNT_COL]

    # validate csv data
    if not all(col in df_flows.columns for col in required_csv_cols):
        print(f"Error: CSV missing required columns: {required_csv_cols}")
        return

    # check if count column is right type
    if not pd.api.types.is_numeric_dtype(df_flows[CSV_COUNT_COL]):
        print(f"Error: CSV count column '{CSV_COUNT_COL}' is not numeric.")
        return

    print("2. Merging and Preparing Data...")
    # ensure ID columns have the same data type for merging
    try:
        gdf_lines[GPKG_ORIGIN_ID_COL] = gdf_lines[GPKG_ORIGIN_ID_COL
                                                  ].astype(str)
        gdf_lines[GPKG_DEST_ID_COL] = gdf_lines[GPKG_DEST_ID_COL].astype(str)
        df_flows[CSV_ORIGIN_ID_COL] = df_flows[CSV_ORIGIN_ID_COL].astype(str)
        df_flows[CSV_DEST_ID_COL] = df_flows[CSV_DEST_ID_COL].astype(str)
    except Exception as e:
        print(f"Warning: Could not ensure consistent"
              f" ID types for merging: {e}")

    # merge flows with geometries
    gdf_merged = gdf_lines.merge(
        df_flows,
        left_on=[GPKG_ORIGIN_ID_COL, GPKG_DEST_ID_COL],
        right_on=[CSV_ORIGIN_ID_COL, CSV_DEST_ID_COL],
        how='inner'  # Only keep lines that have a corresponding flow count
    )

    if gdf_merged.empty:
        print("Error: No matching flows found between GeoPackage and "
              "CSV after merging.")
        return

    print(f"   Merged {len(gdf_merged)} flows with geometries.")

    # reproject to web mercator (EPSG:3857) for compatibility with
    # contextily basemaps
    print(f"   Original CRS: {gdf_merged.crs}")
    if gdf_merged.crs is None:
        print("Warning: No CRS defined. Assuming EPSG:4326 (WGS84).")
        gdf_merged.set_crs("EPSG:4326", inplace=True)

    try:
        gdf_merged = gdf_merged.to_crs(epsg=3857)
        print(f"   Reprojected to {gdf_merged.crs}.")
    except Exception as e:
        print(f"Error during reprojection: {e}. Check if the "
              f"original CRS is valid.")
        return

    # get thresholds and top flows
    count_threshold = gdf_merged[CSV_COUNT_COL
                                 ].quantile(TOP_PERCENTILE_THRESHOLD)
    gdf_top = gdf_merged[gdf_merged[CSV_COUNT_COL] >= count_threshold].copy(
        ).sort_values(by=['COUNT'])
    gdf_other = gdf_merged[gdf_merged[CSV_COUNT_COL] < count_threshold].copy()

    print(f"   Identified {len(gdf_top)} flows in the top "
          f"{100*(1-TOP_PERCENTILE_THRESHOLD):.0f}% "
          f"(Count >= {count_threshold:.2f}).")
    print(f"   {len(gdf_other)} flows in the lower percentile.")

    if gdf_top.empty:
        print("Warning: No flows met the top percentile threshold. "
              "No moving dots will be animated.")

    # normalize count data linearly
    norm = Normalize(vmin=gdf_merged[CSV_COUNT_COL].min(),
                     vmax=gdf_merged[CSV_COUNT_COL].max())
    cmap = plt.get_cmap(FLOW_COLORMAP)

    # function for getting style propertios
    def get_style_props(count):
        normalized = norm(count)
        # Apply non-linear scaling (e.g., power) to emphasize higher counts
        scaled_norm = normalized ** 0.5
        linewidth = MIN_LINEWIDTH + (MAX_LINEWIDTH -
                                     MIN_LINEWIDTH) * scaled_norm
        alpha = MIN_ALPHA + (MAX_ALPHA - MIN_ALPHA) * scaled_norm
        color = cmap(normalized)  # Color based on original normalization
        return linewidth, alpha, color

    print("3. Setting up Plot...")
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_aspect('equal')
    ax.axis('off')  # Turn off the axis border, ticks, and labels

    # plot base lines of top flows
    print("   Plotting base lines for top flows...")
    for _, row in gdf_top.sort_values(by=['COUNT']).iterrows():
        count = row[CSV_COUNT_COL]
        line = row['geometry']
        if line and line.geom_type == 'LineString':

            # slightly thicker/brighter for the animated lines' base
            lw, alpha, color = get_style_props(count)

            # apply glow effect multiplier
            glow_lw = lw * GLOW_EFFECT_MULTIPLIER
            glow_alpha = min(alpha * GLOW_EFFECT_MULTIPLIER, 0.95)  # Cap alpha

            # draw lines
            ax.plot(*line.xy, color=color, linewidth=glow_lw, alpha=glow_alpha,
                    zorder=10)

    # add basemap
    print("   Adding basemap...")
    try:
        # Set plot limits slightly padded BEFORE adding basemap
        minx, miny, maxx, maxy = gdf_merged.total_bounds
        pad = (maxx - minx) * 0.05  # 5% padding for a nicer map
        ax.set_xlim(minx - pad, maxx + pad)
        ax.set_ylim(miny - pad, maxy + pad)
        ctx.add_basemap(ax, source=BASEMAP_SOURCE, zoom='auto')
    except Exception as e:
        print(f"Warning: Could not add basemap: {e}. "
              f"Proceeding without basemap.")

    # animation preparation
    print("4. Preparing Animation...")
    # if gdf is not empty start plotting
    if not gdf_top.empty:

        # get starting locations
        initial_x = [p.x for p in gdf_top.geometry.iloc[0:0]]
        initial_y = [p.y for p in gdf_top.geometry.iloc[0:0]]

        # render the initial dot locations
        dots_scatter = ax.scatter(initial_x, initial_y, color=DOT_COLOR,
                                  s=DOT_SIZE, zorder=15, alpha=0.5)
    else:
        # no dots to animate
        dots_scatter = None

    # get geometries to list if they exist
    if not gdf_top.empty:
        line_geometries = gdf_top['geometry'].tolist()
    else:
        line_geometries = []

    # define init function for the animation
    def init():

        if dots_scatter:

            # create empty data
            dots_scatter.set_offsets(np.empty((0, 2)))
            return dots_scatter,

        # return empty list if no dots
        return []

    # function for updating a frame
    def update(frame):

        # if no line geometries return empty list
        if not line_geometries:
            return []

        # get the fraction for animation loop
        fraction = (frame % NUM_FRAMES) / float(NUM_FRAMES)

        # empty list to add the point movements
        points_xy = []

        # loop over lines
        for line in line_geometries:

            # check if line is correct
            if line and line.geom_type == 'LineString' and line.length > 0:

                # Interpolate point along the line
                interpolated_point = line.interpolate(fraction,
                                                      normalized=True)

                # add interpolated point to list
                points_xy.append([interpolated_point.x, interpolated_point.y])

        # check if list is not empty
        if points_xy:

            # create dots scatter and return it
            dots_scatter.set_offsets(np.array(points_xy))
            return dots_scatter,

        # else return empty list
        else:
            return []
    print("5. Creating and Saving Animation...")
    if not gdf_top.empty:

        # remove white space from figure
        fig.subplots_adjust(left=0, bottom=0, right=1, top=1,
                            wspace=None, hspace=None)

        # set animation object
        anim = FuncAnimation(
            fig,
            update,
            frames=NUM_FRAMES,
            init_func=init,
            repeat_delay=1000,
            interval=1000/FPS,  # Interval in milliseconds
            blit=True  # Use blitting for performance
        )

    else:

        # if no top flows, just save the static plot as a "GIF"
        print("   No top flows to animate. Saving static plot as GIF.")
        plt.savefig(OUTPUT_GIF_PATH, dpi=150, bbox_inches='tight')
        print(f"Static plot saved to {OUTPUT_GIF_PATH}")
        plt.close(fig)
        return

    # save the animation
    try:
        # use pillow writer for animation
        anim.save(OUTPUT_GIF_PATH, writer='pillow',
                  fps=FPS, dpi=50)  # Adjust dpi as needed

        print(f"Animation successfully saved to: {OUTPUT_GIF_PATH}")
    except Exception as e:
        print(f"\nError saving animation: {e}")
        print("This might be due to the animation writer "
              "(e.g., 'pillow' or 'imagemagick').")
        print("Ensure 'Pillow' is installed (`pip install Pillow`).")
        print("Alternatively, try installing 'imagemagick' and using "
              "writer='imagemagick'.")

    # Close the plot figure to free memory
    plt.close(fig)


# run the animation
create_flow_animation()
