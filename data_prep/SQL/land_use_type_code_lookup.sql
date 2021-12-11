/*
Name:land_use_type_code_lookup.sql
Purpose: Gets "plain English" land use type code from Envision Tomorrow table
	Output is used to help display the housing types in human-readable form for
	Community Design report
           
Author: Darren Conly
Last Updated: 11/2019
Updated by: <name>
Copyright:   (c) SACOG
SQL Flavor: SQL Server
*/

USE MTP2020
GO

--Create simple lookup table corresponding land use type descriptions to type codes.
SELECT DISTINCT
	CONVERT(VARCHAR(MAX), LU_SCNYR) AS LU_SCNYR,
	TYPE_CODE
FROM raw_eto2016_latest
WHERE TYPE_CODE <> 0
ORDER BY TYPE_CODE

--SELECT DISTINCT
--	landuse16,
--	TYPE_CODE
--FROM raw_eto2016_latest

--SELECT DISTINCT
--	CONVERT(VARCHAR(MAX), LU_SCNYR) AS LU_SCNYR,
--	TYPE_CODE
--FROM raw_eto2040_latest
--WHERE TYPE_CODE <> 0
--ORDER BY TYPE_CODE


--add type code number to 2016 ilut table
SELECT
	i.*,
	e.TYPE_CODE
INTO mtpuser.ilut_combined2016_23_wtypecode
FROM mtpuser.ilut_combined2016_23 i
	LEFT JOIN raw_eto2016_latest e
		ON i.parcelid = e.parcelid


--add type code to 2040 ilut table
--BEWARE THAT 2040 ENVISION TOMORROW DOES NOT INCLUDE ALL 836,636 PARCELS SO WHERE TYPE CODE IS NULL FOR 2040 THE 2016 TYPE CODE IS USED.
SELECT
	i.*,
	CASE WHEN e40.TYPE_CODE IS NULL THEN e16.TYPE_CODE ELSE e40.TYPE_CODE END AS TYPE_CODE
INTO mtpuser.ilut_combined2040_38_wtypecode
FROM mtpuser.ilut_combined2040_38 i
	LEFT JOIN raw_eto2040_latest e40
		ON i.parcelid = e40.parcelid
	LEFT JOIN raw_eto2016_latest e16
		ON i.parcelid = e16.parcelid

--drop table mtpuser.ilut_combined2016_23_wtypecode
--drop table mtpuser.ilut_combined2040_38_wtypecode