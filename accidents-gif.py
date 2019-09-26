#!/usr/bin/env python
# coding: utf-8

# In[3]:


import folium
import numpy as np
import pandas as pd
import subprocess
import time
import IPython.display

from plotnine import *
from selenium import webdriver

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


# In[5]:


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

# is the point within the top/bottom of the bridge?
# if so, find the bridge lon at that lat and see if the point is within lon +/- width/2
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


# In[6]:


### gif: smooth decreasing radius approach, by week
# starting and ending size/opacity, and number of steps between
steps = 4
rad_max = 60
rad_min = 17
rad_step = (rad_max-rad_min)/steps
opa_max = 0.9
opa_min = 0.3
opa_step = (opa_max-opa_min)/steps

# construct list of dates by month; remove the dates during constructions
dates = [pd.Timestamp(year=y, month=m, day=1) for y in range(2007, 2019) for m in range(1, 13)]
dates = [d for d in dates if d<pd.Timestamp(year=2011, month=1, day=1) or d>pd.Timestamp(year=2016, month=4, day=1)]

# create entries for the radius/opacity steps to take for each point passed
def circle_decay(row, dates):
    born = next(x for x in reversed(dates) if x < row.date)
    dates = [born+pd.Timedelta(days=i) for i in range(steps+1)]
    rads = [rad_max-(rad_step*i) for i in range(steps+1)]
    opas = [opa_max-(opa_step*i) for i in range(steps+1)]
    
    return pd.DataFrame({'born': [born]*(steps+1), 'date': dates, 'rad': rads, 'opa': opas,
                         'lat': [float(row.lat)]*(steps+1), 'lon': [float(row.lon)]*(steps+1)})

# add stepped entries for each df_in row
df_decay = pd.concat([circle_decay(row, dates) for _, row in df_in.iterrows()])
df_decay = df_decay.sort_values(['date', 'rad']).reset_index(drop=True)
df_decay.head(6)


# In[11]:


### creating gif images, note requirements!
# - fill in the paths below where noted and make sure they exist
# - this uses selenium which needs to be installed
# - the geckodriver binary is expected to exist in the directory (hint: just create a symlink to it)

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

# helper function to spit out circles
def make_circle(lat, lon, radius, fill_opacity, date):
    c = folium.Circle(location=[lat, lon], radius=radius, fill=True, stroke=False, fill_opacity=fill_opacity,
                  fill_color='blue' if date < pd.datetime(year=2016, month=4, day=1) else 'red')
    return c

# create map object and fit to target area
m = folium.Map(location=[left_lat, left_lon], zoom_control=False,
               tiles='cartodbpositron', width=550, height=550)
m.fit_bounds(bounds=bbox)
legend.add_to(m)
date_html = """<div style="font-family: hack; color: black; font-size: 1.5em;">2007-01</div>"""
date_legend = folium.Marker(location=[44.9383, -93.0877], icon=folium.DivIcon(html=date_html))
date_legend.add_to(m)

# fg to hold dots that have reached final size
fg = folium.FeatureGroup()

# initialize selenium
browser = webdriver.Firefox()
browser.set_window_size(550, 625)

# change this path!
path = '/path/to/this/repo'
m.save('{}/map.html'.format(path))
browser.get('file://{}/map.html'.format(path))
time.sleep(5)

# when we save the screenshots, they live in the gif_fade sub directory; creat it!
browser.save_screenshot('{}/gif_fade/{}.png'.format(path, '0-0-0'))

for date in df_decay.date.unique():
    # replicate map m, add feature group (small dots)
    m = folium.Map(location=[left_lat, left_lon], zoom_control=False,
               tiles='cartodbpositron', width=550, height=550)
    m.fit_bounds(bounds=bbox)
    legend.add_to(m)
    fg.add_to(m)
    
    date_html = """<div style="font-family: hack; color: black; font-size: 1.5em;">{}-{:02d}</div>""".format(pd.Timestamp(date).year, pd.Timestamp(date).month)
    date_legend = folium.Marker(location=[44.9383, -93.0877], icon=folium.DivIcon(html=date_html))
    date_legend.add_to(m)

    # process points for this date
    df_sub = df_decay.loc[df_decay.date==date]
    done_dots = []
    for i, row in df_sub.iterrows():
        c = make_circle(lat=row.lat, lon=row.lon, radius=row.rad, fill_opacity=row.opa, date=row.born)
        c.add_to(m)
        if row.rad == rad_min:
            done_dots.append(c)
    
    # save m, then open and screenshot with selenium
    m.save('{}/map.html'.format(path))
    browser.get('file://{}/map.html'.format(path))
    time.sleep(1)
    browser.save_screenshot('{}/gif_fade/{}.png'.format(path, pd.to_datetime(date).strftime('%Y-%m-%d')))
    
    # roll over minimized dots into fg
    for c in done_dots:
        c.add_to(fg)
    
if browser:
    browser.quit()


# In[ ]:


### command to spit out a long command to add all images into a gif
# - this relies on imagemagick
# - originally tried to scale the days between accidents to a target gif length
# - gifs have a minimum frame delay, so the animations ended up too long
# - ultimately went with `-delay 1` for all frames, but the other approach is here for those interested

# get unique dates and time between them in days
df_gif = pd.DataFrame({'date': list(df_decay.date.unique())})
df_gif['delta'] = abs(df_gif.date.diff(periods=-1).dt.days)

# the biggest stretch will be for the rows spanning the start/end of construction; re-value this
print(df_gif.loc[df_gif.delta == df_gif.delta.max()])
df_gif.loc[df_gif.delta == df_gif.delta.max(), 'delta'] = 21

# format dates as %Y-%m-%d format, insert initial and fix NaT diff
df_gif.date = pd.to_datetime(df_decay.date.unique()).strftime('%Y-%m-%d')
df_gif.loc[len(df_gif)-1, 'delta'] = 20

print(df_gif.head())

### create imagemagick command to create gif
# target gif runtime in increments of 10ms (100=1sec), for example for a target of 30sec:
runtime = 30*100

# time scale factor = runtime/total days spanned (sum of deltas)
scale = runtime/df_gif.delta.sum()

cmd_list = ['convert', '-loop', '1', '-delay', '50', './gif_fade/0-0-0.png']
for i, row in df_gif.iterrows():
    # accidents on that day, flash for 1 day
    cmd_list.append('-delay')
    # pause between before/after segments; note: this is hacky and dependent on number of gif steps
    if row.date=='2010-12-05':
        cmd_list.append('100')
    else:
        #cmd_list.append('{}'.format(row.delta)) ### here was the variable delta
        cmd_list.append('1')
    cmd_list.append('./gif_fade/{}.png'.format(row.date))

cmd_list.extend(['./gif_fade/animation_weighted.gif'])

# run command to combine all pngs into gif
#subprocess.call(cmd_list)

