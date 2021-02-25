# -*- coding: utf-8 -*-
"""
Created on Wed Dec 11 13:46:21 2019

@author: dconly
"""
import os
import datetime as dt

import pandas as pd
import arcpy

import ppa_input_params as p
import PPA2_masterBYFY_tripshed as tripshed

def make_tripdata_df(in_files):
    # if single CSV, read in to pandas df; if multiple CSVs, read sequentially and append together into single df
    if type(in_files) == 'str':
        out_df = pd.read_csv(in_files)
    else:
        out_df = pd.read_csv(in_files[0])
        for file in in_files[1:]:
            out_df2 = pd.read_csv(file)
            out_df = out_df.append(out_df2)
    
    return out_df


def make_fl_conditional(fc, fl):
    if arcpy.Exists(fl):
        arcpy.Delete_management(fl)
    arcpy.MakeFeatureLayer_management(fc, fl)
    

def esri_field_exists(in_tbl, field_name):
    fields = [f.name for f in arcpy.ListFields(in_tbl)]
    if field_name in fields:
        return True
    else:
        return False


# make dataframe summarizing items by desired polygon ID field (e.g. trips by block group ID)
def get_poly_data(in_df, val_field, agg_fxn, groupby_field, case_field=None):
    
    col_sov = 'PRIVATE_AUTO'
    col_hov = 'CARPOOL'
    col_commveh = 'COMMERCIAL'
    col_tnc = 'ON_DEMAND_AUTO'
    col_walk = 'WALKING'
    col_bike = 'BICYCLE'
    col_transit = 'PUBLIC_TRANSPORT'
    
    col_tottrips = 'tot_trips'
    col_pcttrips = 'pct_of_trips'
    col_trippctlrank = 'trips_pctlrank'
    
    allmodes = [col_sov, col_hov, col_commveh, col_tnc, col_walk, col_bike, col_transit]
    
    piv = in_df.pivot_table(values=val_field, index=groupby_field, columns=case_field, 
                            aggfunc=agg_fxn)
    piv = piv.reset_index()
    
    tblmodes = [mode for mode in allmodes if mode in piv.columns]
    
    piv[col_tottrips] = piv[tblmodes].sum(axis=1)  # count of trips in each poly
    piv[col_pcttrips] = piv[col_tottrips] / piv[col_tottrips].sum()  # pct of total trips from each poly
    
    # percentile rank of each poly in terms of how many trips it produces
    # e.g., 100th percentile means the poly makes more trips than any of the other polys
    piv[col_trippctlrank] = piv[col_tottrips].rank(method='min', pct=True)

    return piv

# filter input polygon set to only retrieve polygons that capture some majority share (cutoff share, e.g., 90%)of the total trips
# but selected in descending order of how many trips were created.
def filter_cumulpct(in_df, sort_col, cutoff):
    df_sorted = in_df.sort_values(sort_col, ascending=False)
    
    col_cumsumpct = 'cumul_sum'
    df_sorted[col_cumsumpct] = df_sorted[sort_col].cumsum()
    
    df_out = df_sorted[df_sorted[col_cumsumpct] <= cutoff]
    
    return df_out

def create_tripshed_poly(in_poly_fc, out_poly_fc, poly_id_field, in_df, df_grouby_field):
    
    # convert numpy (pandas) datatypes to ESRI data types {numpy type: ESRI type}
    dtype_conv_dict = {'float64': 'FLOAT', 'object': 'TEXT', 'int64': 'LONG', 
                       'String': 'TEXT', 'OID': 'LONG', 'Single': 'DOUBLE', 
                       'Integer': 'LONG'}
    
    
    #make copy of base input poly fc that only has features whose IDs are in the dataframe
    fl_input_polys = 'fl_input_polys'
    make_fl_conditional(in_poly_fc, fl_input_polys)
    
    df_ids = tuple(in_df[df_grouby_field])
    
    sql = "{} IN {}".format(poly_id_field, df_ids)
    arcpy.SelectLayerByAttribute_management(fl_input_polys, "NEW_SELECTION", sql)
    
    arcpy.CopyFeatures_management(fl_input_polys, out_poly_fc)

    # add dataframe fields to the trip shed polygon set
            
    #dict of {field: field data type} for input dataframe
    fields_dtype_dict = {col:str(in_df[col].dtype) for col in in_df.columns}
    
    # populate those fields with the dataframe data
    for field in fields_dtype_dict.keys():
        print("adding {} column and data...".format(field))
        field_vals = list(in_df[field]) # get list of values for desired field
        fld_dict = dict(zip(df_ids, field_vals))
        
        fdtype_numpy = fields_dtype_dict[field]
        fdtype_esri = dtype_conv_dict[fdtype_numpy]
        
        # add a field, if needed, to the polygon feature class for the values being added
        if esri_field_exists(out_poly_fc, field):
            pass
        else:
            arcpy.AddField_management(out_poly_fc, field, fdtype_esri)
            
        # populate the field with the appropriate values
        with arcpy.da.UpdateCursor(out_poly_fc, [poly_id_field, field]) as cur:
            for row in cur:
                join_id = row[0]
                if fld_dict.get(join_id) is None:
                    pass
                else:
                    row[1] = fld_dict[join_id]
                    cur.updateRow(row)

