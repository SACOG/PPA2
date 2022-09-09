# -*- coding: utf-8 -*-
#

# Esri start of added imports
import sys, os, arcpy
# Esri end of added imports

# Esri start of added variables
g_ESRI_variable_1 = 'fl_parcel'
g_ESRI_variable_2 = 'fl_project'
# Esri end of added variables

#--------------------------------
# Name:calc_mix_index_sacog.py
# Purpose: calculate the mix index for PPA, with emphasis on measuring how
#          conducive the land use mix is to replacing drive trips with walk
   #        trips due to daily needs like retail, schools, etc. being within walk 
#            or short drive distance. Default is based on 1mi buffer around project.        

# Author: Darren Conly
# Last Updated: 11/2019
# Updated by: <name>
# Copyright:   (c) SACOG
# Python Version: 3.x
# --------------------------------
import time
import pandas as pd
import arcpy

import ppa_input_params as params
import ppa_utils as utils

# =============FUNCTIONS=============================================


def make_summary_df(in_fl, input_cols,  landuse_cols, col_hh, park_calc_dict):

    # load into dataframe
    parcel_df = utils.esri_object_to_df(in_fl, input_cols)

    col_parkac = park_calc_dict['park_acres_field']
    col_lutype = park_calc_dict['lutype_field']
    lutype_parks = park_calc_dict['park_lutype']
    col_area_ac = park_calc_dict['area_field']

    # add col for park acres, set to total parcel acres where land use type is parks/open space land use type
    parcel_df.loc[(parcel_df[col_lutype] == lutype_parks), col_parkac] = parcel_df[col_area_ac]

    cols = landuse_cols + [col_hh]
    out_df = pd.DataFrame(parcel_df[cols].sum(axis = 0)).T

    return out_df


def get_wtd_idx(x, facs, params_df):
    output = 0
    
    for fac in facs:
        fac_ratio = '{}_ratio'.format(fac)
        fac_out = x[fac_ratio] * params_df.loc[fac]['weight']
        output += fac_out
    
    return output
        

def calc_mix_index(in_df, params_df, hh_col, lu_factor_cols, mix_idx_col):
    lu_facs = params_df.index
    
    for fac in lu_facs:
        
        # add column for the "ideal", or "balanced" ratio of that land use to HHs
        bal_col = "{}_bal".format(fac) 
        in_df.loc[in_df[hh_col] != 0, bal_col] = in_df[hh_col] * params_df.loc[fac]['bal_ratio_per_hh']
        
        # if no HH, set bal_col = -1
        in_df.fillna(-1)
        
        ratio_col = "{}_ratio".format(fac)
        
        # if balance value > actual value, return actual value / balance value
        in_df.loc[(in_df[hh_col] != 0) & (in_df[bal_col] > in_df[fac]), ratio_col] = in_df[fac] / in_df[bal_col]
    
        # if balance value < actual value, return balance value / actual value
        in_df.loc[(in_df[hh_col] != 0) & (in_df[bal_col] < in_df[fac]), ratio_col] = in_df[bal_col] / in_df[fac]
        
        # if no HH, set ratio col = -1
        in_df.fillna(-1)
        
    in_df[mix_idx_col] = in_df.apply(lambda x: get_wtd_idx(x, lu_facs, params_df), axis = 1)
    
    return in_df


def get_mix_idx(fc_parcel, fc_project, project_type):
    arcpy.AddMessage("Calculating mix index...")

    sufx = int(time.perf_counter()) + 1
    fl_parcel = os.path.join('memory','fl_parcel{}'.format(sufx))
    fl_project = g_ESRI_variable_2

    if arcpy.Exists(fl_parcel): arcpy.Delete_management(fl_parcel)
    arcpy.MakeFeatureLayer_management(fc_parcel, fl_parcel)
    
    if arcpy.Exists(fl_project): arcpy.Delete_management(fl_project)
    arcpy.MakeFeatureLayer_management(fc_project, fl_project)

    in_cols = [params.col_parcelid, params.col_hh, params.col_k12_enr, params.col_emptot, params.col_empfood,
               params.col_empret, params.col_empsvc, params.col_area_ac, params.col_lutype]

    lu_fac_cols = [params.col_k12_enr, params.col_emptot, params.col_empfood, params.col_empret, params.col_empsvc, params.col_parkac]
    # make parcel feature layer

    buffer_dist = 0 if project_type == params.ptype_area_agg else params.mix_index_buffdist
    arcpy.SelectLayerByLocation_management(fl_parcel, "WITHIN_A_DISTANCE", fl_project, buffer_dist, "NEW_SELECTION")

    summ_df = make_summary_df(fl_parcel, in_cols, lu_fac_cols, params.col_hh, params.park_calc_dict)

    out_df = calc_mix_index(summ_df, params.params_df, params.col_hh, lu_fac_cols, params.mix_idx_col)

    # if you want to make CSV.
    #out_df[[col_hh, mix_idx_col]].to_csv(out_csv, index = False)
    #print("Done! Output CSV: {}".format(out_csv))

    out_val = out_df[params.mix_idx_col][0]
    return {params.mix_idx_col: out_val}

# ===============================SCRIPT=================================================

'''
if __name__ == '__main__':
    
    arcpy.env.workspace = None
    
    # input fc of parcel data--must be points!
    in_pcl_pt_fc = params.parcel_pt_fc_yr(in_year=2016)

    # input line project for basing spatial selection
    project_fc = None

    buff_dist_ft = params.mix_index_buffdist  # distance in feet--MIGHT NEED TO BE ADJUSTED FOR WGS 84--SEE OLD TOOL FOR HOW THIS WAS RESOLVED

    out_dict = get_mix_idx(in_pcl_pt_fc, project_fc, params.ptype_arterial)

    print(out_dict)
    
 '''   


