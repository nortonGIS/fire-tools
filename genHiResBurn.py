#-------------------------------------------------------------------------------
# Name:        highResBurn Tool
# Purpose:     Takes raw naip and raw heights data and segments the data into
#              objects and classifies these objects using a fuzzy classifier
#              rule and the SVM algorithm. Once objects are classified, they
#              are prepared as ASCIIs to be burned in FlamMap.
#
#             Primary Steps:
#               - Segment heights into unique objects using SMS
#               - Calculate and join mean height to objects with Zonal Stastics
#               - Separate ground and nonground features and mask naip
#               - Classify objects using fuzzy classifier rule in 2 stages
#               - Use classified vegetation objects as training samples for SVM
#               - Run SVM and use output to classify 'confused' objects
#               - Assign all objects a fuel model
#               - Create Landscape file (.LCP)
#               - Burn LCP using FlamMap (outputs in default)
#               - Fire line intensity, flame length, and rate of spread calculated
#               - Maximum potential static fire behavior joined back to objects
#               - Pipeline/infrastructure (if present) is assessed by incident threat

# Author:      Peter Norton
#
# Created:     05/25/2017
# Updated:     11/4/2017
# Copyright:   (c) Peter Norton and Matt Ashenfarb 2017
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
# USER LOG
date = "11_11"
# Summary
#
#
#

# Geographic Data
location_name = "Colfax2Reno"
bioregion = "Tahoe" #[Tahoe, Richmond, Grape_Vine]
projection = "UTMZ10"  #["UTMZ10", "UTMZ11"]

# Settings
coarsening_size = "5" #meters
tile_size = "1" #square miles
model = "13"  # Fuel Model set
buff_distance = "1000 feet" # Buffer around infrastructure

# inputs
input_bnd = "bnd.shp"
input_naip = "naip.tif"
input_las = "pointcloud.lasd"
input_heights = "heights.tif"
input_dem = "dem.tif"
input_pipeline = "pipeline.shp"

input_fuel_moisture = "fuel_moisture.fms"
input_wind = ""
input_weather = ""
burn_metrics = ["fli", "fml", "ros"]
#-----------------------------------------------
#-----------------------------------------------

#-----------------------------------------------
#-----------------------------------------------
process_lidar = "No"
align_inputs = "Yes"
pipe_analysis = "Yes"
create_obia = "Yes"
classify_landscape = "Yes"
run_svm = "Yes"
classify_fuels = "Yes"
create_LCP = "Yes"
run_FlamMap = "No"
join_burns = "No"
create_MXD = "Yes"

processes = [
align_inputs,
pipe_analysis,
create_obia,
classify_landscape,
run_svm,
classify_fuels,
create_LCP,
run_FlamMap,
join_burns,
create_MXD]
#-----------------------------------------------
#-----------------------------------------------


#-----------------------------------------------
#-----------------------------------------------
# Processing - DO NOT MODIFY BELOW
#-----------------------------------------------
#-----------------------------------------------

#-----------------------------------------------
#-----------------------------------------------
# Import modules
import arcpy
import os
import sys
import shutil
from arcpy import env
from arcpy.sa import *

drive = os.path.abspath(sys.path[0])[0]
# Overwrite Setting
script_db = drive+":\\TFS_Fire\\fire-tools"
#-----------------------------------------------
#-----------------------------------------------


#-----------------------------------------------
#-----------------------------------------------
# File Structure
folder_structure = [
  "05_Scripts",
  "01_Inputs",
  "02_Unmitigated_Outputs",
  "03_Mitigated_Outputs",
  "04_Scratch"
]

# Dependent scripts
dependent_scripts = [
  "imageEnhancements.py",
  "thresholdsLib.py",
  "tableJoin.py",
  #"mitigation_ts.py"
]

# Dependent dlls
dependent_dlls = [
  "GenLCPv2.dll",
  "FlamMapF.dll"
]
# Create new project folder and set environment
scriptpath = sys.path[0] # Find script
toolpath = os.path.dirname(scriptpath)  # Find parent directory
current_project = os.path.join(toolpath)
if os.path.basename(toolpath) == date:
  arcpy.AddMessage("File structure is setup.")
elif os.path.basename(scriptpath) != date:
    if os.path.basename(scriptpath) == "05_Scripts":
      new_toolpath = os.path.dirname(toolpath)
      current_project = os.path.join(new_toolpath,date)
    else:
      current_project = os.path.join(toolpath,date)
    os.makedirs(current_project)        # Make new project folder
    for folder_name in folder_structure:
      folder = os.path.join(current_project, folder_name)
      os.makedirs(folder)
      if folder_name == "01_Inputs":
        if os.path.basename(scriptpath) == "05_Scripts":
          input_path = os.path.join(toolpath, "01_Inputs")
          for root, dirs, inputs in os.walk(scriptpath):
            for input_file in inputs:
              script_folder = os.path.join(current_project, "05_Scripts")
              base=os.path.basename(input_file)
              extension = os.path.splitext(input_file)[1]
              if extension == ".py" and input_file not in dependent_scripts:
                arcpy.Copy_management(input_file, os.path.join(script_folder, date+".py")) # copies main to script folde
              else:
                arcpy.Copy_management(input_file, os.path.join(script_folder, base))
        else:
          input_path = scriptpath
        for root, dirs, inputs in os.walk(input_path):
          for input_file in inputs:
            base=os.path.basename(input_file)
            extension = os.path.splitext(input_file)[1]

            if extension not in [".py", ".tbx"]:

              input_folder = os.path.join(current_project, folder_name)
              arcpy.Copy_management(os.path.join(input_path,input_file), os.path.join(input_folder, base)) # copies main to script folder
            else:
              input_folder = os.path.join(current_project, "05_Scripts")
              if extension == ".py":
                arcpy.Copy_management(input_file, os.path.join(input_folder, date+".py")) # copies main to script folde
              else:
                arcpy.Copy_management(input_file, os.path.join(input_folder, base)) # copies main to script folde
      elif folder_name == "04_Scratch":
        arcpy.CreateFileGDB_management(folder, "Scratch.gdb")
      elif folder_name == "05_Scripts":
        input_folder = os.path.join(current_project, folder_name)

        for dependent_script in dependent_scripts:
          shutil.copy2(os.path.join(script_db, dependent_script), os.path.join(input_folder, dependent_script)) # copies main to script folder
        for dependent_dll in dependent_dlls:
          shutil.copy2(os.path.join(script_db, dependent_dll), os.path.join(input_folder, dependent_dll)) # copies main to script folder
  #os.remove(scriptpath)

# Dependent scripts
from imageEnhancements import createImageEnhancements
from tableJoin import one_to_one_join
from thresholdsLib import get_thresholds

#Setting inputs, outputs, scratchws, scratch.gdb

inputs = os.path.join(current_project, "01_Inputs")
outputs = os.path.join(current_project, "02_Unmitigated_Outputs")
scratchws = os.path.join(current_project, "04_Scratch")
scratchgdb = os.path.join(scratchws, "Scratch.gdb")
dll_path = os.path.join(current_project, "05_Scripts")
arcpy.env.workspace = scratchws
arcpy.env.overwriteOutput = True

