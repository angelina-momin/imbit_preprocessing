import geopandas as gpd
import rasterio
from rasterio import features
import re
import numpy as np

# CONSTANTS
COL_GM_ID = "ID"

POP_CATEGORIES = [""]


def convert_pop_dens_to_pop_raster(pop_dens_dir):
    """
    Converts a population density raster to a population raster.
    Each cell now has the population size
    """
    pop_raster = pop_dens_raster.copy()
    # Assuming each cell has an attribute 'area' representing its area in square km
    pop_raster["population"] = pop_raster["pop_density"] * pop_raster["area"]

    return pop_raster


def rasterize_gm_polygons(
    pop_raster_dir, gdf_gm_polygons, output_dir
):
    """
    Assigns each population cell to a municipality (GM)
    """
    with rasterio.open(pop_raster_dir) as src:
        pop_raster = src.read(1)
        profile = src.profile
        shape = (src.height, src.width)
        gdf_gm_polygons = gdf_gm_polygons.to_crs(src.crs)

    # Rasterizing municipality polygon to same grid
    gm_shapes = [
        (geom, value)
        for geom, value in zip(gdf_gm_polygons.geometry, gdf_gm_polygons[COL_GM_ID])
    ]
    gm_raster = rasterio.features.rasterize(
        gm_shapes,
        out_shape=shape,
        transform=src.transform,
        fill=-999,  # Background values for areas outside any municipality
        dtype="int",
    )

    profile.update(
        driver="AAIGrid",  # ESRI ASCII Grid format
        count=1,
        dtype=rasterio.int32,
        compress=None  # ASCII grids can’t use compression
    )
        
    with rasterio.open(output_dir, "w", **profile) as dst:
        dst.write(gm_raster.astype(rasterio.int32), 1)

    # with rasterio.open(output_dir, "w", **profile) as dst:
    #     dst.set_band_description(1, "population")
    #     dst.set_band_description(2, "gemeentes")

    #     dst.write(pop_raster.astype(rasterio.float32), 1)
    #     dst.write(gm_raster.astype(rasterio.float32), 2)

import rasterio
from rasterio import features, warp
import numpy as np

def rasterize_gm_polygons(pop_raster_dir, gdf_gm_polygons, output_dir):
    """
    Reprojects the population raster to match the CRS of the municipality polygons,
    then rasterizes municipality (GM) IDs to that grid and saves as an ESRI ASCII Grid (.asc).

    Parameters
    ----------
    pop_raster_dir : str
        Path to the reference population raster
    gdf_gm_polygons : GeoDataFrame
        GeoDataFrame of municipality polygons with column COL_GM_ID
    output_dir : str
        Path to output .asc file (e.g., 'output/gm_raster.asc')
    """
    with rasterio.open(pop_raster_dir) as src:
        pop_raster = src.read(1)
        src_profile = src.profile
        src_crs = src.crs
        dst_crs = gdf_gm_polygons.crs  # Use CRS of GDF

        # Reproject raster to match the GDF CRS
        transform, width, height = warp.calculate_default_transform(
            src_crs, dst_crs, src.width, src.height, *src.bounds
        )

        dst_profile = src_profile.copy()
        dst_profile.update(
            crs=dst_crs,
            transform=transform,
            width=width,
            height=height,
            driver="AAIGrid",
            count=1,
            dtype=rasterio.int32,
            compress=None,
        )

        # Allocate array for reprojected raster
        reprojected = np.empty((height, width), dtype=src.read(1).dtype)

        warp.reproject(
            source=pop_raster,
            destination=reprojected,
            src_transform=src.transform,
            src_crs=src_crs,
            dst_transform=transform,
            dst_crs=dst_crs,
            resampling=warp.Resampling.nearest,
        )

    # Rasterize municipality polygons in the reprojected CRS
    gm_shapes = [
        (geom, value)
        for geom, value in zip(gdf_gm_polygons.geometry, gdf_gm_polygons[COL_GM_ID])
    ]

    gm_raster = features.rasterize(
        gm_shapes,
        out_shape=(height, width),
        transform=transform,
        fill=-999,
        dtype="int32",
    )

    # Write the GM raster in ASCII format
    with rasterio.open(output_dir, "w", **dst_profile) as dst:
        dst.write(gm_raster, 1)

    print(f"✅ Saved municipality raster (CRS={dst_crs.to_string()}) at: {output_dir}")



