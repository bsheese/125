# Data for CS/DS 125 module 08 and its pair activities

These files are kept here so that the notebooks do not depend on outside sites. They were copied from the [seaborn-data](https://github.com/mwaskom/seaborn-data) repository, whose README warns that its files may change or be removed. Its listed origin is given for each file below. That repository also says that some of its datasets were modified from their original sources, and it does not state a license, so check the original source before using a file outside this course.

| File | What one row is | Origin listed by seaborn-data | Changes made here |
|---|---|---|---|
| `data_geyser.csv` | One eruption of Old Faithful | [R `faithful` dataset](https://stat.ethz.ch/R-manual/R-devel/library/datasets/html/faithful.html) | None |
| `data_penguins.csv` | One penguin | [palmerpenguins](https://github.com/allisonhorst/penguins) | None |
| `data_anscombe.csv` | One point in Anscombe's quartet | [Anscombe's quartet](https://en.wikipedia.org/wiki/Anscombe%27s_quartet) | None |
| `data_healthexp.csv` | One country in one year | [Our World in Data](https://ourworldindata.org/grapher/life-expectancy-vs-health-expenditure) | None |
| `data_mpg.csv` | One car model | [data.world cars data](https://data.world/dataman-udit/cars-data) | None |
| `data_diamonds.csv` | One diamond | [ggplot2 `diamonds`](https://ggplot2.tidyverse.org/reference/diamonds.html) | Kept `carat`, `cut`, `color`, `clarity` and `price` to reduce the file size |
| `data_taxis.csv` | One New York City taxi ride, March 2019 | [NYC Taxi and Limousine Commission trip records](https://www1.nyc.gov/site/tlc/about/tlc-trip-record-data.page) | None |
| `data_flights.csv` | Airline passengers in one month | Not listed; the seaborn `flights` dataset | Added a `date` column made from `year` and `month` |
