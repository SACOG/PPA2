# -*- coding: utf-8 -*-
#--------------------------------
# Name:agg_parcel_to_hexgeom.py
# Purpose: intersect parcel and hexagon polygon files to allow area-weighted
#          aggregations of parcel data onto hex polygons
#           this script is focused on area-weighted mix index average, accounting only for developable land (excludes water/rights of way)
#           
# Author: Darren Conly
# Last Updated: 5/24/2019
# Updated by: <name>
# Copyright:   (c) SACOG
# Python Version: 3.x
#--------------------------------

import time
import datetime as dt

import arcpy


arcpy.env.overwriteOutput = True

#==============================

#divide parcel polygons at hex boundaries
def do_intersect(fc_parcels, fc_hexs, fc_intersect_base, fld_pcl_id, fld_pcltotarea): #clean up, fc_intersect doesn't need to be argument; is temp layer
    
    #add field with parcel's total area
    print("Intersecting {} with {}...".format(fc_parcels, fc_hexs))
    if fld_pcltotarea not in [f.name for f in arcpy.ListFields(fc_parcels)]:
        arcpy.AddField_management(fc_parcels, fld_pcltotarea, "FLOAT")
    
    area_pcl = "SHAPE@AREA"
    fields = [fld_pcltotarea, area_pcl]
    
    
    with arcpy.da.UpdateCursor(fc_parcels, fields) as cur:
        for row in cur:
            row[fields.index(fld_pcltotarea)] = row[fields.index(area_pcl)]
            cur.updateRow(row)
    
    #do intersection
    in_features = [fc_parcels, fc_hexs]
    arcpy.Intersect_analysis(in_features, fc_intersect_base)
    
#join ILUT data to polygons formed by intersecting parcel polys with hexes
def join_ilut_to_intersect(fc_intersect_base, tbl_ilutdata, tempfc_intsct_w_ilut, fld_pcl_id):
    print("Joining {} ILUT data to hex-parcel intersect layer...".format(tbl_ilutdata))
    
    arcpy.env.qualifiedFieldNames = False

    fl_intersect = "fl_intersect"
    arcpy.MakeFeatureLayer_management(fc_intersect_base, fl_intersect)
    
    
    #join ILUT or other parcel-level data to parcel pieces in intersect layer
    arcpy.AddJoin_management(fl_intersect, fld_pcl_id, tbl_ilutdata, fld_pcl_id)
    
    #copy features to temp output fc WITHOUT full field qualifiers
    arcpy.CopyFeatures_management(fl_intersect, tempfc_intsct_w_ilut)
    
    #arcpy.Delete_management(tempfc_intersect)
    
def calc_wtd_val(fc_intersect_w_propn, fld_pcltotarea, fldin, fldoutprefix, sufx_proplflds):
    print("multiplying value * area to get weight for parcel pieces in each hex...")
    #add field which'll be populated with the % of parcel that's in hex, as well as weighted value
    fld_pclareapct = "pctpclarea"
    fld_wtd_val = "{}{}".format(fldoutprefix, sufx_proplflds) #get area weighted value for each parcel piece (value = pop, emp, whatever)
    
    if fld_pclareapct not in [f.name for f in arcpy.ListFields(fc_intersect_w_propn)]:
        arcpy.AddField_management(fc_intersect_w_propn, fld_pclareapct, "FLOAT")
    
    if fld_wtd_val not in [f.name for f in arcpy.ListFields(fc_intersect_w_propn)]:
        arcpy.AddField_management(fc_intersect_w_propn, fld_wtd_val, "FLOAT")
    
    fl_intersectjoin = "fl_intersectjoin"
    arcpy.MakeFeatureLayer_management(fc_intersect_w_propn, fl_intersectjoin)
    
    fields = [f.name for f in arcpy.ListFields(fl_intersectjoin)]
    fields.append("SHAPE@AREA")
    
    with arcpy.da.UpdateCursor(fl_intersectjoin, fields) as cur:
        for row in cur:
            #for parcel pieces in a hex, get that piece's share of the total area of the parcel to which the piece belongs
            area_piece = row[fields.index("SHAPE@AREA")]
            pcl_val = row[fields.index(fldin)]
            #pclshare = area_piece / area_totalpcl
            #row[fields.index(fld_pclareapct)] = pclshare
            
            #get "weighted" value for piece = parcel area * parcel value for field of interest
            if pcl_val is None: #if value is null for particular parcel, then pass
                continue
            else:
                wtd_val = pcl_val * area_piece
            row[fields.index(fld_wtd_val)] = wtd_val
            
            cur.updateRow(row)
    
