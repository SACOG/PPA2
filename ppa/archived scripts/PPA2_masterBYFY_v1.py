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
import os

import arcpy
import pandas as pd

import ppa_input_params as p
import accessibility_calcs as acc
import collisions as coll
import complete_street_score as cs
import get_buff_netmiles as bnmi
import get_line_overlap as linex
import get_lutype_acres as luac
import get_truck_data_fwy as truck_fwy
import intersection_density as intsxn
import landuse_buff_calcs as lu_pt_buff
import link_occup_data as link_occ
import mix_index_for_project as mixidx
import npmrds_data_conflation as npmrds
import transit_svc_measure as trnsvc
import urbanization_metrics as urbn


def rename_dict_keys(dict_in, new_key_dict):
    '''if dict in = {0:1} and dict out supposed to be {'zero':1}, this function renames the key accordingly per
    the new_key_dict (which for this example would be {0:'zero'}'''
    dict_out = {}
    for k, v in new_key_dict.items():
        if k in list(dict_in.keys()):
            dict_out[v] = dict_in[k]
        else:
            dict_out[v] = 0
    return dict_out


if __name__ == '__main__':
    time_sufx = str(dt.datetime.now().strftime('%m%d%Y_%H%M'))
    arcpy.env.workspace = r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb'
    arcpy.OverwriteOutput = True

    # project data
    project_fc = r'I:\Projects\Darren\PPA_V2_GIS\scratch.gdb\test_project_xmult_strt'
    proj_name = os.path.basename(project_fc)
    project_type = p.ptype_arterial  # p.ptype_fwy, p.ptype_arterial, or p.ptype_sgr
    adt = 17000
    project_speedlim = 30
    pci = 60  # pavement condition index, will be user-entered value

    output_csv = r'Q:\ProjectLevelPerformanceAssessment\PPAv2\PPA2_0_code\PPA2\ProjectValCSVs\PPA_{}_{}.csv'.format(
        os.path.basename(project_fc), time_sufx)

    # outputs for calling functions, NO future year version; base year only------------------------------------
    accdata = acc.get_acc_data(project_fc, p.accdata_fc, project_type, get_ej=False)
    collision_data = coll.get_collision_data(project_fc, project_type, p.collisions_fc, adt)

    complete_street_score = {'complete_street_score': -1} if project_type == p.ptype_fwy else \
        cs.complete_streets_idx(p.parcel_pt_fc, project_fc, project_type, project_speedlim, p.trn_svc_fc)
    truck_route_pct = {'pct_proj_STAATruckRoutes': 1} if project_type == p.ptype_fwy else \
        linex.get_line_overlap(project_fc, p.freight_route_fc, p.freight_route_fc) # all freeways are STAA truck routes
    ag_acres = luac.get_lutype_acreage(project_fc, p.parcel_poly_fc, p.lutype_ag)
    pct_adt_truck = {"pct_truck_aadt": -1} if project_type != p.ptype_fwy else truck_fwy.get_tmc_truck_data(project_fc, project_type)
    intersxn_data = intsxn.intersection_density(project_fc, p.intersections_base_fc, project_type)
    npmrds_data = npmrds.get_npmrds_data(project_fc, project_type)
    transit_data = trnsvc.transit_svc_density(project_fc, p.trn_svc_fc, project_type)
    bikeway_data = bnmi.get_bikeway_mileage_share(project_fc, p.ptype_sgr)
    infill_status = urbn.projarea_infill_status(project_fc, p.comm_types_fc)
    
    # total job + du density (base year only, for state-of-good-repair proj eval only)
    job_du_dens = lu_pt_buff.point_sum_density(p.parcel_pt_fc, project_fc, project_type, 
                                               [p.col_emptot, p.col_du], p.ilut_sum_buffdist)
    comb_du_dens = sum(list(job_du_dens.values()))
    job_du_dens['job_du_perAcre'] = comb_du_dens

    # get EJ data
    ej_data = lu_pt_buff.point_sum(p.parcel_pt_fc, project_fc, project_type, [p.col_pop_ilut],
                                            p.ilut_sum_buffdist, p.col_ej_ind, case_excs_list=[])
    
    ej_flag_dict = {0: "Pop_NonEJArea", 1: "Pop_EJArea"}  # rename keys from 0/1 to more human-readable names
    ej_data = rename_dict_keys(ej_data, ej_flag_dict)
    ej_data["Pct_PopEJArea"] = ej_data["Pop_EJArea"] / sum(list(ej_data.values()))
    
    accdata_ej = acc.get_acc_data(project_fc, p.accdata_fc, project_type, get_ej=True)  # EJ accessibility data
    ej_data.update(accdata_ej)


    # ---------------------------------------------------------------------------------------------------------
    # outputs that use both base year and future year values--MIGHT WANT TO MAKE SEPARATE SCRIPT-----------------
    #get data on pop, job, k12 totals
    ilut_val_fields = [p.col_pop_ilut, p.col_du, p.col_emptot, p.col_k12_enr, p.col_empind, p.col_persntrip_res] \
                      + p.ilut_ptrip_mode_fields

    # point_sum(fc_pclpt, fc_project, project_type, val_fields, buffdist, case_field=None, case_excs_list=[])
    ilut_buff_vals = lu_pt_buff.point_sum(p.parcel_pt_fc, project_fc, project_type, ilut_val_fields,
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


    # model-based vehicle occupancy
    veh_occ_data = link_occ.get_linkoccup_data(project_fc, p.ptype_arterial, p.model_links_fc)

    # land use diversity index
    mix_index_data = mixidx.get_mix_idx(p.parcel_pt_fc, project_fc, p.ptype_arterial)

    # housing type mix
    housing_mix_data = lu_pt_buff.point_sum(p.parcel_pt_fc, project_fc, project_type, [p.col_du], p.du_mix_buffdist,
                                            p.col_housing_type, case_excs_list=['Other'])

    # acres of "natural resources" (land use type = forest or agriculture)
    nat_resources_data = urbn.nat_resources(project_fc, p.parcel_poly_fc, 2016)

    # combine all together-----------------------------------------------------------

    out_dict = {"project_name": proj_name, "project_type": project_type, 'project_aadt': adt, 'project_pci': pci,
                'project_speedlim': project_speedlim}
    for d in [accdata, collision_data, complete_street_score, truck_route_pct, pct_adt_truck, ag_acres, intersxn_data,
              npmrds_data, ilut_buff_vals, job_du_dens, ej_data, veh_occ_data, transit_data, mix_index_data,
              housing_mix_data, bikeway_data, infill_status, nat_resources_data]:
        out_dict.update(d)

    outdf = pd.DataFrame.from_dict(out_dict, orient='index')
    outdf.to_csv(output_csv)
    arcpy.AddMessage("success!")


