#!/usr/bin/env python
# coding: utf-8

# In[2]:


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


# In[3]:


### creating some boundaries for maps, and filtering to data on the bridge in the target date range
# top and bottom of bridge converted from Google Earth via https://gps-coordinates.org/coordinate-converter.php
top_lat, top_lon = (44.95254, -93.08239)
bot_lat, bot_lon = (44.93950, -93.07538)

# map bounding box corners: [southwest, northeast]
bbox = [[bot_lat+0.001, top_lon+0.0025], [top_lat-0.001, bot_lon+0.0025]]

# two markers placed on the left and right of bridge, subtracted to obtain the width (+ a little buffer)
left_lat, left_lon = (44.94633, -93.07944)
right_lat, right_lon = (44.94633, -93.07844)
width = abs(left_lon-right_lon)*1.1

# only count points if they were before construction started, or after it finished
def point_in_dates(date):
    if date < pd.datetime(year=2011, month=1, day=1) or date > pd.datetime(year=2016, month=4, day=1):
        return True
    return False

# is the lat withint the top/bottom of the bridge?
# if so, find the bridge lon at that point and see if the lon is within +/- width/2
def point_in_bounds(lat, lon):
    if not (lat>bot_lat and lat<top_lat):
        return False
    
    #lon_1 = (lat_1-lat_0)/m + lon_0
    slope = (top_lat-bot_lat)/(top_lon-bot_lon)
    lon_min = ((lat-bot_lat)/slope) + bot_lon - (width/2)
    lon_max = ((lat-bot_lat)/slope) + bot_lon + (width/2)

    if not (lon>lon_min and lon<lon_max):
        return False
    
    return True

# construct a df of only points in the date/location bounds fo rfuture calculations
df_in = pd.DataFrame(columns=['date', 'lat', 'lon', 'sev'])
for i, row in df.iterrows():
    if not point_in_dates(row.date):
        continue
    if not point_in_bounds(row.lat, row.lon):
        continue
    df_in = df_in.append(row)
df_in = df_in.sort_values('date')
df_in = df_in.reset_index(drop=True)
df_in.head()


# In[4]:


### making the map
# create map object and fit to target area
m = folium.Map(location=[left_lat, left_lon], zoom_control=False,
               tiles='cartodbpositron', width=550, height=550)
m.fit_bounds(bounds=bbox)

# helper function to spit out circles
def make_circle(lat, lon, radius, fill_opacity, date):
    c = folium.Circle(location=[lat, lon], radius=radius, fill=True, stroke=False, fill_opacity=fill_opacity,
                  fill_color='blue' if date < pd.datetime(year=2016, month=4, day=1) else 'red')
    return c

# create a legend for colors/dates
legend_html = """<div style="font-family: hack; color: black; font-size: 1.5em; width: 280px; background-color: white; padding: 5px 5px 5px 5px;">
<span style="border-radius: 50%; height: 15px; width: 15px; background-color: blue; display: inline-block"></span>
<strong> old bridge</strong><br/>2007-01-28 to 2010-12-28<br/>205 accidents/1430 days <br/>0.143 accidents/day<br/>
<br/>
<span style="border-radius: 50%; height: 15px; width: 15px; background-color: red; display: inline-block"></span>
<strong> new bridge</strong><br/>2016-04-03 to 2018-12-26<br/>391 accidents/997 days <br/>0.392 accidents/day<br/>
</div>"""
legend = folium.Marker(location=[44.9538, -93.0769],
                       icon=folium.DivIcon(html=legend_html))
legend.add_to(m)

# now add a point for each row in the data
for i, row in df_in.iterrows():
    # uncomment to specifically view accidents with serious injury
    #if not row.sev == 2:
    #    continue
    c = make_circle(lat=row.lat, lon=row.lon, radius=15, fill_opacity=0.3, date=row.date)
    c.add_to(m)
m


# In[5]:


### create dataframe copy, code by before/after, bin dates by year-quarter
df2 = df_in.copy()
df2['state'] = np.where(df2['date']<pd.datetime(year=2011, month=1, day=1), 'before', 'after')
df2['state'] = df2['state'].astype('category')
df2['state'] = df2['state'].cat.reorder_categories(['before', 'after'])
df2['x'] = df2['date'].dt.year.astype('str') + '-Q' + df2['date'].dt.quarter.astype('str')
df2.head()


# In[6]:


### look at accident totals and rate before vs. after bridge project
df_summ = df2.groupby('state', as_index=False).agg({'date': ['count', 'min', 'max']})
df_summ['delta'] = (df_summ['date']['max']-df_summ['date']['min']).dt.days
df_summ['rate'] = df_summ['date']['count']/df_summ['delta']
print(float(df_summ.iloc[1].rate/df_summ.iloc[0].rate))
df_summ


# In[7]:


### bar plot of accidents by quarter
p = ggplot(df2, aes(x='x')) + geom_bar(color='white', position='dodge') + facet_wrap('~state', scales='free_x')
p = p + scale_x_discrete(name='date')
p = p + theme_bw() + theme(axis_text_x=element_text(angle=315, hjust=0), subplots_adjust={'wspace': 0.15})
p.save('accidents-before-vs-after.png', dpi=150, width=10, height=6)
p


# In[8]:


### statistics on severity
df2_sev = df2.groupby(['state', 'sev']).agg({'date': 'count'})
df2_sev['perc'] = df2_sev.groupby(level=0).date.apply(lambda x: x/x.sum())
df2_sev = df2_sev.reset_index()
df2_sev.columns = ['state', 'sev', 'count', 'percent']
df2_sev