#dissolve by hex ID; getting sum, avg, etc. of the values weighted by parcel piece area
def dissolve_x_hex(fc_intersect_w_propn, dict_fld_pcl_vals, fc_hexs, fld_hexid,
                   fc_hexoutput, sufx_proplflds):
    print("dissolving to get area-weighted average value for each hex...")
    arcpy.env.qualifiedFieldNames = False #ensures original table names do not append to joined fields after exporting joined layers.

    area_pcl = 'Shape_Area'
    agg_area = 'SUM_'
    area_pcl_sum = "{}{}".format(agg_area, area_pcl)
    area_pcl_new = 'NetPclArea'
    
    time_id = str(dt.datetime.now().strftime('%Y%m%d%H%M'))
    tbl_tempstats = "TEMP_stats_x_hex{}".format(time_id)
    
    #summarize by hex ID, outputting table
    #e.g. ['POP_propl', etc....], assuming POP is field and "_propl" is suffix
    wtdval_fields = ["{}{}".format(v[0], sufx_proplflds) for k, v in dict_fld_pcl_vals.items()]
    output_wtdav_fields = ["{}{}_awtdavg".format(v[0], sufx_proplflds) for k, v in dict_fld_pcl_vals.items()]
    outfields_dict = dict(zip(wtdval_fields, output_wtdav_fields)) # e.g. {POP_propl: POP_propl_wtdavg,...}
    
    

    # [[agg_col_name, aggregation type]], e.g [['POP_propl','SUM'],...]
    flds_stats_tbl = [["{}{}".format(v[0], sufx_proplflds),v[1]] for k, v in dict_fld_pcl_vals.items()]
    flds_stats_tbl.append([area_pcl,'SUM']) # add on total on-parcel area within hex
    
    
    # pdb.set_trace()
    arcpy.Statistics_analysis(fc_intersect_w_propn, tbl_tempstats, flds_stats_tbl, fld_hexid)
    
    fl_hexs = "fl_hexs"
    arcpy.MakeFeatureLayer_management(fc_hexs, fl_hexs)
    
    #join summary x hex ID table to hex feature class.
    arcpy.AddJoin_management(fl_hexs, fld_hexid, tbl_tempstats, fld_hexid)
    arcpy.CopyFeatures_management(fl_hexs, fc_hexoutput)

    for field in wtdval_fields:
        if outfields_dict[field] not in [f.name for f in arcpy.ListFields(fc_hexoutput)]:
            arcpy.AddField_management(fc_hexoutput, outfields_dict[field], "FLOAT")

        curfields = [f.name for f in arcpy.ListFields(fc_hexoutput)]
        curfields = curfields + [area_pcl_sum] # need to manually add area field (normally SHAPE@AREA)
        field_wtdval = "SUM_{}".format(field)

        with arcpy.da.UpdateCursor(fc_hexoutput, curfields) as cur:
            for row in cur:
                wtd_val = row[curfields.index(field_wtdval)]
                area = row[curfields.index(area_pcl_sum)]
                if wtd_val is None or area is None:
                    continue
                else:
                    wtd_avg_val = wtd_val / area
                    output_field = outfields_dict[field]
                    row[curfields.index(output_field)] = wtd_avg_val
                    cur.updateRow(row)

    arcpy.AlterField_management(fc_hexoutput, area_pcl_sum, area_pcl_new)

    arcpy.Delete_management(tbl_tempstats)
    arcpy.Delete_management(fc_intersect_w_propn)
    

