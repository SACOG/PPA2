SELECT *
FROM npmrds_2018_alltmc_paxtruck_comb
WHERE tmc_code = '105-16235'
AND DATEPART(hh, measurement_tstamp) = 19
--AND DATENAME(dw, measurement_tstamp) NOT IN ('Saturday', 'Sunday')