location_name = "Big_Creek"
OpenTopo = "https://cloud.sdsc.edu/v1/AUTH_opentopography/PC_Bulk/CA15_Pfeiffer/"
LiDAR_Drive = "F:\\CA_Lidar_data\\OpenTopography"

pull_lidar = "Yes"

import os
import urllib as u
import re
import shutil
import subprocess
import arcpy
from arcpy import env
import sys


drive = os.path.abspath(sys.path[0])[0]
# Overwrite Setting
script_db = drive+":\\TFS_Fire\\fire-tools"

#Need to create a folder on the F:drive and store the script that downloads into it
scriptpath = sys.path[0]                                
setup_path = os.path.dirname(scriptpath)           #Setup or Master
location_folder = os.path.dirname(setup_path)

lidar_path = os.path.join(setup_path, "LiDAR")
if not os.path.isdir(lidar_path):
    os.makedirs(lidar_path)

LAS_path = os.path.join(LiDAR_Drive, location_name)
if not os.path.isdir(LAS_path):
    os.makedirs(LAS_path)

shutil.copy2(os.path.join(script_db, "__init__.py"), os.path.join(LAS_path, "__init__.py"))
shutil.copy2(os.path.join(script_db, "downloadLiDAR.py"), os.path.join(LAS_path, "downloadLiDAR.py")) # copies main to script folder
sys.path.append(LAS_path)


from downloadLiDAR import * #pull_OpenTopo

pull_OpenTopo(lidar_path, OpenTopo)

lidar = os.path.join(lidar_path, "lidar.lasd")
desc = arcpy.Describe(lidar)
origin_coord = str(desc.extent.XMin)+ " " +str(desc.extent.YMin)
y_axis_coord = str(desc.extent.XMin)+ " " +str(desc.extent.YMax)
#--------------------------------------
#--------------------------------------
# def download_NAIP():
#     gdrive_output = ""

#     bnd_WGS = os.path.join(scratchgdb, "bnd_WGS")
#     projection = ""
#     arcpy.ProjectRaster_management(bnd_zones, bnd_WGS, projection, "BILINEAR")
#     desc = arcpy.Describe(bnd_WGS)
#     origin_coord = str(desc.extent.XMin)+ " " +str(desc.extent.YMin)
#     y_axis_coord = str(desc.extent.XMin)+ " " +str(desc.extent.YMax)

#     class location:
#       def __init__(self, name, start, end, lon1, lat1, lon2, lat2):
#         self.name = location_name
#         self.start = lidar_date+"-01-01"
#         self.end = str(int(lidar_date)+10)+"-12-30"
#         self.lon1 = desc.extent.XMin
#         self.lat1 = desc.extent.YMin
#         self.lon2 = desc.extent.XMax
#         self.lat2 = desc.extent.YMax

#     naip = location(location_name)

#     naip.boundary = ee.Geometry.Rectangle([naip.lon1, naip.lat1, naip.lon2, naip.lat2]);
#     naip.image = (((ee.ImageCollection("USDA/NAIP/DOQQ")).filterDate(naip.start, naip.end)).first()).mosaic()

#     task = ee.Export.image.toDrive(naip.image, naip.name,  gdrive_output, naip.name, "", "", 1)

#     task.start()

# if pull_imagery == "Yes":
#     download_NAIP()