#-----------------------------------------------
#-----------------------------------------------
# Set Global Variables
# Raw inputs
raw_naip = os.path.join(inputs, input_naip) # NAIP Imagery at 1m res
lasd = os.path.join(inputs, input_las)
raw_heights = os.path.join(inputs, input_heights) # Heights
raw_dem = os.path.join(inputs, input_dem) # DEM
pipeline = os.path.join(inputs, input_pipeline) # Pipeline
fuel_moisture = os.path.join(inputs, input_fuel_moisture) # Fuel Moisture
wind = os.path.join(inputs, input_wind) # Wind
weather = os.path.join(inputs, input_weather) # Weather

#-----------------------------------------------
#-----------------------------------------------

#-----------------------------------------------
#-----------------------------------------------
# Set Create Layers
# Inputs
bnd_zones = os.path.join(inputs, input_bnd) # Bounding box for each tile

# Outputs
S1_classified = os.path.join(outputs, "S1_classified.shp")
classified = os.path.join(outputs, "classified.shp")
analysis_area = bnd_zones  # analysis area/ area of interest
dem = os.path.join(outputs, "dem.tif")  # Resampled DEM in native units
heights = os.path.join(outputs, "heights.tif")  # Resampled heights in native units
scaled_heights = os.path.join(outputs, "scaled_heights.tif")  # Heights in project units
scaled_dem = os.path.join(outputs, "scaled_dem.tif")  # DEM in project units



naip = os.path.join(outputs, "naip_"+coarsening_size+"m.tif")  # NAIP in project units
naip_b1 = os.path.join(naip, "Band_1")
naip_b2 = os.path.join(naip, "Band_2")
naip_b3 = os.path.join(naip, "Band_3")
naip_b4 = os.path.join(naip, "Band_4")
#-----------------------------------------------
#-----------------------------------------------

#-----------------------------------------------
#-----------------------------------------------
# Alert function with step counter
count = 1
def generateMessage(text):
  global count
  arcpy.AddMessage("Step " + str(count) + ": " +text),
  count += 1

def newProcess(text):
  global count
  count = 1
  arcpy.AddMessage("-----------------------------")
  arcpy.AddMessage("Process: "+text)
  arcpy.AddMessage("-----------------------------")


# Details
arcpy.AddMessage("Site: "+location_name)
arcpy.AddMessage("Projection: "+projection)
arcpy.AddMessage("Resolution: "+coarsening_size + "m")
arcpy.AddMessage("Fuel Model: "+model)
arcpy.AddMessage("-----------------------------")
#-----------------------------------------------
#-----------------------------------------------

#-----------------------------------------------
#-----------------------------------------------
# Projection and scaling information
if projection == "UTMZ10":
  scale_height = 1
  scale_naip = 1
  unit = "Meters"
  projection = "PROJCS['NAD_1983_UTM_Zone_10N',GEOGCS['GCS_North_American_1983',DATUM['D_North_American_1983',SPHEROID['GRS_1980',6378137.0,298.257222101]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]],PROJECTION['Transverse_Mercator'],PARAMETER['False_Easting',500000.0],PARAMETER['False_Northing',0.0],PARAMETER['Central_Meridian',-123.0],PARAMETER['Scale_Factor',0.9996],PARAMETER['Latitude_Of_Origin',0.0],UNIT['Meter',1.0]]"
elif projection == "UTMZ11":
  scale_height = 1
  scale_naip = 1
  unit = "Meters"
  projection = "PROJCS['NAD_1983_UTM_Zone_11N',GEOGCS['GCS_North_American_1983',DATUM['D_North_American_1983',SPHEROID['GRS_1980',6378137.0,298.257222101]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]],PROJECTION['Transverse_Mercator'],PARAMETER['False_Easting',500000.0],PARAMETER['False_Northing',0.0],PARAMETER['Central_Meridian',-117.0],PARAMETER['Scale_Factor',0.9996],PARAMETER['Latitude_Of_Origin',0.0],UNIT['Meter',1.0]]"
elif projection == "SPIII":
  scale_height = 1
  scale_naip = 3.28084
  unit = "Feet"
  projection = "PROJCS['NAD_1983_StatePlane_California_III_FIPS_0403_Feet',GEOGCS['GCS_North_American_1983',DATUM['D_North_American_1983',SPHEROID['GRS_1980',6378137.0,298.257222101]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]],PROJECTION['Lambert_Conformal_Conic'],PARAMETER['False_Easting',6561666.666666666],PARAMETER['False_Northing',1640416.666666667],PARAMETER['Central_Meridian',-120.5],PARAMETER['Standard_Parallel_1',37.06666666666667],PARAMETER['Standard_Parallel_2',38.43333333333333],PARAMETER['Latitude_Of_Origin',36.5],UNIT['Foot_US',0.3048006096012192]]"
elif projection == "SPIV":
  scale_height = 1
  scale_naip = 3.28084
  unit = "Feet"
  projection = "PROJCS['NAD_1983_StatePlane_California_VI_FIPS_0406_Feet',GEOGCS['GCS_North_American_1983',DATUM['D_North_American_1983',SPHEROID['GRS_1980',6378137.0,298.257222101]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]],PROJECTION['Lambert_Conformal_Conic'],PARAMETER['False_Easting',6561666.666666666],PARAMETER['False_Northing',1640416.666666667],PARAMETER['Central_Meridian',-116.25],PARAMETER['Standard_Parallel_1',32.78333333333333],PARAMETER['Standard_Parallel_2',33.88333333333333],PARAMETER['Latitude_Of_Origin',32.16666666666666],UNIT['Foot_US',0.3048006096012192]]"
#-----------------------------------------------
#-----------------------------------------------

#-----------------------------------------------
#-----------------------------------------------
arcpy.AddMessage("-----------------------------")
arcpy.AddMessage("Processing Started.")
arcpy.AddMessage("-----------------------------")


#-----------------------------------------------
#-----------------------------------------------



