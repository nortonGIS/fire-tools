#-------------------------------------------------------------------------------
# Name:        tableJoin Tool
# Purpose:     This tool adds a new column to the desired table and updates the 
# 				rows with values from a 1:1 matched table from zonal statistics.
#
#			
#
# Author:      Peter Norton
#
# Created:     05/25/2017
# Updated:     08/28/2017
# Copyright:   (c) Peter Norton 2017
#-------------------------------------------------------------------------------

import arcpy

def one_to_one_join(table1, table2, attr, data_type):
	#add column
	arcpy.AddField_management(table1, attr, data_type)

	#update column
	searchcursor = arcpy.SearchCursor(table2)
	searchrow = searchcursor.next()
	updatecursor = arcpy.UpdateCursor(table1)
	updaterow = updatecursor.next()
	while searchrow:

		updaterow.setValue(attr, searchrow.getValue(attr))
		updatecursor.updateRow(updaterow)
		searchrow = searchcursor.next()
		updaterow = updatecursor.next()

def replace(file, field1, field2):
    
    #update column
    searchcursor = arcpy.SearchCursor(file)
    searchrow = searchcursor.next()
    updaterow = updatecursor.next()
    
    while searchrow:
        if searchrow.getValue(field2) != "confusion":
            updaterow.setValue(field1, searchrow.getValue(field2))
            updatecursor.updateRow(updaterow)
        searchrow = searchcursor.next()
        updaterow = updatecursor.next()