# get PPA buffer data for trip shed
def get_poly_avg(input_poly_fc):
    # as of 11/26/2019, each of these outputs are dictionaries
    accdata = acc.get_acc_data(input_poly_fc, p.accdata_fc, p.ptype_area_agg, get_ej=False)
    collision_data = coll.get_collision_data(input_poly_fc, p.ptype_area_agg, p.collisions_fc, 0)
    mix_data = mixidx.get_mix_idx(p.parcel_pt_fc, input_poly_fc, p.ptype_area_agg)
    intsecn_dens = intsxn.intersection_density(input_poly_fc, p.intersections_base_fc, p.ptype_area_agg)
    bikeway_covg = bufnet.get_bikeway_mileage_share(input_poly_fc, p.ptype_area_agg)
    tran_stop_density = trn_svc.transit_svc_density(input_poly_fc, p.trn_svc_fc, p.ptype_area_agg)

    emp_ind_wtot = lubuff.point_sum(p.parcel_pt_fc, input_poly_fc, p.ptype_area_agg, [p.col_empind, p.col_emptot], 0)
    emp_ind_pct = {'EMPIND_jobshare': emp_ind_wtot[p.col_empind] / emp_ind_wtot[p.col_emptot] \
                   if emp_ind_wtot[p.col_emptot] > 0 else 0}

    pop_x_ej = lubuff.point_sum(p.parcel_pt_fc, input_poly_fc, p.ptype_area_agg, [p.col_pop_ilut], 0, p.col_ej_ind)
    pop_tot = sum(pop_x_ej.values())
    key_yes_ej = max(list(pop_x_ej.keys()))
    pct_pop_ej = {'Pct_PopEJArea': pop_x_ej[key_yes_ej] / pop_tot if pop_tot > 0 else 0}

    job_pop_dens = lubuff.point_sum_density(p.parcel_pt_fc, input_poly_fc, p.ptype_area_agg, \
                                            [p.col_du, p.col_emptot], 0)
    total_dens = {"job_du_perNetAcre": sum(job_pop_dens.values())}

    out_dict = {}
    for d in [accdata, collision_data, mix_data, intsecn_dens, bikeway_covg, tran_stop_density, pct_pop_ej,\
              emp_ind_pct, total_dens]:
        out_dict.update(d)

    return out_dict


def make_trip_shed_report(in_tripdata_files, tripdata_val_field, tripdata_agg_fxn, tripdata_groupby_field,
                   in_poly_fc, out_poly_fc, poly_id_field, tripdata_case_field=None):

    # import CSV trip data into dataframe
    df_tripdata = make_tripdata_df(in_tripdata_files)
    
    # summarize by polygon and whatever case value
    df_groupd_tripdata = get_poly_data(df_tripdata, tripdata_val_field, tripdata_agg_fxn, tripdata_groupby_field, tripdata_case_field)

    # filter out block groups that don't meet inclusion criteria (remove polys that have few trips, but keep enough polys to capture X percent of all trips)
    df_outdata = filter_cumulpct(df_groupd_tripdata, 'pct_of_trips', 0.9)

    # make new polygon feature class with trip data
    create_tripshed_poly(in_poly_fc, out_poly_fc, poly_id_field, df_outdata, tripdata_groupby_field)
    
    # get PPA buffer data for trip shed
    


if __name__ == '__main__':
    
    # ------------------USER INPUTS----------------------------------------
    
    arcpy.env.workspace = r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb'
    dir_tripdata = r'Q:\ProjectLevelPerformanceAssessment\PPAv2\Replica\ReplicaDownloads'
    
    proj_name = 'test_project'
    
    tripdata_files = ['trips_list_sr51brg_thu_0000_1259.zip',
                      'trips_list_sr51brg_thu_1259_2359.zip']
    
    csvcol_bgid = 'origin_blockgroup_id'  # Replica/big data block group ID column
    csvcol_mode = 'trip_primary_mode'  # Replica/big data trip mode column
    
    csvcol_valfield = 'trip_start_time' # field for which you want to aggregate values
    val_aggn_type = 'count'  # how you want to aggregate the values field (e.g. count of values, sum of values, avg, etc.)
    
    # feature class of polygons to which you'll join data to based on ID field
    fc_bg = "BlockGroups2010"
    fc_poly_id_field = "GEOID10"
    
    make_tripshed_poly = True

    #------------RUN SCRIPT------------------------------------
    os.chdir(dir_tripdata)
    
    timesufx = str(dt.datetime.now().strftime('%m%d%Y_%H%M'))
    fc_tripshed_out = "TripShed_{}{}".format(proj_name, timesufx)
    
    df_tripdata = make_tripdata_df(tripdata_files)
    
    pivtbl = get_poly_data(df_tripdata, csvcol_valfield, val_aggn_type, csvcol_bgid, csvcol_mode)
    df_out = filter_cumulpct(pivtbl, 'pct_of_trips', 0.9)
    
    if make_tripshed_poly:
        print("adding data to {} feature class...".format(fc_bg))
        create_tripshed_poly(fc_bg, fc_tripshed_out, fc_poly_id_field, df_out, csvcol_bgid)
    