#-----------------------------------------------
#-----------------------------------------------
def align():
  text = "Aligning cells."
  newProcess(text)
  # Resample NAIP Imagery, heights, and DEM to
  # align cells and scale measurements to
  # projection. Resampled layers will be saved to
  # 'Outputs' folder

  #NAIP
  text = "Resampling NAIP image."
  generateMessage(text)

  naip = os.path.join(outputs,"naip_"+coarsening_size+"m.tif")
  bnd_zones_rast = os.path.join(scratchgdb, "bnd_zones_rast")
  cell_size = int(int(coarsening_size)*scale_naip)
  naip_cell_size = str(cell_size) +" "+str(cell_size)
  arcpy.Resample_management(raw_naip, naip, naip_cell_size, "BILINEAR") # Bilinear Interpolation reduce image distortion when scaling.It linearly interpolates the nearest 4 pixels
  arcpy.DefineProjection_management(naip, projection)
  bands = ["Band_1","Band_2","Band_3","Band_4"] # NAIP has 4 bands (in increasing order) B,G,R,NIR

  # Create a fitted, resampled boundary
  text = "Creating a boundary based on resampled NAIP imagery extent."
  generateMessage(text)

  this = Int(Raster(naip)*0)
  this.save(bnd_zones_rast)
  arcpy.DefineProjection_management(bnd_zones_rast, projection)
  arcpy.RasterToPolygon_conversion(bnd_zones_rast, bnd_zones, "NO_SIMPLIFY", "Value")



   #-----------------------------------------------
   #-----------------------------------------------
  def lasToHeights():

    # -------------Create DEM, DSM, Heights--------------------
    #
    cell_size = int(int(coarsening_size)*scale_naip)

    #
    # Create DEM
    text = "Creating heights."
    generateMessage(text)

    last_pulse = os.path.join(inputs, "FP.lasd")
    first_pulse_classes = ["1"]
    arcpy.MakeLasDatasetLayer_management(lasd, first_pulse, first_pulse_classes)

    text = "First Pulses separated."
    generateMessage(text)

    # Create Last Pulse lasd
    last_pulse = os.path.join(inputs, "LP.lasd")
    last_pulse_classes = ["2"]
    arcpy.MakeLasDatasetLayer_management(lasd, last_pulse, last_pulse_classes)
    text = "Last Pulses separated."
    generateMessage(text)

    arcpy.LasDatasetToRaster_conversion(lasd, dem, "ELEVATION", "BINNING MINIMUM LINEAR", "FLOAT", "CELLSIZE", cell_size, "")
    #
    # Create DSM
    arcpy.LasDatasetToRaster_conversion(lasd, dsm, "ELEVATION", "BINNING MAXIMUM SIMPLE", "FLOAT", "CELLSIZE", cell_size, "")


    # Create Heights
    hts_interm1 = os.path.join(scratchws,"hts_interm1.tif")
    hts_interm2 = os.path.join(scratchws,"hts_interm2.tif")

    ht = Float(dsm)-Float(dem)
    ht = Con(IsNull(Float(ht)), 0, Float(ht))
    ht = Con(Float(ht) < 0, 0, Float(ht))
    heights = SetNull(Float(ht),Float(ht),"VALUE > 350")                 # Minimum "Cloud" heights defined here.  NOTE UNITS
    if arcpy.GetRasterProperties_management(ht,"ANYNODATA").getOutput(0):
        arcpy.AddMessage("Interpolating under clouds/birds.")
        ht.save(hts_interm1)
        ht.save(hts_interm2)
        del ht
        cloudrast = os.path.join(scratchws,"cloudrast")
        arcpy.gp.Reclassify_sa(hts_interm1, "VALUE", "0 500 NODATA;NODATA 1", cloudrast, "DATA")
        cloudpts = os.path.join(scratchws,"cloudpts")
        arcpy.RasterToPoint_conversion(cloudrast,cloudpts,"VALUE")
        cloudpts_buf30 = os.path.join(scratchws,"cloudptsbuf30")
        arcpy.Buffer_analysis(cloudpts, cloudpts_buf30, "30 Meters", "FULL", "ROUND", "ALL", "", "PLANAR")
        nocloudmask = ExtractByMask(hts_interm2,cloudpts_buf30)
        interppts = os.path.join(scratchws,"interppts")
        arcpy.RasterToPoint_conversion(nocloudmask, interppts,"")
        NNinterp = os.path.join(scratchws,"NNinterp")
        arcpy.gp.NaturalNeighbor_sa(interppts, "grid_code", NNinterp, hts_interm2)
        arcpy.MosaicToNewRaster_management(hts_interm2+";"+NNinterp, inputs,"heights.tif", "", "32_BIT_FLOAT", "", "1", "FIRST", "FIRST")
        arcpy.AddMessage("heights.tif created in Outputs folder.")
    else:
        ht.save(heights)

    #
    # Create Boundary
    heights = os.path.join(inputs,"heights.tif")

  if process_lidar == "Yes":

    lasToHeights()
  #Heights
  text = "Resampling heights."
  generateMessage(text)


  arcpy.env.snapRaster = naip
  factor = float(cell_size)/float(scale_naip) # scale naiip
  arcpy.Resample_management(raw_heights, heights, str(scale_naip) + " " + str(scale_naip), "BILINEAR") # Bilinear Interpolation reduce image distortion when scaling.It linearly interpolates the nearest 4 pixels
  this = Aggregate(heights, factor, "MEDIAN") # Aggregate cells by maximum to preserve max heights
  arcpy.DefineProjection_management(this, projection)
  this = ExtractByMask(this, bnd_zones_rast) # Extract scaled
  this.save(heights)

  #DEM
  text = "Resampling DEM."
  generateMessage(text)


  arcpy.env.snapRaster = naip
  factor = float(cell_size)/float(scale_height)
  arcpy.Resample_management(raw_dem, dem, str(scale_height) + " " + str(scale_height), "BILINEAR")
  this = Aggregate(dem, factor, "MEDIAN")
  arcpy.DefineProjection_management(this, projection)
  this = ExtractByMask(this, bnd_zones_rast)
  this.save(dem)
  #-----------------------------------------------
  #-----------------------------------------------

  if pipe_analysis == "Yes":

    #-----------------------------------------------
    #-----------------------------------------------
    text = "Creating "+str(buff_distance)+" buffer around the pipeline."
    generateMessage(text)

    #Variables
    pipe_seg = os.path.join(outputs, "pipe_seg.shp")
    pipe_buffer = os.path.join(outputs, "pipe_buffer.shp")
    pipe_buffer_clip = os.path.join(scratchgdb, "pipe_buffer_clip")
    pipe_rast = os.path.join(scratchgdb, "pipe_rast")
    naip_pipe = os.path.join(scratchgdb, "naip_pipe")
    height_pipe = os.path.join(scratchgdb, "height_pipe")
    pipe_proj = os.path.join(scratchgdb, "pipe_proj")
    bnd_rast = os.path.join(scratchgdb, "bnd_rast")
    bands = ["Band_1","Band_2","Band_3","Band_4"]
    pipe_bands = []
    global analysis_area
    analysis_area = pipe_buffer

    # Clip pipeline to study area, buffer pipeline
    arcpy.Clip_analysis(pipeline, bnd_zones, pipe_seg)
    arcpy.PolygonToRaster_conversion(bnd_zones, "FID", bnd_rast, "CELL_CENTER", "", int(coarsening_size))
    arcpy.Buffer_analysis(pipe_seg, pipe_buffer, buff_distance, "", "", "ALL")
    arcpy.PolygonToRaster_conversion(pipe_buffer, "FID", pipe_rast, "CELL_CENTER")
    arcpy.ProjectRaster_management(pipe_rast, pipe_proj, bnd_zones, "BILINEAR", str(cell_size) +" "+str(cell_size))
    this = ExtractByMask(pipe_proj, bnd_zones)
    this.save(pipe_buffer_clip)
    arcpy.RasterToPolygon_conversion(pipe_buffer_clip, pipe_buffer, "NO_SIMPLIFY")



    # Extract NAIP and heights to pipeline buffer
    this = ExtractByMask(naip, pipe_buffer)
    this.save(naip_pipe)

    for band in bands:
      band_ras = os.path.join(scratchgdb, band)
      naip_band = os.path.join(naip_pipe, band)
      outRas = Con(IsNull(naip_band),0, naip_band)
      outRas.save(band_ras)
      pipe_bands.append(band_ras)
    arcpy.CompositeBands_management(pipe_bands, naip)
    arcpy.DefineProjection_management(naip, projection)

    this = ExtractByMask(heights, pipe_buffer)
    this.save(height_pipe)
    outRas = Con(IsNull(height_pipe),0, Raster(height_pipe))
    outRas.save(heights)
    #-----------------------------------------------
    #-----------------------------------------------
if align_inputs == "Yes":
  align()
#-----------------------------------------------
#-----------------------------------------------


#-----------------------------------------------
#-----------------------------------------------
# Iterate through all zones (if possible)

