USE NPMRDS
GO

--test table
create table #tempdow (
dayname varchar(10)
)
;
--test table values
INSERT INTO #tempdow VALUES ('Tuesday')
INSERT INTO #tempdow VALUES ('Wednesday')
INSERT INTO #tempdow VALUES ('Thursday')
INSERT INTO #tempdow VALUES ('Friday')
INSERT INTO #tempdow VALUES ('Saturday')
INSERT INTO #tempdow VALUES ('Sunday')

--declare the table that will be the list of values that you want to filter to (in this case, only choosing weekdays)
DECLARE @weekdays TABLE (weekdayname VARCHAR(9))
	INSERT INTO @weekdays VALUES ('Monday')
	INSERT INTO @weekdays VALUES ('Tuesday')
	INSERT INTO @weekdays VALUES ('Wednesday')
	INSERT INTO @weekdays VALUES ('Thursday')
	INSERT INTO @weekdays VALUES ('Friday')

--test run
SELECT * from #tempdow where dayname in (select weekdayname from @weekdays)

SELECT * from #tempdow 