# Esri start of added imports
import sys, os, arcpy
# Esri end of added imports

# Esri start of added variables
g_ESRI_variable_1 = 'fl_parcel'
g_ESRI_variable_2 = 'fl_project'
g_ESRI_variable_3 = 'fl_buff'
g_ESRI_variable_4 = os.path.join(arcpy.env.scratchGDB, 'temp_intersect')
g_ESRI_variable_5 = 'fl_intersect'
# Esri end of added variables

#--------------------------------
# Name:get_lutype_acres.py
# Purpose: Based on parcel polygon intersection with buffer around project segment, get % of acres near project that are of specific land use type
#           This version of script calculates the percent based on on-parcel acres (i.e., the total acreage excludes water/rights of way)
#
# Author: Darren Conly
# Last Updated: 12/30/2019
# Updated by: <name>
# Copyright:   (c) SACOG
# Python Version: 3.x
#--------------------------------
import time

import ppa_input_params as params

class GetLandUseArea():
    def __init__(self, fc_project, projtyp, fc_poly_parcels):
        
        #user inputs
        self.fc_project = fc_project
        self.projtyp = projtyp
        self.fc_poly_parcels = fc_poly_parcels
        
        # fixed values
        self.fc_intersect = g_ESRI_variable_4
        
        # derived/calculated objects
        self.buff_pclpoly_intersect()
        
    def buff_pclpoly_intersect(self):
        # arcpy.AddMessage("script updated {}".format(int(time.perf_counter()))) # when troubleshooting
        
    
        sufx = int(time.perf_counter()) + 1
        fl_parcels = os.path.join(arcpy.env.scratchGDB, 'fl_parcels{}'.format(sufx))
        fl_project = g_ESRI_variable_2
    
        if arcpy.Exists(fl_parcels): arcpy.Delete_management(fl_parcels)
        
        arcpy.MakeFeatureLayer_management(self.fc_poly_parcels, fl_parcels)
        
        if arcpy.Exists(fl_project): arcpy.Delete_management(fl_project)
        arcpy.MakeFeatureLayer_management(self.fc_project, fl_project)  
    
        # create temporary buffer IF the input project fc is a line. 
        # If it's a polygon, then don't make separate buffer
        if self.projtyp == params.ptype_area_agg:
            fc_buff = self.fc_project
        else:
            buff_dist = params.ilut_sum_buffdist  # distance in feet
            fc_buff = os.path.join(arcpy.env.scratchGDB, "temp_buff_hmi")  # r"memory\temp_buff_hmi"
            if arcpy.Exists(fc_buff): arcpy.Delete_management(fc_buff)
            arcpy.Buffer_analysis(fl_project, fc_buff, buff_dist)
    
        fl_buff = g_ESRI_variable_3
        arcpy.MakeFeatureLayer_management(fc_buff, fl_buff)
        
    
        """ 
        # calculate buffer area, inclusive of water bodies and rights of way
        buff_area_ft2 = 0
        with arcpy.da.SearchCursor(fl_buff, ["SHAPE@AREA"]) as cur:
            for row in cur:
                buff_area_ft2 += row[0]
        buff_acre = buff_area_ft2 / params.ft2acre  # convert from ft2 to acres. may need to adjust for projection-related issues. See PPA1 for more info
        """
    
        # create intersect layer of buffer with parcels of selected LUTYPE
        if arcpy.Exists(self.fc_intersect): arcpy.Delete_management(self.fc_intersect)
        arcpy.Intersect_analysis([fl_buff, fl_parcels], self.fc_intersect, "ALL", "", "INPUT")
        
        for item in [fl_parcels, fl_project, fl_buff]:
            try:
                arcpy.Delete_management(item)
            except:
                arcpy.AddWarning("Unable to delete feature layer {}".format(item))
                continue

    def get_lu_acres(self, lutype):
        # calculate total area on parcels within buffer (excluding water and rights of way)
        fl_intersect = g_ESRI_variable_5
        
        if arcpy.Exists(fl_intersect): arcpy.Delete_management(fl_intersect)
        arcpy.MakeFeatureLayer_management(self.fc_intersect, fl_intersect)
    
        # get total acres within intersect polygons
        pclarea_inbuff_ft2 = 0  # total on-parcel acres within buffer
        lutype_intersect_ft2 = 0  # total acres of specified land use type within buffer
        with arcpy.da.SearchCursor(fl_intersect, ["SHAPE@AREA", params.col_lutype]) as cur:
            for row in cur:
                pclarea_inbuff_ft2 += row[0]
                if row[1] == lutype:
                    lutype_intersect_ft2 += row[0]
    
        # get share of on-parcel land within buffer that is of specified land use type
        pct_lutype = lutype_intersect_ft2 / pclarea_inbuff_ft2 if pclarea_inbuff_ft2 > 0 else 0
    
        # convert to acres
        buff_acre = pclarea_inbuff_ft2 / params.ft2acre
        lutype_intersect_acres = lutype_intersect_ft2 / params.ft2acre
    
        return {'total_net_pcl_acres': buff_acre, 'net_{}_acres'.format(lutype): lutype_intersect_acres,
                'pct_{}_inbuff'.format(lutype): pct_lutype}



if __name__ == '__main__':
    arcpy.env.workspace = r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb'

    parcel_featclass = params.parcel_poly_fc_yr(in_year=2016)  # 'parcel_data_polys_2016'
    project_featclass = r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb\Polylines_1'
    lutype_in = 'Agriculture'

    out_pcl_data = GetLandUseArea(project_featclass, params.ptype_sgr, parcel_featclass).get_lu_acres(lutype_in)
    print(out_pcl_data)




