This repo houses traffic crash dates, locations, and severity scores for Ramsey County
in MN. The data was obtained via the Dept. of Public Safety in an attempt to understand if
the [Layfayette Bridge project](https://en.wikipedia.org/wiki/Lafayette_Bridge) has
contributed to an increase in crashes.

Anecdotal evidence (e.g. a daily commute on Hwy 52 from Plato to I-94E) suggests that the
new layout is poorly designed, creating vast differences in speed and no clear
understanding of where to merge.

The data confirms that crashes are occurring on the bridge at a higher rate since the
completion of the project in April 2016, showing an 2.7x increase.

```
|        |     *date* |            |             | *crashes* |            |
| period |      start |        end | range, days |     count | count/days |
|--------+------------+------------+-------------+-----------+------------|
| before | 2007-01-28 | 2010-12-28 |        1430 |       205 |      0.143 |
| after  | 2016-04-03 | 2018-12-26 |         997 |       391 |      0.392 |

```

**crashes by year/quarter before and after the bridge redo**

![crashes-before-vs-after](./pics/crashes-before-vs-after.png)

**gif of crashes by month on the old/new bridge**

![crash-gif](./gif/crashes.gif)
