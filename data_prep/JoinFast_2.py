import arcpy

arcpy.env.workspace = r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb'
arcpy.OverwriteOutput = True

left_table = 'parcel_data_pts_2016' #can be feature class or table
right_table = 'ilut_combined2016_23_latest' #can be feature class or table

join_key_field_left = 'PARCELID' #case sensitive!
join_key_field_right = 'PARCELID'
val_field_right = 'VMT_TOT_RES'
field_to_calc = 'VMT_TOT_RES'
field_to_calc_dtype = "FLOAT" #FLOAT, TEXT, SHORT, or LONG

print("loading values from right-side table into dict...")
val_dict = {}

fields_right = [join_key_field_right, val_field_right]
fields_left = [join_key_field_left, field_to_calc]
allfields_lefttable = [f.name for f in arcpy.ListFields(left_table)]

with arcpy.da.SearchCursor(right_table, fields_right) as cur:
    for row in cur:
        pclid = row[fields_right.index(join_key_field_right)]
        val = row[fields_right.index(val_field_right)]
        val_dict[pclid] = val


print("updating...")
if field_to_calc not in allfields_lefttable:
    arcpy.AddField_management(left_table, field_to_calc, field_to_calc_dtype)
else:
    arcpy.DeleteField_management(left_table, field_to_calc)
    arcpy.AddField_management(left_table, field_to_calc, field_to_calc_dtype)

with arcpy.da.UpdateCursor(left_table, fields_left) as cur:
    for row in cur:
        pclid = row[fields_left.index(join_key_field_left)]
        if val_dict.get(pclid) is not None:
            row[fields_left.index(field_to_calc)] = val_dict[pclid]
            cur.updateRow(row)
        else:
            continue

print("success!")
