#--------------------------------------------------------------------------------------------------------------------------------------
# Name:        fuelSpotter Tool
# Author:      Peter Norton
# Created:     05/25/2017
# Updated:     01/27/2018
# Copyright:   (c) Peter Norton and Matt Ashenfarb 2017
#--------------------------------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------------------------------
#
# USER LOG
date = "1_27"
# Geographic Data
location_name = "Orinda_Downs"
bioregion = "CA_Oak_Woodlands" #["Sierra_Nevada_Mountains","CA_Oak_Woodlands", "SoCal_Mountains"]


summary = ""
#summary = "Purpose:     \\n"+
#          "(1) Process raw imagery and raw lidar data into landscape objects that are classified into fire behavior fuel models.\\n"+
#          "(2) Create all necessary input files for FlamMap's landscape file (.LCP) and burn using FlamMap DLL.\\n"+
#          "(3) Join all burn metrics to objects. If an infrastructure file exists, then burns will be joined to infrsx segments.\\n"+
#          "(4) Populate an MXD with all necessary shapefiles.\\n"

projection = "UTMZ10"  #["UTMZ10", "UTMZ11"]
lidar_date = 2008
naip_date = 2009
burn_metrics = ["fml", "ros", "fi", "fli"]

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

align_inputs = "No" # "Align and Scale inputs"
pipe_analysis = "No"  # "Reduce Analysis to Infrastructure Buffer"
generate_land_cover = "Yes"  # "Generate Land Cover & SVM"
fire_behavior = "No"  # "Run FlamMap & Join Burns"
create_MXD = "No"  # "Create or Update MXD"

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
script_db = drive+":\\Modeling\\fire-tools"
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
naip_1m = os.path.join(inputs, input_naip) # NAIP Imagery at 1m res
lasd = os.path.join(inputs, input_las)
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
naip_5m = os.path.join(outputs,"naip_5m.tif")
S1_classified = os.path.join(outputs, "S1_classified.shp")
classified_landscape = os.path.join(outputs, "classified.shp")

b1 = os.path.join(scratchgdb, "Band_1")
b2 = os.path.join(scratchgdb, "Band_2")
b3 = os.path.join(scratchgdb, "Band_3")
b4 = os.path.join(scratchgdb, "Band_4")

zone_num = 0

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

