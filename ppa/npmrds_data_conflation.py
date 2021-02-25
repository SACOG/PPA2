# Esri start of added imports
import sys, os, arcpy
# Esri end of added imports

# Esri start of added variables
g_ESRI_variable_1 = 'fl_splitprojlines'
g_ESRI_variable_2 = 'fl_splitproj_w_tmcdata'
g_ESRI_variable_3 = "{} = '{}'"
g_ESRI_variable_4 = '{} IS NOT NULL'
g_ESRI_variable_5 = os.path.join(arcpy.env.packageWorkspace,'index')
g_ESRI_variable_6 = 'fl_project'
g_ESRI_variable_7 = 'fl_speed_data'
g_ESRI_variable_8 = '{} IN {}'
g_ESRI_variable_9 = 'fl_tmc_buff'
# Esri end of added variables

'''
#--------------------------------
# Name:PPA_getNPMRDSdata.py
# Purpose: Get distance-weighted average speed from NPMRDS data for PPA project,
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
import re
import datetime as dt
import time

import arcpy
#from arcgis.features import SpatialDataFrame
import pandas as pd

import ppa_input_params as params
import ppa_utils as utils

arcpy.env.overwriteOutput = True

dateSuffix = str(dt.date.today().strftime('%m%d%Y'))



# ====================FUNCTIONS==========================================

def get_wtd_speed(in_df, in_field, direction, fld_pc_len_ft):
    fielddir = "{}{}".format(direction, in_field)
    
    fld_invspd = "spdinv_hpm"
    fld_pc_tt = "projpc_tt"
    fld_len_mi = "pc_len_mi"
    
    in_df[fld_invspd] = 1/in_df[in_field]  # calculate each piece's "hours per mile", or inverted speed, as 1/speed
        
    # get each piece's travel time, in hours as inverted speed (hrs per mi) * piece distance (mi)
    in_df[fld_len_mi] = in_df[fld_pc_len_ft]/params.ft2mile
    in_df[fld_pc_tt] = in_df[fld_invspd] * in_df[fld_len_mi]
        
    # get total travel time, in hours, for all pieces, then divide total distance, in miles, for all pieces by the total tt
    # to get average MPH for the project
    proj_mph = in_df[fld_len_mi].sum() / in_df[fld_pc_tt].sum()
    
    return {fielddir: proj_mph}


def conflate_tmc2projline(fl_proj, dirxn_list, tmc_dir_field,
                          fl_tmcs_buffd, fields_calc_dict):

    speed_data_fields = [k for k, v in fields_calc_dict.items()]
    out_row_dict = {}
    
    # get length of project
    fld_shp_len = "SHAPE@LENGTH"
    fld_totprojlen = "proj_length_ft"
    
    with arcpy.da.SearchCursor(fl_proj, fld_shp_len) as cur:
        for row in cur:
            out_row_dict[fld_totprojlen] = row[0]
    
    for direcn in dirxn_list:
        # https://support.esri.com/en/technical-article/000012699
        
        # temporary files
        scratch_gdb = arcpy.env.scratchGDB
        
        temp_intersctpts = os.path.join(scratch_gdb, "temp_intersectpoints")  # r"{}\temp_intersectpoints".format(scratch_gdb)
        temp_intrsctpt_singlpt = os.path.join(scratch_gdb, "temp_intrsctpt_singlpt") # converted from multipoint to single point (1 pt per feature)
        temp_splitprojlines = os.path.join(scratch_gdb, "temp_splitprojlines") # fc of project line split up to match TMC buffer extents
        temp_splitproj_w_tmcdata = os.path.join(scratch_gdb, "temp_splitproj_w_tmcdata") # fc of split project lines with TMC data on them
        
        fl_splitprojlines = g_ESRI_variable_1
        fl_splitproj_w_tmcdata = g_ESRI_variable_2
        
        # get TMCs whose buffers intersect the project line
        arcpy.SelectLayerByLocation_management(fl_tmcs_buffd, "INTERSECT", fl_proj)
        
        # select TMCs that intersect the project and are in indicated direction
        sql_sel_tmcxdir = g_ESRI_variable_3.format(tmc_dir_field, direcn)
        arcpy.SelectLayerByAttribute_management(fl_tmcs_buffd, "SUBSET_SELECTION", sql_sel_tmcxdir)
        
        # split the project line at the boundaries of the TMC buffer, creating points where project line intersects TMC buffer boundaries
        arcpy.Intersect_analysis([fl_proj, fl_tmcs_buffd],temp_intersctpts,"","","POINT")
        arcpy.MultipartToSinglepart_management (temp_intersctpts, temp_intrsctpt_singlpt)
        
        # split project line into pieces at points where it intersects buffer, with 10ft tolerance
        # (not sure why 10ft tolerance needed but it is, zero tolerance results in some not splitting)
        arcpy.SplitLineAtPoint_management(fl_proj, temp_intrsctpt_singlpt,
                                          temp_splitprojlines, "10 Feet")
        arcpy.MakeFeatureLayer_management(temp_splitprojlines, fl_splitprojlines)
        
        # get TMC speeds onto each piece of the split project line via spatial join
        arcpy.SpatialJoin_analysis(temp_splitprojlines, fl_tmcs_buffd, temp_splitproj_w_tmcdata,
                                   "JOIN_ONE_TO_ONE", "KEEP_ALL", "#", "HAVE_THEIR_CENTER_IN", "30 Feet")
                                   
        # convert to fl and select records where "check field" col val is not none
        arcpy.MakeFeatureLayer_management(temp_splitproj_w_tmcdata, fl_splitproj_w_tmcdata)
        
        check_field = speed_data_fields[0]  # choose first speed value field for checking--if it's null, then don't include those rows in aggregation
        sql_notnull = g_ESRI_variable_4.format(check_field)
        arcpy.SelectLayerByAttribute_management(fl_splitproj_w_tmcdata, "NEW_SELECTION", sql_notnull)
        
        # convert the selected records into a numpy array then a pandas dataframe
        flds_df = [fld_shp_len] + speed_data_fields 
        df_spddata = utils.esri_object_to_df(fl_splitproj_w_tmcdata, flds_df)

        # remove project pieces with no speed data so their distance isn't included in weighting
        df_spddata = df_spddata.loc[pd.notnull(df_spddata[speed_data_fields[0]])].astype(float)
        
        # remove rows where there wasn't enough NPMRDS data to get a valid speed or reliability reading
        df_spddata = df_spddata.loc[df_spddata[flds_df].min(axis=1) > 0]
        
        dir_len = df_spddata[fld_shp_len].sum() #sum of lengths of project segments that intersect TMCs in the specified direction
        out_row_dict["{}_calc_len".format(direcn)] = dir_len #"calc" length because it may not be same as project length
        
        
        # go through and do conflation calculation for each TMC-based data field based on correct method of aggregation
        for field, calcmthd in fields_calc_dict.items():
            if calcmthd == params.calc_inv_avg: # See PPA documentation on how to calculated "inverted speed average" method
                sd_dict = get_wtd_speed(df_spddata, field, direcn, fld_shp_len)
                out_row_dict.update(sd_dict)
            elif calcmthd == params.calc_distwt_avg:
                fielddir = "{}{}".format(direcn, field)  # add direction tag to field names
                # if there's speed data, get weighted average value.
                linklen_w_speed_data = df_spddata[fld_shp_len].sum()
                if linklen_w_speed_data > 0: #wgtd avg = sum(piece's data * piece's len)/(sum of all piece lengths)
                    avg_data_val = (df_spddata[field]*df_spddata[fld_shp_len]).sum() \
                                    / df_spddata[fld_shp_len].sum()
    
                    out_row_dict[fielddir] = avg_data_val
                else:
                    out_row_dict[fielddir] = df_spddata[field].mean() #if no length, just return mean speed? Maybe instead just return 'no data avaialble'? Or -1 to keep as int?
                    continue
            else:
                continue

    #cleanup
    fcs_to_delete = [temp_intersctpts, temp_intrsctpt_singlpt, temp_splitprojlines, temp_splitproj_w_tmcdata]
    for fc in fcs_to_delete:
        arcpy.Delete_management(fc)
    return pd.DataFrame([out_row_dict])
    
    
def simplify_outputs(in_df, proj_len_col):
    dirlen_suffix = '_calc_len'
    
    proj_len = in_df[proj_len_col][0]
    
    re_lendir_col = '.*{}'.format(dirlen_suffix)
    lendir_cols = [i for i in in_df.columns if re.search(re_lendir_col, i)]
    df_lencols = in_df[lendir_cols]    
    
    max_dir_len = df_lencols.max(axis = 1)[0] # direction for which project has longest intersect with TMC. assumes just one record in the output
    
    #if there's less than 10% overlap in the 'highest overlap' direction, then say that the project is not on any TMCs (and any TMC data is from cross streets or is insufficient to represent the segment)
    if (max_dir_len / proj_len) < 0.1:
        out_df = pd.DataFrame([-1], columns=['SegmentSpeedData'])
        return out_df.to_dict('records')
    else:
        max_len_col = df_lencols.idxmax(axis = 1)[0] #return column name of direction with greatest overlap
        df_lencols2 = df_lencols.drop(max_len_col, axis = 1)
        secndmax_col = df_lencols2.idxmax(axis = 1)[0] #return col name of direction with second-most overlap (should be reverse of direction with most overlap)

        maxdir = max_len_col[:max_len_col.find(dirlen_suffix)] #direction name without '_calc_len' suffix
        secdir = secndmax_col[:secndmax_col.find(dirlen_suffix)]

        outcols_max = [c for c in in_df.columns if re.match(maxdir, c)]
        outcols_sec = [c for c in in_df.columns if re.match(secdir, c)]

        outcols = outcols_max + outcols_sec

        return in_df[outcols].to_dict('records')
    
def make_df(in_dict):
    re_dirn = re.compile("(.*BOUND).*") # retrieve direction
    re_metric = re.compile(".*BOUND(.*)") # retrieve name of metric
    
    df = pd.DataFrame.from_dict(in_dict, orient=g_ESRI_variable_5)
    
    col_metric = 'metric'
    col_direction = 'direction'
    
    df[col_direction] = df.index.map(lambda x: re.match(re_dirn, x).group(1))
    df[col_metric] = df.index.map(lambda x: re.match(re_metric, x).group(1))
    
    df_out = df.pivot(index=col_metric, columns=col_direction, values=0 )
    
    return df_out


def get_npmrds_data(fc_projline, str_project_type):
    arcpy.AddMessage("Calculating congestion and reliability metrics...")
    arcpy.OverwriteOutput = True

    fl_projline = g_ESRI_variable_6
    arcpy.MakeFeatureLayer_management(fc_projline, fl_projline)

    # make feature layer from speed data feature class
    fl_speed_data = g_ESRI_variable_7
    arcpy.MakeFeatureLayer_management(params.fc_speed_data, fl_speed_data)

    # make flat-ended buffers around TMCs that intersect project
    arcpy.SelectLayerByLocation_management(fl_speed_data, "WITHIN_A_DISTANCE", fl_projline, params.tmc_select_srchdist, "NEW_SELECTION")
    if str_project_type == 'Freeway':
        sql = g_ESRI_variable_8.format(params.col_roadtype, params.roadtypes_fwy)
        arcpy.SelectLayerByAttribute_management(fl_speed_data, "SUBSET_SELECTION", sql)
    else:
        sql = "{} NOT IN {}".format(params.col_roadtype, params.roadtypes_fwy)
        arcpy.SelectLayerByAttribute_management(fl_speed_data, "SUBSET_SELECTION", sql)

    # create temporar buffer layer, flat-tipped, around TMCs; will be used to split project lines
    temp_tmcbuff = os.path.join(arcpy.env.scratchGDB, "TEMP_linkbuff_4projsplit")
    fl_tmc_buff = g_ESRI_variable_9
    arcpy.Buffer_analysis(fl_speed_data, temp_tmcbuff, params.tmc_buff_dist_ft, "FULL", "FLAT")
    arcpy.MakeFeatureLayer_management(temp_tmcbuff, fl_tmc_buff)

    # get "full" table with data for all directions
    projdata_df = conflate_tmc2projline(fl_projline, params.directions_tmc, params.col_tmcdir,
                                        fl_tmc_buff, params.spd_data_calc_dict)

    # trim down table to only include outputs for directions that are "on the segment",
    # i.e., that have most overlap with segment
    out_dict = simplify_outputs(projdata_df, 'proj_length_ft')[0]

    #cleanup
    arcpy.Delete_management(temp_tmcbuff)

    return out_dict


# =====================RUN SCRIPT===========================
    
'''
if __name__ == '__main__':
    start_time = time.time()
    
    workspace = None
    arcpy.env.workspace = workspace

    project_line = "test_project_causeway_fwy" # arcpy.GetParameterAsText(0) #"NPMRDS_confl_testseg_seconn"
    proj_type = params.ptype_fwy # arcpy.GetParameterAsText(2) #"Freeway"

    test_dict = get_npmrds_data(project_line, proj_type)
    print(test_dict)

    elapsed_time = round((time.time() - start_time)/60, 1)
    print("Success! Time elapsed: {} minutes".format(elapsed_time))    
    
'''

    


