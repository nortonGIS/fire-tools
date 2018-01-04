from __main__ import *

import os
import urllib as u
import re
import subprocess
import arcpy
from arcpy import env

LAS_path = sys.path[0] 
def pull_OpenTopo(lidar_path, OpenTopo):    
    lasd = os.path.join(lidar_path, "lidar.lasd")
    lasfiles = []

    #Define the root url for the Lidar website we're going to scrape from

    #Open and read out Lidar Website Html
    htmlfile_lev1 = u.urlopen(OpenTopo)
    htmltext_lev1 = htmlfile_lev1.read()

    #Split html string output from page to prepare for download URL extrapolation (via Regex)
    htmltext_split = htmltext_lev1.split('<td class="colname">')

    #Pull out and download URL's per lidar element (file)
    num_files = 0

    for item in htmltext_split:
        regex_lid = '<a href="(.+?)">.*</a>'
        pattern_lid = re.compile(regex_lid)
        lidar_URL = re.findall(pattern_lid, item)
        if lidar_URL and lidar_URL[0] !="../":
                num_files += 1

    arcpy.AddMessage(str(num_files)+" files to be downloaded.")
    i = 0
    for item in htmltext_split:
        regex_lid = '<a href="(.+?)">.*</a>'
        pattern_lid = re.compile(regex_lid)
        lidar_URL = re.findall(pattern_lid, item)
        #Take download URL and execute - note that the Lidar files will save in the same folder as this python script
        if lidar_URL and lidar_URL[0] !="../":
            newURL = OpenTopo + lidar_URL[0]
            #print newURL
            laz = lidar_URL[0][:-4] + ".laz"
            las = lidar_URL[0][:-4] + ".las"

            u.urlretrieve(newURL, laz)
            
            # Unzip LAZ
            args = "E:\\TFS_Fire\\fire-tools\\laszip-cli.exe -i "+laz+" -o "+las
            subprocess.call(args)
            i += 1
            las = os.path.join(LAS_path, las)
            lasfiles.extend([las])
            arcpy.AddMessage(str(i)+" of "+str(num_files))
    arcpy.CreateLasDataset_management(lasfiles, lasd)