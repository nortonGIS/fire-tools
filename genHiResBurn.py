#--------------------------------------------------------------------------------------------------------------------------------------
# Name:        genHiResBurn Tool
# Author:      Peter Norton
# Created:     05/25/2017
# Updated:     12/16/2017
# Copyright:   (c) Peter Norton and Matt Ashenfarb 2017
#--------------------------------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------------------------------
#
# USER LOG
date = "1_4-2012"
# Geographic Data
location_name = "Yosemite"
bioregion = "Sierra_Nevada_Mountains" #["Sierra_Nevada_Mountains","CA_Oak_Woodlands", "SoCal_Mountains"]


summary = ""
#summary = "Purpose:     \\n"+
#          "(1) Process raw imagery and raw lidar data into landscape objects that are classified into fire behavior fuel models.\\n"+
#          "(2) Create all necessary input files for FlamMap's landscape file (.LCP) and burn using FlamMap DLL.\\n"+
#          "(3) Join all burn metrics to objects. If an infrastructure file exists, then burns will be joined to infrsx segments.\\n"+
#          "(4) Populate an MXD with all necessary shapefiles.\\n"

projection = "UTMZ11"  #["UTMZ10", "UTMZ11"]
lidar_date = 2013
naip_date = 2014
burn_metrics = ["fml", "ros", "fi"]

# Settings
coarsening_size = "5" #meters
tile_size = "1" #square miles
buff_distance = "1000 feet" # Buffer around infrastructure

# inputs
input_bnd = "bnd.shp"
input_naip = "naip.tif"
input_las = "pointcloud.lasd"
input_heights = "heights.tif"
input_dem = "dem.tif"
input_pipeline = "pipeline.shp"

# not active
input_fuel_moisture = "fuel_moisture.fms"
input_wind = ""
input_weather = ""

#--------------------------------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------------------------------

#-----------------------------------------------
#-----------------------------------------------

pull_imagery = "No"
process_lidar = "Yes" # Process LiDAR data
align_inputs = "Yes" # "Align and Scale inputs"
pipe_analysis = "No"  # "Reduce Analysis to Infrastructure Buffer"
generate_land_cover = "Yes"  # "Generate Land Cover & SVM"
fire_behavior = "No"  # "Run FlamMap & Join Burns"
create_MXD = "Yes"  # "Create or Update MXD"

processes = [
[align_inputs, "Align Inputs"],
[pipe_analysis, "Extract Infrastructure"],
[generate_land_cover, "Generate Land Cover"],
[fire_behavior, "Assess Fire Behavior"],
[create_MXD, "Create MXD: "+location_name]
]
#-----------------------------------------------
#-----------------------------------------------


#-----------------------------------------------
#-----------------------------------------------
# Processing - DO NOT MODIFY BELOW
#-----------------------------------------------
#-----------------------------------------------

#-----------------------------------------------
#-----------------------------------------------
# Import
import time
import arcpy
#import ee
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
from thresholdsLib import *

#Setting inputs, outputs, scratchws, scratch.gdb

inputs = os.path.join(current_project, "01_Inputs")
outputs = os.path.join(current_project, "02_Unmitigated_Outputs")
scratchws = os.path.join(current_project, "04_Scratch")
scratchgdb = os.path.join(scratchws, "Scratch.gdb")
dll_path = os.path.join(current_project, "05_Scripts")
arcpy.env.workspace = scratchgdb
arcpy.env.overwriteOutput = True

#-----------------------------------------------
#-----------------------------------------------
# Set Global Variables
# Raw inputs
raw_naip = os.path.join(inputs, input_naip) # NAIP Imagery at 1m res
lasd = os.path.join(inputs, input_las)
raw_heights = os.path.join(inputs, input_heights) # Heights
raw_dem = os.path.join(inputs, input_dem) # DEM
raw_dsm = os.path.join(inputs, "dsm.tif")
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
classified_landscape = os.path.join(outputs, "classified.shp")

used_tiles = os.path.join(outputs, "bnd_fishnet.shp")
analysis_area = used_tiles #bnd_zones  # analysis area/ area of interest
dem = os.path.join(outputs, "dem_"+coarsening_size+"m.tif")  # Resampled DEM in native units
heights = os.path.join(outputs, "heights_"+coarsening_size+"m.tif")  # Resampled heights in native units
scaled_heights = os.path.join(outputs, "scaled_heights.tif")  # Heights in project units
scaled_dem = os.path.join(outputs, "scaled_dem.tif")  # DEM in project units
canopy_cover_tif = os.path.join(outputs,"canopy_cover.tif")
canopycover = os.path.join(scratchgdb, "canopycover")
tiles_used = 1


naip = os.path.join(outputs, "naip_"+coarsening_size+"m.tif")  # NAIP in project units
naip_b1 = os.path.join(naip, "Band_1")
naip_b2 = os.path.join(naip, "Band_2")
naip_b3 = os.path.join(naip, "Band_3")
naip_b4 = os.path.join(naip, "Band_4")
#-----------------------------------------------
#-----------------------------------------------

#-----------------------------------------------
#-----------------------------------------------
# Details
arcpy.AddMessage("Site: "+location_name)
arcpy.AddMessage("Projection: "+projection)
arcpy.AddMessage("Resolution: "+coarsening_size + "m")

#Create Process Log
info  = os.path.join(current_project, "README.txt")
if os.path.isfile(info):
  os.remove(info)
f = open(info, "w")
f.write(date+"\n")
f.write(location_name+"\n")
f.write("-----------------------------"+"\n")
f.write(summary+"\n")
f.write("-----------------------------"+"\n")
#f.close()

def log(message):
#  f = open(info, "w")
  f.write(message+"\n")
#  f.close()

arcpy.AddMessage("-----------------------------")
arcpy.AddMessage("Processes enabled:")
for process in processes:
  if process[0] == "Yes":
    arcpy.AddMessage("    -"+process[1])
arcpy.AddMessage("-----------------------------")

# Alert function with step counter
count = 1
def generateMessage(text):
  global count
  message = "Step " + str(count) + ": " +text
  arcpy.AddMessage(message)
  count += 1
  log(message)


def newProcess(text):
  global count
  count = 1
  message = "Process: "+text
  arcpy.AddMessage("-----------------------------")
  arcpy.AddMessage(message)
  arcpy.AddMessage("-----------------------------")
  log(message)

