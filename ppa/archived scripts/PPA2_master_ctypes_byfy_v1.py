# --------------------------------
# Name: PPA2_masterTest.py
# Purpose: testing master script to call can combine all PPA modules
#
#
# Author: Darren Conly
# Last Updated: <date>
# Updated by: <name>
# Copyright:   (c) SACOG
# Python Version: 3.x
# --------------------------------
import datetime as dt

import arcpy
import pandas as pd

import ppa_input_params as p
import accessibility_calcs as acc
import collisions as coll
import get_buff_netmiles as bufnet
import intersection_density as intsxn
import landuse_buff_calcs as lubuff
import mix_index_for_project as mixidx

import transit_svc_measure as trn_svc


def get_poly_avg(input_poly_fc):
    # as of 11/26/2019, each of these outputs are dictionaries
    accdata = acc.get_acc_data(input_poly_fc, p.accdata_fc, p.ptype_area_agg, get_ej=False)
    collision_data = coll.get_collision_data(input_poly_fc, p.ptype_area_agg, p.collisions_fc, 0)
    mix_data = mixidx.get_mix_idx(p.parcel_pt_fc, input_poly_fc, p.ptype_area_agg)
    intsecn_dens = intsxn.intersection_density(input_poly_fc, p.intersections_base_fc, p.ptype_area_agg)
    bikeway_covg = bufnet.get_bikeway_mileage_share(input_poly_fc, p.ptype_area_agg)
    tran_stop_density = trn_svc.transit_svc_density(input_poly_fc, p.trn_svc_fc, p.ptype_area_agg)

    emp_ind_wtot = lubuff.point_sum(p.parcel_pt_fc, input_poly_fc, p.ptype_area_agg, [p.col_empind, p.col_emptot], 0)
    emp_ind_pct = {'emp_ind_pct': emp_ind_wtot[p.col_empind] / emp_ind_wtot[p.col_emptot]}

    pop_x_ej = lubuff.point_sum(p.parcel_pt_fc, input_poly_fc, p.ptype_area_agg, [p.col_pop_ilut], 0, p.col_ej_ind)
    pop_tot = sum(pop_x_ej.values())
    pct_pop_ej = {'pct_ej_pop': pop_x_ej[1] / pop_tot}

    job_pop_dens = lubuff.point_sum_density(p.parcel_pt_fc, input_poly_fc, p.ptype_area_agg, \
                                            [p.col_du, p.col_emptot], 0)
    total_dens = {"job_du_dens_ac": sum(job_pop_dens.values())}

    out_dict = {}
    for d in [accdata, collision_data, mix_data, intsecn_dens, bikeway_covg, tran_stop_density, pct_pop_ej,\
              emp_ind_pct, total_dens]:
        out_dict.update(d)

    return out_dict

def poly_avg_futyears(input_poly_fc, data_year): #IDEALLY could make this part of get_poly_avg as single function with variable number of input args
    mix_data = mixidx.get_mix_idx(p.parcel_pt_fc_yr(data_year), input_poly_fc, p.ptype_area_agg)    
    return mix_data


if __name__ == '__main__':
    time_sufx = str(dt.datetime.now().strftime('%m%d%Y_%H%M'))
    arcpy.env.workspace = r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb'
    arcpy.OverwriteOutput = True
    base_year = 2016
    future_year = 2040
    
    # fc of community type polygons
    ctype_fc = p.comm_types_fc
    output_csv = r'Q:\ProjectLevelPerformanceAssessment\PPAv2\PPA2_0_code\PPA2\AggValCSVs\Agg_ppa_vals{}.csv'.format(time_sufx)
    
    test_run = True
    
    # ------------------SELDOM-CHANGED INPUTS-----------------------------------------

    # fl_ctype = 'fl_ctype'
    # arcpy.MakeFeatureLayer_management(ctype_fc, fl_ctype)

    # loop through each feature in ctype fc, make a temp fc of it, run the calcs on that fc
    # get list of ctypes to search/loop through
    region = 'REGION'
    
    ctypes_list = []

    with arcpy.da.SearchCursor(ctype_fc, [p.col_ctype]) as cur:
        for row in cur:
            ctypes_list.append(row[0])
            
    if test_run:
        ctypes_list = ['Urban core']

    base_out_dict = {}
    fy_out_dict = {}
    # for each ctype, select polygon feature from cytpes fc and export to temporary single feature fc
    for ctype in ctypes_list:
        arcpy.AddMessage("\ngetting aggregate values for {} community type".format(ctype))
        temp_poly_fc = 'TEMP_ctype_fc'
        temp_poly_fc_fp = 'memory/{}'.format(temp_poly_fc)

        sql = "{} = '{}'".format(p.col_ctype, ctype)
        # arcpy.SelectLayerByAttribute_management(fl_ctype, "NEW_SELECTION", sql)
        if arcpy.Exists(temp_poly_fc_fp):
            arcpy.Delete_management(temp_poly_fc_fp)
        arcpy.FeatureClassToFeatureClass_conversion(ctype_fc, 'memory', temp_poly_fc, sql)

        # on that temp fc, run the PPA tools, but SET BUFFER DISTANCES TO ZERO SOMEHOW
        # this will return a dict with all numbers for that ctype
        poly_dict = get_poly_avg(temp_poly_fc_fp)
        
        base_out_dict[ctype] = poly_dict
        # for all keys in the output dict, add a tag to the key value to indicate community type
        # append it to a master dict
        
        ##---------future year data-----------------------------------------------
        print("calculating numbers for future year for {} community type...".format(ctype))

        fy_vals_dict = poly_avg_futyears(temp_poly_fc_fp, future_year) #get future-year data--IDEALLY would make refer to list of future years
    
        fy_out_dict[ctype] = fy_vals_dict

    print("getting regional aggregate values...")
    base_out_dict[region] = get_poly_avg(p.region_fc)
    
    # for now, don't do FY mix index for region because base-year region LU mix is the basis for the
    # mix index values. If you want to get regional mix index for FY you'd need
    # to recalculate for the future year.
    # fy_out_dict[region] = poly_avg_futyears(p.region_fc, future_year)

    base_df = pd.DataFrame.from_dict(base_out_dict, orient='columns')
    fy_df = pd.DataFrame.from_dict(fy_out_dict, orient='columns')

    
    out_df = base_df.join(fy_df, rsuffix = future_year)
    out_df.to_csv(output_csv)
    arcpy.AddMessage("summary completed as {}".format(output_csv))