def find_stems(fuel, fm):

  heights_1m = os.path.join(outputs,"heights_1m_"+str(zone_num)+".tif")
  trees_zone = os.path.join(scratchgdb, "trees_"+str(zone_num))
  tree_bnd = os.path.join(scratchws, "trees_"+str(zone_num)+".shp")
  existing_canopy_centroids = os.path.join(scratchws, "canopy_cntrs_"+str(zone_num)+".shp")
  tree_thiessen = os.path.join(outputs, "treeThiessen_"+str(zone_num)+".shp")
  thiessen = os.path.join(scratchgdb, "thiessen_"+str(zone_num))
  temp = os.path.join(scratchgdb, "temp_"+str(zone_num))
  zone_heights = os.path.join(scratchws, "heights_"+str(zone_num)+".tif")

  text = "Segmenting canopies."
  generateMessage(text)

  # Create raster of vegetation heights

  global zone_num

  # Parameters
  this = SetNull(fuel, heights_1m, "Value < "+str(fm))
  this.save(zone_heights)
  this = Raster(zone_heights)
  max_canopy_height = Int(this.maximum)
  max_base_height = max_canopy_height
  incr = -1
  i = 0
  
  while max_canopy_height > 1.8:
      upper = max_canopy_height
      max_canopy_height += incr
      lower = max_canopy_height
      if lower < 0:
        lower = 0
      # text = "Making horizontal slices: "+str(lower)+" "+str(upper)
      # generateMessage(text)

      ht_slice = os.path.join(scratchgdb, "slice_"+str(upper)+str(zone_num))
      canopy_select = os.path.join(scratchgdb, "canopy_select_"+str(zone_num))
      slice_sms = os.path.join(scratchws, "slice_sms_"+str(zone_num)+".tif")
      slice_poly = os.path.join(scratchgdb, "slice_poly_"+str(upper)+str(zone_num))
      canopies = os.path.join(scratchgdb, "canopies_"+str(upper)+str(zone_num))
      new_canopies = os.path.join(scratchgdb, "new_canopies_"+str(zone_num))
      new_canopy_centroids = os.path.join(scratchgdb, "new_canopy_cntr_"+str(zone_num))
      existing_canopy_centroids = os.path.join(scratchgdb, "existing_canopy_cntr_"+str(zone_num))
      
      existing_canopies = os.path.join(scratchgdb, "existing_canopies_"+str(zone_num))
      temp = os.path.join(scratchgdb, "temp_"+str(zone_num))
      
      delete_shapes = [canopy_select, ht_slice, slice_sms, slice_poly, canopies, new_canopies]

      vert_max = Con(Int(zone_heights)>= upper, upper, Int(zone_heights))
      vert_min = Con(Int(vert_max) <= lower, 0, Int(vert_max))
      vert_min.save(ht_slice)
      
      #convert slice to polygons and extract canopies
     
      arcpy.RasterToPolygon_conversion(ht_slice, slice_poly, "NO_SIMPLIFY", "VALUE")
      arcpy.Select_analysis (slice_poly, canopy_select, "gridcode <> 0")
      arcpy.Dissolve_management(canopy_select, canopies, "", "", "SINGLE_PART")
      arcpy.AddField_management(canopies, "h", "INTEGER")
      arcpy.CalculateField_management(canopies, "h", 1)
      

      #join previous centroids to canopy polygons
      if i > 0:
        arcpy.SpatialJoin_analysis(canopies, existing_canopy_centroids, existing_canopies,  "JOIN_ONE_TO_ONE")
        where_clause = "Exist IS NULL"# AND Shape_Length > 3"
        arcpy.Select_analysis(existing_canopies, new_canopies, where_clause)

        #create new canopy centroids
        arcpy.FeatureToPoint_management(new_canopies, new_canopy_centroids, "INSIDE")
        arcpy.AddField_management(new_canopy_centroids, "Exist", "INTEGER")
        arcpy.CalculateField_management(new_canopy_centroids, "Exist", 1)
        
        new_cntr_fields = [f.name for f in arcpy.ListFields(new_canopy_centroids)]
        delete_fields = []
        for field in new_cntr_fields:
          if field not in ex_cntr_fields:
            arcpy.DeleteField_management(new_canopy_centroids, field)
        
        arcpy.Append_management(new_canopy_centroids, existing_canopy_centroids, "TEST")
          
      else:
        new_canopies = canopies
    
        #create new canopy centroids
        arcpy.FeatureToPoint_management(new_canopies, existing_canopy_centroids, "INSIDE")
        arcpy.AddField_management(existing_canopy_centroids, "Exist", "INTEGER")
        arcpy.CalculateField_management(existing_canopy_centroids, "Exist", 1)
        ex_cntr_fields = [f.name for f in arcpy.ListFields(existing_canopy_centroids)]

      for shape in delete_shapes:
        arcpy.Delete_management(shape)
      i += 1

  arcpy.CreateThiessenPolygons_analysis(existing_canopy_centroids, thiessen)
  thiessen_rast = os.path.join(scratchgdb, "thiessen_rast_"+str(zone_num))
  arcpy.PolygonToRaster_conversion(thiessen, "OBJECTID", thiessen_rast, "CELL_CENTER", "", 1)
  arcpy.RasterToPolygon_conversion(thiessen_rast, thiessen, "NO_SIMPLIFY", "Value")


  arcpy.RasterToPolygon_conversion(fuel, tree_bnd, "NO_SIMPLIFY", "Value")
  arcpy.Clip_analysis(thiessen, tree_bnd, tree_thiessen)
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
lidar_projection = arcpy.Describe(lasd).spatialReference
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

  #-----------------------------------------------
  #-----------------------------------------------
  text = "Aligning cells."
  newProcess(text)
  # Resample NAIP Imagery, heights, and DEM to align cells and scale measurements to projection. Resampled layers will be saved to 'Outputs' folder

  #NAIP
  text = "Resampling NAIP image."
  generateMessage(text)

  bnd_zones_rast = os.path.join(scratchgdb, "bnd_zones_rast")
  cell_size = int(coarsening_size)
  naip_cell_size = str(cell_size) +" "+str(cell_size)
  arcpy.Resample_management(naip_1m, naip_5m, naip_cell_size, "BILINEAR") # Bilinear Interpolation reduce image distortion when scaling.It linearly interpolates the nearest 4 pixels
  #arcpy.DefineProjection_management(naip_5m, projection)
  bands = ["Band_1","Band_2","Band_3","Band_4"] # NAIP has 4 bands (in increasing order) B,G,R,NIR

  arcpy.env.snapRaster = naip_1m
  # Create a fitted, resampled boundary
  text = "Creating a boundary based on resampled NAIP imagery extent."
  generateMessage(text)

  this = Int(Raster(naip_1m)*0)
  this.save(bnd_zones_rast)
  arcpy.DefineProjection_management(bnd_zones_rast, projection)
  arcpy.RasterToPolygon_conversion(bnd_zones_rast, bnd_zones, "NO_SIMPLIFY", "Value")

  #make fishnet with 1km x 1km
  analysis_area = os.path.join(outputs, "bnd_fishnet.shp")

  text = "Creating a fishnet."
  generateMessage(text)

  fishnet = os.path.join(scratchws, "fishnet.shp")

  desc = arcpy.Describe(naip_1m)
  origin_coord = str(desc.extent.XMin)+ " " +str(desc.extent.YMin)
  y_axis_coord = str(desc.extent.XMin)+ " " +str(desc.extent.YMax)

  cell_width = 1000
  cell_height = 1000

  arcpy.CreateFishnet_management(fishnet, origin_coord, y_axis_coord, cell_width, cell_height, "", "", "", "NO_LABELS", naip_1m, "POLYGON")
  arcpy.Clip_analysis(fishnet, bnd_zones, analysis_area)
  arcpy.DefineProjection_management(analysis_area, projection)

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
arcpy.env.extent = naip_1m

