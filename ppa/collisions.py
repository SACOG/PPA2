# Esri start of added imports
import sys, os, arcpy
# Esri end of added imports

# Esri start of added variables
g_ESRI_variable_1 = 'fl_polygon'
g_ESRI_variable_2 = 'fl_model_links'
g_ESRI_variable_3 = 'fl_selection_poly'
g_ESRI_variable_4 = 'fl_centerline'
g_ESRI_variable_5 = 'proj_fl'
g_ESRI_variable_6 = 'collision_fl'
# Esri end of added variables

# --------------------------------
# Name:collisions.py
# Purpose: calculate collision data for PPA tool based on geocoded TIMS data (tims.berkeley.edu)
#
#
# Author: Darren Conly
# Last Updated: 1/31/2020
# Updated by: <name>
# Copyright:   (c) SACOG
# Python Version: 3.x
# --------------------------------
import time
import arcpy

import ppa_input_params as params
import ppa_utils as utils


# for aggregate, polygon-based avgs (e.g., community type, whole region), use model for VMT; for
# project, the VMT will be based on combo of project length and user-entered ADT for project
def get_model_link_sums(fc_polygon, fc_model_links):
    '''For all travel model highway links that have their center within a polygon (e.g. buffer
    around a project line, or a community type, or a trip shed), sum the values for user-specified
    metrics. E.g. daily VMT for all selected intersectin model links, total lane miles on intersecting
    links, etc.'''

    sufx = int(time.perf_counter()) + 1
    fl_polygon = os.path.join('memory','fl_polygon{}'.format(sufx))
    fl_model_links = os.path.join('memory','fl_model_links{}'.format(sufx))
    
    if arcpy.Exists(fl_polygon): arcpy.Delete_management(fl_polygon)
    arcpy.MakeFeatureLayer_management(fc_polygon, fl_polygon)
    
    if arcpy.Exists(fl_model_links): arcpy.Delete_management(fl_model_links)
    arcpy.MakeFeatureLayer_management(fc_model_links, fl_model_links)

    # select model links whose centroid is within the polygon area
    arcpy.SelectLayerByLocation_management(fl_model_links, "HAVE_THEIR_CENTER_IN", fl_polygon)

    link_data_cols =[params.col_capclass, params.col_distance, params.col_lanemi, params.col_dayvmt]
    output_data_cols =[params.col_dayvmt, params.col_distance]

    # load model links, selected to be near project, into a dataframe
    df_linkdata = utils.esri_object_to_df(fl_model_links, link_data_cols)

    # get total VMT for links within the area
    out_dict = {col: df_linkdata[col].sum() for col in output_data_cols}
    return out_dict


def get_centerline_miles(selection_poly_fc, centerline_fc):
    '''Calculate centerline miles for all road links whose center is within a polygon,
    such as a buffer around a road segment, or community type, trip shed, etc.'''
    sufx = int(time.perf_counter()) + 1
    fl_selection_poly = os.path.join('memory','fl_selection_poly{}'.format(sufx))
    fl_centerline = os.path.join('memory','fl_centerline{}'.format(sufx))
    
    if arcpy.Exists(fl_selection_poly): arcpy.Delete_management(fl_selection_poly)
    arcpy.MakeFeatureLayer_management(selection_poly_fc, fl_selection_poly)
    
    if arcpy.Exists(fl_centerline): arcpy.Delete_management(fl_centerline)
    arcpy.MakeFeatureLayer_management(centerline_fc, fl_centerline)

    arcpy.SelectLayerByLocation_management(fl_centerline, "HAVE_THEIR_CENTER_IN", fl_selection_poly)

    cline_miles = 0
    with arcpy.da.SearchCursor(fl_centerline, "SHAPE@LENGTH") as cur:
        for row in cur:
            cline_miles += row[0]

    return cline_miles / params.ft2mile