def empty_scratchgdb():
  if arcpy.Exists(scratchgdb):  
    arcpy.Delete_management(scratchgdb)
  arcpy.CreateFileGDB_management(scratchws, "Scratch.gdb")

ts = 0
total_area = 0
remaining_area = 0
completed_area = 0
zone_area = 0
times = []
def estimate_time(zone_num):

  global ts
  global total_area
  global completed_area
  global remaining_area
  global zone_area
  global times

  tf = time.time()
  te = tf - ts
  ts = tf

  tem = te//60

  completed_area += zone_area
  percent_area = int((completed_area/total_area)*100)
  remaining_area = total_area-completed_area
  zone_runtime = tem//(zone_area) #runtime for sq. km

  times.extend([zone_runtime])
  avg_time = sum(times)//len(times)
  remaining_time = int(avg_time*remaining_area)
  hours = remaining_time//60
  minutes = remaining_time%10

  arcpy.AddMessage(str(percent_area)+" % Completed  |  Estimated time remaining: "+ str(hours)+"hrs:"+str(minutes)+"min")
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

  def download_NAIP():
    gdrive_output = ""

    bnd_WGS = os.path.join(scratchgdb, "bnd_WGS")
    projection = ""
    arcpy.ProjectRaster_management(bnd_zones, bnd_WGS, projection, "BILINEAR")
    desc = arcpy.Describe(bnd_WGS)
    origin_coord = str(desc.extent.XMin)+ " " +str(desc.extent.YMin)
    y_axis_coord = str(desc.extent.XMin)+ " " +str(desc.extent.YMax)

    class location:
      def __init__(self, name, start, end, lon1, lat1, lon2, lat2):
        self.name = location_name
        self.start = lidar_date+"-01-01"
        self.end = str(int(lidar_date)+10)+"-12-30"
        self.lon1 = desc.extent.XMin
        self.lat1 = desc.extent.YMin
        self.lon2 = desc.extent.XMax
        self.lat2 = desc.extent.YMax

    naip = location(location_name)

    naip.boundary = ee.Geometry.Rectangle([naip.lon1, naip.lat1, naip.lon2, naip.lat2]);
    naip.image = (((ee.ImageCollection("USDA/NAIP/DOQQ")).filterDate(naip.start, naip.end)).first()).mosaic()

    task = ee.Export.image.toDrive(naip.image, naip.name,  gdrive_output, naip.name, "", "", 1)

    task.start()

  if pull_imagery == "Yes":
    download_NAIP()
  #-----------------------------------------------
  #-----------------------------------------------



  #-----------------------------------------------
  #-----------------------------------------------
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
  cell_size = int(coarsening_size)
  naip_cell_size = str(cell_size) +" "+str(cell_size)
  arcpy.Resample_management(raw_naip, naip, naip_cell_size, "BILINEAR") # Bilinear Interpolation reduce image distortion when scaling.It linearly interpolates the nearest 4 pixels
  arcpy.DefineProjection_management(naip, projection)
  bands = ["Band_1","Band_2","Band_3","Band_4"] # NAIP has 4 bands (in increasing order) B,G,R,NIR

  arcpy.env.snapRaster = naip

  # Create a fitted, resampled boundary
  text = "Creating a boundary based on resampled NAIP imagery extent."
  generateMessage(text)

  this = Int(Raster(naip)*0)
  this.save(bnd_zones_rast)
  arcpy.DefineProjection_management(bnd_zones_rast, projection)
  arcpy.RasterToPolygon_conversion(bnd_zones_rast, bnd_zones, "NO_SIMPLIFY", "Value")

  #make fishnet with 1km x 1km
  analysis_area = os.path.join(outputs, "bnd_fishnet.shp")

  text = "Creating a fishnet."
  generateMessage(text)

  fishnet = os.path.join(scratchws, "fishnet.shp")

  desc = arcpy.Describe(naip)
  origin_coord = str(desc.extent.XMin)+ " " +str(desc.extent.YMin)
  y_axis_coord = str(desc.extent.XMin)+ " " +str(desc.extent.YMax)

  cell_width = 1000
  cell_height = 1000

  arcpy.CreateFishnet_management(fishnet, origin_coord, y_axis_coord, cell_width, cell_height, "", "", "", "NO_LABELS", naip, "POLYGON")
  arcpy.Clip_analysis(fishnet, bnd_zones, analysis_area)
  #arcpy.DefineProjection_management(analysis_area, projection)

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

    las_dem = os.path.join(scratchws, "las_dem.tif")
    las_dsm = os.path.join(scratchws, "las_dsm.tif")
    temp = os.path.join(scratchws, "temp.tif")

    arcpy.LasDatasetToRaster_conversion(lasd, las_dem, "ELEVATION", "BINNING MINIMUM LINEAR", "FLOAT", "CELLSIZE", cell_size, "")
    this = Float(las_dem)#*0.3048
    this.save(temp)
    arcpy.ProjectRaster_management(temp, raw_dem, projection, "BILINEAR")
    #
    # Create DSM
    arcpy.LasDatasetToRaster_conversion(lasd, las_dsm, "ELEVATION", "BINNING MAXIMUM SIMPLE", "FLOAT", "CELLSIZE", cell_size, "")
    this = Float(las_dsm)#*0.3048
    this.save(temp)
    arcpy.ProjectRaster_management(temp, raw_dsm, projection, "BILINEAR")


    # Create Heights
    hts_interm1 = os.path.join(scratchws,"hts_interm1.tif")
    hts_interm2 = os.path.join(scratchws,"hts_interm2.tif")
    heights_sp = os.path.join(scratchws, "hts_sp.tif")
    raw_heights = os.path.join(inputs,"heights.tif")

    ht = Float(raw_dsm)-Float(raw_dem)
    ht = Con(IsNull(Float(ht)), 0, Float(ht))
    ht = Con(Float(ht) < 0, 0, Float(ht))
    ht.save(raw_heights)

  if process_lidar == "Yes":
    lasToHeights()

  heights = os.path.join(outputs, "heights_"+coarsening_size+"m.tif")  # Resampled heights in native units
  #this = Aggregate(raw_heights, coarsening_size, "MEDIAN")
  #arcpy.ProjectRaster_management(heights_sp, heights, projection, "BILINEAR")
  arcpy.env.snapRaster = naip

  this = ExtractByMask(raw_heights, bnd_zones_rast) # Extract scaled
  this.save(heights)

  this = ExtractByMask(raw_dem, bnd_zones_rast) # Extract scaled
  this.save(dem)


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

    # Clip pipeline to study area, buffer pipeline
    arcpy.Clip_analysis(pipeline, bnd_zones, pipe_seg)
    arcpy.PolygonToRaster_conversion(bnd_zones, "FID", bnd_rast, "CELL_CENTER", "", int(coarsening_size))
    arcpy.Buffer_analysis(pipe_seg, pipe_buffer, buff_distance, "", "", "ALL")
    arcpy.PolygonToRaster_conversion(pipe_buffer, "FID", pipe_rast, "CELL_CENTER")
    arcpy.ProjectRaster_management(pipe_rast, pipe_proj, bnd_zones, "BILINEAR", str(cell_size) +" "+str(cell_size))
    this = ExtractByMask(pipe_proj, bnd_zones)
    this.save(pipe_buffer_clip)
    arcpy.RasterToPolygon_conversion(pipe_buffer_clip, bnd_zones, "NO_SIMPLIFY")

    # determine what tiles the pipeline falls within
    text = "Finding fishnet tiles containing pipleline."
    generateMessage(text)
    pipe_in_tile = []
    searchcursor = arcpy.SearchCursor(analysis_area)
    tiles = searchcursor.next()
    while tiles:
      tile_num = tiles.getValue("FID")
      tile = os.path.join(scratchgdb, "tile_"+str(tile_num))
      pipe_tile = os.path.join(scratchgdb, "pipe_tile_"+str(tile_num))
      where_clause = "FID = " + str(tile_num)

      arcpy.Select_analysis(analysis_area, tile, where_clause)
      arcpy.Clip_analysis(bnd_zones, tile, pipe_tile)
      if arcpy.management.GetCount(pipe_tile)[0] != "0":
        pipe_in_tile.extend([pipe_tile])
      else:
        arcpy.DeleteFeatures_management(pipe_tile)
      tiles = searchcursor.next()
    arcpy.Merge_management(pipe_in_tile, used_tiles)
    global tiles_used
    tiles_used = len(pipe_in_tile)

    global analysis_area
    analysis_area = used_tiles


    # Extract NAIP and heights to pipeline buffer
    this = ExtractByMask(naip, analysis_area)
    this.save(naip_pipe)

    for band in bands:
      band_ras = os.path.join(scratchgdb, band)
      naip_band = os.path.join(naip_pipe, band)
      outRas = Con(IsNull(naip_band),0, naip_band)
      outRas.save(band_ras)
      pipe_bands.append(band_ras)
    arcpy.CompositeBands_management(pipe_bands, naip)
    arcpy.DefineProjection_management(naip, projection)

    this = ExtractByMask(heights, analysis_area)
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
def gen_lc():

  create_obia = "Yes"
  classify_landscape = "Yes"
  run_svm = "Yes"
  merge_landcover_tiles = "Yes"
  generate_ascii = "Yes"

  # Iterate through all zones (if possible)
  tot_num_tiles = arcpy.management.GetCount(analysis_area)[0]

  landscape_analysis = []
  searchcursor = arcpy.SearchCursor(analysis_area)
  zones = searchcursor.next()
  global ts
  ts = time.time()

  arcpy.AddField_management(bnd_zones, "Shape_area", "DOUBLE")
  arcpy.CalculateField_management(bnd_zones, "Shape_area", "!SHAPE.AREA@SQUAREKILOMETERS!", "PYTHON_9.3")
  cursor = arcpy.SearchCursor(bnd_zones)
  global total_area
  for row in cursor:
    total_area = row.getValue("Shape_area")

  while zones:
    zone_num = zones.getValue("FID")
    if zone_num <= -1:  #No 31,32
      #If tile is created already, skip to next in queue
      zones = searchcursor.next()

    else:
      sms_fc = os.path.join(scratchgdb, "sms_fc_"+str(zone_num))
      landscape_fc = os.path.join(scratchws, "landscape_fc_"+str(zone_num)+".shp")

      def obia():
        text = "Running an OBIA for zone "+str(zone_num+1)+" of "+str(tot_num_tiles)+"."
        newProcess(text)

        #Variables
        sms_fc = os.path.join(scratchgdb, "sms_fc_"+str(zone_num))
        bnd = os.path.join(scratchws, "zone_"+str(zone_num)+".shp")
        bnd_rast = os.path.join(scratchws, "bnd.tif")
        naip_zone = os.path.join(scratchws, "naip_zone_"+str(zone_num)+".tif")
        naip_zone_b1 = os.path.join(naip_zone, "Band_1")
        naip_zone_b2 = os.path.join(naip_zone, "Band_2")
        naip_zone_b3 = os.path.join(naip_zone, "Band_3")
        naip_zone_b4 = os.path.join(naip_zone, "Band_4")
        heights_zone = os.path.join(outputs, "height_zone_"+str(zone_num)+".tif")
        naip_sms = os.path.join(scratchgdb, "naip_sms_"+str(zone_num))



        # Create zone boundary and extract NAIP and heights
        where_clause = "FID = " + str(zone_num)
        arcpy.Select_analysis(analysis_area, bnd, where_clause)

        arcpy.AddField_management(bnd, "Shape_area", "DOUBLE")
        arcpy.CalculateField_management(bnd, "Shape_area", "!SHAPE.AREA@SQUAREKILOMETERS!", "PYTHON_9.3")
        cursor = arcpy.SearchCursor(bnd)
        global zone_area
        for row in cursor:
          zone_area = row.getValue("Shape_area")


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

        surfaces = ["ground", "nonground"]

        #Variables

        #Variables - temporary
        ground_mask_seg = os.path.join(scratchgdb, "ground_mask_seg")
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

        # Create masks for ground and nonground features according to ground_ht_threshold
        if unit == "Meters":
          ground_ht_threshold = 0.6096

        # Find cell size of imagery
        cell_size = str(arcpy.GetRasterProperties_management(naip, "CELLSIZEX", ""))

        this = SetNull(Int(heights_zone),Int(heights_zone),"VALUE > " + str(ground_ht_threshold))
        this.save(ground_mask_seg)

        if arcpy.sa.Raster(ground_mask_seg).maximum > 1:
          arcpy.RasterToPolygon_conversion(mask, ground_mask_raw, "NO_SIMPLIFY", "VALUE")
          arcpy.Dissolve_management(ground_mask_raw, ground_dissolve_output)

          # A process of clipping polygons and erasing rasters
          where_clause = "Shape_Area > " + str(min_cell_area)
          arcpy.Erase_analysis(bnd, ground_dissolve_output, nonground_mask_raw)
          arcpy.PolygonToRaster_conversion(nonground_mask_raw, "OBJECTID", nonground_mask_raster, "CELL_CENTER", "", cell_size)
          arcpy.RasterToPolygon_conversion(nonground_mask_raster, nonground_mask_raw, "NO_SIMPLIFY", "VALUE")
          arcpy.Select_analysis(nonground_mask_raw, nonground_mask_poly, where_clause)
          arcpy.Erase_analysis(bnd, nonground_mask_poly, ground_mask_poly)
          arcpy.PolygonToRaster_conversion(ground_mask_poly, "OBJECTID", ground_mask_raster, "CELL_CENTER", "", cell_size)

          arcpy.RasterToPolygon_conversion(ground_mask_raster, ground_mask_raw, "NO_SIMPLIFY", "VALUE")
          arcpy.Select_analysis(ground_mask_raw, ground_mask_poly, where_clause)
          arcpy.Erase_analysis(bnd, ground_mask_poly, nonground_mask_poly)

        else:
          nonground_mask_poly = bnd
          surfaces = ["nonground"]
        #-----------------------------------------------
        #-----------------------------------------------

        #-----------------------------------------------
        #-----------------------------------------------
        # Segment each surface separately using SMS
        spectral_detail = 20
        spatial_detail = 20
        min_seg_size = 1


        naip_lst = []

        for surface in surfaces:

          #-----------------------------------------------
          #-----------------------------------------------
          text = "Extracting NAIP imagery by "+ surface + " mask."
          generateMessage(text)

          #Variables - temporary
          sms_raster = os.path.join(outputs, surface+"_sms_raster.tif")
          naip_fc =  os.path.join(scratchgdb, surface + "_naip_fc")
          mask_poly = os.path.join(scratchgdb, surface+ "_mask_poly")
          mask = mask_poly
          sms = os.path.join(scratchgdb, surface+"_sms")
          naip_mask = os.path.join(scratchgdb,surface + "_naip")
          mask_raw = os.path.join(scratchgdb, surface + "_mask_raw")
          dissolve_output = os.path.join(scratchgdb, surface + "_mask_dis")

          if len(surfaces) == 1:
            mask = bnd
            mask_poly = bnd

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

        text = "Calculating zonal majority of each spectral enhancement for each object."
        generateMessage(text)
        for ie in created_enhancements_1m:
          
          outTable = os.path.join(scratchgdb, "zonal_"+os.path.basename(ie))

          field = image_enhancements.pop(0)
          z_stat = ZonalStatisticsAsTable(sms_fc, "JOIN", ie, outTable, "NODATA", "MEDIAN")
          arcpy.AddField_management(outTable, field, "INTEGER")
          arcpy.CalculateField_management(outTable, field, "[MEDIAN]")
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


      # Assigns classess
      def createClassMembership(fc, stage, field, evaluator, fxn):
        def classify():
          if stage == "S1":
            if evaluator:
              imp = evaluator[0]
              veg = evaluator[1]
              return ("def landcover(x):\\n"+
                     "  membership = \"\"\\n"+
                     "  if "+imp+":\\n"+
                     "    membership += \"I\"\\n"+
                     "  if "+veg+":\\n"+
                     "    membership += \"V\"\\n"+
                     "  return membership\\n"
                     )
            else:
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
              
          elif stage == "S2":
            if evaluator:
              healthy = evaluator[0]
              senescent = evaluator[1]
              return ("def landcover(x):\\n"+
                       "  membership = \"\"\\n"+
                       "  if "+healthy+":\\n"+
                       "    membership += \"H\"\\n"+
                       "  if "+senescent+":\\n"+
                       "    membership += \"S\"\\n"+
                       "  return membership\\n"
                       )
            else:
              return("def landcover(a,b):\\n"+
                     "  membership = a+b\\n"+
                     "  H,S = 0,0\\n"+
                     "  for m in membership:\\n"+
                     "    if m == \"H\":\\n"+
                     "      H += 1\\n"+
                     "    if m == \"S\":\\n"+
                     "      S += 1\\n"+
                     "  if H < S:\\n"+
                     "    return \"senescent_tree\"\\n"+
                     "  return \"healthy_tree\"\\n"
                       )

        arcpy.AddField_management(fc, "_"+field, "TEXT")
        arcpy.CalculateField_management(fc, "_"+field, fxn, "PYTHON_9.3", classify())
      #-----------------------------------------------
      #-----------------------------------------------

      #-----------------------------------------------
      #-----------------------------------------------
      # Classifier methods

      location = Fire_Env(bioregion)

      stages = ["S1","S2"]

      # Indices used for each stage of classification
      indices = location.spectral_indices

      def classify_objects():
        for stage in stages:
          text = "Executing Stage "+str(stage)+" classification."
          generateMessage(text)

          # Stage 1 classification workflow
          if stage == "S1":
            ndvi = createClassMembership(sms_fc, stage, "ndvi", location.S1_ndvi, "landcover(!ndvi!)")
            gndvi = createClassMembership(sms_fc, stage, "gndvi", location.S1_gndvi, "landcover(!gndvi!)")
            ndwi = createClassMembership(sms_fc, stage, "ndwi", location.S1_ndwi, "landcover(!ndwi!)")
            osavi = createClassMembership(sms_fc, stage, "osavi", location.S1_osavi, "landcover(!osavi!)")
            s1 = createClassMembership(sms_fc, stage, "S1", "", "landcover(!_ndvi!,!_gndvi!,!_ndwi!,!_osavi!)")
            #-----------------------------------------------
            #-----------------------------------------------
            
            text = "Classifying confused land cover with SVM."
            generateMessage(text)

            # Variables
            confused = os.path.join(scratchws, "confused.shp")
            veg_join = os.path.join(scratchgdb, "veg_join")
            training_samples = os.path.join(scratchws, "training_fc.shp")
            merged = os.path.join(scratchgdb, "merged_imp_veg")
            composite = os.path.join(scratchws, "composite.tif")
            confused_composite = os.path.join(scratchws, "confused_composite.tif")
            confused_composite_rast = os.path.join(scratchws, "confused_composit_rast.tif")
            veg_imp = os.path.join(scratchws, "veg_imp.shp")

            # Create dataset with only confused objects
            text = "Creating confused objects."
            generateMessage(text)

            arcpy.Select_analysis(sms_fc, confused, "_S1 = 'confusion'")
            if arcpy.management.GetCount(confused)[0] != "0":

              # Indices used as bands in raster for SVM
              band_lst = ["ndvi", "ndwi", "height"]

              # Creating Layer composite
              text = "Creating LiDAR-Multispectral stack."
              generateMessage(text)

              confused_ie_lst = []
              bands_5m = createImageEnhancements(band_lst, naip, heights, "5m", scratchgdb)
              arcpy.CompositeBands_management(bands_5m, composite)
              arcpy.DefineProjection_management(composite, projection)
              #-----------------------------------------------
              #-----------------------------------------------

              #-----------------------------------------------
              #-----------------------------------------------
              text = "Preparing training samples for SVM."
              generateMessage(text)

              # Variables
              svm_training = os.path.join(scratchws, "svm_training.shp")
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

              arcpy.Select_analysis(sms_fc, svm_training, "_S1 <> 'confusion'")
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
              arcpy.CalculateField_management(svm_training, "Classname", "[_S1]")
              arcpy.CalculateField_management(svm_training, "Classvalue", "classvalue(!_S1!)", "PYTHON_9.3", classvalue())
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
              out_definition = os.path.join(scratchws, "svm_classifier.ecd")
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
              svm = os.path.join(scratchws, "svm.tif")

              # Creating classifier rule from training samples
              arcpy.gp.TrainSupportVectorMachineClassifier(composite, svm_training, out_definition, "", maxNumSamples, attributes)

              # Classifying raster with pixel-based method, not segmented raster

              for ie in bands_5m:
                band = os.path.basename(ie)
                confused_ie = os.path.join(scratchgdb, "confused_"+band)
                this = ExtractByMask(ie, confused)
                this = Con(IsNull(Float(this)), -10000, Float(this))
                this.save(confused_ie)
                confused_ie_lst.extend([confused_ie])
              arcpy.CompositeBands_management(confused_ie_lst, composite)
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
              arcpy.CalculateField_management(confused, "_S1", "landcover(!MAJORITY!)", "PYTHON_9.3", classify_confusion())
              #-----------------------------------------------
              #-----------------------------------------------

              #-----------------------------------------------
              #-----------------------------------------------
              text = "Creating contiguously classified primitive land cover."
              generateMessage(text)

              # Merging all layers back together as classified layer
              arcpy.Select_analysis(sms_fc, veg_imp, "_S1 <> 'confusion'")
              arcpy.Merge_management([confused, veg_imp], S1_classified)
            else:
              arcpy.Select_analysis(sms_fc, S1_classified, "_S1 <> 'confusion'")

          
          #-----------------------------------------------
          #-----------------------------------------------

          # Stage 2 classification workflow
          elif stage == "S2":

            features = []
            covers = location.fuels
            #arcpy.AddMessage(covers)
            for cover in covers:
              class landcover:
                def __init__(self, cover):
                  self.stage = cover[0]
                  self.fuel_model = cover[1]
                  self.min_height = cover[2][0]
                  self.max_height = cover[2][1]
                  self.spectral_detail = cover[3][0]
                  self.spatial_detail = cover[3][1]
                  self.min_seg_size = cover[3][2]

              lc = landcover(cover)

              if lc.stage == "nonburnable":
                landcover = "impervious"
              else:
                landcover = "vegetation"

              s1_heights = os.path.join(scratchgdb, landcover+"_heights")
              heights_zone = os.path.join(outputs, "height_zone_"+str(zone_num)+".tif")
              primitive_mask = os.path.join(scratchws, landcover+"_"+str(zone_num)+".shp")
              cm_heights = os.path.join(scratchgdb, "cm_heights")

              arcpy.Select_analysis(S1_classified, primitive_mask, "_S1 = '"+landcover+"'")
              this = Int(Float(heights)*100)
              this.save(cm_heights)
              if arcpy.management.GetCount(primitive_mask)[0] != "0":
                this = ExtractByMask(cm_heights, primitive_mask)
                this.save(s1_heights)

                stage_output = os.path.join(outputs, landcover+"_"+str(zone_num)+".shp")
                stage_rast = os.path.join(scratchgdb, lc.stage)
                stage_mask = os.path.join(scratchgdb, lc.stage+"_mask")
                naip_fuel = os.path.join(scratchgdb, "naip_"+lc.stage)
                fuel_sms_rast = os.path.join(scratchgdb, lc.stage+"_sms_rast")
                fuel_sms = os.path.join(scratchgdb, lc.stage+"_sms")
                fuel_fc = os.path.join(scratchgdb, lc.stage+"_fc")

                text = "Creating "+ lc.stage +" objects."
                generateMessage(text)

                if lc.stage == "nonburnable":
                  arcpy.Select_analysis(S1_classified, fuel_fc, "_S1 = 'impervious'")
                  if arcpy.management.GetCount(fuel_fc)[0] != "0":
                    arcpy.AddField_management(fuel_fc, "_S2", "TEXT")
                    arcpy.CalculateField_management(fuel_fc, "_S2", "label(!_S2!)", "PYTHON_9.3", "def label(x):\\n  return \""+lc.stage+"\"\\n")
                    arcpy.AddField_management(fuel_fc, "fuel", "INTEGER")
                    arcpy.CalculateField_management(fuel_fc, "fuel", lc.fuel_model)
                    features.extend([fuel_fc])

                else:

                  this = Con((Int(s1_heights)>lc.min_height) & (Int(s1_heights)<=lc.max_height), 1)
                  this.save(stage_rast)

                  #Clip NAIP by layer elevation
                  if arcpy.sa.Raster(stage_rast).maximum == 1:
                    arcpy.RasterToPolygon_conversion(stage_rast, stage_mask, "NO_SIMPLIFY", "VALUE")
                    this = ExtractByMask(naip, stage_mask)
                    this.save(naip_fuel)
                    naip_raster_slide = os.path.join(scratchws, "naip_slide.tif")
                    bands_fuel = []
                    for i in range(4):
                      band = os.path.join(naip_fuel, "Band_")
                      band_raster_slide = os.path.join(scratchgdb, "bandfuel_"+str(i+1))
                      this = Con(IsNull(Float(naip_fuel)), -10000, Float(naip_fuel))
                      this.save(band_raster_slide)
                      bands_fuel.extend([band_raster_slide])
                    arcpy.CompositeBands_management(bands_fuel, naip_raster_slide)
                    
                    # Creating objects and clipping to surface type
                    if arcpy.sa.Raster(naip_raster_slide).maximum > 0:
                      if lc.stage == "tree":

                        tree_fishnet = os.path.join(scratchgdb, "tree_fishnet_"+str(zone_num))

                        desc = arcpy.Describe(stage_rast)
                        origin_coord = str(desc.extent.XMin)+ " " +str(desc.extent.YMin)
                        y_axis_coord = str(desc.extent.XMin)+ " " +str(desc.extent.YMax)

                        arcpy.CreateFishnet_management(tree_fishnet, origin_coord, y_axis_coord, coarsening_size, coarsening_size, "", "", "", "NO_LABELS", stage_rast, "POLYGON")
                        arcpy.DefineProjection_management(tree_fishnet, projection)
                        arcpy.Clip_analysis(tree_fishnet, stage_mask, fuel_fc)
                        arcpy.DeleteFeatures_management(tree_fishnet)

                        arcpy.AddField_management(fuel_fc, "JOIN", "INTEGER")
                        arcpy.CalculateField_management(fuel_fc, "JOIN", "[OBJECTID]")

                        # Join image enhancements to tree tiles
                        for field in indices:
                          outTable = os.path.join(scratchgdb, "zonal_tree_"+field+"_"+str(zone_num))
                          ie = field+"_"+str(zone_num)
                          z_table = ZonalStatisticsAsTable(fuel_fc, "JOIN", ie, outTable, "NODATA", "MEDIAN")
                          arcpy.AddField_management(outTable, field, "FLOAT")
                          arcpy.CalculateField_management(outTable, field, "[MEDIAN]")
                          one_to_one_join(fuel_fc, outTable, field, "FLOAT")

                        ndvi = createClassMembership(fuel_fc, stage, "ndvi", location.tree_ndvi, "landcover(!ndvi!)")                  
                        ndwi = createClassMembership(fuel_fc, stage, "ndwi", location.tree_ndwi, "landcover(!ndwi!)")
                        s2 = createClassMembership(fuel_fc, stage, "S2", "", "landcover(!_ndvi!,!_ndwi!)")

                        features.extend([fuel_fc])

                      else:
                        seg_naip = SegmentMeanShift(naip_raster_slide, lc.spectral_detail, lc.spatial_detail, lc.min_seg_size)
                        seg_naip.save(fuel_sms_rast)
                        this = ExtractByMask(fuel_sms_rast, naip_fuel)
                        this.save(fuel_sms_rast)

                        if arcpy.sa.Raster(fuel_sms_rast).maximum > 0:
                          arcpy.RasterToPolygon_conversion(fuel_sms_rast, fuel_fc, "NO_SIMPLIFY", "VALUE")
                          features.extend([fuel_fc])

                    arcpy.AddField_management(fuel_fc, "fuel", "INTEGER")
                    if lc.stage != "tree":
                      arcpy.AddField_management(fuel_fc, "_S2", "TEXT")
                      arcpy.CalculateField_management(fuel_fc, "_S2", lc.stage)
                      arcpy.CalculateField_management(fuel_fc, "fuel", int(lc.fuel_model))
                    else:
                      arcpy.CalculateField_management(fuel_fc, "fuel", "label(!_S2!)", "PYTHON_9.3",  "def label(x):\\n  if x == \"senescent_tree\":\\n    return int(13)\\n  elif x == \"healthy_tree\":\\n    return int(\""+lc.fuel_model+"\")")
                  
                    #Delete extra fields
                    # fields = [f.name for f in arcpy.ListFields(fuel_fc)]
                    # delete_fields = []
                    # for field in fields:
                    #   if field not in ["OBJECTID", "Shape", "Shape_Area", "Shape_Length", "ID", "_S2", "fuel"]:
                    #     delete_fields.append(field)
                    # arcpy.DeleteField_management(fuel_fc, delete_fields)

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

            arcpy.CalculateField_management(outTable, "height", "[MAX]")
            one_to_one_join(landscape_fc, outTable, "height", "FLOAT")

            arcpy.AddField_management(landscape_fc, "stand", "INTEGER")
            arcpy.CalculateField_management(landscape_fc, "stand", "label(!fuel!,!height!)", "PYTHON_9.3", "def label(x, y):\\n  if x == 10 or x == 2:\\n    return int(y)\\n  return 0")


            estimate_time(zone_num)

        #empty_scratchgdb()
      if classify_landscape == "Yes":
        classify_objects()

      # iterate through next zone if possible
      landscape_analysis.append(landscape_fc)
      zones = searchcursor.next()

  def merge_tiles():
    if len(landscape_analysis) > 0:
      text = "Creating contiguous land cover for entire analysis area (joining tiles)."
      newProcess(text)

      arcpy.Merge_management(landscape_analysis, classified_landscape)
      tree_cover = os.path.join(scratchgdb, "tree_cover")
      
      where_clause = "_S2 = 'healthy_tree' OR _S2 = 'senescent_tree'"
      arcpy.Select_analysis(classified_landscape, tree_cover, where_clause)
      arcpy.Dissolve_management(tree_cover, canopycover)
      text = "Fuel complex created."
      generateMessage(text)


      #-----------------------------------------------
      #-----------------------------------------------
  if merge_landcover_tiles == "Yes":
    merge_tiles()

  def convertToAscii():

    arcpy.env.snapRaster = naip

    fuel_lst = ["fuel", "canopy", "stand"]
    elevation_lst = ["slope", "elevation", "aspect"]
    landscape_elements = fuel_lst + elevation_lst
    ascii_layers = []
    
    for layer in landscape_elements:

      # Variables
      ascii_output = os.path.join(outputs, layer + ".asc")
      where_clause = layer +" <> 9999"
      temp = os.path.join(scratchws, "t_"+layer+".shp")
      temp_raster = os.path.join(scratchws, "t_"+layer+"_r.tif")
      final = os.path.join(scratchws, layer+".tif")

      text = "Generating "+layer+" ascii layer."
      generateMessage(text)  # Variables

      # Selecting layer and converting to raster
      if layer in fuel_lst:
        if layer == "canopy":
          text = "Calculating Canopy Cover (%)."
          generateMessage(text)
          # Create FP.lasd
          FP_lasd = os.path.join(scratchws, "FP.lasd")
          arcpy.MakeLasDatasetLayer_management(lasd,FP_lasd,[0,1,3,4,5,6,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31],"","","","","")

          #
          # Create LP.lasd
          LP_lasd = os.path.join(scratchws, "LP.lasd")
          arcpy.MakeLasDatasetLayer_management(lasd,LP_lasd,[1,2,8,10,21,22],"","","","","")
          #
          # Create FP_count.tif
          FP_count_tif = os.path.join(scratchws,"FP_count.tif")
          arcpy.LasPointStatsAsRaster_management(FP_lasd, FP_count_tif,"POINT_COUNT","CELLSIZE", coarsening_size)
          FP_count = Con(IsNull(FP_count_tif),0,FP_count_tif)
          #
          # Create All_pt_count.tif
          All_pt_count_tif = os.path.join(scratchws,"All_pt_count.tif")
          arcpy.LasPointStatsAsRaster_management(lasd, All_pt_count_tif,"POINT_COUNT","CELLSIZE",coarsening_size)
          All_pt_count = All_pt_count_tif
          #
          # Calculate Canopy Cover (FP/LP Ratio)
          temp = os.path.join(scratchws, "temp.tif")
          canopy_cover = Divide(Float(FP_count), Float(All_pt_count))
          canopy_cover = Int(Float(canopy_cover)*100)
          canopy_cover = Con(canopy_cover==100,99,canopy_cover)
          this = ExtractByMask(canopy_cover, canopycover)
          this = Con(IsNull(this), 0, this)
          this.save(temp)
          arcpy.ProjectRaster_management(temp, canopy_cover_tif, projection, "BILINEAR", "5")
          arcpy.CopyRaster_management(canopy_cover_tif, final, "", "", "0", "NONE", "NONE", "32_BIT_SIGNED","NONE", "NONE", "TIFF", "NONE")
        else:
          arcpy.Select_analysis(classified_landscape, temp, where_clause)
          arcpy.PolygonToRaster_conversion(temp, layer, final, "CELL_CENTER", "", int(coarsening_size))
      elif layer in elevation_lst:

        # Calculating elevation derived layers
        if layer == "slope":
          arcpy.Slope_3d(dem, temp_raster, "DEGREE")
        elif layer == "aspect":
          arcpy.Aspect_3d(dem, temp_raster)
        elif layer == "elevation":
          temp_raster = dem

        # Preparing raster for LCP specifications
        arcpy.CopyRaster_management(temp_raster, final, "", "", "0", "NONE", "NONE", "32_BIT_SIGNED","NONE", "NONE", "TIFF", "NONE")

      arcpy.DefineProjection_management(final, projection)

      # Extracting layer by analysis area
      #ready = ExtractByMask(final, classified_landscape)
      ready = ExtractByMask(final, naip)
      ready.save(temp_raster)

      # Converting to ascii format and adding to list for LCP tool
      arcpy.RasterToASCII_conversion(ready, ascii_output)
      ascii_layers.append(ascii_output)

  # Coding note: Check to see that lists are concatenated
  if generate_ascii == "Yes":
    convertToAscii()

