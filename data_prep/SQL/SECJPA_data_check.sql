USE NPMRDS

SELECT
	tmc,
	DATEPART(mm,measurement_tstamp) AS month,
	DATEPART(dw,measurement_tstamp) AS dow,
	COUNT(*) AS epochs
FROM npmrds_2018_all_tmcs_txt tmc
	JOIN npmrds_2018_alltmc_paxveh tt
		ON tmc.tmc = tt.tmc_code
WHERE tmc.road LIKE 'GRANT LINE RD'
GROUP BY 	tmc,
	DATEPART(mm,measurement_tstamp),
	DATEPART(dw,measurement_tstamp)
ORDER BY tmc, DATEPART(mm,measurement_tstamp), DATEPART(dw,measurement_tstamp)