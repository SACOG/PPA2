/*
Name: HoursCongestedConditions.sql
Purpose: On an average weekday, for how many hours is the TMC "congested", with its observed speed being less than
some % of the free-flow (reference) speed?
           
Author: Darren Conly
Last Updated: 8/29/2019
Updated by: <name>
Copyright:   (c) SACOG
SQL Flavor: SQL Server

Test TMC (I-5 SB over American River) = '105-04713'
*/

USE NPMRDS
;

SELECT
	DISTINCT tmc_code,
	PERCENTILE_CONT(0.85)
		WITHIN GROUP (ORDER BY speed)
		OVER (PARTITION BY tmc_code) 
		AS speed_85_offpk
INTO #ff_speed
FROM npmrds_2018_alltmc_paxveh
WHERE (DATEPART(hh,measurement_tstamp) >=20
		OR DATEPART(hh,measurement_tstamp) < 6)
;

WITH all_days_cong AS (
SELECT
	tt.tmc_code,
	DATEPART(dy, tt.measurement_tstamp) AS doy,
	SUM(CASE WHEN speed / p.speed_85_offpk <= 0.6 
			THEN 0.25 ELSE 0 END) AS congested_hours, --using manually-determined reference speed since it's missing from some TMCs for no apparent reason
	COUNT(*)*0.25 AS total_hours
FROM npmrds_2018_alltmc_paxveh tt
	LEFT JOIN #ff_speed p
		ON tt.tmc_code = p.tmc_code
WHERE DATEPART(dw, tt.measurement_tstamp) IN (2,3,4,5,6) --weekdays only
GROUP BY tt.tmc_code, DATEPART(dy, tt.measurement_tstamp)
)


SELECT
	tmc_code,
	AVG(congested_hours) AS avg_daily_conghrs,
	MIN(total_hours) AS min_day_hrs_w_data,
	AVG(total_hours) AS avg_daily_hrs_w_data
FROM all_days_cong
GROUP BY tmc_code

--drop table #ff_speed
