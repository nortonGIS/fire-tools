#-------------------------------------------------------------------------------
# Name:        bioregion class#			
#
# Author:      Peter Norton
#
# Created:     09/19/2017
# Updated:     -
# Copyright:   (c) Peter Norton 2017
#-------------------------------------------------------------------------------
#-----------------------------------------------
#-----------------------------------------------


#-----------------------------------------------
#-----------------------------------------------
# Import modules
import arcpy
import os
import sys
from arcpy import env
from arcpy.sa import *

def get_fuels(bioregion):
    
  details = []

  if bioregion == "Sierra_Nevada_Mountains":
    landcover = "grass"
    fuelmodel = "01"
    cm_heights = [-1, 60.96]
    spectral_detail, spatial_detail, min_seg_size = 10, 10, 1
    details.extend([[landcover, fuelmodel, cm_heights, [spectral_detail, spatial_detail, min_seg_size]]])
    
    landcover = "shrub"
    fuelmodel = "06"
    cm_heights = [60.96, 304.8]
    spectral_detail, spatial_detail, min_seg_size = 20, 20, 1
    details.extend([[landcover, fuelmodel, cm_heights, [spectral_detail, spatial_detail, min_seg_size]]])
   
    landcover = "tree"
    fuelmodel = "10"
    cm_heights = [304.8, 10000]
    spectral_detail, spatial_detail, min_seg_size = 20, 20, 1
    details.extend([[landcover, fuelmodel, cm_heights, [spectral_detail, spatial_detail, min_seg_size]]])

    cover = "impervious"
    landcover = "pavement"
    fuelmodel = "98"
    cm_heights = [0, 60.96]
    spectral_detail, spatial_detail, min_seg_size = "", "",""
    details.extend([[cover, landcover, fuelmodel, cm_heights, [spectral_detail, spatial_detail, min_seg_size]]])

    cover = "impervious"
    landcover = "building"
    fuelmodel = "99"
    cm_heights = [60.96, 10000]
    spectral_detail, spatial_detail, min_seg_size = "", "",""
    details.extend([[cover, landcover, fuelmodel, cm_heights, [spectral_detail, spatial_detail, min_seg_size]]])

  elif bioregion == "CA_Oak_Woodlands":
    cover = "vegetation"
    landcover = "grass"
    fuelmodel = "01"
    cm_heights = [-1, 60.96]
    spectral_detail, spatial_detail, min_seg_size = 10, 10, 1
    details.extend([[cover, landcover, fuelmodel, cm_heights, [spectral_detail, spatial_detail, min_seg_size]]])
    
    cover = "vegetation"
    landcover = "shrub"
    fuelmodel = "06"
    cm_heights = [60.96, 304.8]
    spectral_detail, spatial_detail, min_seg_size = 20, 20, 1
    details.extend([[cover, landcover, fuelmodel, cm_heights, [spectral_detail, spatial_detail, min_seg_size]]])
   
    cover = "vegetation"
    landcover = "tree"
    fuelmodel = "02"
    cm_heights = [304.8, 10000]
    spectral_detail, spatial_detail, min_seg_size = 20, 20, 1
    details.extend([[cover, landcover, fuelmodel, cm_heights, [spectral_detail, spatial_detail, min_seg_size]]])

    cover = "impervious"
    landcover = "pavement"
    fuelmodel = "98"
    cm_heights = [0, 60.96]
    spectral_detail, spatial_detail, min_seg_size = "", "",""
    details.extend([[cover, landcover, fuelmodel, cm_heights, [spectral_detail, spatial_detail, min_seg_size]]])

    cover = "impervious"
    landcover = "building"
    fuelmodel = "99"
    cm_heights = [60.96, 10000]
    spectral_detail, spatial_detail, min_seg_size = "", "",""
    details.extend([[cover, landcover, fuelmodel, cm_heights, [spectral_detail, spatial_detail, min_seg_size]]])

  elif bioregion == "SoCal_Mountains":
    landcover = "grass"
    fuelmodel = "01"
    cm_heights = [-1, 60.96]
    spectral_detail, spatial_detail, min_seg_size = 10, 10, 1
    details.extend([[landcover, fuelmodel, cm_heights, [spectral_detail, spatial_detail, min_seg_size]]])

    landcover = "shrub"
    fuelmodel = "06"
    cm_heights = [60.96, 182.88]
    spectral_detail, spatial_detail, min_seg_size = 20, 20, 1
    details.extend([[landcover, fuelmodel, cm_heights, [spectral_detail, spatial_detail, min_seg_size]]])

    landcover = "chaparral"
    fuelmodel = "04" 
    cm_heights = [182.88, 304.8]
    spectral_detail, spatial_detail, min_seg_size = 20, 20, 1
    details.extend([[landcover, fuelmodel, cm_heights, [spectral_detail, spatial_detail, min_seg_size]]])

    landcover = "tree"
    fuelmodel = "02"
    cm_heights = [304.8, 10000]
    spectral_detail, spatial_detail, min_seg_size = 20, 20, 1
    details.extend([[landcover, fuelmodel, cm_heights, [spectral_detail, spatial_detail, min_seg_size]]])

    cover = "impervious"
    landcover = "pavement"
    fuelmodel = "98"
    cm_heights = [0, 60.96]
    spectral_detail, spatial_detail, min_seg_size = "", "",""
    details.extend([[cover, landcover, fuelmodel, cm_heights, [spectral_detail, spatial_detail, min_seg_size]]])

    cover = "impervious"
    landcover = "building"
    fuelmodel = "99"
    cm_heights = [60.96, 10000]
    spectral_detail, spatial_detail, min_seg_size = "", "",""
    details.extend([[cover, landcover, fuelmodel, cm_heights, [spectral_detail, spatial_detail, min_seg_size]]])

  return details

