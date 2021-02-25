# --------------------------------
# Name: PPA2_masterTest.py
# Purpose: get values for the "trip shed" for freeway projects.
#
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
import pandas as pd

import ppa_input_params as p
import accessibility_calcs as acc
# import collisions as coll
# import complete_street_score as cs
# import get_buff_netmiles as bnmi
# import get_line_overlap as linex
import get_lutype_acres as luac
# import get_truck_data_fwy as truck_fwy
# import intersection_density as intsxn
import landuse_buff_calcs as lu_pt_buff
# import link_occup_data as link_occ
import mix_index_for_project as mixidx
# import npmrds_data_conflation as npmrds
# import transit_svc_measure as trnsvc
import urbanization_metrics as urbn
import ppa_utils as utils


def get_singleyr_data(fc_tripshedpoly, projtyp, adt, out_dict={}):
    print("getting accessibility data for base...")
    accdata = acc.get_acc_data(fc_tripshedpoly, p.accdata_fc, projtyp, get_ej=False)
        
    print("getting ag acreage data for base...")
    ag_acres = luac.get_lutype_acreage(fc_tripshedpoly, projtyp, p.parcel_poly_fc, p.lutype_ag)
    
    # total job + du density (base year only, for state-of-good-repair proj eval only)
    print("getting ILUT data for base...")
    job_du_dens = lu_pt_buff.point_sum_density(p.parcel_pt_fc, fc_tripshedpoly, projtyp, 
                                               [p.col_emptot, p.col_du], p.ilut_sum_buffdist)
    comb_du_dens = sum(list(job_du_dens.values()))
    job_du_dens['job_du_perNetAcre'] = comb_du_dens

    # get EJ data
    print("getting EJ data for base...")
    ej_data = lu_pt_buff.point_sum(p.parcel_pt_fc, fc_tripshedpoly, projtyp, [p.col_pop_ilut],
                                            p.ilut_sum_buffdist, p.col_ej_ind, case_excs_list=[])
    
    ej_flag_dict = {0: "Pop_NonEJArea", 1: "Pop_EJArea"}  # rename keys from 0/1 to more human-readable names
    ej_data = utils.rename_dict_keys(ej_data, ej_flag_dict)
    ej_data["Pct_PopEJArea"] = ej_data["Pop_EJArea"] / sum(list(ej_data.values()))
    
    accdata_ej = acc.get_acc_data(fc_tripshedpoly, p.accdata_fc, projtyp, get_ej=True)  # EJ accessibility data
    ej_data.update(accdata_ej)

    # for base dict, add items that only have a base year value (no future year values)
    for d in [accdata, ag_acres, job_du_dens, ej_data]:
        out_dict_base.update(d)

    outdf = pd.DataFrame.from_dict(out_dict_base, orient='index')
    
    return outdf

def get_multiyear_data(fc_tripshedpoly, projtyp, base_df, analysis_year):
    print("getting multi-year data for {}...".format(analysis_year))
    ilut_val_fields = [p.col_pop_ilut, p.col_du, p.col_emptot, p.col_k12_enr, p.col_empind, p.col_persntrip_res] \
                  + p.ilut_ptrip_mode_fields    

    fc_pcl_pt = p.parcel_pt_fc_yr(year)
    fc_pcl_poly = p.parcel_poly_fc_yr(year)

    year_dict = {}
    # get data on pop, job, k12 totals
    # point_sum(fc_pclpt, fc_tripshedpoly, projtyp, val_fields, buffdist, case_field=None, case_excs_list=[])
    ilut_buff_vals = lu_pt_buff.point_sum(fc_pcl_pt, fc_tripshedpoly, projtyp, ilut_val_fields,
                                          p.ilut_sum_buffdist, case_field=None, case_excs_list=[])

    ilut_indjob_share = {"{}_jobshare".format(p.col_empind): ilut_buff_vals[p.col_empind] / ilut_buff_vals[p.col_emptot]}
    ilut_buff_vals.update(ilut_indjob_share)

    ilut_mode_split = {"{}_share".format(modetrp): ilut_buff_vals[modetrp] / ilut_buff_vals[p.col_persntrip_res]
                       for modetrp in p.ilut_ptrip_mode_fields}
    ilut_buff_vals.update(ilut_mode_split)

    # cleanup to remove non-percentage mode split values, if we want to keep output CSV from getting too long.
    # for trip_numcol in p.ilut_ptrip_mode_fields: del ilut_buff_vals[trip_numcol]

    # job + du total
    job_du_tot = {"SUM_JOB_DU": ilut_buff_vals[p.col_du] + ilut_buff_vals[p.col_emptot]}


    # land use diversity index
    mix_index_data = mixidx.get_mix_idx(fc_pcl_pt, fc_tripshedpoly, projtyp)

    # housing type mix
    housing_mix_data = lu_pt_buff.point_sum(fc_pcl_pt, fc_tripshedpoly, projtyp, [p.col_du], p.du_mix_buffdist,
                                            p.col_housing_type, case_excs_list=['Other'])

    # acres of "natural resources" (land use type = forest or agriculture)
    nat_resources_data = urbn.nat_resources(fc_tripshedpoly, projtyp, fc_pcl_poly, year)
    # combine into dict
    for d in [ilut_buff_vals, job_du_tot, mix_index_data, housing_mix_data, nat_resources_data]:
        year_dict.update(d)

    # make dict into dataframe
    df_year_out = pd.DataFrame.from_dict(year_dict, orient='index')
    
    return df_year_out

    
