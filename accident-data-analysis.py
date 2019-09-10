import folium
import numpy as np
import pandas as pd

from plotnine import *

def read_data():
    df1 = pd.read_excel('./public-accident-data.xlsx', sheet_name='2007-2015',
                        usecols=[3, 4, 5, 8], names=['date', 'lat', 'lon', 'sev'])
    df2 = pd.read_excel('./public-accident-data.xlsx', sheet_name='2016-2018',
                        usecols=[3, 4, 5, 8], names=['date', 'lat', 'lon', 'sev'])
    # join data sets
    df = df1.append(df2).reset_index()
    # remove rows with missing data, then convert lat/lon to numeric
    df = df[df.lon != '.']
    df['lat'] = df['lat'].astype(float)
    df['lon'] = df['lon'].astype(float)
    # with data converted, remove any rows missing lat/lon
    df = df[df.lat != 0]
    # save out in .csv for faster future reads
    df.to_csv('public-accident-data.csv', index=False)

# run this if input changes
#read_data()
df = pd.read_csv('public-accident-data.csv', converters={'date': pd.to_datetime})


# bounding box ranges
bbox = [[44.92, -93.09], [44.96, -93.04]]
lat = [44.92, 44.96]
lon = [-93.1, -93.05]

# create map object and fit to target area
m = folium.Map(location=[np.mean(lat), np.mean(lon)])
m.fit_bounds(bounds=bbox)

corners = [(44.9380, -93.072),
           (44.952,  -93.080),
           (44.952,  -93.0846),
           (44.9380, -93.0768)]
lat_min = corners[0][0]
lat_max = corners[1][0]


def point_in_dates(date):
    if date < pd.datetime(year=2011, month=1, day=1) or date > pd.datetime(year=2016, month=4, day=1):
        return True
    return False

def point_in_bounds(lat, lon):
    slope_left = (corners[2][0]-corners[3][0]) / (corners[2][1]-corners[3][1])
    slope_right = (corners[1][0]-corners[0][0]) / (corners[1][1]-corners[0][1])
    lon_min = corners[3][1]+(lat-lat_min)/slope_left
    lon_max = corners[0][1]+(lat-lat_min)/slope_right
    
    if lat>lat_min and lat<lat_max and lon>lon_min and lon<lon_max:
        return True
    return False

# used for troubleshooting corners
#combos.append([44.95, -93.074])
#for combo in combos:
#    point_in_bounds(combo[0], combo[1])
#    folium.Marker(location=[combo[0], combo[1]]).add_to(m)
df_in = pd.DataFrame(columns=['date', 'lat', 'lon', 'sev'])
for i, row in df.iterrows():
    if not point_in_dates(row.date):
        continue
    if not point_in_bounds(row.lat, row.lon):
        continue
    folium.Marker(location=[row.lat, row.lon],
                  icon=folium.Icon(color='blue' if row.date < pd.datetime(year=2016, month=4, day=1) else 'red')).add_to(m)
    df_in = df_in.append(row)

m.save('accident-map.html')

### summarizing the data in our target parallelogram
# create a new grouping column based on project start date
df2 = df_in.copy()
df2['state'] = np.where(df2['date']<pd.datetime(year=2011, month=1, day=1), 'before', 'after')
df2['state'] = df2['state'].astype('category')
df2['state'] = df2['state'].cat.reorder_categories(['before', 'after'])
# create a column for plotting by quarter
df2['x'] = df2['date'].dt.year.astype('str') + '-Q' + df2['date'].dt.quarter.astype('str')

# aggregate data by before/after and show dates, date ranges, and accident counts
df2.groupby('state').agg({'date': ['count', 'min', 'max',
                                   lambda dates: max(dates)-min(dates)]})


# bar plot of accidents by year-quarter
p = ggplot(df2, aes(x='x')) + geom_bar(color='white', position='dodge') + facet_wrap('~state', scales='free_x')
p = p + scale_x_discrete(name='date')
p = p + theme_bw() + theme(axis_text_x=element_text(angle=315, hjust=0), subplots_adjust={'wspace': 0.15})
p.save('accidents-before-vs-after.png', dpi=150, width=10, height=6)
p

### looking at severity statistics
df2_sev = df2.groupby(['state', 'sev']).agg({'date': 'count'})
df2_sev['perc'] = df2_sev.groupby(level=0).date.apply(lambda x: x/x.sum())
df2_sev = df2_sev.reset_index()
df2_sev.columns = ['state', 'sev', 'count', 'percent']
df2_sev