def get_thresholds(bioregion, spectral_index):
  
  if bioregion == "Sierra_Nevada_Mountains":
    if spectral_index == "ndvi":
      imp = [-1000, -120]
      veg = [-10, 600]
    elif spectral_index == "ndwi":
        imp = [-20, 1000]
        veg = [-1000, -30]
    elif spectral_index == "gndvi":
        imp = [-1000, -50]
        veg = [-20, 1000]
    elif spectral_index == "osavi":
        imp = [-1000, -130]
        veg = [-80, 760]

  elif bioregion == "CA_Oak_Woodlands":
    if spectral_index == "ndvi":
        imp = [-1000, -300]
        veg = [-180, 1000] 
    elif spectral_index == "ndwi":
        imp = [240, 1000]
        veg = [-1000, 180] 
    elif spectral_index == "gndvi":
        imp = [-1000, -170] 
        veg = [-300, 1000]
    elif spectral_index == "osavi":
        imp = [-1000, -250] 
        veg = [-170, 1000] 

  elif bioregion == "SoCal_Mountains":
    if spectral_index == "ndvi":
      imp = [-1000, 0]
      veg = [0, 1000]
    elif spectral_index == "ndwi":
      veg = [-1000, 0]
      imp = [0, -1000]
    elif spectral_index == "gndvi":
      imp = [-1000, 0]
      veg = [0, 1000]
    elif spectral_index == "osavi":
      imp = [-1000, 400]
      veg = [400, 1000]

  return [spectral_index, imp, veg]


def get_tree_health(bioregion, spectral_index):

  if bioregion == "Sierra_Nevada_Mountains":
    if spectral_index == "ndwi":
      healthy = "-1000 <= x <= -200"
      senescent = "-200 <= x <= 1000"
    elif spectral_index == "ndvi":
      healthy = "100 <= x <= 1000" 
      senescent = "-1000 <= x <= 100"
  
  elif bioregion == "CA_Oak_Woodlands":
    if spectral_index == "ndwi":
      healthy = "-1000 <= x <= 0"
      senescent = "0 <= x <= 1000" 
    elif spectral_index == "ndvi":
      healthy = "-100 <= x <= 1000" 
      senescent = "-1000 <= x < -100"

  elif bioregion == "SoCal_Mountains":
    if spectral_index == "ndwi":  
      healthy = "-1000 <= x <= 0"
      senescent = "0 <= x <= 1000" 
    elif spectral_index == "ndvi":    
      healthy = "-100 <= x <= 1000" 
      senescent = "-1000 <= x < -100"

  return [healthy, senescent]

class Fire_Env:
  def __init__(self, bioregion):
    self.bioregion = bioregion
    self.fuels = get_fuels(bioregion)
    self.spectral_indices = ["ndvi", "ndwi", "gndvi", "osavi"]
    self.S1_ndvi = get_thresholds(bioregion, "ndvi")
    self.S1_ndwi = get_thresholds(bioregion, "ndwi")
    self.S1_gndvi = get_thresholds(bioregion, "gndvi")
    self.S1_osavi = get_thresholds(bioregion, "osavi")
    self.tree_ndvi = get_tree_health(bioregion, "ndvi")
    self.tree_ndwi = get_tree_health(bioregion, "ndwi")

#----------------------------------------------------------------
#----------------------------------------------------------------                
      