searchcursor = arcpy.SearchCursor(analysis_area)
zones = searchcursor.next()
while zones:
  zone_num = zones.getValue("FID")
  sms_fc = os.path.join(scratchgdb, "sms_fc_"+str(zone_num))
  landscape_fc = os.path.join(scratchgdb, "landscape_fc_"+str(zone_num))

  def obia():
    text = "Running an OBIA for zone "+str(zone_num)
    newProcess(text)

    #Variables
    bnd = os.path.join(outputs, "zone_"+str(zone_num)+".shp")
    bnd_rast = os.path.join(outputs, "bnd.tif")
    where_clause = "FID = " + str(zone_num)
    naip_zone = os.path.join(outputs, "naip_zone_"+str(zone_num)+".tif")
    naip_zone_b1 = os.path.join(naip_zone, "Band_1")
    naip_zone_b2 = os.path.join(naip_zone, "Band_2")
    naip_zone_b3 = os.path.join(naip_zone, "Band_3")
    naip_zone_b4 = os.path.join(naip_zone, "Band_4")
    heights_zone = os.path.join(outputs, "height_zone_"+str(zone_num)+".tif")
    naip_sms = os.path.join(scratchgdb, "naip_sms_"+str(zone_num))
    sms_fc = os.path.join(scratchgdb, "sms_fc_"+str(zone_num))



    # Create zone boundary and extract NAIP and heights

    arcpy.Select_analysis(analysis_area, bnd, where_clause)
    this = ExtractByMask(naip, bnd)
    this.save(naip_zone)
    this = ExtractByMask(heights, bnd)
    this.save(heights_zone)
    #-----------------------------------------------
    #-----------------------------------------------

    # Create Image Enhancements and join to objects
    text = "Creating image enhancements."
    generateMessage(text)

    image_enhancements = ["ndvi", "ndwi", "gndvi", "osavi"]
    created_enhancements_1m = createImageEnhancements(image_enhancements, naip_zone, heights_zone, zone_num, scratchgdb)


    #-----------------------------------------------
    #-----------------------------------------------
    text = "Creating ground and nonground surfaces."
    generateMessage(text)

    #Variables
    ground_mask_poly = os.path.join(scratchgdb, "ground_mask_poly")
    nonground_mask_poly = os.path.join(scratchgdb, "nonground_mask_poly")
    ground_mask_raw = os.path.join(scratchgdb, "ground_mask_raw")
    nonground_mask_raw = os.path.join(scratchgdb, "nonground_mask_raw")
    ground_dissolve_output = os.path.join(scratchgdb, "ground_mask_dis")
    nonground_dissolve_output = os.path.join(scratchgdb, "nonground_mask_dis")
    ground_mask_raster = os.path.join(scratchgdb, "ground_mask_raster")
    nonground_mask_raster = os.path.join(scratchgdb, "nonground_mask_raster")
    nonground_mask_resample = os.path.join(scratchgdb, "nonground_mask_resample")
    ground_mask_resample = os.path.join(scratchgdb, "ground_mask_resample")

    #Find minimum cell area
    min_cell_area = int(float(str(arcpy.GetRasterProperties_management(naip, "CELLSIZEX", "")))**2)+1
    where_clause = "Shape_Area > " + str(min_cell_area)

    # Create masks for ground and nonground features according to ground_ht_threshold
    if unit == "Meters":
      ground_ht_threshold = 0.6096
    elif unit == "Feet":
      ground_ht_threshold = 2

    mask = SetNull(Int(heights_zone),Int(heights_zone),"VALUE > " + str(ground_ht_threshold))
    arcpy.RasterToPolygon_conversion(mask, ground_mask_raw, "NO_SIMPLIFY", "VALUE", )
    arcpy.Dissolve_management(ground_mask_raw, ground_dissolve_output)

    # Find cell size of imagery
    cell_size = str(arcpy.GetRasterProperties_management(naip, "CELLSIZEX", ""))

    # A process of clipping polygons and erasing rasters
    arcpy.Erase_analysis(bnd, ground_dissolve_output, nonground_mask_raw)
    arcpy.PolygonToRaster_conversion(nonground_mask_raw, "OBJECTID", nonground_mask_raster, "CELL_CENTER", "", cell_size)
    arcpy.RasterToPolygon_conversion(nonground_mask_raster, nonground_mask_raw, "NO_SIMPLIFY", "VALUE")
    arcpy.Select_analysis(nonground_mask_raw, nonground_mask_poly, where_clause)
    arcpy.Erase_analysis(bnd, nonground_mask_poly, ground_mask_poly)
    arcpy.PolygonToRaster_conversion(ground_mask_poly, "OBJECTID", ground_mask_raster, "CELL_CENTER", "", cell_size)
    arcpy.RasterToPolygon_conversion(ground_mask_raster, ground_mask_raw, "NO_SIMPLIFY", "VALUE")
    arcpy.Select_analysis(ground_mask_raw, ground_mask_poly, where_clause)
    arcpy.Erase_analysis(bnd, ground_mask_poly, nonground_mask_poly)
    #-----------------------------------------------
    #-----------------------------------------------

    #-----------------------------------------------
    #-----------------------------------------------
    # Segment each surface separately using SMS
    spectral_detail = 10
    spatial_detail = 20
    min_seg_size = 1

    surfaces = ["ground", "nonground"]
    naip_lst = []
    ground_mask_poly = []

    for surface in surfaces:

      #-----------------------------------------------
      #-----------------------------------------------
      text = "Extracting NAIP imagery by "+ surface + " mask."
      generateMessage(text)

      #Variables
      sms_raster = os.path.join(scratchgdb, surface+"_sms_raster")
      naip_fc =  os.path.join(scratchgdb, surface + "_naip_fc")
      mask_poly = os.path.join(scratchgdb, surface+ "_mask_poly")
      mask = mask_poly
      sms = os.path.join(scratchgdb, surface+"_sms")
      naip_mask = os.path.join(scratchgdb,surface + "_naip")
      mask_raw = os.path.join(scratchgdb, surface + "_mask_raw")
      dissolve_output = os.path.join(scratchgdb, surface + "_mask_dis")

      #Raster to be segmented
      ndwi = os.path.join(scratchgdb, "ndwi_"+str(zone_num))
      this = ExtractByMask(ndwi, mask) #naip_zone
      this.save(naip_mask)
      surface_raster_slide = Con(IsNull(Float(naip_mask)), -10000, Float(naip_mask))
      #-----------------------------------------------
      #-----------------------------------------------

      #-----------------------------------------------
      #-----------------------------------------------
      text = "Segmenting "+ surface +" objects."
      generateMessage(text)

      # Creating objects and clipping to surface type
      seg_naip = SegmentMeanShift(surface_raster_slide, spectral_detail, spatial_detail, min_seg_size) #, band_inputs)
      seg_naip.save(sms_raster)
      arcpy.RasterToPolygon_conversion(sms_raster, naip_fc, "NO_SIMPLIFY", "VALUE")
      arcpy.Clip_analysis(naip_fc, mask_poly, sms)
      naip_lst.extend([sms])
      #-----------------------------------------------
      #-----------------------------------------------

    #-----------------------------------------------
    #-----------------------------------------------
    text = "Merging ground and nonground objects."
    generateMessage(text)

    # Merge surface layers, clip to pipe buffer
    sms_full = os.path.join(scratchgdb, "sms_full")
    sms_fc_multi = os.path.join(scratchws,"sms_fc_multi.shp")

    arcpy.Merge_management(naip_lst, sms_full)
    arcpy.Clip_analysis(sms_full, bnd, sms_fc_multi)
    arcpy.MultipartToSinglepart_management(sms_fc_multi, sms_fc)

    # Update Join IDs
    arcpy.AddField_management(sms_fc, "JOIN", "INTEGER")
    rows = arcpy.UpdateCursor(sms_fc)
    i = 1
    for row in rows:
      row.setValue("JOIN", i)
      rows.updateRow(row)
      i+= 1

    #-----------------------------------------------
    #-----------------------------------------------
   
    text = "Calculating zonal median of each spectral enhancement for each object."
    generateMessage(text)
    for ie in created_enhancements_1m:
      field = image_enhancements.pop(0)
      outTable = os.path.join(scratchgdb, "zonal_"+os.path.basename(ie))
      z_stat = ZonalStatisticsAsTable(sms_fc, "JOIN", ie, outTable, "NODATA", "MAJORITY")
      arcpy.AddField_management(outTable, field, "INTEGER")
      arcpy.CalculateField_management(outTable, field, "[MAJORITY]")
      one_to_one_join(sms_fc, outTable, field, "INTEGER")

    arcpy.DefineProjection_management(sms_fc, projection)
    #-----------------------------------------------
    #-----------------------------------------------

    #-----------------------------------------------
    #-----------------------------------------------
    # Fuzzy rule classifier
    #
    #Primitive types = [vegetation, impervious, water, confusion]
    #Land cover types = [tree, shrub, grass, pavement, building, water]
    #
    # Stages:
    #   1. Classify object based on majority primitive type
    #   2. Classify each primitive object based on IE and height
  if create_obia == "Yes":
    obia()
  #-----------------------------------------------
  #-----------------------------------------------

  #-----------------------------------------------
  #-----------------------------------------------
  def classify(stage, landcover, field):
    if stage == "S1":
      if field == "S1_grid":
        threshold = get_thresholds(bioregion, stage, landcover, field, unit)
        healthy = threshold[0]
        dry = threshold[1]
        return("def landcover(x):\\n"+
               "  if x "+healthy+":\\n"+
               "    return \"healthy\"\\n"+
               "  elif x "+dry+":\\n"+
               "    return \"senescent\"\\n"+
               "  return \"impervious\""
               )

      elif field == "S1_ndvi":
        threshold = get_thresholds(bioregion, stage, landcover, field, unit)
        imp = threshold[0]
        veg = threshold[1]
        return ("def landcover(x):\\n"+
               "  membership = \"\"\\n"+
               "  if "+imp+":\\n"+
               "    membership += \"I\"\\n"+
               "  if "+veg+":\\n"+
               "    membership += \"V\"\\n"+
               "  return membership\\n"
               )

      elif field == "S1_ndwi":
        threshold = get_thresholds(bioregion, stage, landcover, field, unit)
        imp = threshold[0]
        veg = threshold[1]
        return ("def landcover(x):\\n"+
               "  membership = \"\"\\n"+
               "  if "+imp+":\\n"+
               "    membership += \"I\"\\n"+
               "  if "+veg+":\\n"+
               "    membership += \"V\"\\n"+
               "  return membership\\n"
               )

      elif field == "S1_gndv":
        threshold = get_thresholds(bioregion, stage, landcover, field, unit)
        imp = threshold[0]
        veg = threshold[1]
        return ("def landcover(x):\\n"+
               "  membership = \"\"\\n"+
               "  if "+imp+":\\n"+
               "    membership += \"I\"\\n"+
               "  if "+veg+":\\n"+
               "    membership += \"V\"\\n"+
               "  return membership\\n"
               )

      elif field == "S1_osav":
        threshold = get_thresholds(bioregion, stage, landcover, field, unit)
        imp = threshold[0]
        veg = threshold[1]
        return ("def landcover(x):\\n"+
               "  membership = \"\"\\n"+
               "  if "+imp+":\\n"+
               "    membership += \"I\"\\n"+
               "  if "+veg+":\\n"+
               "    membership += \"V\"\\n"+
               "  return membership\\n"
               )

      elif field == "S1":
        return("def landcover(a,b,c,d):\\n"+
               "  membership = a+b+c+d\\n"+
               "  V,I = 0,0\\n"+
               "  for m in membership:\\n"+
               "    if m == \"V\":\\n"+
               "      V += 1\\n"+
               "    if m == \"I\":\\n"+
               "      I += 1\\n"+
               "  if V > I:\\n"+
               "    return \"vegetation\"\\n"+
               "  elif I > V:\\n"+
               "    return \"impervious\"\\n"+
               "  else:\\n"+
               "    return \"confusion\"\\n"
               )

  # Assigns classess
  def createClassMembership(stage, landcover, field, field_lst, output):
    if field in stages:
      field_lst = field_lst[:-2]
      fxn = "landcover("+field_lst+")"

    else:
      index = field
      field = stage+"_"+field[:4]
      field_lst += "!"+field+"!, "
      fxn = "landcover(!"+index+"!)"

    label_class = classify(stage, landcover, field)
    arcpy.AddField_management(output, field, "TEXT")
    arcpy.CalculateField_management(output, field, fxn, "PYTHON_9.3", label_class)
    return field_lst
  #-----------------------------------------------
  #-----------------------------------------------

  #-----------------------------------------------
  #-----------------------------------------------
  # Classifier methods
  stages = ["S1","S2"]
  class_structure = [
                     ["vegetation",
                          ["grass", "shrub", "tree"]],
                     ["impervious",
                          ["building", "path"]]
                    ]

  # Indices used for each stage of classification
  s1_indices = ["ndvi", "ndwi", "gndvi", "osavi"]#, "gridcode"]
  s2_indices = ["height"]#, "gridcode"]

  def classify_objects():
    lst_merge = []
    veg_lst = []
    imp_lst = []

    for stage in stages:
      text = "Executing Stage "+str(stage)+" classification."
      newProcess(text)

      # Stage 1 classification workflow
      if stage == "S1":
        s1_indices.extend([stage])
        field_lst = ""
        for field in s1_indices:

          # Assign full membership
          if field == "S1":
            text = "Creating primitive-type objects."
            generateMessage(text)

            # Classification method
            createClassMembership(stage, "", field, field_lst, sms_fc)

            # Create new shapefiles with primitive classess
            for primitive in class_structure:
              landcover = primitive[0]
              output = os.path.join(outputs, landcover+"_"+str(zone_num)+".shp")
              where_clause = "S1 = '" + landcover + "'"
              arcpy.Select_analysis(sms_fc, output, where_clause)


          # Assign partial membership
          else:
            text = "Classifying objects by "+field+"."
            generateMessage(text)
            field_lst = createClassMembership(stage, "", field, field_lst, sms_fc)

        #-----------------------------------------------
        #-----------------------------------------------
        def SVM():
          text = "Classifying confused land cover with SVM."
          newProcess(text)

          # Variables
          confused = os.path.join(outputs, "confused.shp")
          veg_join = os.path.join(scratchgdb, "veg_join")
          training_samples = os.path.join(outputs, "training_fc.shp")
          merged = os.path.join(scratchgdb, "merged_imp_veg")
          composite = os.path.join(outputs, "composite.tif")
          confused_composite = os.path.join(outputs, "confused_composite.tif")
          confused_composite_rast = os.path.join(scratchws, "confused_composit_rast.tif")
          veg_imp = os.path.join(scratchws, "veg_imp.shp")

          # Create dataset with only confused objects
          text = "Creating confused objects."
          generateMessage(text)

          arcpy.Select_analysis(sms_fc, confused, "S1 = 'confusion'")

          # Indices used as bands in raster for SVM
          band_lst = ["ndvi", "ndwi", "height"]

          # Creating Layer composite
          text = "Creating LiDAR-Multispectral stack."
          generateMessage(text)

          confused_ie_lst = []
          bands_5m = createImageEnhancements(band_lst, naip, heights, "5m", scratchgdb)
          for ie in bands_5m:
            band = os.path.basename(ie)
            confused_ie = os.path.join(scratchgdb, "confused_"+band)
            this = ExtractByMask(ie, confused)
            this = Con(IsNull(Float(this)), -10000, Float(this))
            this.save(confused_ie)
            confused_ie_lst.extend([confused_ie])
          arcpy.CompositeBands_management(confused_ie_lst, composite)
          arcpy.DefineProjection_management(composite, projection)


          #-----------------------------------------------
          #-----------------------------------------------

          #-----------------------------------------------
          #-----------------------------------------------
          text = "Preparing training samples for SVM."
          generateMessage(text)

          # Variables
          svm_training = os.path.join(outputs, "svm_training.shp")
          training_fields = [["Classname", "TEXT"], ["Classvalue", "LONG"], ["RED", "LONG"], ["GREEN", "LONG"], ["BLUE", "LONG"], ["Count", "LONG"]]
          zonal_training = os.path.join(scratchgdb, "zonal_train")

          # Adding the appropriate fields for training samples
          #arcpy.FeatureClassToFeatureClass_conversion (training_samples, outputs, "svm_training")
          def classvalue():
            return ("def classvalue(x):\\n"+
                     "  if x == \"vegetation\":\\n"+
                     "    return 0\\n"+
                     "  elif x == \"impervious\": \\n"+
                     "    return 1\\n"
                     )

          arcpy.Select_analysis(sms_fc, svm_training, "S1 <> 'confusion'")
          for field in training_fields:
            field_name = field[0]
            field_type = field[1]
            arcpy.AddField_management(svm_training, field_name, field_type)

          # Calculating attributes for training samples
          arcpy.AddField_management(svm_training, "JOIN", "INTEGER")
          arcpy.CalculateField_management(svm_training, "JOIN", "[FID]")
          z_stat = ZonalStatisticsAsTable(svm_training, "JOIN", composite, zonal_training, "NODATA", "ALL")
          arcpy.AddField_management(svm_training, "COUNT", "LONG")
          one_to_one_join(svm_training, zonal_training, "COUNT", "INTEGER")
          arcpy.CalculateField_management(svm_training, "Classname", "[S1]")
          arcpy.CalculateField_management(svm_training, "Classvalue", "classvalue(!S1!)", "PYTHON_9.3", classvalue())
          arcpy.CalculateField_management(svm_training, "RED", 1)
          arcpy.CalculateField_management(svm_training, "GREEN", 1)
          arcpy.CalculateField_management(svm_training, "BLUE", 1)
          arcpy.CalculateField_management(svm_training, "COUNT", "[COUNT]")

          # Removing unnecessary fields for training samples
          fields = [f.name for f in arcpy.ListFields(svm_training)]
          delete_fields = []
          for field in fields:
            if field not in ["FID", "Shape", "Shape_Area", "Shape_Length", "Classname", "Classvalue", "RED", "GREEN", "BLUE", "Count"]:
              delete_fields.append(field)
          arcpy.DeleteField_management(svm_training, delete_fields)

          # Parameters used for SVM
          out_definition = os.path.join(outputs, "svm_classifier.ecd")
          maxNumSamples = "100"
          attributes = "" #[COLOR, SHAPE, etc.]
          # No color because color isn't related to land cover type
          # No to shape because shape isn't associated with any type
          #-----------------------------------------------
          #-----------------------------------------------

          #-----------------------------------------------
          #-----------------------------------------------
          text = "Classifying composite using Support Vector Machines."
          generateMessage(text)

          # Variables
          svm = os.path.join(outputs, "svm.tif")

          # Creating classifier rule from training samples
          arcpy.gp.TrainSupportVectorMachineClassifier(composite, svm_training, out_definition, "", maxNumSamples, attributes)

          # Classifying raster with pixel-based method, not segmented raster
          classifiedraster = ClassifyRaster(composite, out_definition, "")
          classifiedraster.save(svm)

          #-----------------------------------------------
          #-----------------------------------------------

          #-----------------------------------------------
          #-----------------------------------------------
          text = "Classifying 'Confused' objects with SVM outputs."
          generateMessage(text)

          # Variables
          zonal_svm = os.path.join(scratchgdb, "zonal_svm")

          ## Joining zonal majority to confused object
          
          z_stat = ZonalStatisticsAsTable(confused, "JOIN", svm, zonal_svm, "NODATA", "MAJORITY")
          arcpy.AddField_management(confused, "MAJORITY", "LONG")
          one_to_one_join(confused, zonal_svm, "MAJORITY", "LONG")

          # Assigning land cover to 'Confused' objects
          def classify_confusion():
            vegetation = "x == 0"
            impervious = "x == 1"
            return("def landcover(x):\\n"+
                         "  if "+vegetation+":\\n"+
                         "    return \"vegetation\"\\n"+
                         "  elif "+impervious+":\\n"+
                         "    return \"impervious\"\\n"
                         )
          arcpy.CalculateField_management(confused, "S1", "landcover(!MAJORITY!)", "PYTHON_9.3", classify_confusion())
          #-----------------------------------------------
          #-----------------------------------------------

          #-----------------------------------------------
          #-----------------------------------------------
          text = "Creating contiguously classified primitive land cover."
          generateMessage(text)

          # Merging all layers back together as classified layer
          arcpy.Select_analysis(sms_fc, veg_imp, "S1 <> 'confusion'")
          arcpy.Merge_management([confused, veg_imp], S1_classified)

        if run_svm ==  "Yes":
          SVM()
      #-----------------------------------------------
      #-----------------------------------------------

      # Stage 2 classification workflow
      elif stage == "S2":

        s2_indices.extend([stage])
        features = []
        for primitive in class_structure:
          landcover = primitive[0]
          s1_heights = os.path.join(scratchgdb, landcover+"_heights")
          heights_zone = os.path.join(outputs, "height_zone_"+str(zone_num)+".tif")
          primitive_mask = os.path.join(outputs, landcover+"_"+str(zone_num)+".shp")
          cm_heights = os.path.join(scratchgdb, "cm_heights")

          text = "Preparing "+landcover+" height surfaces."
          generateMessage(text)

          arcpy.Select_analysis(S1_classified, primitive_mask, "S1 = '"+landcover+"'")
          this = Int(Float(heights)*100)
          this.save(cm_heights)
          this = ExtractByMask(cm_heights, primitive_mask)
          this.save(s1_heights)

          stage_output = os.path.join(outputs, landcover+"_"+str(zone_num)+".shp")
          field_lst = ""
          s2 = primitive[1]

          for stage in s2:
            stage_rast = os.path.join(scratchgdb, stage)
            stage_mask = os.path.join(scratchgdb, stage+"_mask")
            naip_fuel = os.path.join(scratchgdb, "naip_"+stage)
            fuel_sms_rast = os.path.join(scratchgdb, stage+"_sms_rast")
            fuel_sms = os.path.join(scratchgdb, stage+"_sms")
            fuel_fc = os.path.join(scratchgdb, stage+"_fc")
            
            text = "Creating "+ stage +" objects."
            generateMessage(text)

            if stage == "grass":
              spectral_detail = 10
              spatial_detail = 10
              min_seg_size = 1
              s2 = "grass"

              this = Con(Int(s1_heights)<=30.48, 1)

            elif stage == "shrub":

              spectral_detail = 20
              spatial_detail = 20
              min_seg_size = 1
              s2 = "shrub"

              this = Con((Int(s1_heights)>30.48) & (Int(s1_heights)<=182.88), 1)

            elif stage == "tree":
              
              spectral_detail = 20
              spatial_detail = 20
              min_seg_size = 1
              s2 = "tree"

              this = Con(Int(s1_heights)>182.88, 1)

            elif stage == "path":
              
              spectral_detail = 1
              spatial_detail = 1
              min_seg_size = 1
              s2 = "path"

              this = Con(Int(s1_heights)<=30.48, 1)

            elif stage == "building":

              spectral_detail = 1
              spatial_detail = 20
              min_seg_size = 1
              s2 = "building"

              this = Con(Int(s1_heights)>30.48, 1)

            this.save(stage_rast)

            arcpy.RasterToPolygon_conversion(stage_rast, stage_mask, "NO_SIMPLIFY", "VALUE")
        
            this =  ExtractByMask(naip, stage_mask)
            this.save(naip_fuel)
        
            
            naip_raster_slide = Con(IsNull(Float(naip_fuel)), -10000, Float(naip_fuel))

            # Creating objects and clipping to surface type
            seg_naip = SegmentMeanShift(naip_raster_slide, spectral_detail, spatial_detail, min_seg_size)
            seg_naip.save(fuel_sms_rast)
            this = ExtractByMask(fuel_sms_rast, naip_fuel)
            this.save(fuel_sms_rast)
            arcpy.RasterToPolygon_conversion(fuel_sms_rast, fuel_fc, "NO_SIMPLIFY", "VALUE")
            fxn = "S2()"
            label_class = "def S2():\\n"+"  return '"+s2+"'\\n"
            arcpy.AddField_management(fuel_fc, "S2", "TEXT")
            arcpy.CalculateField_management(fuel_fc, "S2", fxn, "PYTHON_9.3", label_class)
            #arcpy.CalculateField_management(fuel_fc, "S2", "'"+s2+"'")
            features.extend([fuel_fc])

        text = "Creating contiguous land cover."
        generateMessage(text)

        arcpy.Merge_management(features, landscape_fc)
        # Update Join IDs
        arcpy.AddField_management(landscape_fc, "JOIN", "INTEGER")
        rows = arcpy.UpdateCursor(landscape_fc)
        i = 1
        for row in rows:
          row.setValue("JOIN", i)
          rows.updateRow(row)
          i+= 1


        outTable = os.path.join(scratchgdb, "zonal_height")
        z_stat = ZonalStatisticsAsTable(landscape_fc, "JOIN", heights_zone, outTable, "NODATA", "MAXIMUM")
        arcpy.AddField_management(outTable, "height", "FLOAT")
        arcpy.CalculateField_management(outTable, "height", "[MAX]")
        one_to_one_join(landscape_fc, outTable, "height", "FLOAT")
          
        
      # Variables

  if classify_landscape == "Yes":
    classify_objects()
  # iterate through next zone if possible
  zones = searchcursor.next()
  #-----------------------------------------------
  #-----------------------------------------------