if __name__ == '__main__':
    # =====================================USER/TOOLBOX INPUTS===============================================
    arcpy.env.workspace = r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb'
    arcpy.OverwriteOutput = True

    # project data
    tripshed_fc = r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb\TripShed_test_project01032020_1109'  # TripShed_test_project01032020_1109
    proj_name =  os.path.basename(tripshed_fc) # os.path.basename(tripshed_fc)
    project_type = p.ptype_area_agg  # p.ptype_fwy, p.ptype_arterial, or p.ptype_sgr
    adt = 17000
    
    # CSV of aggregate values by community type and for whole region
    aggvals_csv = r"Q:\ProjectLevelPerformanceAssessment\PPAv2\PPA2_0_code\PPA2\AggValCSVs\Agg_ppa_vals01022020_1004.csv"

    # =======================BEGIN SCRIPT==============================================================
    analysis_years = [2016, 2040]  # which years will be used.
    time_sufx = str(dt.datetime.now().strftime('%m%d%Y_%H%M'))
    output_csv = r'Q:\ProjectLevelPerformanceAssessment\PPAv2\PPA2_0_code\PPA2\ProjectValCSVs\PPA_TripShed_{}_{}.csv'.format(
        os.path.basename(tripshed_fc), time_sufx)

    out_dict_base = {"project_name": proj_name, "project_type": project_type, 'project_aadt': adt}

    # metrics that only have base year value ------------------------------------
    outdf_base = get_singleyr_data(tripshed_fc, project_type, adt, out_dict_base)

    # ---------------------------------------------------------------------------------------------------------
    # outputs that use both base year and future year values

    for year in analysis_years:
        df_year = get_multiyear_data(tripshed_fc, project_type, outdf_base, year)
        # if it's base year, then append values to bottom of outdf_base,
        # if it's future year, then left-join the values to the outdf.
        # table has metrics as rows; years as columns (and will also append     
        if year == min(analysis_years):
            out_df = outdf_base.rename(columns={0: 'tripshed_{}'.format(year)})
            df_year = df_year.rename(columns={0: 'tripshed_{}'.format(year)})
            out_df = out_df.append(df_year)
        else:
            df_year = df_year.rename(columns={0: 'tripshed_{}'.format(year)})
            out_df = out_df.join(df_year)
        
    # get community type and regional level data
    df_aggvals = pd.read_csv(aggvals_csv, index_col = 'Unnamed: 0')
    col_aggvals_year = 'year'
    cols_ctype_reg = ['REGION']
    
    for year in analysis_years:
        df_agg_yr = df_aggvals[df_aggvals[col_aggvals_year] == year]  # filter to specific year
        df_agg_yr = df_agg_yr[cols_ctype_reg]  # only include community types for community types that project is in
        df_agg_yr = df_agg_yr.rename(columns={col:'{}_{}'.format(col, year) for col in list(df_agg_yr.columns)})
        
        out_df = out_df.join(df_agg_yr)

    out_df.to_csv(output_csv)
    print("success!")


