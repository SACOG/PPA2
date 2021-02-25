# --------------------------------
# Name: complete_street_score.py
# Purpose: Calculate complete street index (CSI) for project, which is proxy 
#       to describe how beneficial complete streets treatments would be for the project segment.
#
# Author: Darren Conly
# Last Updated: <date>
# Updated by: <name>
# Copyright:   (c) SACOG
# Python Version: 3.x
# --------------------------------
import datetime as dt
import os

import arcpy

import ppa_input_params as params
import landuse_buff_calcs as lubuff
import transit_svc_measure as ts

    
def complete_streets_idx(fc_pclpt, fc_project, project_type, posted_speedlim, transit_event_fc):
    '''Calculate complete street index (CSI) for project
        CSI = (students/acre + daily transit vehicle stops/acre + BY jobs/acre + BY du/acre) * (1-(posted speed limit - threshold speed limit)*speed penalty factor)
        '''
    # col_area_ac
    # col_k12_enr
    # col_emptot
    # col_du
    # cs_buffdist
    # cs_threshold_speed
    # cs_spd_pen_fac
    
    
    # don't give complete street score for freeway projects or if sponsor didn't enter speed limit
    if project_type == params.ptype_fwy or posted_speedlim <= 1: 
        csi = -1
    else:
        # arcpy.AddMessage("Calculating complete street score...")
    
        # get transit service density around project
        tran_stops_dict = ts.transit_svc_density(fc_project, transit_event_fc, project_type)
        transit_svc_density = list(tran_stops_dict.values())[0]
    
        lu_fac_cols = [params.col_area_ac, params.col_k12_enr, params.col_emptot, params.col_du]
        lu_vals_cols = [params.col_k12_enr, params.col_emptot, params.col_du]
    
        # get sums of the lu_fac_cols within project buffer area
        lu_vals_dict = lubuff.point_sum(fc_pclpt, fc_project, project_type, lu_fac_cols, params.cs_buffdist)
        print(lu_vals_dict)
    
        #dens_score = (student_dens + trn_svc_dens + job_dens + du_dens)
        if lu_vals_dict[params.col_area_ac] == 0:
            dens_score = 0
        else:
            dens_score = sum([lu_vals_dict[i] / lu_vals_dict[params.col_area_ac] for i in lu_vals_cols]) + transit_svc_density
    
        csi = dens_score * (1 - (posted_speedlim - params.cs_threshold_speed) * params.cs_spd_pen_fac)

    out_dict = {'complete_street_score': csi}
    
    return out_dict

def make_fc_with_csi(network_fc, transit_event_fc, fc_pclpt, project_type):
    start_time = dt.datetime.now()
    
    fld_oid = "OBJECTID"
    fld_geom = "SHAPE@"
    fld_strtname = "FULLSTREET"
    fld_spd = "SPEED"
    fld_len = "SHAPE@LENGTH"
    fld_csi = "CompltStreetIdx"
    
    fields = [fld_geom, fld_strtname, fld_spd, fld_len, fld_oid]
    
    time_sufx = str(dt.datetime.now().strftime('%m%d%Y%H%M'))
    output_fc = "CompleteStreetMap{}".format(time_sufx)
    
    arcpy.CreateFeatureclass_management(arcpy.env.workspace, output_fc,"POLYLINE", spatial_reference = 2226)
    
    arcpy.AddField_management(output_fc, fld_strtname, "TEXT")
    arcpy.AddField_management(output_fc, fld_spd, "SHORT")
    arcpy.AddField_management(output_fc, fld_csi, "FLOAT")
    
    
    fl_network = "fl_network"
    if arcpy.Exists(fl_network): arcpy.Delete_management(fl_network)
    arcpy.MakeFeatureLayer_management(network_fc, fl_network)
    
    print("inserting rows...")
    with arcpy.da.InsertCursor(output_fc, [fld_geom, fld_strtname, fld_spd, fld_csi]) as inscur:
        with arcpy.da.SearchCursor(fl_network, fields) as cur:
            for i, row in enumerate(cur):
                if i % 1000 == 0:
                    print("{} rows processed".format(i))
                geom = row[0]
                stname = row[1]
                speedlim = row[2]
                # seglen = row[3]
                oid = row[4]
                
                sql = "{} = {}".format(fld_oid, oid) # BIG PROBLEM = THE LAND USE BUFF CALCS TAKES IN A FEATURE CLASS, NOT A FEATURE SO THIS NEEDS TO BE FIXED
                arcpy.SelectLayerByAttribute_management(fl_network, "NEW_SELECTION", sql)
                fc_features = arcpy.GetCount_management(network_fc)[0]
                print("{} features in input network FC are selected".format(fc_features))
                
                csi_dict = complete_streets_idx(network_fc, geom, project_type, speedlim, transit_event_fc)
                csi = csi_dict['complete_street_score']
                
                ins_row = [geom, stname, speedlim, csi]
                inscur.insertRow(ins_row)
    time_elapsed = dt.datetime.now() - start_time
    print("Finished! Processed {} rows in {}".format(i, time_elapsed))
        


if __name__ == '__main__':
    arcpy.env.workspace = r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb'

    # input fc of parcel data--must be points!
    in_pcl_pt_fc = os.path.join(params.fgdb, params.parcel_pt_fc_yr(in_year=2016))
    value_fields = [params.col_area_ac, params.col_k12_enr, params.col_emptot, params.col_du]
    posted_speedlimit = 30 # mph
    ptype = 'Arterial'

    # input line project for basing spatial selection
    input_network_fc = 'ArterialCollector_2019_sample'
    trnstops_fc = os.path.join(params.fgdb, params.trn_svc_fc)


    # output_dict = complete_streets_idx(in_pcl_pt_fc, project_fc, ptype, posted_speedlimit, trnstops_fc)
    make_fc_with_csi(input_network_fc, trnstops_fc, in_pcl_pt_fc, ptype)
    