def gen_lc():

  create_obia = "Yes"

  process_lidar = "No"
  classify_S1 = "Yes"
  classify_S2 = "Yes"
  find_canopies = "No"
  merge_landcover_tiles = "Yes"


  # Iterate through all zones (if possible)
  tot_num_tiles = arcpy.management.GetCount(analysis_area)[0]

  fuel_lst = []
  canopy_lst = []
  stand_lst = []
  elevation_lst = [] 
  slope_lst = []
  aspect_lst = []

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
    global zone_num
    zone_num = zones.getValue("FID")
    if zone_num < -1:  #skip if needed
      #If tile is created already, skip to next in queue
      zones = searchcursor.next()

    else:

      def obia():
        text = "Running an OBIA for zone "+str(zone_num+1)+" of "+str(tot_num_tiles)+"."
        newProcess(text)

        #Variables
        bnd = os.path.join(scratchws, "zone_"+str(zone_num)+".shp")
        bnd_rast = os.path.join(scratchws, "bnd.tif")
        naip_zone_5m = os.path.join(scratchws, "naip_5m_"+str(zone_num)+".tif")
        naip_zone_1m = os.path.join(scratchws, "naip_1m_"+str(zone_num)+".tif")
        naip_zone_b1 = os.path.join(naip_zone_1m, "Band_1")
        naip_zone_b2 = os.path.join(naip_zone_1m, "Band_2")
        naip_zone_b3 = os.path.join(naip_zone_1m, "Band_3")
        naip_zone_b4 = os.path.join(naip_zone_1m, "Band_4")

        heights_zone = os.path.join(outputs, "stand_"+str(zone_num)+".tif")
        dem_zone = os.path.join(outputs, "dem_"+str(zone_num)+".tif")

        # Create zone boundary and extract NAIP and heights
        arcpy.env.extent = analysis_area
        where_clause = "FID = " + str(zone_num)
        arcpy.Select_analysis(analysis_area, bnd, where_clause)

        arcpy.AddField_management(bnd, "Shape_area", "DOUBLE")
        arcpy.CalculateField_management(bnd, "Shape_area", "!SHAPE.AREA@SQUAREKILOMETERS!", "PYTHON_9.3")
        cursor = arcpy.SearchCursor(bnd)
        global zone_area
        for row in cursor:
          zone_area = row.getValue("Shape_area")

        arcpy.env.extent = bnd
        arcpy.env.snapRaster = naip_5m
        this = ExtractByMask(naip_5m, bnd)
        this.save(naip_zone_5m)

        arcpy.env.snapRaster = naip_1m
        this = ExtractByMask(naip_1m, bnd)
        this.save(naip_zone_1m)

        def lasToHeights():

          # -------------Create DEM, DSM, Heights, Canopy Cover--------------------
          #
          naip_zone_1m = os.path.join(scratchws, "naip_1m_"+str(zone_num)+".tif")
          lasd_zone = os.path.join(outputs, "pointcloud_"+str(zone_num)+".lasd")
          las_dem = os.path.join(scratchws, "las_dem_"+str(zone_num)+".tif")
          las_dsm = os.path.join(scratchws, "las_dsm_"+str(zone_num)+".tif")
          heights_1m = os.path.join(outputs, input_heights) # Heights
          dem_1m = os.path.join(outputs, "dem_1m_"+str(zone_num)+".tif")
          dsm_1m = os.path.join(outputs, "dsm_1m_"+str(zone_num)+".tif")
          temp = os.path.join(scratchws, "temp.tif")

          arcpy.env.snapRaster = naip_1m
          cell_size = int(int(coarsening_size)*scale_naip)
          
          #check if NAIP and LAS are in same projection
          las_scale = 1
          las_cell_size = 1
          naip_lidar_prj = projection
          if projection != lidar_projection:
            naip_zone_LAS_proj = os.path.join(scratchws, "prj_n_"+str(zone_num))
            las_scale = 0.3048
            las_cell_size = 3.28084
            
            arcpy.ProjectRaster_management(naip_zone_1m, naip_zone_LAS_proj, lidar_projection, "BILINEAR")
            naip_lidar_prj = naip_zone_LAS_proj
            arcpy.env.extent = naip_lidar_prj

          #Extract LAS by NAIP zone bnd
          arcpy.ddd.ExtractLas(lasd, outputs, naip_lidar_prj, rearrange_points='MAINTAIN_POINTS', compute_stats='NO_COMPUTE_STATS', out_las_dataset = lasd_zone)
          
          #
          # Create DEM
          text = "Creating Elevation."
          generateMessage(text)

          arcpy.env.snapRaster = naip_lidar_prj
          LP_zone = os.path.join(scratchws, "LP_"+str(zone_num)+".lasd")
          arcpy.MakeLasDatasetLayer_management(lasd_zone,LP_zone,"","Last Return","","","","")
          arcpy.LasDatasetToRaster_conversion(LP_zone, las_dem, "ELEVATION", "BINNING MINIMUM LINEAR", "FLOAT", "CELLSIZE", las_cell_size, las_scale)
          arcpy.DefineProjection_management(las_dem, lidar_projection)

          arcpy.env.extent = bnd
          arcpy.env.snapRaster = naip_1m
          arcpy.ProjectRaster_management(las_dem, temp, projection, "BILINEAR")
          
          #arcpy.env.snapRaster = naip_5m
          this = ExtractByMask(temp, bnd)
          this.save(dem_1m)
          
          arcpy.env.snapRaster = naip_5m
          this = Aggregate(dem_1m, coarsening_size, "MEDIAN")
          this.save(dem_zone)

          # Create Slope
          text = "Creating Slope."
          generateMessage(text)
          
          arcpy.env.snapRaster = naip_1m
          slope_1m = os.path.join(scratchgdb, "slope_1m_"+str(zone_num))
          slope_zone = os.path.join(outputs, "slope_"+str(zone_num)+".tif")
          arcpy.Slope_3d(dem_1m, slope_1m, "DEGREE")

          arcpy.env.snapRaster = naip_5m
          this = Con(IsNull(slope_1m), 0, slope_1m)
          this = Aggregate(this, coarsening_size, "MEDIAN")
          this.save(slope_zone)

          # Create Aspect
          text = "Creating Aspect."
          generateMessage(text)

          arcpy.env.snapRaster = naip_1m
          aspect_1m = os.path.join(scratchgdb, "aspect_1m_"+str(zone_num))
          aspect_zone = os.path.join(outputs, "aspect_"+str(zone_num)+".tif")
          arcpy.Aspect_3d(dem_1m, aspect_1m)

          arcpy.env.snapRaster = naip_5m
          this = Con(IsNull(aspect_1m), 0, aspect_1m)
          this = Aggregate(this, coarsening_size, "MEDIAN")
          this.save(aspect_zone)

          # Create Canopy Cover

          text = "Creating Canopy Cover."
          generateMessage(text)

          All_count = os.path.join(scratchgdb, "All_count_"+str(zone_num))
          All_1m = os.path.join(scratchgdb, "All_1m_"+str(zone_num))
          All_5m = os.path.join(scratchgdb, "All_5m_"+str(zone_num))

          arcpy.env.extent = naip_lidar_prj
          arcpy.env.snapRaster = naip_lidar_prj
          arcpy.LasPointStatsAsRaster_management(lasd_zone, All_count,"POINT_COUNT","CELLSIZE", las_cell_size)
          arcpy.DefineProjection_management(All_count, lidar_projection)

          arcpy.env.extent = bnd
          arcpy.env.snapRaster = naip_1m
          arcpy.ProjectRaster_management(All_count, All_1m, projection, "BILINEAR")
          this = Con(IsNull(All_1m),0,All_1m)

          
          arcpy.env.snapRaster = naip_5m
          this = Aggregate(this, coarsening_size, "MEDIAN")
          this.save(All_5m)
          
          FP_zone = os.path.join(scratchws, "FP_"+str(zone_num)+".lasd")
          FP_count = os.path.join(scratchgdb, "FP_count_"+str(zone_num))
          FP_1m = os.path.join(scratchgdb, "FP_1m_"+str(zone_num))
          FP_5m = os.path.join(scratchgdb, "FP_5m_"+str(zone_num))

          arcpy.env.extent = naip_lidar_prj
          arcpy.env.snapRaster = naip_lidar_prj
          arcpy.MakeLasDatasetLayer_management(lasd_zone, FP_zone,"","First of Many","","","","")
          arcpy.LasPointStatsAsRaster_management(FP_zone, FP_count,"POINT_COUNT","CELLSIZE",las_cell_size)
          arcpy.DefineProjection_management(FP_count, lidar_projection)

          arcpy.env.extent = bnd
          arcpy.env.snapRaster = naip_1m
          arcpy.ProjectRaster_management(FP_count, FP_1m, projection, "BILINEAR")
          this = Con(IsNull(FP_1m),0,FP_1m,)
          this = ExtractByMask(temp, bnd)

          arcpy.env.snapRaster = naip_5m
          this = Aggregate(this, coarsening_size, "MEDIAN")
          this.save(FP_5m)

          
          canopy_5m = os.path.join(scratchws, "cc_5m_"+str(zone_num)+".tif")
          this = Int(Float(Divide(Float(FP_5m) / Float(All_5m)))*100)
          this = Con(this, 99, this, "Value = 100")
          this.save(canopy_5m)

          #
          # Create DSM

          text = "Creating Heights."
          generateMessage(text)

          arcpy.env.extent = naip_lidar_prj
          arcpy.env.snapRaster = naip_lidar_prj
          arcpy.LasDatasetToRaster_conversion(lasd_zone, las_dsm, "ELEVATION", "BINNING MAXIMUM NONE", "FLOAT", "CELLSIZE", las_cell_size, las_scale)
          arcpy.DefineProjection_management(las_dsm, lidar_projection)
          this_dsm = Con(IsNull(las_dsm),las_dem, las_dsm)
          this_dsm = FocalStatistics(this_dsm, NbrRectangle(2,2, "CELL"), "MAXIMUM", "DATA")
          dsm_smooth = os.path.join(scratchws, "dsm_smooth.tif")
          this_dsm.save(dsm_smooth)

          arcpy.env.extent = bnd
          arcpy.env.snapRaster = naip_1m
          arcpy.ProjectRaster_management(dsm_smooth, temp, projection, "BILINEAR")
          this = ExtractByMask(temp, bnd)
          this.save(dsm_1m)


          # Create Heights
          hts_interm1 = os.path.join(scratchws,"hts_interm1.tif")
          hts_interm2 = os.path.join(scratchws,"hts_interm2.tif")
          heights_sp = os.path.join(scratchws, "hts_sp.tif")
          heights_1m = os.path.join(outputs,"heights_1m_"+str(zone_num)+".tif")


          ht = Float(dsm_1m)-Float(dem_1m)
          ht = Con(IsNull(Float(ht)), 0, Float(ht))
          ht = Con(Float(ht) < 0, 0, Float(ht))
          ht.save(heights_1m)
          
          arcpy.env.snapRaster = naip_5m
          this = Aggregate(heights_1m, coarsening_size, "MEDIAN")
          this.save(heights_zone)

          # Interpolate over error due to birds
          # bird_height = "150"
          # heights = SetNull(Float(ht),Float(ht),"VALUE > "+bird_height)
          # if int(arcpy.GetRasterProperties_management(heights,"ANYNODATA").getOutput(0)):
          #   arcpy.AddMessage("Interpolating under clouds/birds.")
          #   heights.save(hts_interm1)
          #   heights.save(hts_interm2)
          #   del heights
          #   cloudrast = os.path.join(scratchgdb,"cloudrast")
          #   arcpy.gp.Reclassify_sa(hts_interm1, "VALUE", "-10000 10000 NODATA;NODATA 1", cloudrast, "DATA")
          #   cloudpts = os.path.join(scratchgdb,"cloudpts")
          #   arcpy.RasterToPoint_conversion(cloudrast,cloudpts,"VALUE")
          #   cloudpts_buf30 = os.path.join(scratchgdb,"cloudptsbuf30")
          #   arcpy.Buffer_analysis(cloudpts, cloudpts_buf30, "30 Feet", "FULL", "ROUND", "ALL", "", "PLANAR")
          #   nocloudmask = ExtractByMask(hts_interm2,cloudpts_buf30)
          #   interppts = os.path.join(scratchgdb,"interppts")
          #   arcpy.RasterToPoint_conversion(nocloudmask, interppts,"")
          #   NNinterp = os.path.join(scratchgdb,"NNinterp")
          #   arcpy.gp.NaturalNeighbor_sa(interppts, "grid_code", NNinterp, hts_interm2)   # Natural Neighbor Interpolation over bird error regions
          #   arcpy.MosaicToNewRaster_management(hts_interm2+";"+NNinterp,scratchws,"interp_heights.tif", "", "32_BIT_FLOAT", "", "1", "FIRST", "FIRST")
          #   interp_ht = os.path.join(scratchws,"interp_heights.tif")
          #   arcpy.Clip_management(interp_ht,"",raw_heights,bnd_rast,"NoData","ClippingGeometry","MAINTAIN_EXTENT")

        if process_lidar == "Yes":
          lasToHeights()

        def normalize(index):
            return (2 * (Float(index) - Float(index.minimum)) / (Float(index.maximum) - Float(index.minimum))) - 1

        def createImageEnhancements(image_enhancements):
          created_enhancements = []

          for field in image_enhancements:
            #Variables
            enhancement_path = os.path.join(scratchws, field+"_"+str(zone_num)+".tif")

            # -----------------------------------------------
            # -----------------------------------------------
            # Equations
            if field == "ndvi":
              inValueRaster = Int((((Float(naip_zone_b4))-(Float(naip_zone_b1))) / ((Float(naip_zone_b4))+(Float(naip_zone_b1))))*1000)
              inValueRaster.save(enhancement_path)
            elif field == "ndwi":
              inValueRaster = Int((((Float(naip_zone_b2))-(Float(naip_zone_b4))) / ((Float(naip_zone_b2))+(Float(naip_zone_b4))))*1000)
              inValueRaster.save(enhancement_path)
            elif field == "gndvi":
              inValueRaster = Int((((Float(naip_zone_b4))-(Float(naip_zone_b2))) / ((Float(naip_zone_b4))+(Float(naip_zone_b2))))*1000)
              inValueRaster.save(enhancement_path)
            elif field == "osavi":
              inValueRaster = Int((normalize((1.5 * (Float(naip_zone_b4) - Float(naip_zone_b1))) / ((Float(naip_zone_b4)) + (Float(naip_zone_b1)) + 0.16)))*1000)
              inValueRaster.save(enhancement_path)

            created_enhancements.extend([enhancement_path])
          return created_enhancements

        def burnable():
          # Create Image Enhancements and join to objects
          text = "Creating 1m burnable surface."
          generateMessage(text)

          image_enhancements = ["ndvi", "ndwi", "gndvi", "osavi"]

          created_enhancements_1m = createImageEnhancements(image_enhancements)

          arcpy.env.extent = bnd
          arcpy.env.snapRaster = naip_1m

          s1_ = []
          s1_1m = os.path.join(scratchws, "s1_1m.tif")
          s1_5m = os.path.join(scratchws, "s1_5m.tif")

          location = Fire_Env(bioregion)
          evaluators = [location.S1_ndvi, location.S1_ndwi, location.S1_gndvi, location.S1_osavi]
          for e in evaluators:

            x = os.path.join(scratchws, e[0]+"_"+str(zone_num)+".tif")
            ie_s1 = os.path.join(scratchws, e[0]+"_s1.tif")

            imp_min = e[1][0]
            imp_max = e[1][1]
            veg_min = e[2][0]
            veg_max = e[2][1]

            # -1 = Impervious, 0 = confused, 1 = vegetation
            veg = Con(x, Con(x, 1, 0, "Value <= " +str(veg_max)), 0, "Value >= "+str(veg_min))
            imp = Con(x, Con(x, -1, 0, "Value <= " +str(imp_max)), 0, "Value >= "+str(imp_min))
            this = CellStatistics([veg, imp], "SUM", "DATA")
            #this = Con(x, Con(x, -1, Con(x, Con(x, 1, 0, "Value <= " +str(veg_max)), 0, "Value >= "+str(veg_min)), "Value <= "+str(imp_max)), 0, "Value >= "+str(imp_min))
            this.save(ie_s1)
            s1_.extend([ie_s1])
          this = CellStatistics(s1_, "MEAN", "DATA")

          heights_zone = os.path.join(outputs, "heights_1m_"+str(zone_num)+".tif")

          #this = CellStatistics(s1_, "SUM", "DATA")
          #this = Con(this, -1, Con(this, 1, 0, "Value >= 1"), "Value <= -1")
          this = Con(this, -1, 1, "Value <= 0")

          #if heights over 1m, then impervious
          #this = Con(this, Con(heights_zone, -1, 0, "Value > 1"), this, "Value = 0")


          this.save(s1_1m)

          arcpy.env.snapRaster = naip_5m
          this = Aggregate(this, coarsening_size, "MEDIAN")
          this.save(s1_5m)

        if classify_S1 == "Yes":
          burnable()
      
        def lc():

          #s1_heights = os.path.join(scratchgdb, landcover+"_heights")
          s1_5m = os.path.join(scratchws, "s1_5m.tif")
          s1_1m = os.path.join(scratchws, "s1_1m.tif")
          veg_heights = os.path.join(outputs, "veg_zone_"+str(zone_num)+".tif")
          imp_heights = os.path.join(outputs, "imp_zone_"+str(zone_num)+".tif")
          cm_heights = os.path.join(scratchgdb, "cm_heights")

          s1 = os.path.join(scratchws, "s1_1m.tif")
          s2_5m = os.path.join(outputs, "s2_5m.tif")
          heights_zone = os.path.join(outputs, "heights_1m_"+str(zone_num)+".tif")

          arcpy.env.extent = bnd
          arcpy.env.snapRaster = naip_1m

          this = Int(Float(heights_zone)*100)
          this.save(cm_heights)

          this = Con(s1, cm_heights, -9999, "Value = -1")
          this.save(imp_heights)

          this = Con(s1, cm_heights, -9999, "Value = 1")
          this.save(veg_heights)

          location = Fire_Env(bioregion)

          fuel_lst = []
          fuels_1m = os.path.join(outputs, "fuel_1m_"+str(zone_num)+".tif")
          fuels_5m = os.path.join(outputs, "fuel_"+str(zone_num)+".tif")
          

          covers = location.fuels
          #arcpy.AddMessage(covers)
          for cover in covers:
            class landcover:
              def __init__(self, cover):
                self.cover = cover[0]
                self.stage = cover[1]
                self.fuel_model = cover[2]
                self.min_height = cover[3][0]
                self.max_height = cover[3][1]
                self.spectral_detail = cover[4][0]
                self.spatial_detail = cover[4][1]
                self.min_seg_size = cover[4][2]

            lc = landcover(cover)
          
            fuel = os.path.join(scratchgdb, lc.stage)

            
            text = "Geolocating "+str(lc.stage)+"."
            generateMessage(text)

            if lc.cover == "vegetation":
              fuels_heights = veg_heights

            elif lc.cover == "impervious":
              fuels_heights = imp_heights

            if arcpy.sa.Raster(fuels_heights).maximum > 0:
              this = SetNull(fuels_heights, SetNull(fuels_heights, int(lc.fuel_model), "Value < "+str(lc.min_height)), "Value > "+str(lc.max_height))
              if this.maximum > 0:
                this.save(fuel)
                fuel_lst.extend([fuel])

                if lc.stage == "tree" and find_canopies == "Yes":

                  find_stems(fuel, lc.fuel_model)
    
          this = CellStatistics(fuel_lst, "SUM", "DATA")
          this.save(fuels_1m)
          
          arcpy.env.snapRaster = naip_5m
          this = Aggregate(this, coarsening_size, "MEDIAN")
          this.save(fuels_5m)

          # Canopy cover
          canopy_zone = os.path.join(outputs, "canopy_"+str(zone_num)+".tif")
          canopy_5m = os.path.join(scratchws, "cc_5m_"+str(zone_num)+".tif")
          tree_cover = os.path.join(scratchgdb, "tree")
          this = ExtractByMask(canopy_5m, tree_cover)
          this.save(canopy_zone)

          estimate_time(zone_num)
          #zones = searchcursor.next()
        if classify_S2 == "Yes":
          lc()

      if create_obia == "Yes":
        obia()

      zones = searchcursor.next()


  def merge_tiles():
    LCP_layers = ["fuel", "canopy", "stand", "dem", "slope", "aspect"]
    arcpy.env.extent = analysis_area
    arcpy.env.snapRaster = naip_5m

    for layer in LCP_layers:

      layer_lst = []
      for i in range(int(tot_num_tiles)):

        tile = os.path.join(outputs, layer+"_"+str(i)+".tif")
        if arcpy.Exists(tile):
          layer_lst.extend([tile])

      text = "Joining "+str(len(layer_lst))+" "+layer+" tiles."
      generateMessage(text)

      temp = os.path.join(scratchgdb, "temp")
      output = os.path.join(outputs, "lcp_"+layer+".tif")
      ascii_output = os.path.join(outputs, layer+".asc")

      arcpy.MosaicToNewRaster_management(layer_lst, outputs, "lcp_"+layer+".tif", "", "32_BIT_SIGNED", "", 1, "MAXIMUM", "")
      arcpy.RasterToASCII_conversion(output, ascii_output)

      if layer == "fuel":
        arcpy.RasterToPolygon_conversion(output, classified_landscape, "NO_SIMPLIFY", "VALUE")
        text = "Land Cover objects created."
        generateMessage(text)
    #-----------------------------------------------
    #-----------------------------------------------

  if merge_landcover_tiles == "Yes":
    merge_tiles()

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
    arcpy.env.snapRaster = naip_5m
    cell_size = str(arcpy.GetRasterProperties_management(naip_1m, "CELLSIZEX", ""))
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