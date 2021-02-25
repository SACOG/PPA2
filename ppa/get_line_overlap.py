# Esri start of added imports
import sys, os, arcpy
# Esri end of added imports

# Esri start of added variables
g_ESRI_variable_1 = 'fl_splitprojlines'
g_ESRI_variable_2 = 'fl_splitproj_w_linkdata'
g_ESRI_variable_3 = 'fl_project'
g_ESRI_variable_4 = 'fl_network_lines'
g_ESRI_variable_5 = 'fl_link_buff'
# Esri end of added variables

'''
#--------------------------------
# Name:get_line_overlap.py
# Purpose: See what share of a user-input project line overlaps with another network (e.g., STAA freight line network, bike lane network, etc)
#          
#           
# Author: Darren Conly
# Last Updated: <date>
# Updated by: <name>
# Copyright:   (c) SACOG
# Python Version: <version>
#--------------------------------

Sample projects used: CAL20466, SAC25062
'''
import os
import datetime as dt
import time

import arcpy

arcpy.env.overwriteOutput = True

dateSuffix = str(dt.date.today().strftime('%m%d%Y'))



#====================FUNCTIONS==========================================


def conflate_link2projline(fl_proj, fl_links_buffd, links_desc):

    # get length of project
    fld_shp_len = "SHAPE@LENGTH"

    project_len = 0
    with arcpy.da.SearchCursor(fl_proj, fld_shp_len) as cur:
        for row in cur:
            project_len += row[0]
        
    # temporary files
    scratch_gdb = arcpy.env.scratchGDB
            
    temp_intersctpts = os.path.join(scratch_gdb, "temp_intersectpoints")  # r"{}\temp_intersectpoints".format(scratch_gdb)
    temp_intrsctpt_singlpt = os.path.join(scratch_gdb, "temp_intrsctpt_singlpt") # converted from multipoint to single point (1 pt per feature)
    temp_splitprojlines = os.path.join(scratch_gdb, "temp_splitprojlines") # fc of project line split up to match link buffer extents
    temp_splitproj_w_linkdata = os.path.join(scratch_gdb, "temp_splitproj_w_linkdata") # fc of split project lines with link data on them

    fl_splitprojlines = g_ESRI_variable_1
    fl_splitproj_w_linkdata = g_ESRI_variable_2

    # get links whose buffers intersect the project line
    arcpy.SelectLayerByLocation_management(fl_links_buffd, "INTERSECT", fl_proj)

    #split the project line at the boundaries of the link buffer, creating points where project line intersects link buffer boundaries
    arcpy.Intersect_analysis([fl_proj, fl_links_buffd],temp_intersctpts,"","","POINT")
    arcpy.MultipartToSinglepart_management (temp_intersctpts, temp_intrsctpt_singlpt)

    # split project line into pieces at points where it intersects buffer, with 10ft tolerance
    # (not sure why 10ft tolerance needed but it is, zero tolerance results in some not splitting)
    arcpy.SplitLineAtPoint_management(fl_proj, temp_intrsctpt_singlpt,
                                      temp_splitprojlines, "10 Feet")
    arcpy.MakeFeatureLayer_management(temp_splitprojlines, fl_splitprojlines)

    # get link speeds onto each piece of the split project line via spatial join
    arcpy.SpatialJoin_analysis(temp_splitprojlines, fl_links_buffd, temp_splitproj_w_linkdata,
                               "JOIN_ONE_TO_ONE", "KEEP_ALL", "#", "HAVE_THEIR_CENTER_IN", "30 Feet")

    # convert to fl and select records where "check field" col val is not none
    arcpy.MakeFeatureLayer_management(temp_splitproj_w_linkdata, fl_splitproj_w_linkdata)

    #return total project length, project length that overlaps input line network, and pct
    join_count = "Join_Count"
    link_overlap_dist = 0
    with arcpy.da.SearchCursor(fl_splitproj_w_linkdata, [fld_shp_len, join_count]) as cur:
        for row in cur:
            if row[1] > 0:
                link_overlap_dist += row[0]
            else:
                continue

    overlap_pct = link_overlap_dist / project_len
    
    links_desc = links_desc.replace(" ","_")
    out_dict = {'project_length': project_len, 'overlap with {}'.format(links_desc): link_overlap_dist,
                'pct_proj_{}'.format(links_desc): overlap_pct}

    # cleanup
    fcs_to_delete = [temp_intersctpts, temp_intrsctpt_singlpt, temp_splitprojlines, temp_splitproj_w_linkdata]
    for fc in fcs_to_delete:
        arcpy.Delete_management(fc)

    return out_dict


def get_line_overlap(fc_projline, fc_network_lines, links_desc):
    arcpy.AddMessage("Estimating share of project line that is {}...".format(links_desc))

    arcpy.OverwriteOutput = True
    SEARCH_DIST_FT = 100
    LINKBUFF_DIST_FT = 90

    # make feature layers of NPMRDS and project line
    fl_projline = g_ESRI_variable_3
    arcpy.MakeFeatureLayer_management(fc_projline, fl_projline)

    fl_network_lines = g_ESRI_variable_4
    arcpy.MakeFeatureLayer_management(fc_network_lines, fl_network_lines)

    # make flat-ended buffers around links that intersect project
    arcpy.SelectLayerByLocation_management(fl_network_lines, "WITHIN_A_DISTANCE", fl_projline, SEARCH_DIST_FT, "NEW_SELECTION")

    # create temporar buffer layer, flat-tipped, around links; will be used to split project lines
    temp_linkbuff = os.path.join(arcpy.env.scratchGDB, "TEMP_linkbuff_4projsplit")
    fl_link_buff = g_ESRI_variable_5
    arcpy.Buffer_analysis(fl_network_lines, temp_linkbuff, LINKBUFF_DIST_FT, "FULL", "FLAT")
    arcpy.MakeFeatureLayer_management(temp_linkbuff, fl_link_buff)

    # get dict of data
    projdata_dict = conflate_link2projline(fl_projline, fl_link_buff, links_desc)
    
    arcpy.Delete_management(temp_linkbuff)

    return projdata_dict


# =====================RUN SCRIPT===========================
    '''
if __name__ == '__main__':
    start_time = time.time()

    arcpy.env.workspace = None

    link_fc = 'BikeRte_C1_C2_C4_2017' #network of lines whose overlap with the project you want to get (e.g., truck routes, bike paths, etc.
    links_description = "BikeC1C2C4"
    
    #BikeRte_C1_C2_C4_2017 for bike routes

    project_line = "test_project_STAA_partialOverlap" # arcpy.GetParameterAsText(0) #"NPMRDS_confl_testseg_seconn"
    proj_name = "TestProj" # arcpy.GetParameterAsText(1) #"TestProj"
    proj_type = "Arterial" # arcpy.GetParameterAsText(2) #"Freeway"



    arcpy.OverwriteOutput = True
    projdata = get_line_overlap(project_line, link_fc, links_description)
    print(projdata)

    elapsed_time = round((time.time() - start_time)/60, 1)
    print("Success! Time elapsed: {} minutes".format(elapsed_time))    
    
'''
        
    


