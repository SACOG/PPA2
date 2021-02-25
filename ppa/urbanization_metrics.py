# Esri start of added imports
import sys, os, arcpy
# Esri end of added imports

# Esri start of added variables
g_ESRI_variable_1 = 'memory/temp_intersect_fc'
# Esri end of added variables

# --------------------------------
# Name:urbanization_metrics.py
# Purpose: (1) categorize project as infill, greenfield, or spanning infill + greenfield areas
#          (2) calculate loss of natural resources (acres of ag + forest + open space)
#
# Author: Darren Conly
# Last Updated: <date>
# Updated by: <name>
# Copyright:   (c) SACOG
# Python Version: 3.x
# --------------------------------

import arcpy
import pdb

from get_lutype_acres import GetLandUseArea
import ppa_input_params as params

# get list of ctypes that a project passes through. "infill" if ctype = is established or corridor; greenfield if not
def projarea_infill_status(fc_project, comm_types_fc):
    arcpy.AddMessage("Determining project greenfield/infill status...")
    temp_intersect_fc = g_ESRI_variable_1

    arcpy.Intersect_analysis([fc_project, comm_types_fc], temp_intersect_fc)

    proj_len_infill = 0
    proj_len_greenfield = 0

    with arcpy.da.SearchCursor(temp_intersect_fc, [params.col_ctype, "SHAPE@LENGTH"]) as cur:
        for row in cur:
            if row[0] in params.ctypes_infill:
                proj_len_infill += row[1]
            else:
                proj_len_greenfield += row[1]

    pct_infill = proj_len_infill / (proj_len_infill + proj_len_greenfield)
    if pct_infill >= params.threshold_val:
        category = "Infill project"
    elif pct_infill < (1-params.threshold_val):
        category = "Greenfield project"
    else:
        category = "Project spans both infill and greenfield areas"

    return {"Project's use of existing assets": category}


def nat_resources(fc_project, projtyp, fc_pcl_poly, year=2016):  # NOTE - this is year dependent!
    nat_resource_ac = 0
    
    # pdb.set_trace()
    pcl_buff_intersect = GetLandUseArea(fc_project, projtyp, fc_pcl_poly)
    
    for lutype in params.lutypes_nat_resources:
        lutype_ac_dict = pcl_buff_intersect.get_lu_acres(lutype)
        lutype_acres = lutype_ac_dict['net_{}_acres'.format(lutype)]
        nat_resource_ac += lutype_acres

    return {"nat_resource_acres": nat_resource_ac}


if __name__ == '__main__':
    arcpy.env.workspace = r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb'

    # input fc of parcel data--must be polygons!
    in_pcl_base_fc = params.parcel_poly_fc_yr(in_year=2016)
    # in_pcl_future_tbl =
    # in_ctypes_fc =

    # input line project for basing spatial selection
    project_fc = r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb\Polylines_1'

    # infill_status_dict = projarea_infill_status(project_fc, params.comm_types_fc)
    # print(infill_status_dict)

    nat_resources_dict = nat_resources(project_fc, params.ptype_arterial, in_pcl_base_fc)
    print(nat_resources_dict)
