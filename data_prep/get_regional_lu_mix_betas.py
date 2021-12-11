# -*- coding: utf-8 -*-
"""
Purpose - calculate regional 'beta' values, or ideal mix values of stuff like 
retail employees, service employees, K12 enrollment, etc. on a per-HH basis for purpose
of calculating a mix that represents the regional mix of this stuff per household
and that mix ratio represents the 'ideal' mix.

Created on Fri Oct 18 11:40:55 2019

@author: DConly
"""

import arcpy

arcpy.env.workspace = r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb'

in_tbl =  'ilut_combined2016_23_latest'

col_hh = 'HH_hh'
emp_mix_cols = ['ENR_K12','EMPRET','EMPTOT','EMPSVC','EMPFOOD']
col_acres = 'GISAc'
col_lutype = 'LUTYPE'
val_parks = 'Park and/or Open Space'

#===========BEGIN SCRIPT=========================


tview = 'table_view'
arcpy.MakeTableView_management(in_tbl,tview)


#get total hhs in region
tot_hh = 0
with arcpy.da.SearchCursor(tview, col_hh)  as cur:
    for row in cur:
        tot_hh += row[0]
        
beta_ratios = []

#get ratios for employment types
for col in emp_mix_cols:
    print('getting beta ratio for {}...'.format(col))
    col_sum = 0
    
    with arcpy.da.SearchCursor(tview, col)  as cur:
        for row in cur:
            col_sum += row[0]
    
    ratio = col_sum / tot_hh
    beta_ratios.append(ratio)
    
print('success! do not forget about parks!')

#get ratio for park acres
sql_forparks = "{} = '{}'".format(col_lutype, val_parks)

parkac_sum = 0

with arcpy.da.SearchCursor(tview, col_acres, sql_forparks)  as cur:
    for row in cur:
        parkac_sum += row[0]

ratio_parks = parkac_sum/tot_hh
beta_ratios.append(ratio_parks)
