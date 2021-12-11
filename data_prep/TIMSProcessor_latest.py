# -*- coding: utf-8 -*-
"""
Created on Tue Jul 25 16:58:09 2017

@author: dconly

PURPOSE:
	Take in multiple CSV files of collision data and combine them
	For coordinates, use POINT_X and POINT_Y as defaults; otherwise
	use the CHP coordinates (less reliable, but something)
    
df to numpy array
https://pandas.pydata.org/pandas-docs/stable/generated/pandas.DataFrame.values.html#pandas.DataFrame.values
http://pro.arcgis.com/en/pro-app/arcpy/data-access/numpyarraytotable.htm

"""

import pandas as pd
import arcpy
import re
import os

in_csv_folder = r'I:\Projects\Darren\PPA_V2_GIS\CSV\collision data'

#output as CSV
make_csv = True
out_csv_folder = r'I:\Projects\Darren\PPA_V2_GIS\CSV\collision data'

#output to FGDB
make_fc = False #there's an issue with this, see the make_fc function for details
arcpy.env.workspace = r"I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb"
temp_colln_table = "in_memory/temp_collision_table"
colln_xylayer = "colln_xylayer"
collision_fc = "collisions2014_2018"

sr_tims = arcpy.SpatialReference(4326)  #4326 = WGS 1984
sr_sacog = arcpy.SpatialReference(2226) #2226 = SACOG NAD 83 CA State Plane Zone 2

#=======================COLUMN INDICATORS============
case_id = 'CASE_ID'
colln_year = 'ACCIDENT_YEAR'
x_tims = 'POINT_X'
y_tims = 'POINT_Y'
x_chp = 'LONGITUDE'
y_chp = 'LATITUDE'
x_final = 'x_final'
y_final = 'y_final'

#============FUNCTIONS==========
            

def coordCombin(in_csv,folder = in_csv_folder):
    in_csv = os.path.join(in_csv_folder,in_csv)
    in_df = pd.DataFrame(pd.read_csv(in_csv,sep = ','))
    
    in_df[x_final] = in_df[x_tims]
    in_df[y_final] = in_df[y_tims]
    
#    in_df.apply(set_final_cv, axis = 1)

    #by default, x_final and y_final will = POINT_X and POINT_Y,
    #which are through TIMS geocoding
    in_df[x_final] = in_df[x_tims]
    in_df[y_final] = in_df[y_tims]

    #if x_final == 0 then set x_final = 'X_CHP'
    in_df.loc[in_df[x_final] == 0, x_final] = in_df[x_chp]
    in_df.loc[pd.isnull(in_df[x_final]), x_final] = in_df[x_chp]
    
    in_df.loc[in_df[y_final] == 0, y_final] = in_df[y_chp]
    in_df.loc[pd.isnull(in_df[y_final]), y_final] = in_df[y_chp]
    
    
    #if CHP coords don't exist, then set final x/y values to zero
    in_df.loc[in_df[x_final] == 0, x_final] = 0
    in_df.loc[pd.isnull(in_df[x_final]), x_final] = 0
    
    in_df.loc[in_df[y_final] == 0, y_final] = 0
    in_df.loc[pd.isnull(in_df[y_final]), y_final] = 0
    
    return in_df
                                 
    
#=============APPEND TABLES TOGETHER==============
def combine_tables(folder = in_csv_folder):
    in_csvs = os.listdir(in_csv_folder) # returns all input CSVs as a list
    in_csvs = [i for i in in_csvs if re.match(".*.csv",i)]
    
    print('reading ' + in_csvs[0])
    
    final_table = coordCombin(in_csvs[0])
    
    
    for csv in in_csvs[1:]:
        print('reading ' + csv)
        final_table = final_table.append(coordCombin(csv))
    
    return final_table
    
def validation_stats(in_df):
    no_coords_yr = in_df[in_df[x_final] == 0] \
                    .groupby(colln_year).count()[x_final]
                    
    coords_yr = in_df[in_df[y_final] != 0] \
                    .groupby(colln_year).count()[y_final]
                    
    div = pd.DataFrame(pd.concat([no_coords_yr, coords_yr], axis=1))
    div['pct_geocoded'] = div[y_final]/(div[x_final] + div[y_final])
    
    div = div.rename(columns = {x_final:'not_geocoded', y_final:'geocoded'})
    
    print('-'*20)
    print('Pct geocoded:')
    print(div)

def make_csv(in_df):
    print('outputting to combined CSV...')
    
    output_csv = 'SACOG_collisions' #don't add file extension
    start_year = str(in_df[colln_year].min())  
    end_year = str(in_df[colln_year].max())
    
    out_csv_path = os.path.join(out_csv_folder,"{}{}_{}.csv".format(output_csv,start_year,end_year))
    in_df.to_csv(out_csv_path,index = False)
    
def make_fc(in_df):
    print("making GIS feature class in {}...".format(arcpy.env.workspace))
    
    np_from_df = in_df.to_records()
    
    arcpy.da.NumPyArrayToTable(np_from_df,temp_colln_table)
    
    arcpy.MakeXYEventLayer_management(temp_colln_table, x_final, y_final, 
                                      colln_xylayer, sr_tims)
    
    arcpy.CopyFeatures_management(colln_xylayer, collision_fc)
    
def do_work(in_csv_folder, make_csv = True, make_fc = True):
    comb_df = combine_tables(in_csv_folder)
    
    if make_csv:
        make_csv(comb_df)
    
#    if make_fc:    
#        make_fc(comb_df) #this is having an issue converting from df > nparray > gis table
    
    validation_stats(comb_df)
    
if __name__ == '__main__':
    do_work(in_csv_folder, make_csv, make_fc)
    
    
#    out_table = combine_tables(in_csv_folder)
#    ot_geog = out_table[[case_id,y_chp,x_chp,x_tims,y_tims,
#                     x_final,y_final]]

    