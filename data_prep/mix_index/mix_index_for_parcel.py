# -*- coding: utf-8 -*-
#--------------------------------
# Name:calc_mix_index_sacog.py
# Purpose: calculate the mix index for PPA, with emphasis on measuring how
#          conducive the land use mix is to replacing drive trips with walk
   #        trips due to daily needs like retail, schools, etc. being within walk distance           

# Author: Darren Conly
# Last Updated: <date>
# Updated by: <name>
# Copyright:   (c) SACOG
# Python Version: 3.x
#--------------------------------

import pandas as pd
#import arcpy
#from arcgis.features import GeoAccessor, GeoSeriesAccessor


#=============FUNCTIONS=============================================

def get_wtd_idx(x, facs, params_df):
    output = 0
    
    for fac in facs:
        fac_ratio = '{}_ratio'.format(fac)
        fac_out = x[fac_ratio] * params_df.loc[fac]['weight']
        output += fac_out
    
    return output
        
    
    

def calc_mix_index(in_df, params_csv, hh_col, lu_factor_cols):
    
    params_df = pd.read_csv(params_csv, index_col = 'lu_fac')
    
    lu_facs = params_df.index
    
    for fac in lu_facs:
        
        #add column for the "ideal", or "balanced" ratio of that land use to HHs
        bal_col = "{}_bal".format(fac) 
        in_df.loc[in_df[hh_col] != 0, bal_col] = in_df[hh_col] * params_df.loc[fac]['bal_ratio_per_hh']
        
        #if no HH, set bal_col = -1
        in_df.fillna(-1)
        
        ratio_col = "{}_ratio".format(fac)
        
        #if balance value > actual value, return actual value / balance value
        in_df.loc[(in_df[hh_col] != 0) & (in_df[bal_col] > in_df[fac]), ratio_col] = in_df[fac] / in_df[bal_col]
    
        #if balance value < actual value, return balance value / actual value
        in_df.loc[(in_df[hh_col] != 0) & (in_df[bal_col] < in_df[fac]), ratio_col] = in_df[bal_col] / in_df[fac]
        
        #if no HH, set ratio col = -1
        in_df.fillna(-1)
        
    in_df['mix_index_1mi'] = in_df.apply(lambda x: get_wtd_idx(x, lu_facs, params_df), axis = 1)
    
    return in_df

def do_work(in_csv, out_csv, params_csv, input_cols, landuse_cols, col_k12_enr, 
            col_stugrd, col_stuhgh, col_hh):
    parcel_df = pd.read_csv(in_csv, usecols = input_cols)
    parcel_df[col_k12_enr] = parcel_df[col_stugrd] + parcel_df[col_stuhgh]
    
    out_df = calc_mix_index(parcel_df, params_csv, col_hh, lu_fac_cols)
    out_df[[col_parcelid, col_hh, 'mix_index_1mi']].to_csv(out_csv, index = False)
    print("Done! Output CSV: {}".format(out_csv))

#===============================SCRIPT=================================================

if __name__ == '__main__':
    
    #arcpy.env.workspace = r'Q:\SACSIM19\Integration Data Summary\ILUT GIS\ILUT GIS.gdb'
    
    #input csv/txt of parcel data
    in_pcl_csv = r"I:\Projects\Darren\PPA_V2_GIS\SACSIM Model Data\parcel_16_buf_flat_testSample.txt"    
    
    # weighting values {land use:[optimal ratio per household, weight given to that ratio]}
    mix_idx_params_csv = r"Q:\ProjectLevelPerformanceAssessment\PPAv2\PPA2_0_code\PrepDataInputs\mix_idx_params.csv"
    
    # output csv for testing
    out_csv = r'C:\Users\dconly\PPA_TEMPFILES\test_mixindex_out.csv'
    

    #input columns
    col_parcelid = 'parcelid'
    col_hh = 'hh_2'
    col_stugrd = 'stugrd_2'
    col_stuhgh = 'stuhgh_2'
    col_emptot = 'emptot_2'
    col_empfood = 'empfoo_2'
    col_empret = 'empret_2'
    col_empsvc = 'empsvc_2'
    col_parkac = 'aparks_2'
    col_k12_enr = 'k12_enr'
    
    in_cols = [col_parcelid, col_hh, col_stugrd, col_stuhgh, col_emptot, col_empfood,
               col_empret, col_empsvc, col_parkac]
    
    lu_fac_cols = [col_k12_enr, col_emptot, col_empfood,
               col_empret, col_empsvc, col_parkac]
    
    #=====================================================================
    do_work(in_pcl_csv, out_csv, mix_idx_params_csv, in_cols, lu_fac_cols, col_k12_enr, 
            col_stugrd, col_stuhgh, col_hh)

    
    
    

