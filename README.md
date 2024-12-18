# Edge-bundling tool for regional flows
This repository hosts the scripts to perform edge-path bundling (Wallinger et al. 2022) for flow data. It's primary use case is to model flows across NUTS regions in Europe. It's inputs are two CSV files, one for point feature data and associated coordinates, and another for flows (edges) to be bundled. It outputs a GeoPackage file. The script expects the data to be in WGS84 coordinate reference system. The scripts in this repo are repurposed versions of the original scripts written by Peterka (2023).

![Map of flows between continental NUTS 2 regions across Europe](od_edgebund_vis.png)

## Requirements

The scripts within the repo require Python 3.10 or newer version with the following packages:

1. `pandas`
2. `geopandas`
3. `tqdm`
4. `shapely`

On top of these Python requirements, the script expects the input CSV data (centroids and edges) to have a certain structure.

## Data structure for input files

#### Centroid file

| NUTS_ID | X | Y |
| ---- | :----- | :---------- |
| NUTS ID code of region | X coordinate in WGS84 of the centroid | Y coordinate of the centroid |

#### Edge file

| ORIGIN | DESTINATION | OD_ID | COUNT |
| ---- | :----- | :---------- | :---------- |
| NUTS ID code of origin | NUTS ID code of destination | ID made of origin and destination codes joined by an underscore (_) | Integer/floating point number of flow strength |

## Usage

Run the tool by typing in the following command:

```
python bundle_edges.py -c /path/to/centroids.csv -ew /path/to/edges.csv -o /path/to/output.gpkg
```

## References
Wallinger, M., Archambault, D., Auber, D., Nöllenburg, M., & Peltonen, J. (2022). Edge-Path Bundling: A Less Ambiguous Edge Bundling Approach. IEEE Transactions on Visualization and Computer Graphics, 28(1), 313–323. https://doi.org/10.1109/TVCG.2021.3114795

Peterka, O. (2024). Xpeterk1/edge-path-bundling. https://github.com/xpeterk1/edge-path-bundling (Original work published 2023).

## Citation

```
@asoftware{Vaisanen2024,
  title = {Edge bundling tool for regional flows},
  author = {Väisänen, Tuomas and Inkeröinen, Oula and Malekzadeh, Milad and Järv, Olle},
  year = {2024},
  address = {Helsinki, Finland},
  doi = {10.5281/ZENODO.xxxxxxxx},
  urldate = {2024-29-10},
  howpublished = {Zenodo}
}
```
