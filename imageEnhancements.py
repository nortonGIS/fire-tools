#-------------------------------------------------------------------------------
# Name:        thresholdsLib Tool
# Purpose:     This tool adds a new column to the desired table and updates the 
#         rows with values from a 1:1 matched table from zonal statistics.
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


def normalize(index):
    return (2 * (Float(index) - Float(index.minimum)) / (Float(index.maximum) - Float(index.minimum))) - 1

def createImageEnhancements(image_enhancements, naip, heights, ID, scratchgdb):

  naip_b1 = os.path.join(naip, "Band_1")
  naip_b2 = os.path.join(naip, "Band_2")
  naip_b3 = os.path.join(naip, "Band_3")
  naip_b4 = os.path.join(naip, "Band_4")

  created_enhancements = []

  for field in image_enhancements:
    #Variables
    enhancement_path = os.path.join(scratchgdb, field+"_"+str(ID))

    # -----------------------------------------------
    # -----------------------------------------------
    # Equations
    if field == "ndvi":
      inValueRaster = Int((((Float(naip_b4))-(Float(naip_b1))) / ((Float(naip_b4))+(Float(naip_b1))))*1000)
      inValueRaster.save(enhancement_path)
    elif field == "ndwi":
      inValueRaster = Int((((Float(naip_b2))-(Float(naip_b4))) / ((Float(naip_b2))+(Float(naip_b4))))*1000)
      inValueRaster.save(enhancement_path)
    elif field == "gndvi":
      inValueRaster = Int((((Float(naip_b4))-(Float(naip_b2))) / ((Float(naip_b4))+(Float(naip_b2))))*1000)
      inValueRaster.save(enhancement_path)
    elif field == "osavi":
      inValueRaster = Int((normalize((1.5 * (Float(naip_b4) - Float(naip_b1))) / ((Float(naip_b4)) + (Float(naip_b1)) + 0.16)))*1000)
      inValueRaster.save(enhancement_path)
    elif field == "height":
      output = os.path.join(scratchgdb, "heights_"+str(ID))
      inValueRaster = Int(heights)
      inValueRaster.save(enhancement_path)

    created_enhancements.extend([enhancement_path])
  return created_enhancements
  # -----------------------------------------------
  # -----------------------------------------------