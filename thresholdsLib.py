#-------------------------------------------------------------------------------
# Name:        thresholdsLib Tool
# Purpose:     This tool adds a new column to the desired table and updates the 
# 				rows with values from a 1:1 matched table from zonal statistics.
#
#			
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

def get_thresholds(bioregion, stage, landcover, field, unit):
  if unit == "Meters":
    ground_ht_threshold = 60.96 #0.6096m * 100
  elif unit == "Feet":
    ground_ht_threshold = 2
  #returns list of values for index based on input name
  if bioregion == "Tahoe":
    if stage == "S1":
        if field == "S1_ndvi":
            imp = "-880 <= x <= -120" #[-0.88, -0.12]
            veg = "-10 <= x <= 600"  #[-0.01, 0.6]
            return [imp, veg]

        elif field == "S1_ndwi":
            imp = "-20 <= x <= 910"  #[-0.02, 0.91]
            veg = "-460 <= x <= -30" #[-0.46, -0.03]
            return [imp,veg]

        elif field == "S1_gndv":
            imp = "-940<= x <= -50"  #[-0.94, -0.05]
            veg = "-20 <= x <= 380" #[-0.02, 0.38]
            return [imp,veg]

        elif field == "S1_osav":
            imp = "-940 <= x <= -130"  #[-0.94, -0.13]
            veg = "-80 <= x <= 760" #[-0.08, 0.76]
            return [imp,veg]

    elif stage == "S2":
        if landcover == "vegetation": 
          if field == "S2_heig":
            grass = "x <= "+str(ground_ht_threshold)
            shrub = "x <= "+str(3*ground_ht_threshold)
            tree = "x > "+str(3*ground_ht_threshold)
            return [grass, shrub, tree]		     

        elif landcover == "impervious":
            if field == "S2_heig":
              path = "x <= "+str(ground_ht_threshold)
              building = "x > "+str(ground_ht_threshold)
              return [path, building]
                
  if bioregion == "Richmond":
    if stage == "S1":
      if field == "S1_grid":

        healthy = ">= 250" #[250,255]
        dry = "<= 249"  #[0, 249]

        return[healthy, dry]

      elif field == "S1_ndvi":
        imp = "-880 <= x <= -200" #[-0.88, -0.2]
        veg = "-180 <= x <= 500"  #[-0.18, 0.5]
        return [imp, veg]

      elif field == "S1_ndwi":
        imp = "240 <= x <= 910"  #[0.24, 0.91]
        veg = "-410 <= x <= 180" #[-0.41, 0.18]
        return [imp, veg]
      
      elif field == "S1_gndv":
        imp = "-940<= x <= -170"  #[-0.94, -0.17]
        veg = "-300 <= x <= 380" #[-0.3, 0.38]
        return [imp, veg]

      elif field == "S1_osav":
        imp = "-940 <= x <= -250"  #[-0.94, -0.25]
        veg = "-150 <= x <= 760" #[-0.15, 0.76]
        return [imp, veg]

    elif stage == "S2":
      if landcover == "vegetation":
        if field == "S2_grid":
          dry = ">= 250"    #[250, 255]
          healthy = "<= 249"    #(0, 249]
          return [dry, healthy]
                
        elif field == "S2_heig":
          grass = "x <= "+str(ground_ht_threshold)
          shrub = "x <= "+str(3*ground_ht_threshold)
          tree = "x > "+str(3*ground_ht_threshold)
          return [grass, shrub, tree]   
      
        elif field == "S2":
          return("def landcover(a):\\n"+
                 "    return a "
                 )

      elif landcover == "impervious":
        
        if field == "S2_heig":
          path = "x <= "+str(ground_ht_threshold)
          building = "x > "+str(ground_ht_threshold)
          return [path, building]

  elif bioregion == "Grape_Vine":
    if stage == "S1":
      if field == "S1_ndvi":
        imp = "x <= -50"
        veg = "x >= 20"  
        return [imp, veg]

      elif field == "S1_ndwi":
        imp = "x >= 20"  #[0.24, 0.91]
        veg = "x <= -100" #[-0.41, 0.18]
        return [imp, veg]
      
      elif field == "S1_gndv":
        imp = "x <= -50"  #[-0.94, -0.17]
        veg = "x >= 0" #[-0.3, 0.38]
        return [imp, veg]

      elif field == "S1_osav":
        imp = "x <= -400"  #[-0.94, -0.25]
        veg = "x >= 200" #[-0.15, 0.76]
        return [imp, veg]
      