if generate_land_cover == "Yes":
  gen_lc()
#-----------------------------------------------
#-----------------------------------------------

#-----------------------------------------------
#-----------------------------------------------

def measure_fire_behavior():

  create_LCP = "No"
  run_FlamMap = "No"
  join_burns = "Yes"

  # behvaior metrics ={flame length, rate of spread, fire intenstiy}

  processes = [
  [create_LCP,"Create LCP"],
  [run_FlamMap,"Run FlamMap"]]

  for process in processes:
    if process:
      arcpy.AddMessage(process[1])

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
    arcpy.env.workspace = scratchws


    def convertToAscii(x, landscape_elements):

      for layer in landscape_elements:

        # Variables
        ascii_output = os.path.join(outputs, layer + ".asc")
        where_clause = layer +" <> 9999"
        temp = os.path.join(scratchws, "t_"+layer+".shp")
        temp_raster = os.path.join(scratchws, "t_"+layer+"_r.tif")
        final = os.path.join(scratchws, layer+".tif")

        # Selecting layer and converting to raster
        if layer in fuel_lst:
          if layer == "canopy":
            text = "Calculating Canopy Cover (%)."
            generateMessage(text)
            # Create FP.lasd
            FP_lasd = os.path.join(scratchws, "FP.lasd")
            arcpy.MakeLasDatasetLayer_management(lasd,FP_lasd,[0,1,3,4,5,6,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31],"","","","","")

            #
            # Create LP.lasd
            LP_lasd = os.path.join(scratchws, "LP.lasd")
            arcpy.MakeLasDatasetLayer_management(lasd,LP_lasd,[1,2,8,10,21,22],"","","","","")
            #
            # Create FP_count.tif
            FP_count_tif = os.path.join(scratchws,"FP_count.tif")
            arcpy.LasPointStatsAsRaster_management(FP_lasd,FP_count_tif,"POINT_COUNT","CELLSIZE",16.4042)
            FP_count = Con(IsNull(FP_count_tif),0,FP_count_tif)
            #
            # Create All_pt_count.tif
            All_pt_count_tif = os.path.join(scratchws,"All_pt_count.tif")
            arcpy.LasPointStatsAsRaster_management(lasd,All_pt_count_tif,"POINT_COUNT","CELLSIZE",16.4042)
            All_pt_count = All_pt_count_tif
            #
            # Calculate Canopy Cover (FP/LP Ratio)
            temp = os.path.join(scratchws, "temp.tif")
            canopy_cover = Divide(Float(FP_count), Float(All_pt_count))
            canopy_cover = Int(Float(canopy_cover)*100)
            canopy_cover = Con(canopy_cover==100,99,canopy_cover)
            this = ExtractByMask(canopy_cover, canopycover)
            this = Con(IsNull(this), 0, this)
            this.save(temp)
            arcpy.ProjectRaster_management(temp, canopy_cover_tif, projection, "BILINEAR", "5")
            arcpy.CopyRaster_management(canopy_cover_tif, final, "", "", "0", "NONE", "NONE", "32_BIT_SIGNED","NONE", "NONE", "TIFF", "NONE")
          else:
            arcpy.Select_analysis(classified_landscape, temp, where_clause)
            arcpy.PolygonToRaster_conversion(temp, layer, final, "CELL_CENTER", "",dem)
        elif layer in elevation_lst:

          # Calculating elevation derived layers
          if layer == "slope":
            arcpy.Slope_3d(dem, temp_raster, "DEGREE")
          elif layer == "aspect":
            arcpy.Aspect_3d(dem, temp_raster)
          elif layer == "elevation":
            temp_raster = dem

          # Preparing raster for LCP specifications
          arcpy.CopyRaster_management(temp_raster, final, "", "", "0", "NONE", "NONE", "32_BIT_SIGNED","NONE", "NONE", "TIFF", "NONE")

        arcpy.DefineProjection_management(final, projection)

        # Extracting layer by analysis area
        #ready = ExtractByMask(final, classified_landscape)
        ready = ExtractByMask(final, dem)
        ready.save(temp_raster)

        # Converting to ascii format and adding to list for LCP tool
        arcpy.RasterToASCII_conversion(ready, ascii_output)
        ascii_layers.append(ascii_output)

        text = "The "+layer+" ascii file was created."
        generateMessage(text)


    # Coding note: Check to see that lists are concatenated
    convertToAscii(classified_landscape, fuel_lst + elevation_lst)

    #-----------------------------------------------
    #-----------------------------------------------

  #   #-----------------------------------------------
  #   #-----------------------------------------------
  #   text = "Creating LCP file."
  #   generateMessage(text)

  #   import ctypes
  #   ##
  #   ### Variables
  #   landscape_file = os.path.join(outputs, "landscape.lcp")
  #   genlcp = os.path.join(dll_path, "GenLCPv2.dll")
  #   Res = landscape_file
  #   Elev = os.path.join(outputs,"elevation.asc")
  #   Slope = os.path.join(outputs,"slope.asc")
  #   Aspect = os.path.join(outputs,"aspect.asc")
  #   Fuel = os.path.join(outputs,"fuel.asc")
  #   Canopy = os.path.join(outputs,"canopy.asc")

  #   # Create LCP
  #   dll = ctypes.cdll.LoadLibrary(genlcp)
  #   fm = getattr(dll, "?Gen@@YAHPBD000000@Z")
  #   fm.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
  #   fm.restype = ctypes.c_int

  #   e = fm(Res, Elev, Slope, Aspect, Fuel, Canopy, "")
  #   if e > 0:
  #     arcpy.AddError("Error {0}".format(e))
  # if create_LCP == "Yes":
  #   LCP()
  # #-----------------------------------------------
  # #-----------------------------------------------

  # #-----------------------------------------------
  # #-----------------------------------------------
  # def burn():
  #   text = "Running FlamMap."
  #   newProcess(text)

  #   # Burn in FlamMap
  #   #
  #   flamMap = os.path.join(dll_path, "FlamMapF.dll")
  #   dll = ctypes.cdll.LoadLibrary(flamMap)
  #   fm = getattr(dll, "?Run@@YAHPBD000NN000HHN@Z")
  #   fm.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_double, ctypes.c_double, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_int, ctypes.c_double]
  #   fm.restype = ctypes.c_int

  #   Landscape = landscape_file
  #   FuelMoist = fuel_moisture
  #   OutputFile = os.path.join(outputs, "Burn")
  #   FuelModel = "-1"
  #   Windspeed = 30.0  # mph
  #   WindDir = 0.0   # Direction angle in degrees
  #   Weather = "-1"
  #   WindFileName = "-1"
  #   DateFileName = "-1"
  #   FoliarMoist = 100 # 50%
  #   CalcMeth = 0    # 0 = Finney 1998, 1 = Scott & Reinhardt 2001
  #   Res = -1.0

  #   e = fm(Landscape, FuelMoist, OutputFile, FuelModel, Windspeed, WindDir, Weather, WindFileName, DateFileName, FoliarMoist, CalcMeth, Res)
  #   if e > 0:
  #     arcpy.AddError("Problem with parameter {0}".format(e))


  #   for root, dirs, fm_outputs in os.walk(outputs): #Check to confirm outputs are saved here
  #      for burn in fm_outputs:
  #         if burn[-3:].lower() in burn_metrics:
  #             metric = burn[-3:].lower()
  #             burn_ascii = os.path.join(outputs, metric+".asc")
  #             os.rename(os.path.join(outputs, burn), burn_ascii)


  #   text = "Burn complete."
  #   generateMessage(text)
  # if run_FlamMap == "Yes":
  #   burn()

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
      elif metric == "fi":
        unit_scalar = 1#3.28084

      this = Raster(raw_raster)*unit_scalar
      this.save(scaled_raster)
      arcpy.Resample_management(scaled_raster, burn, naip_cell_size, "NEAREST")

      #-----------------------------------------------
      #-----------------------------------------------

      #-----------------------------------------------
      #-----------------------------------------------
      # Calculate zonal max and join to each objects
      arcpy.AddField_management(classified_landscape, "JOIN", "INTEGER")
      arcpy.CalculateField_management(classified_landscape, "JOIN", "[FID]+1")
      z_table = ZonalStatisticsAsTable(classified_landscape, "JOIN", burn, outTable, "NODATA", "MAXIMUM")
      arcpy.AddField_management(outTable, metric, "FLOAT")
      arcpy.CalculateField_management(outTable, metric, "[MAX]")
      one_to_one_join(classified_landscape, outTable, metric, "FLOAT")
      #-----------------------------------------------
      #-----------------------------------------------

    #-----------------------------------------------
    #-----------------------------------------------
    text = "All burn severity joins are complete."
    generateMessage(text)
  if join_burns == "Yes":
    burn_obia()

  # Clip pipeline by burn similarities
  #if pipe_analysis == "Yes":
    #arcpy.Select_analysis(classified_landscape, )

if fire_behavior == "Yes":
  measure_fire_behavior()
  
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
  symbol_layers = [classified_landscape, pipeline]
  classified_layers = ["landcover"]#, "fli", "ros", "fml"]
  layers = [dem, scaled_dem, heights, scaled_heights, raw_naip, naip]

  fields = [f.name for f in arcpy.ListFields(classified_landscape)]
  for field in fields:
    if field in burn_metrics:
      classified_layers.extend([field])


  # Symbology
  #df_lst = []
  for symbol in classified_layers:
    layer = arcpy.mapping.Layer(classified_landscape)
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