import csv
import logging
import os

import rasterio
import geopandas as gpd
import numpy as np

logger = logging.getLogger(__name__)

# Create table of weighted foi, with rows for each day and columns for each gm
# The values will the weighted foi values

# The weighted foi (table values) will be calculated by taking the sum of the product
# of (foi * pop_frac) for each raster cell within a gemeente


# The first row of data will be the gm_ids

def create_weighted_foi_table(dir_multiband_foi: str, dir_imm_shp: str, dir_pop_frac: str, dir_gm_raster: str, dir_output: str):
    """
    Create table of weighted foi, with rows for each day and columns for each gm
    The values will the weighted foi values

    The weighted foi (table values) will be calculated by taking the sum of the product
    of ((1-e^(-foi)) * pop_frac) for each raster cell within a gemeente
    """

    foi_ras = rasterio.open(dir_multiband_foi)
    pop_frac_ras = rasterio.open(dir_pop_frac).read(1)
    gm_ras = rasterio.open(dir_gm_raster).read(1)

    # Replace negative pop frac values with 0
    pop_frac_ras[pop_frac_ras < 0] = 0

    # Add gm ids as first rows
    gm_gdf = gpd.read_file(dir_imm_shp)
    list_gm_ids = gm_gdf["ID"].tolist()
    
    list_rows = []
    list_rows.append(list_gm_ids)

    # Create row weighted foi for each band (which is each day)
    for band_index in range(1, foi_ras.count + 1):
        foi_ras_day = foi_ras.read(band_index)

        # Replace all negative values in foi_ras_day with 0
        foi_ras_day[foi_ras_day < 0] = 0

        new_row = _compute_weighted_foi_row(foi_ras_day, pop_frac_ras, gm_ras, list_gm_ids)
        list_rows.append(new_row)

    # Creating csv and saving it
    with open(dir_output, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(list_rows)

        logger.info(f"Created weighted foi csv at location: {dir_output}")


def _compute_weighted_foi_row(foi_ras, pop_frac_ras, gm_ras, list_gm_ids: list[int]):

    rows = []
    for gm_id in list_gm_ids:
        # Create mask where gm_ras has cell value equal to gm_id
        mask = (gm_ras == gm_id)   
        # Calculate weighted foi as sum(foi * pop_frac) for those cells
        weighted_foi = np.sum((1 - np.exp(-foi_ras[mask])) * pop_frac_ras[mask]) 
        rows.append(weighted_foi)

    return rows

if __name__ == "__main__":

    dir_multiband_foi = "data/input/foi/foi_aligned.tif"

    dir_imm_shp = "../imbit_model/data/input/imm_startpop/test.shp"
    dir_pop_frac = "data/input/pop_frac/pop_frac.tif"
    dir_gm_raster = "data/input/gemeentes/gm_id.tif"

    dir_output = "data/output/foi/weighted_foi.csv"

    create_weighted_foi_table(dir_multiband_foi, dir_imm_shp, dir_pop_frac, dir_gm_raster, dir_output)
