import os
import sys
sys.path.append('../../')

import config

import geopandas as gpd
import pandas as pd
import subprocess

# Change disease type number if necessary
DISEASE_TYPE = 3

# Function to transform the crs of farm grid to the crs of the gemeente
def transform_loc_grid_crs(
  inf_loc_gdf,
  gemeente_gdf,
  transformed_farm_shp_dir = "output/farm_transformed_crs.shp",
  save_file=False
):
  if inf_loc_gdf.crs != gemeente_gdf.crs:
    inf_loc_gdf = inf_loc_gdf.to_crs(gemeente_gdf.crs)

  if save_file == True:
    inf_loc_gdf.to_file(transformed_farm_shp_dir)

  return inf_loc_gdf

# Function to transform each farm polygon to centroids
def convert_loc_to_centroids(
  inf_loc_gdf,
  inf_loc_dir = "output/farm_centroid.shp",
  save_file = False
):

  inf_loc_gdf["geometry"] = inf_loc_gdf["geometry"].centroid

  if save_file == True:
    inf_loc_gdf.to_file(inf_loc_dir)

  return inf_loc_gdf

# Function to add to each farm the gemeente ID of the gemeente they belong to
def add_gm_ids_loc_centroids(
  inf_loc_gdf,
  gemeente_gdf,
  output_inf_loc_dir = "output/farm_with_gm_id.shp",
  save_file = False
):
  # Spatial join to match grid points with gemeente geometries
  joined_gdf = gpd.sjoin(left_df= inf_loc_gdf, right_df=gemeente_gdf[["OBJECTID", "geometry"]], how="left", predicate="within")
 
  # Assign the gemeente_id from the join result
  inf_loc_gdf["gm_id"] = joined_gdf["OBJECTID"]

  # Saving file
  if save_file:
    inf_loc_gdf.to_file(output_inf_loc_dir)

  return inf_loc_gdf

# Function to add to each farm the gemeente ID of the gemeente they belong to
def add_gm_names_loc_centroids(
  farm_gdf,
  gemeente_gdf,
  output_farm_dir = "output/farm_with_gm_id.shp",
  save_file = False
):
  # Spatial join to match grid points with gemeente geometries
  joined_gdf = gpd.sjoin(left_df= farm_gdf, right_df=gemeente_gdf[["gemeente", "geometry"]], how="left", predicate="within")
 
  # Assign the gemeente_id from the join result
  farm_gdf["name"] = joined_gdf["gemeente"]

  # Saving file
  if save_file:
    farm_gdf.to_file(output_farm_dir)

  return farm_gdf

def discard_inf_loc_outside_nl(
  loc_gdf
):
  # Discarding farms that have NA for gm_id. This means these farms
  # are outside the NL
  loc_gdf = loc_gdf[loc_gdf["name"].notna()].copy()

  # Convert to integer type if no missing values are expected
  loc_gdf["name"] = loc_gdf["name"].astype("str")
  loc_gdf["node"] = loc_gdf["node"].astype("int")

  loc_gdf = loc_gdf[loc_gdf["node"] != 19271]

  return(loc_gdf)

# Function to transform the iv table so that each row represents the time and the
# columns are the
def create_iv_tables(
    traj_csv_dir,
    output_iv_table_dir="output/env_table.csv",
    preprocessed_farm_dir="output/preprocessed_farm.shp"
):

    trajectory_data = pd.read_csv(traj_csv_dir)
    grid_df = gpd.read_file(preprocessed_farm_dir)

    # Pivot the data on time column so each time is on the row and the columns are the nodes' IV values
    iv_table = trajectory_data.pivot(index="time", columns="node", values="ENV").reset_index()

    # Removing the column index name
    iv_table.columns.name = None

    # Deleting columns corresponding to IV values for nodes that are not in preprocessed grid.
    # The nodes not present in preprocessed grid were outside of the country
    iv_table = iv_table[iv_table.columns.intersection(grid_df["node"].values)]

    iv_table.to_csv(output_iv_table_dir, index=False)

if __name__ == "__main__":
    output_loc_name = "animal_infc_loc.shp"
    output_table_name = "infc_table.csv"

    if DISEASE_TYPE == 1:
        input_dir = config.DISEASE_1_INPUT


    elif DISEASE_TYPE == 3:
        input_dir = config.DISEASE_3_INPUT

    for dir in os.listdir(input_dir):
        if dir.startswith('outbreak-'):
            outbreak_num = dir.split('-')[1]

        else:
            continue
        
        outbrk_input_dir = f"{input_dir}/outbreak-{outbreak_num}"
        root_output_dir = f"{input_dir}/outbreak_{outbreak_num}"

        # Directories to input files
        ani_infc_loc_shp_dir = f"{outbrk_input_dir}/grid.geojson"
        traj_csv_dir = f"{outbrk_input_dir}/trajectory.csv"

        # We need to unzip the traj csv file
        if "trajectory.csv" not in os.listdir(outbrk_input_dir):
            traj_zip_dir = f"{outbrk_input_dir}/trajectory.csv.gz"
            subprocess.run(['gunzip', traj_zip_dir])

        # Directories to output_files
        prc_infc_loc_shp_dir = f"{root_output_dir}/{output_loc_name}"
        iv_table_dir = f"{root_output_dir}/{output_table_name}"

        # Script to run preprocessing
        og_infc_loc_gdf = gpd.read_file(ani_infc_loc_shp_dir) 
        gemeente_gdf = gpd.read_file(config.GM_SHP_DIR)

        trans_infc_loc_gdf = transform_loc_grid_crs(og_infc_loc_gdf, gemeente_gdf)
        trans_infc_loc_gdf = convert_loc_to_centroids(trans_infc_loc_gdf)
        trans_infc_loc_gdf = add_gm_names_loc_centroids(trans_infc_loc_gdf, gemeente_gdf)
        trans_infc_loc_gdf = discard_inf_loc_outside_nl(trans_infc_loc_gdf)

        if not os.path.isdir(root_output_dir):
            os.makedirs(root_output_dir)

        trans_infc_loc_gdf.to_file(prc_infc_loc_shp_dir)

        print(f"Created output file for {outbreak_num}")
        create_iv_tables(traj_csv_dir, iv_table_dir,prc_infc_loc_shp_dir)

        df = pd.read_csv(iv_table_dir)

    print("Preprocessing complete")