#-----------------------------------------------
#-----------------------------------------------
def fuels():

  text = "Assigning fuel models."
  newProcess(text)

  # Variables
  land_cover_fields = [["fuel", "S2"], ["canopy", "S2"], ["stand", "height"]]

  def classify(model, x):

    # Anderson 13 fuel models
    if model == "13":
      building = "99"
      tree = "10"
      shrub = "6"
      grass = "1"
      water = "98"
      path = "99"
    elif model != "13":
      #-----------------------------------------------
      #-----------------------------------------------
      text = "Cannot classify fuels. Only Anderson 13 are available."
      generateMessage(text)
      #-----------------------------------------------
      classify("13", output_field)
    if x == "fuel":
      return ("def classify(x):\\n"+
              "  if x == \"building\":\\n"+
              "    return "+building+"\\n"+
              "  elif x == \"path\": \\n"+
              "    return "+path+"\\n"+
              "  elif x == \"water\":\\n"+
              "    return "+water+"\\n"+
              "  elif x == \"grass\":\\n"+
              "    return "+grass+"\\n"+
              "  elif x == \"shrub\":\\n"+
              "    return "+shrub+"\\n"+
              "  elif x == \"tree\":\\n"+
              "    return "+tree+"\\n"
              )

    elif x == "canopy":
      return ("def classify(x):\\n"+
              "  if x == \"tree\":\\n"+
              "    return 50\\n"+ # 50% canopy cover b/c
              "  return 0"
              )
    # Returns height attribute - May delete if cannot include into .LCP
    elif x == "stand":
      return("def classify(x):\\n"+
             "  return x"
             )

  for field in land_cover_fields:
    input_field = field[1]
    output_field = field[0]
    arcpy.AddField_management(landscape_fc, output_field, "INTEGER")
    fxn = "classify(!"+input_field+"!)"
    label_class = classify(model, output_field)
    arcpy.CalculateField_management(landscape_fc, output_field, fxn, "PYTHON_9.3", label_class)

  #-----------------------------------------------
  #-----------------------------------------------

  #-----------------------------------------------
  #-----------------------------------------------
  text = "Fuel complex created."
  generateMessage(text)
