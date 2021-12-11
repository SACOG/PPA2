'''
PURPOSE:
	Add a column to TIMS data that tags whether the crash occurred on a
	grade-separated, limited-access freeway
	
More data notes:
	Q:\ProjectLevelPerformanceAssessment\DataLayers_Proof_of_Concept\Spreadsheet\CombinedCollisionData\Potential Freeway Filters.docx
	
9/14/2017
	consider making this part of TimsProcessor script when time permits
	
	
Run in python shell
execfile(r'Q:\ProjectLevelPerformanceAssessment\DataLayers_Proof_of_Concept\Python\TIMS_fwy_tagger_latest.py')

Run from command line
python Q:\ProjectLevelPerformanceAssessment\DataLayers_Proof_of_Concept\Python\TIMS_fwy_tagger_latest.py
'''

import arcpy
arcpy.env.overwriteOutput = True

#===============USER INPUTS=============================

arcpy.env.workspace = r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb'

tims_input = "SACOG_collisions2014_2018_XYTableToPoint"
tims_hwy_ind = "STATE_HWY_IND"

centerline = "RegionalCenterline_2019"
centerline_fwy_ind = "FWY_YN"

tims_gdb_output = "Collisions2014to2018fwytag"

#=====================LOAD INPUT LAYERS====================
#bring in inputs
print('loading inputs...')
arcpy.MakeFeatureLayer_management(centerline,"centerline_lyr")
arcpy.MakeFeatureLayer_management(tims_input,"tims_lyr")


print('filtering and adding columns to tims data...')
#get centerline features that freeways (tag based on 2017 CMP freeway definitions)
sql_centerline = "{} = 1".format(centerline_fwy_ind)
arcpy.SelectLayerByAttribute_management("centerline_lyr", 
											"NEW_SELECTION", 
											sql_centerline)


#add column "fwy_yn" to tims data, set default to 0
arcpy.AddField_management("tims_lyr","fwy_yn","SHORT")
arcpy.CalculateField_management("tims_lyr","fwy_yn",0)

#get tims records that are on highways 
sql_tims = "{} = 'Y'".format(tims_hwy_ind)
arcpy.SelectLayerByAttribute_management("tims_lyr", 
											"NEW_SELECTION", 
											sql_tims)

#from filtered tims data get records that are within 100feet of the filtered 
#centerline features
arcpy.SelectLayerByLocation_management("tims_lyr",
										"WITHIN_A_DISTANCE",
										"centerline_lyr",
										100,
										"SUBSET_SELECTION")

										
										
# and tag all of the currently-selected TIMS features = 1

arcpy.CalculateField_management("tims_lyr","fwy_yn",1)

#clear selection to have all TIMS records
arcpy.SelectLayerByAttribute_management("tims_lyr", "CLEAR_SELECTION")


#POSSIBLE FUTURE ADD-IN - take out tims records that lack tims geocode and that are 
# >100 feet from centerline features
#rough way to eliminate bad chp geocodes

#export to gdb feature--in future, you may be able to filter out bad geocodes here!
print('exporting to {} as gdb object...'.format(tims_gdb_output))
arcpy.FeatureClassToFeatureClass_conversion("tims_lyr", arcpy.env.workspace, tims_gdb_output)

print('done!')