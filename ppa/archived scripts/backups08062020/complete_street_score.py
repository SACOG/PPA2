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
import arcpy

import ppa_input_params as params
import landuse_buff_calcs as lubuff
import transit_svc_measure as ts


def complete_streets_idx(fc_pclpt, fc_project, project_type, posted_speedlim, transit_event_fc):
    '''Calculate complete street index (CSI) for project
        CSI = (students/acre + daily transit vehicle stops/acre + BY jobs/acre + BY du/acre) * (1-(posted speed limit - threshold speed limit)*speed penalty factor)
        '''
    # don't give complete street score for freeway projects or if sponsor didn't enter speed limit
    if project_type == params.ptype_fwy or posted_speedlim <= 1: 
        csi = -1
    else:
        arcpy.AddMessage("Calculating complete street score...")
    
        # get transit service density around project
        tran_stops_dict = ts.transit_svc_density(fc_project, transit_event_fc, project_type)
        transit_svc_density = list(tran_stops_dict.values())[0]
    
        lu_fac_cols = [params.col_area_ac, params.col_k12_enr, params.col_emptot, params.col_du]
        lu_vals_cols = [params.col_k12_enr, params.col_emptot, params.col_du]
    
        # get sums of the lu_fac_cols within project buffer area
        lu_vals_dict = lubuff.point_sum(fc_pclpt, fc_project, project_type, lu_fac_cols, params.cs_buffdist)
    
        #dens_score = (student_dens + trn_svc_dens + job_dens + du_dens)
        dens_score = sum([lu_vals_dict[i] / lu_vals_dict[params.col_area_ac] for i in lu_vals_cols]) + transit_svc_density
    
        csi = dens_score * (1 - (posted_speedlim - params.cs_threshold_speed) * params.cs_spd_pen_fac)

    out_dict = {'complete_street_score': csi}
    
    return out_dict


# if __name__ == '__main__':
#     arcpy.env.workspace = None

#     # input fc of parcel data--must be points!
#     in_pcl_pt_fc = "parcel_data_2016_11062019_pts"
#     value_fields = [params.col_area_ac, params.col_k12_enr, params.col_emptot, params.col_du]
#     posted_speedlimit = 30 # mph
#     ptype = params.ptype_fwy

#     # input line project for basing spatial selection
#     project_fc = None
#     trnstops_fc = 'transit_stoplocn_w_eventcount_2016'


#     output_dict = complete_streets_idx(in_pcl_pt_fc, project_fc, ptype, posted_speedlimit, trnstops_fc)
#     print(output_dict)