if classify_fuels == "Yes":
  fuels()

#-----------------------------------------------
#-----------------------------------------------

#-----------------------------------------------
#-----------------------------------------------
def LCP():
  text = "Creating Landscape File."
  newProcess(text)

  # Variables
  fuel_lst = ["fuel", "canopy", "stand"]
  elevation_lst = ["slope", "elevation", "aspect"]
  ascii_layers = []
  fuel = os.path.join(outputs, "fuel.asc")

  def convertToAscii(x, landscape_elements):

    for layer in landscape_elements:

      # Variables
      ascii_output = os.path.join(outputs, layer + ".asc")
      where_clause = layer +" <> 9999"
      temp = os.path.join(scratchgdb, "t_"+layer)
      temp_raster = os.path.join(scratchgdb, "t_"+layer+"_r")
      final = os.path.join(scratchgdb, layer)

      # Selecting layer and converting to raster
      if layer in fuel_lst:
        arcpy.Select_analysis(landscape_fc, temp, where_clause)
        arcpy.PolygonToRaster_conversion(temp, layer, temp_raster, "CELL_CENTER", "",dem)
      elif layer in elevation_lst:

        # Calculating elevation derived layers
        if layer == "slope":
          arcpy.Slope_3d(dem, temp_raster, "DEGREE")
        elif layer == "aspect":
          arcpy.Aspect_3d(dem, temp_raster)
        elif layer == "elevation":
          temp_raster = dem

      # Preparing raster for LCP specifications
      arcpy.CopyRaster_management(temp_raster, final, "", "", "0", "NONE", "NONE", "32_BIT_SIGNED","NONE", "NONE", "GRID", "NONE")
      arcpy.DefineProjection_management(temp_raster, projection)

      # Extracting layer by analysis area
      ready = ExtractByMask(final, naip)
      ready.save(temp_raster)

      # Converting to ascii format and adding to list for LCP tool
      arcpy.RasterToASCII_conversion(ready, ascii_output)
      ascii_layers.append(ascii_output)

      text = "The "+layer+" ascii file was created."
      generateMessage(text)

  # Coding note: Check to see that lists are concatenated
  convertToAscii(landscape_fc, fuel_lst + elevation_lst)

  #-----------------------------------------------
  #-----------------------------------------------

  #-----------------------------------------------
  #-----------------------------------------------
  text = "Creating LCP file."
  generateMessage(text)

  import ctypes
  ##
  ### Variables
  landscape_file = os.path.join(outputs, "landscape.lcp")
  genlcp = os.path.join(dll_path, "GenLCPv2.dll")
  Res = landscape_file
  Elev = os.path.join(outputs,"elevation.asc")
  Slope = os.path.join(outputs,"slope.asc")
  Aspect = os.path.join(outputs,"aspect.asc")
  Fuel = os.path.join(outputs,"fuel.asc")
  Canopy = os.path.join(outputs,"canopy.asc")

  # Create LCP
  dll = ctypes.cdll.LoadLibrary(genlcp)
  fm = getattr(dll, "?Gen@@YAHPBD000000@Z")
  fm.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
  fm.restype = ctypes.c_int

  e = fm(Res, Elev, Slope, Aspect, Fuel, Canopy, "")
  if e > 0:
    arcpy.AddError("Error {0}".format(e))