def add_pop_cat_to_raster_cells(pop_raster_dir, imm_start_pop_dir, pop_raster_final_dir):
  with rasterio.open(pop_raster_dir) as src:
      pop_data = src.read(1)
      gm_data = src.read(2)
      profile = src.profile  
      shape = pop_data.shape

  gdf_imm = gpd.read_file(imm_start_pop_dir)

  # Obtaining the population categories and calculating the ratios
  pop_cat = [col[1:] for col in gdf_imm.columns if re.match("^[Ss]\d{5}$", col)]  
  for col in pop_cat:
      gdf_imm[col + "_ratio"] = gdf_imm[f"S{col}"]*10 / gdf_imm["TotPop"]
  
  # Creating dict for each GM ID and its population category ratios
  lookup = gdf_imm.set_index("ID")[[c + "_ratio" for c in pop_cat]].to_dict(orient="index")

  # Allocate output arrays
  pop_by_cat = {cat: np.full(shape, np.nan, dtype=np.float32) for cat in pop_cat}

  # Distributing population into categories based on GM ratios
  gm_ids = np.unique(gm_data[gm_data > 0])
  for gm in gm_ids:
      if gm not in lookup:
          continue
      mask = gm_data == gm
      for cat in pop_cat:
          ratio = lookup[gm][cat + "_ratio"]
          if np.isnan(ratio):
              continue
          pop_by_cat[cat][mask] = pop_data[mask] * ratio

  # Saving the raster file
  profile.update(count=len(pop_cat), dtype=rasterio.float32)
  with rasterio.open(pop_raster_final_dir, "w", **profile) as dst:
      for i, cat in enumerate(pop_cat, start=1):
          dst.write(pop_by_cat[cat], i)
          dst.set_band_description(i, cat)

# def add_pop_cat_to_raster_cells(pop_raster_dir, imm_start_pop_dir, pop_raster_final_dir, value_per_cell=200):
#    # --- Read input raster ---
#     with rasterio.open(pop_raster_dir) as src:
#         pop_data = src.read(1)
#         profile = src.profile
#         shape = pop_data.shape

#     # --- Read shapefile to get S-column names ---
#     gdf_imm = gpd.read_file(imm_start_pop_dir)
#     pop_cat = [col[1:] for col in gdf_imm.columns if re.match(r"^[Ss]\d{5}$", col)]

#     # --- Allocate arrays with constant value ---
#     pop_by_cat = {cat: np.full(shape, value_per_cell, dtype=np.float32) for cat in pop_cat}

#     # --- Save output raster ---
#     profile.update(count=len(pop_cat) + 2, dtype=rasterio.float32)
#     with rasterio.open(pop_raster_final_dir, "w", **profile) as dst:
#         dst.set_band_description(1, "population")
#         dst.set_band_description(2, "gemeentes")
#         for i, cat in enumerate(pop_cat, start=3):
#             dst.write(pop_by_cat[cat], i)
#             dst.set_band_description(i, f"S{cat}")


def preprocess_pop_spatial_layer(
    pop_dens_dir,
    pop_raster_dir,
    gm_polygon_raster_dir,
    imm_start_pop_dir
):
    """
    Preprocesses population density raster and assigns municipalities
    """

    gdf_gm_polygon = gpd.read_file(gm_shp_dir)

    convert_pop_dens_to_pop_raster(pop_dens_dir, pop_raster_dir)
    rasterize_gm_polygons(pop_raster_dir, gdf_gm_polygon)
    add_pop_cat_to_raster_cells(gm_polygon_raster_dir, imm_start_pop_dir)


if __name__ == "__main__":
    pop_dens_dir = "input/pop_dens/nld_pd_2013_1km.tif"
    gm_poly_shp_dir = "input/gemeentes/corrected/Gemeentes2013TrMr.shp"
    gm_centroid_shp_dir = "input/gemeentes/points/StartPopulationHighR70TrMr.shp"
    gm_polygon_raster_dir = "output/pop_raster/pop_gm.asc"
    pop_raster_final_dir = "output/pop_raster/pop_gm_cat.tif"

    # Join the gm_poly and gm_centroid shapefiles
    gdf_gm_poly = gpd.read_file(gm_poly_shp_dir)
    gdf_gm_centroid = gpd.read_file(gm_centroid_shp_dir)

    gdf_gm = gpd.sjoin(
        gdf_gm_poly,
        gdf_gm_centroid[["ID", "geometry"]],
        how="left",
        predicate="contains",
    )

    # rasterize_gm_polygons(pop_dens_dir, gdf_gm, gm_polygon_raster_dir)
    add_pop_cat_to_raster_cells(gm_polygon_raster_dir, gm_centroid_shp_dir, pop_raster_final_dir)

