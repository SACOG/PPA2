#land use buffer calcs

"""
Get following numbers within 0.5mi of project area:
    sum of jobs
    sum of dwelling units
    sum of trips (for each mode)

"""
import arcpy
import pandas as pd

import ppa_input_params as p

def get_other_yr_data(fl_selected_data, tbl_futyr, join_key_col, value_fields):
    #make list of join key values whose values you want from joining table
    tv_futyear = "tv_futureyear"
    arcpy.MakeTableView_management(tbl_futyr, tv_futyear)
    
    
    filtered_join_keys = []
    with arcpy.da.SearchCursor(fl_selected_data, join_key_col) as cur:
        for row in cur:
            filtered_join_keys.append(row[0])

    #cursor for right-hand table: if the join key value is in list of join key values, then add as item to list of lists
    rows_otheryear_data = []

    value_fields.append(join_key_col)
    with arcpy.da.SearchCursor(tbl_futyr, value_fields) as cur:
        for row in cur:
            join_key_val = row[value_fields.index(join_key_col)]
            if join_key_val in filtered_join_keys:
                data_row = list(row)
                rows_otheryear_data.append(data_row)

    #make a dataframe from the list of lists.
    otheryear_pcldf = pd.DataFrame(rows_otheryear_data, columns=value_fields)
    return otheryear_pcldf

def point_sum(fc_pclpt, fc_project, project_type, val_fields, case_field=None, case_excs_list=[]):
    arcpy.env.OverwriteOutput = True
    
    arcpy.AddMessage("aggregating land use data...")
    fl_parcel = "fl_parcel"
    arcpy.MakeFeatureLayer_management(fc_pclpt, fl_parcel)
    fl_project = "fl_project"
    arcpy.MakeFeatureLayer_management(fc_project, fl_project)

    buff_dist = 0 if project_type == p.ptype_area_agg else p.ilut_sum_buffdist
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
    
    parcel_fyr_df = get_other_yr_data(fl_parcel, "ilut_combined2040_38_latest", "PARCELID", val_fields)

    if case_field is not None:
        parcel_df = parcel_df.loc[~parcel_df[case_field].isin(case_excs_list)] #exclude specified categories
        out_df = parcel_df.groupby(case_field).sum().T # get sum by category (case field)
        # NEXT ISSUE - need to figure out how to show all case types, even if no parcels with that case type within the buffer
    else:
        out_df = pd.DataFrame(parcel_df[val_fields].sum(axis=0)).T

    out_dict = out_df.to_dict('records')[0]


    return parcel_fyr_df

# gets density of whatever you're summing, based on parcel area (i.e., excludes rivers, lakes, road ROW, etc.)
# considers parcel area for parcels whose centroid is in the buffer. This is because the initial values are based on
# entire parcels, not parcels that've been chopped by a buffer boundary
def point_sum_density(fc_pclpt, fc_project, project_type, val_fields, case_field=None, case_excs_list=[]):

    # make sure you calculate the area for normalizing
    if p.col_area_ac not in val_fields:
        val_fields.append(p.col_area_ac)

    #get values (e.g. total pop, total jobs, etc.)
    dict_vals = point_sum(fc_pclpt, fc_project, project_type, val_fields, case_field, case_excs_list)

    #calculate density per unit of area for each value (e.g. jobs/acre, pop/acre, etc.)
    area_unit = "acre"
    dict_out = {}
    for valfield, val in dict_vals.items():
        if valfield == p.col_area_ac:
            continue
        else:
            val_density = dict_vals[valfield] / dict_vals[p.col_area_ac]
            dict_out_key = "{}_{}".format(valfield, area_unit)
            dict_out[dict_out_key] = val_density

    return dict_out

if __name__ == '__main__':
    arcpy.env.workspace = r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb'

    # input fc of parcel data--must be points!
    in_pcl_pt_fc = p.parcel_pt_fc
    value_fields = ['POP_TOT', 'EMPTOT', 'EMPIND', 'PT_TOT_RES', 'SOV_TOT_RES', 'HOV_TOT_RES', 'TRN_TOT_RES',
                    'BIK_TOT_RES', 'WLK_TOT_RES']

    # input line project for basing spatial selection
    project_fc = r'I:\Projects\Darren\PPA_V2_GIS\scratch.gdb\test_project_YubaCity'
    ptype = p.ptype_sgr

    # get jobs, dwelling units, trips by mode within 0.5mi
    #output_dict = point_sum(in_pcl_pt_fc, value_fields, 2640, project_fc)
    #print(output_dict)

    # dwelling units by housing type within 1mi
    #output_dict = point_sum(in_pcl_pt_fc, ['DU_TOT'], 5280, project_fc, case_field='TYPCODE_DESC', case_excs_list=['Other'])
    #print(output_dict)
    # EJ population
#    output_dict = point_sum(in_pcl_pt_fc, project_fc, ptype, ['POP_TOT'], 2640, )  # case_field='EJ_2018'
#    print(output_dict)
    
    test_output_df = point_sum(in_pcl_pt_fc, project_fc, ptype, ['POP_TOT'], 2640, )

#    # point_sum(fc_pclpt, fc_project, project_type, val_fields, case_field=None, case_excs_list=[])
#    output_dens_dict = point_sum_density(in_pcl_pt_fc, project_fc, ptype, ['POP_TOT', 'EMPTOT'])
#    print(output_dens_dict)