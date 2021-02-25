# Esri start of added imports
import sys, os, arcpy
# Esri end of added imports

# Esri start of added variables
g_ESRI_variable_1 = 'proj_fl'
g_ESRI_variable_2 = 'modlink_fl'
# Esri end of added variables

# --------------------------------
# Name:collisions.py
# Purpose: calculate collision data for PPA tool.
#
#
# Author: Darren Conly
# Last Updated: <date>
# Updated by: <name>
# Copyright:   (c) SACOG
# Python Version: 3.x
# --------------------------------
import pandas as pd
import arcpy

import ppa_input_params as params
import ppa_utils as utils


def link_vehocc(row):
    vol_sov = row[params.col_sovvol]
    vol_hov2 = row[params.col_hov2vol]
    vol_hov3 = row[params.col_hov3vol]
    vol_commveh = row[params.col_daycommvehvol]
    total_veh_vol = sum([vol_sov, vol_hov2, vol_hov3, vol_commveh])

    out_row = (vol_commveh + vol_sov + vol_hov2 * params.fac_hov2 + vol_hov3 * params.fac_hov3) / total_veh_vol
    return out_row


def get_wtdavg_vehocc(in_df):

    col_wtdvol = 'col_wtdvol'
    in_df = in_df.loc[in_df[params.col_dayvehvol] > 0]  # exclude links with daily volume of zero.
    in_df[col_wtdvol] = in_df.apply(lambda x: link_vehocc(x), axis = 1)

    sumprod = in_df[params.col_lanemi].dot(in_df[col_wtdvol])
    lanemi_tot = in_df[params.col_lanemi].sum()
    output_val = sumprod / lanemi_tot

    return output_val


def get_wtdavg_vehvol(in_df, col_vehtype):

    sumprod = in_df[params.col_lanemi].dot(in_df[col_vehtype]) # sum product of lanemi * volume, for the occupancy class (sov, hov2, hov3+)
    lanemi_tot = in_df[params.col_lanemi].sum()
    output_vehvol = sumprod / lanemi_tot  # lanemi-weighted average volume for the occupancy class

    return output_vehvol


def get_linkoccup_data(fc_project, project_type, fc_model_links):
    arcpy.AddMessage("Getting modeled vehicle occupancy data...")
    fl_project = g_ESRI_variable_1
    fl_model_links = g_ESRI_variable_2

    arcpy.MakeFeatureLayer_management(fc_project, fl_project)
    arcpy.MakeFeatureLayer_management(fc_model_links, fl_model_links)

    # get model links that are on specified link type with centroid within search distance of project
    arcpy.SelectLayerByLocation_management(fl_model_links, 'HAVE_THEIR_CENTER_IN', fl_project, params.modlink_searchdist)

    # load data into dataframe then subselect only ones that are on same road type as project (e.g. fwy vs. arterial)
    df_cols = [params.col_capclass, params.col_lanemi, params.col_tranvol, params.col_dayvehvol, params.col_sovvol, params.col_hov2vol, params.col_hov3vol,
               params.col_daycommvehvol]
    df_linkdata = utils.esri_object_to_df(fl_model_links, df_cols)

    if project_type == params.ptype_fwy:
        df_linkdata = df_linkdata.loc[df_linkdata[params.col_capclass].isin(params.capclasses_fwy)]
    else:
        df_linkdata = df_linkdata.loc[df_linkdata[params.col_capclass].isin(params.capclass_arterials)]

    df_trnlinkdata = df_linkdata.loc[pd.notnull(df_linkdata[params.col_tranvol])]
    avg_proj_trantrips = get_wtdavg_vehvol(df_trnlinkdata, params.col_tranvol) if df_trnlinkdata.shape[0] > 0 else 0
    avg_proj_vehocc = get_wtdavg_vehocc(df_linkdata) if df_linkdata.shape[0] > 0 else 0

    out_dict = {"avg_2way_trantrips": avg_proj_trantrips, "avg_2way_vehocc": avg_proj_vehocc}

    return out_dict

'''
if __name__ == '__main__':
    arcpy.env.workspace = None

    proj_line_fc = None
    model_link_fc = 'model_links_2016'
    proj_type = params.ptype_arterial

    output = get_linkoccup_data(proj_line_fc, proj_type, model_link_fc)

    print(output)
    '''