def do_work(fc_parcels, fc_hexs, fld_hexid, tbl_ilutdata, fld_pcl_id, dict_fld_pcl_vals, fc_hexoutput,
            make_new_pcl_intersect_layer = True):
    
    time_id = str(dt.datetime.now().strftime('%Y%m%d%H%M'))
    fld_pcltotarea = "pcltotarea" #clean this up. This variable is declared twice
    
    #make layer that's intersect of parcels and hexs
    fc_intersect_base = "PclHexIntersect_base"
    if make_new_pcl_intersect_layer:
        do_intersect(fc_parcels, fc_hexs, fc_intersect_base, fld_pcl_id, fld_pcltotarea)
    
    #join ILUT data to the intersect layer
    tempfc_intsct_w_ilut = "TEMPintsct_w_ILUT{}".format(time_id)
    join_ilut_to_intersect(fc_intersect_base, tbl_ilutdata, tempfc_intsct_w_ilut, fld_pcl_id)
    
    sufx_proplflds = "_propl" #suffix to give to field names to indicate they're proportional to share of parcel
    
    #calculate area-weighted ILUT values for hexes
    fc_intsct_out = "PclHexIntsct_wValPropns{}".format(time_id)
    arcpy.CopyFeatures_management(tempfc_intsct_w_ilut, fc_intsct_out)
    
    for fldin, fldoutprefix in dict_fld_pcl_vals.items():
        print("calculating {} field...".format(fldoutprefix))
        fldoutprefix = fldoutprefix[0]
        calc_wtd_val(fc_intsct_out, fld_pcltotarea, fldin, fldoutprefix, sufx_proplflds)
    
    dissolve_x_hex(fc_intsct_out, dict_fld_pcl_vals, fc_hexs, fld_hexid, fc_hexoutput, sufx_proplflds)
    
    arcpy.Delete_management(tempfc_intsct_w_ilut)
        

if __name__ == '__main__':
    arcpy.env.workspace = r'Q:\SACSIM19\Integration Data Summary\ILUT GIS\ILUT GIS.gdb'

    start_time = time.time()
    date_sufx = str(dt.date.today().strftime('%Y%m%d'))
    
    
    fc_parcels = "parcel_master_simple05202019"
    fld_pcl_id = 'parcelid' #join field for parcelid--should be same for all tables
    fld_hexid = "GRID_ID"
    
    fc_hexs = "hex_base_05202019"  # "hex_base_sample"
    

    # data table that contains population, emp, other data you want to summarize at hex level
    #should have in same GDB and trim fields down to those you need to save space  
    tbl_ilutdata = "pcl_w_mixindex_multbuff_11052019"
    ilut_year = 2016
    
    fc_hexoutput = "hex_w_wtdavgs{}_{}".format(ilut_year, date_sufx)
    
    #{<field name from ILUT>:<prefix for value output field>}
    agg_sum = "SUM"
    agg_mean = "MEAN"

    #standard field dict based on ILUT
    dict_fld_pcl_vals = {'mix_index_1mi':['mixidx', agg_sum]
                         # 'EMPTOT':['EMP', agg_sum],
                         # 'HOMEEMP':['HEMP', agg_sum],
                         # 'HH_TOT_P':['HHPOP', agg_sum],
                         # 'VMT_TOT_RES':['VMTRES', agg_sum]
                         }
						 
    
    #if intersected hex-parcel layer already done, save ~3mins of run time by skipping its creation and using existing one
    make_new_pcl_intersect_layer = False
    
    do_work(fc_parcels, fc_hexs, fld_hexid, tbl_ilutdata, fld_pcl_id, dict_fld_pcl_vals, fc_hexoutput,
            make_new_pcl_intersect_layer, ilut_year)
    
    elapsed_time = round((time.time() - start_time)/60,1)
    print("Success! Elapsed time: {} minutes".format(elapsed_time))
    
    