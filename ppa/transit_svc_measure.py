# Esri start of added imports
import sys, os, arcpy
# Esri end of added imports

# Esri start of added variables
g_ESRI_variable_1 = 'fl_projline'
g_ESRI_variable_2 = 'fl_trnstp'
g_ESRI_variable_3 = 'fl_buff'
# Esri end of added variables

# --------------------------------
# Name: transit_svc_measure.py
# Purpose: Estimate transit service density near project
#
#
# Author: Darren Conly
# Last Updated: <date>
# Updated by: <name>
# Copyright:   (c) SACOG
# Python Version: 3.x
# --------------------------------
import gc
import time

import arcpy

import ppa_input_params as params


def trace():
    import traceback, inspect
    tb = sys.exc_info()[2]
    tbinfo = traceback.format_tb(tb)[0]
    # script name + line number
    line = tbinfo.split(", ")[1]
    filename = inspect.getfile(inspect.currentframe())
    # Get Python syntax error
    synerror = traceback.format_exc().splitlines()[-1]
    return line, filename, synerror


def get_poly_area(poly_fl):
    buff_area_ft2 = 0
    with arcpy.da.SearchCursor(poly_fl, ["SHAPE@AREA"]) as cur:
        for row in cur:
            buff_area_ft2 += row[0]

    buff_acre = buff_area_ft2 / params.ft2acre  # convert from ft2 to acres. may need to adjust for projection-related issues. See PPA1 for more info
    return buff_acre

def transit_svc_density(fc_project, fc_trnstops, project_type):

    arcpy.AddMessage("calculating transit service density...")
    sufx = int(time.perf_counter()) + 1
    fl_project = g_ESRI_variable_1
    fl_trnstops = os.path.join('memory','trnstp{}'.format(sufx))

    try:
        if arcpy.Exists(fl_project): arcpy.Delete_management(fl_project)
        arcpy.MakeFeatureLayer_management(fc_project, fl_project)
        
        if arcpy.Exists(fl_trnstops): arcpy.Delete_management(fl_trnstops)
        arcpy.MakeFeatureLayer_management(fc_trnstops, fl_trnstops)
        
        # analysis area. If project is line or point, then it's a buffer around the line/point.
        # If it's a polygon (e.g. ctype or region), then no buffer and analysis area is that within the input polygon
        if project_type == params.ptype_area_agg:
            fc_buff = fc_project
        else:
            fc_buff = r"memory\temp_buff_qmi"
            arcpy.Buffer_analysis(fl_project, fc_buff, params.trn_buff_dist)

        fl_buff = g_ESRI_variable_3

        if arcpy.Exists(fl_buff): arcpy.Delete_management(fl_buff)
        arcpy.MakeFeatureLayer_management(fc_buff, fl_buff)

        # calculate buffer area
        buff_acres = get_poly_area(fl_buff)

        # get count of transit stops within buffer
        arcpy.SelectLayerByLocation_management(fl_trnstops, "INTERSECT", fl_buff, 0, "NEW_SELECTION")

        transit_veh_events = 0

        with arcpy.da.SearchCursor(fl_trnstops, [params.col_transit_events]) as cur:
            for row in cur:
                vehstops = row[0] if row[0] is not None else 0
                transit_veh_events += vehstops

        trnstops_per_acre = transit_veh_events / buff_acres if buff_acres > 0 else 0

    except:
        trnstops_per_acre = -1.0 
        msg = "{}, {}".format(arcpy.GetMessages(2), trace())
        arcpy.AddWarning(msg)
    finally:
        '''
        if arcpy.Exists(fl_trnstops): 
            try:
                arcpy.Delete_management(fl_trnstops)
                arcpy.AddMessage("Successfully post-cleaned transit processes...")
            except:
                msg = "trying arcpy.Delete_management: {}, {}".format(arcpy.GetMessages(2), trace())
                arcpy.AddWarning(msg)
        '''
        return {"TrnVehStop_Acre": trnstops_per_acre}
        n = gc.collect()




        
'''
if __name__ == '__main__':
    arcpy.env.workspace = None

    proj_line_fc = None
    trnstops_fc = 'transit_stoplocn_w_eventcount_2016'
    ptype = params.ptype_arterial

    output = transit_svc_density(proj_line_fc, trnstops_fc, ptype)
    print(output)
'''