def get_collision_data(fc_project, project_type, fc_colln_pts, project_adt):
    '''Inputs:
        fc_project = project line around which a buffer will be drawn for selecting collision locations
        project_type = whether it's a freeway project, arterial project, etc. Or if it is a 
        community design project.
        
        With user-entered ADT (avg daily traffic) and a point layer of collision locations, function calculates
        several key safety metrics including total collisions, collisions/100M VMT, percent bike/ped collisions, etc.'''
        
    arcpy.AddMessage("Aggregating collision data...")

    fc_model_links = params.model_links_fc()

    sufx = int(time.perf_counter()) + 1
    fl_project = g_ESRI_variable_5
    fl_colln_pts = os.path.join('memory','fl_colln_pts{}'.format(sufx))
    
    if arcpy.Exists(fl_project): arcpy.Delete_management(fl_project)
    arcpy.MakeFeatureLayer_management(fc_project, fl_project)
    
    if arcpy.Exists(fl_colln_pts): arcpy.Delete_management(fl_colln_pts)
    arcpy.MakeFeatureLayer_management(fc_colln_pts, fl_colln_pts)

    # if for project segment, get annual VMT for project segment based on user input and segment length
    df_projlen = utils.esri_object_to_df(fl_project, ["SHAPE@LENGTH"])
    proj_len_mi = df_projlen.iloc[0][0] / params.ft2mile  # return project length in miles

    # for aggregate, polygon-based avgs (e.g., community type, whole region), use model for VMT; for
    # project, the VMT will be based on combo of project length and user-entered ADT for project
    # approximate annual project VMT, assuming ADT is reflective of weekdays only, but assumes
    if project_type == params.ptype_area_agg:
        vmt_dict = get_model_link_sums(fc_project, fc_model_links)
        dayvmt = vmt_dict[params.col_dayvmt]
        ann_proj_vmt = dayvmt * 320
        proj_len_mi = get_centerline_miles(fc_project, params.reg_artcollcline_fc) # only gets for collector streets and above
    else:
        ann_proj_vmt = project_adt * proj_len_mi * 320

    # get collision totals
    searchdist = 0 if project_type == params.ptype_area_agg else params.colln_searchdist
    arcpy.SelectLayerByLocation_management(fl_colln_pts, 'WITHIN_A_DISTANCE', fl_project, searchdist)
    colln_cols =[params.col_fwytag, params.col_nkilled, params.col_bike_ind, params.col_ped_ind]
    
    df_collndata = utils.esri_object_to_df(fl_colln_pts, colln_cols)
    
    # filter so that fwy collisions don't get tagged to non-freeway projects, and vice-versa
    if project_type == params.ptype_fwy:
        df_collndata = df_collndata.loc[df_collndata[params.col_fwytag] == 1]
    elif project_type == params.ptype_area_agg:
        pass  # for aggregating at polygon level, like region or community type, we want all collisions on all roads
    else:
        df_collndata = df_collndata.loc[df_collndata[params.col_fwytag] == 0]

    total_collns = df_collndata.shape[0]
    fatal_collns = df_collndata.loc[df_collndata[params.col_nkilled] > 0].shape[0]
    bikeped_collns = df_collndata.loc[(df_collndata[params.col_bike_ind] == params.ind_val_true)
                                      | (df_collndata[params.col_ped_ind] == params.ind_val_true)].shape[0]
    pct_bikeped_collns = bikeped_collns / total_collns if total_collns > 0 else 0

    bikeped_colln_clmile = bikeped_collns / proj_len_mi

    # collisions per million VMT (MVMT) = avg annual collisions / (modeled daily VMT * 320 days) * 1,000,000
    avg_ann_collisions = total_collns / params.years_of_collndata
    avg_ann_fatalcolln = fatal_collns / params.years_of_collndata

    colln_rate_per_vmt = avg_ann_collisions / ann_proj_vmt * 100000000 if ann_proj_vmt > 0 else -1
    fatalcolln_per_vmt = avg_ann_fatalcolln / ann_proj_vmt * 100000000 if ann_proj_vmt > 0 else -1
    pct_fatal_collns = avg_ann_fatalcolln / avg_ann_collisions if avg_ann_collisions > 0 else 0

    out_dict = {"TOT_COLLISNS": total_collns, "TOT_COLLISNS_PER_100MVMT": colln_rate_per_vmt,
                "FATAL_COLLISNS": fatal_collns, "FATAL_COLLISNS_PER_100MVMT": fatalcolln_per_vmt,
                "PCT_FATAL_COLLISNS": pct_fatal_collns, "BIKEPED_COLLISNS": bikeped_collns, 
                "BIKEPED_COLLISNS_PER_CLMILE": bikeped_colln_clmile, "PCT_BIKEPED_COLLISNS": pct_bikeped_collns}

    return out_dict