if create_LCP == "Yes":
  LCP()
#-----------------------------------------------
#-----------------------------------------------

#-----------------------------------------------
#-----------------------------------------------
def burn():
  text = "Running FlamMap."
  newProcess(text)

  # Burn in FlamMap
  #
  flamMap = os.path.join(dll_path, "FlamMapF.dll")
  dll = ctypes.cdll.LoadLibrary(flamMap)
  fm = getattr(dll, "?Run@@YAHPBD000NN000HHN@Z")
  fm.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_double, ctypes.c_double, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_int, ctypes.c_double]
  fm.restype = ctypes.c_int

  Landscape = landscape_file
  FuelMoist = fuel_moisture
  OutputFile = os.path.join(outputs, "Burn")
  FuelModel = "-1"
  Windspeed = 30.0  # mph
  WindDir = 0.0   # Direction angle in degrees
  Weather = "-1"
  WindFileName = "-1"
  DateFileName = "-1"
  FoliarMoist = 100 # 50%
  CalcMeth = 0    # 0 = Finney 1998, 1 = Scott & Reinhardt 2001
  Res = -1.0

  e = fm(Landscape, FuelMoist, OutputFile, FuelModel, Windspeed, WindDir, Weather, WindFileName, DateFileName, FoliarMoist, CalcMeth, Res)
  if e > 0:
    arcpy.AddError("Problem with parameter {0}".format(e))


  for root, dirs, fm_outputs in os.walk(outputs): #Check to confirm outputs are saved here
     for burn in fm_outputs:
        if burn[-3:].lower() in burn_metrics:
            metric = burn[-3:].lower()
            burn_ascii = os.path.join(outputs, metric+".asc")
            os.rename(os.path.join(outputs, burn), burn_ascii)


  text = "Burn complete."
  generateMessage(text)
