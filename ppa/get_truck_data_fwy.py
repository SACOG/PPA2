# Esri start of added imports
import sys, os, arcpy
# Esri end of added imports

# Esri start of added variables
g_ESRI_variable_1 = 'fl_project'
g_ESRI_variable_2 = 'fl_speed_data'
g_ESRI_variable_3 = '{} IN {}'
g_ESRI_variable_4 = 'fl_tmc_buff'
# Esri end of added variables

#--------------------------------
# Name:get_truck_data_fwy.py
# Purpose: Estimate share of traffic on freeways that is trucks; based on Caltrans truck counts.
#          
#           
# Author: Darren Conly
# Last Updated: 02/2020
# Updated by: <name>
# Copyright:   (c) SACOG
# Python Version: <version>
#--------------------------------


import os

import arcpy
import pandas as pd

import ppa_input_params as params
import npmrds_data_conflation as ndc

def get_wtdavg_truckdata(in_df, col_name):
    len_cols = ['{}_calc_len'.format(dirn) for dirn in params.directions_tmc]
    val_cols = ['{}{}'.format(dirn, col_name) for dirn in params.directions_tmc]

    wtd_dict = dict(zip(len_cols, val_cols))

    wtd_val_sum = 0
    dist_sum = 0

    for dirlen, dirval in wtd_dict.items():
        dir_val2 = 0 if pd.isnull(in_df[dirval][0]) else in_df[dirval][0]
        dir_wtdval = in_df[dirlen][0] * dir_val2
        wtd_val_sum += dir_wtdval
        dist_sum += in_df[dirlen][0]

    return wtd_val_sum / dist_sum if dist_sum > 0 else -1




def get_tmc_truck_data(fc_projline, str_project_type):

    arcpy.OverwriteOutput = True
    fl_projline = g_ESRI_variable_1
    arcpy.MakeFeatureLayer_management(fc_projline, fl_projline)

    # make feature layer from speed data feature class
    fl_speed_data = g_ESRI_variable_2
    arcpy.MakeFeatureLayer_management(params.fc_speed_data, fl_speed_data)

    # make flat-ended buffers around TMCs that intersect project
    arcpy.SelectLayerByLocation_management(fl_speed_data, "WITHIN_A_DISTANCE", fl_projline, params.tmc_select_srchdist, "NEW_SELECTION")
    if str_project_type == 'Freeway':
        sql = g_ESRI_variable_3.format(params.col_roadtype, params.roadtypes_fwy)
        arcpy.SelectLayerByAttribute_management(fl_speed_data, "SUBSET_SELECTION", sql)
    else:
        sql = "{} NOT IN {}".format(params.col_roadtype, params.roadtypes_fwy)
        arcpy.SelectLayerByAttribute_management(fl_speed_data, "SUBSET_SELECTION", sql)

    # create temporar buffer layer, flat-tipped, around TMCs; will be used to split project lines
    scratch_gdb = arcpy.env.scratchGDB
        
    temp_tmcbuff = os.path.join(scratch_gdb, "TEMP_tmcbuff_4projsplit")
    fl_tmc_buff = g_ESRI_variable_4
    arcpy.Buffer_analysis(fl_speed_data, temp_tmcbuff, params.tmc_buff_dist_ft, "FULL", "FLAT")
    arcpy.MakeFeatureLayer_management(temp_tmcbuff, fl_tmc_buff)

    # get "full" table with data for all directions
    projdata_df = ndc.conflate_tmc2projline(fl_projline, params.directions_tmc, params.col_tmcdir, 
                                            fl_tmc_buff, params.truck_data_calc_dict)

    out_dict = {}
    for field, calcmthd in params.truck_data_calc_dict.items():
        if calcmthd == params.calc_distwt_avg:
            output_val = get_wtdavg_truckdata(projdata_df, field)
            out_dict["{}_proj".format(field)] = output_val
        else:
            continue
        
    return out_dict

    arcpy.Delete_management(temp_tmcbuff)

'''
if __name__ == '__main__':

    workspace = None
    arcpy.env.workspace = workspace

    project_line = None
    proj_type = "Freeway"  # arcpy.GetParameterAsText(2) #"Freeway"

    # make feature layers of NPMRDS and project line

    output_dict = get_tmc_truck_data(project_line, proj_type)
    print(output_dict)
    
    '''
