#--------------------------------
# Name:get_lutype_acres.py
# Purpose: Based on parcel polygon intersection with buffer around project segment, get % of acres near project that are of specific land use type
#
#
# Author: Darren Conly
# Last Updated: <date>
# Updated by: <name>
# Copyright:   (c) SACOG
# Python Version: 3.x
#--------------------------------

import arcpy

import ppa_input_params as p


def make_fl_conditional(fc, fl):
    if arcpy.Exists(fl):
        arcpy.Delete_management(fl)
    arcpy.MakeFeatureLayer_management(fc, fl)


def get_lutype_acreage(fc_project, fc_poly_parcels, lutype):
    arcpy.AddMessage("Estimating {} acres near project...".format(lutype))

    fl_parcels = "fl_parcel"
    fl_project = "fl_project"

    for fc, fl in {fc_project: fl_project, fc_poly_parcels: fl_parcels}.items():
        make_fl_conditional(fc, fl)
        # if arcpy.Exists(fl):
        #     arcpy.Delete_management(fl)
        #     arcpy.MakeFeatureLayer_management(fc, fl)
        # else:
        #     arcpy.MakeFeatureLayer_management(fc, fl)

    # create temporary buffer
    buff_dist = 2640  # distance in feet
    fc_buff = r"memory\temp_buff_qmi"
    arcpy.Buffer_analysis(fl_project, fc_buff, buff_dist)

    fl_buff = "fl_buff"
    arcpy.MakeFeatureLayer_management(fc_buff, fl_buff)

    # calculate buffer area, inclusive of water bodies and rights of way
    buff_area_ft2 = 0
    with arcpy.da.SearchCursor(fl_buff, ["SHAPE@AREA"]) as cur:
        for row in cur:
            buff_area_ft2 += row[0]
    buff_acre = buff_area_ft2 / p.ft2acre  # convert from ft2 to acres. may need to adjust for projection-related issues. See PPA1 for more info

    # create intersect layer of buffer with parcels, to "slice" parcels so you only
    # capture parcel portions that are within buffer. We want to do this since we are 
    # calculating the percent of total land within buffer that is a given land use.
    fc_intersect = r"memory\temp_intersect"
    arcpy.Intersect_analysis([fl_buff, fl_parcels], fc_intersect, "ALL", "", "INPUT")
    
    fl_intersect = "fl_intersect"
    make_fl_conditional(fc_intersect, fl_intersect)


    # get total acres within intersect polygons
    tot_net_pclarea_ft2 = 0
    lutype_intersect_ft2 = 0
    with arcpy.da.SearchCursor(fl_intersect, ["SHAPE@AREA", p.col_lutype_base]) as cur:
        for row in cur:
            area = row[0]
            lutype_val = row[1]
            if lutype_val == lutype:
                lutype_intersect_ft2 += area
            tot_net_pclarea_ft2 += area

    # convert to acres
    lutype_intersect_acres = lutype_intersect_ft2 / p.ft2acre  
    tot_net_pcl_acres = tot_net_pclarea_ft2 / p.ft2acre
    
    # pct_lutype_infullbuff = lutype_intersect_acres / buff_acre if buff_acre > 0 else 0
    net_pct_lutype = lutype_intersect_acres / tot_net_pcl_acres if tot_net_pcl_acres > 0 else 0

    [arcpy.Delete_management(item) for item in [fl_parcels, fl_project, fc_buff, fl_buff, fc_intersect, fl_intersect]]

    return {'total_buff_acres': buff_acre, 'net_onpcl_buff_acres': tot_net_pcl_acres, 
            '{}_acres'.format(lutype): lutype_intersect_acres, 'pct_netPclAcs_{}_inBuff'.format(lutype): net_pct_lutype}



if __name__ == '__main__':
    arcpy.env.workspace = r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb'

    parcel_featclass = p.parcel_poly_fc #'parcel_data_polys_2016'
    project_featclass = r'I:\Projects\Darren\PPA_V2_GIS\scratch.gdb\test_project_SEConnector'
    lutype = p.lutype_ag

    out_pcl_data = get_lutype_acreage(project_featclass, parcel_featclass, lutype)
    print(out_pcl_data)

    # NOT 11/22/2019 - THIS IS GETTING AS PCT OF BUFFER AREA, NOT DEVELOPABLE ON-PARCEL ACRES! SHOULD FIX

