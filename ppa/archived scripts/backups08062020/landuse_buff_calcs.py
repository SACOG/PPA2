# Esri start of added imports
import sys, os, arcpy
# Esri end of added imports

# Esri start of added variables
g_ESRI_variable_1 = 'fl_parcel'
g_ESRI_variable_2 = 'fl_project'
# Esri end of added variables

#land use buffer calcs

"""
Get following numbers within 0.5mi of project area:
    sum of jobs
    sum of dwelling units
    sum of trips (for each mode)

"""
import time

import arcpy
import pandas as pd

import ppa_input_params as params

def point_sum(fc_pclpt, fc_project, project_type, val_fields, buffdist, case_field=None, case_excs_list=[]):
    arcpy.AddMessage("Aggregating land use data...")
    
    sufx = int(time.perf_counter()) + 1
    fl_parcel = os.path.join('memory','fl_parcel{}'.format(sufx))
    fl_project = g_ESRI_variable_2
    
    if arcpy.Exists(fl_parcel): arcpy.Delete_management(fl_parcel)
    arcpy.MakeFeatureLayer_management(fc_pclpt, fl_parcel)
    
    if arcpy.Exists(fl_project): arcpy.Delete_management(fl_project)
    arcpy.MakeFeatureLayer_management(fc_project, fl_project)    

    buff_dist = 0 if project_type == params.ptype_area_agg else buffdist
    arcpy.SelectLayerByLocation_management(fl_parcel, "WITHIN_A_DISTANCE", fl_project, buff_dist)

    # If there are no points in the buffer (e.g., no collisions on segment, no parcels, etc.),
    # still add those columns, but make them = 0
    file_len = arcpy.GetCount_management(fl_parcel)
    file_len = int(file_len.getOutput(0))

    if case_field is not None:
        val_fields.append(case_field)

    # load parcel data into dataframe
    rows_pcldata = []
    with arcpy.da.SearchCursor(fl_parcel, val_fields) as cur:
        for row in cur:
            df_row = list(row)
            rows_pcldata.append(df_row)

    parcel_df = pd.DataFrame(rows_pcldata, columns = val_fields)

    if case_field is not None:
        parcel_df = parcel_df.loc[~parcel_df[case_field].isin(case_excs_list)] #exclude specified categories
        out_df = parcel_df.groupby(case_field).sum().T # get sum by category (case field)
        # NEXT ISSUE - need to figure out how to show all case types, even if no parcels with that case type within the buffer
    else:
        out_df = pd.DataFrame(parcel_df[val_fields].sum(axis=0)).T

    out_dict = out_df.to_dict('records')[0]

    return out_dict

# gets density of whatever you're summing, based on parcel area (i.e., excludes rivers, lakes, road ROW, etc.)
# considers parcel area for parcels whose centroid is in the buffer. This is because the initial values are based on
# entire parcels, not parcels that've been chopped by a buffer boundary
def point_sum_density(fc_pclpt, fc_project, project_type, val_fields, buffdist, case_field=None, case_excs_list=[]):

    # area used in density calculation is land on parcels whose centroid is within the buffer distance. It includes
    # area of entire parcel, both inside and outside the buffer, not "slices" of parcels that are bisected by buffer boundary.
    
    # make sure you calculate the area for normalizing
    if params.col_area_ac not in val_fields:
        val_fields.append(params.col_area_ac)

    #get values (e.g. total pop, total jobs, etc.)
    dict_vals = point_sum(fc_pclpt, fc_project, project_type, val_fields, buffdist, case_field, case_excs_list)

    # calculate density per unit of area for each value (e.g. jobs/acre, pop/acre, etc.)
    # This density is based on total parcel area, i.e., even if parts of some of the parcels are outside of the
    # buffer polygon. Since it is density this is a good method (alternative, which would give same answer, is to do
    # the intersect, then divide that area by the area-weighted value (value = pop, emptot, etc.). But this is simpler and
    # gives same density number.

    area_unit = "NetPclAcre"
    dict_out = {}
    for valfield, val in dict_vals.items():
        if valfield == params.col_area_ac:
            continue
        else:
            val_density = dict_vals[valfield] / dict_vals[params.col_area_ac]
            dict_out_key = "{}_{}".format(valfield, area_unit)
            dict_out[dict_out_key] = val_density

    return dict_out

'''
if __name__ == '__main__':
    arcpy.env.workspace = None

    # input fc of parcel data--must be points!
    in_pcl_pt_fc = params.parcel_pt_fc_yr(2016)
    value_fields = ['POP_TOT', 'EMPTOT', 'EMPIND', 'PT_TOT_RES', 'SOV_TOT_RES', 'HOV_TOT_RES', 'TRN_TOT_RES',
                    'BIK_TOT_RES', 'WLK_TOT_RES']

    # input line project for basing spatial selection
    project_fc = None
    ptype = params.ptype_arterial

    # point_sum(fc_pclpt, fc_project, project_type, val_fields, case_field=None, case_excs_list=[])
    # output_dict = point_sum(in_pcl_pt_fc, project_fc, ptype, ['POP_TOT'], 2640, case_field='EJ_2018', case_excs_list=[])
    # ej_flag_dict = {0: "Pop_NonEJ", 1: "Pop_EJ"}
    # out_dict2 = {}
    # for k, v in ej_flag_dict.items():
    #     if k in list(output_dict.keys()):
    #         out_dict2[v] = output_dict[k]
    #     else:
    #         out_dict2[v] = 0

    # print(point_sum_density(in_pcl_pt_fc, project_fc, ptype, ['EMPTOT', 'DU_TOT'], 2640))
    
    print(point_sum(in_pcl_pt_fc, project_fc, ptype, ['EMPTOT', 'DU_TOT', 'GISAc'], 2640))

    #ej_data_arterial = {v: output_dict.pop(k) for k, v in ej_flag_dict.items() if output_dict.get(k) is not None}
'''