if run_FlamMap == "Yes":
  burn()
#-----------------------------------------------
#-----------------------------------------------
def burn_obia():
  text = "Running OBIA on fire behavior metrics."
  newProcess(text)
  # Set Cell Size
  arcpy.env.snapRaster = naip
  cell_size = str(arcpy.GetRasterProperties_management(naip, "CELLSIZEX", ""))
  naip_cell_size = cell_size +" " +cell_size
  #-----------------------------------------------
  #-----------------------------------------------

  for metric in burn_metrics:

    #-----------------------------------------------
    #-----------------------------------------------
    text = "Calculating and joining max " + metric + " to each object."
    generateMessage(text)
    #-----------------------------------------------
    #Set variables
    in_ascii_file = os.path.join(outputs, metric + ".asc")
    burn = os.path.join(scratchgdb, metric)
    raw_raster = os.path.join(scratchgdb, metric  + "_raw")
    scaled_raster = os.path.join(outputs, metric +"_scaled.tif")
    raster_resample = os.path.join(outputs, metric + "_res.tif")
    #shift = os.path.join(outputs, metric+".tif")
    outTable = os.path.join(scratchgdb, "zonal_"+metric)

    #-----------------------------------------------
    #-----------------------------------------------
    # Convert ascii output to raster and align cells
    arcpy.ASCIIToRaster_conversion(in_ascii_file, raw_raster, "FLOAT")
    arcpy.DefineProjection_management(raw_raster, projection)

    if metric == "fli":
      unit_scalar = 1#0.288894658
    elif metric == "fml":
      unit_scalar = 1
    elif metric == "ros":
      unit_scalar = 1#3.28084

    this = Raster(raw_raster)*unit_scalar
    this.save(scaled_raster)
    arcpy.Resample_management(scaled_raster, burn, naip_cell_size, "NEAREST")

    #-----------------------------------------------
    #-----------------------------------------------

    #-----------------------------------------------
    #-----------------------------------------------
    # Calculate zonal max and join to each objects
    arcpy.CalculateField_management(landscape_fc, "JOIN", "[FID]+1")
    z_table = ZonalStatisticsAsTable(landscape_fc, "JOIN", burn, outTable, "NODATA", "MAXIMUM")
    arcpy.AddField_management(outTable, metric, "FLOAT")
    arcpy.CalculateField_management(outTable, metric, "[MAX]")
    one_to_one_join(landscape_fc, outTable, metric, "FLOAT")
    #-----------------------------------------------
    #-----------------------------------------------

  #-----------------------------------------------
  #-----------------------------------------------
  text = "All burn severity joins are complete."
  generateMessage(text)
if join_burns == "Yes":
  burn_obia()
#-----------------------------------------------
#-----------------------------------------------

def MXD():

  mxd_file = os.path.join(current_project, location_name+".mxd")

  symbology_path = drive+":\\TFS_Fire\\Symbology"
  if not os.path.isfile(mxd_file):
    text = "Creating new MXD: "+location_name+"."
    generateMessage(text)
    new_file = "Yes"
    mxd_path = os.path.join(symbology_path, "blank.mxd")
  else:
    mxd_path = mxd_file
    text = "Updating existing MXD: "+os.path.basename(mxd_path)+"."
    generateMessage(text)
    new_file = "No"
  mxd = arcpy.mapping.MapDocument(mxd_path)
  df = arcpy.mapping.ListDataFrames(mxd, "Layers")[0]

  # Layers
  symbol_layers = [landscape_fc, pipeline]
  classified_layers = ["landcover"]#, "fli", "ros", "fml"]
  layers = [dem, scaled_dem, heights, scaled_heights, raw_naip, naip]

  fields = [f.name for f in arcpy.ListFields(landscape_fc)]
  for field in fields:
    if field in burn_metrics:
      classified_layers.extend([field])


  # Symbology
  #df_lst = []
  for symbol in classified_layers:
    layer = arcpy.mapping.Layer(landscape_fc)
    symbology = os.path.join(symbology_path, symbol+".lyr")
    symbologyFields = ["VALUE_FIELD", "#", "S2"],
    arcpy.ApplySymbologyFromLayer_management(layer, symbology)#, symbologyFields)
  #  df_lst.append(new)

  #or layer in df_lst:
  arcpy.mapping.AddLayer(df, layer, "TOP")
  if new_file == "Yes":
    mxd.saveACopy(mxd_file)
  else:
    mxd.save()

  #for layer in layers:
  #  arcpy.mapping.AddLayer(df, layer)

if create_MXD == "Yes":
  MXD()
#-----------------------------------------------
text = "All processes are complete."
generateMessage(text)
#-----------------------------------------------