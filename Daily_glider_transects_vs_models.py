#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun  4 09:51:35 2019

@author: aristizabal
"""

#%% User input

# lat and lon bounds
lon_lim = [-110.0,-10.0]
lat_lim = [15.0,45.0]

# urls 
url_glider = 'https://data.ioos.us/gliders/erddap'
url_GOFS = 'http://tds.hycom.org/thredds/dodsC/GLBv0.08/expt_93.0/ts3z'
url_RTOFS = 'https://nomads.ncep.noaa.gov:9090/dods/rtofs/rtofs_global'

# Bathymetry file
bath_file = '/Users/aristizabal/Desktop/MARACOOS_project/Maria_scripts/nc_files/GEBCO_2014_2D_-100.0_0.0_-10.0_70.0.nc'

#%%

from erddapy import ERDDAP
import pandas as pd

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import cmocean

from datetime import datetime, timedelta

import numpy as np
import xarray as xr
import netCDF4

#%% Get time bounds for the previous day

te = datetime.today() 
tend = datetime(te.year,te.month,te.day)

#ti = datetime.today() - timedelta(1)
ti = datetime.today() - timedelta(2)
tini = datetime(ti.year,ti.month,ti.day)

#%% Look for datasets in IOOS glider dac
 
print('Looking for glider data sets')
e = ERDDAP(server = url_glider)

# Grab every dataset available
datasets = pd.read_csv(e.get_search_url(response='csv', search_for='all'))

# Search constraints
kw = {
    'min_lon': lon_lim[0],
    'max_lon': lon_lim[1],
    'min_lat': lat_lim[0],
    'max_lat': lat_lim[1],
    'min_time': tini.strftime('%Y-%m-%dT%H:%M:%SZ'),
    'max_time': tend.strftime('%Y-%m-%dT%H:%M:%SZ'),
}

search_url = e.get_search_url(response='csv', **kw)
#print(search_url)

# Grab the results
search = pd.read_csv(search_url)

# Extract the IDs
gliders = search['Dataset ID'].values

msg = 'Found {} Glider Datasets:\n\n{}'.format
print(msg(len(gliders), '\n'.join(gliders)))
    
# Setting constraints
constraints = {
        'time>=': tini,
        'time<=': tend,
        'latitude>=': lat_lim[0],
        'latitude<=': lat_lim[1],
        'longitude>=': lon_lim[0],
        'longitude<=': lon_lim[1],
        }

variables = [
        'depth',
        'latitude',
        'longitude',
        'time',
        'temperature',
        'salinity'
        ]

e = ERDDAP(
        server=url_glider,
        protocol='tabledap',
        response='nc'
        )

#%% Read GOFS 3.1 output

print('Retrieving coordinates from GOFS 3.1')
GOFS31 = xr.open_dataset(url_GOFS,decode_times=False)
    
latGOFS = GOFS31.lat[:]
lonGOFS = GOFS31.lon[:]
depthGOFS = GOFS31.depth[:]
ttGOFS = GOFS31.time
tGOFS = netCDF4.num2date(ttGOFS[:],ttGOFS.units) 

#tmin = datetime.datetime.strptime(date_ini,'%Y-%m-%dT%H:%M:%SZ')
#tmax = datetime.datetime.strptime(date_end,'%Y-%m-%dT%H:%M:%SZ')

tmin = tini
tmax = tend

oktimeGOFS = np.where(np.logical_and(tGOFS >= tmin, tGOFS <= tmax))
timeGOFS = tGOFS[oktimeGOFS]

#%% Read RTOFS output

print('Retrieving coordinates from RTOFS')
#url_RTOFS1 = url_RTOFS + tend.strftime('%Y%m%d') + '/rtofs_glo_3dz_nowcast_6hrly_us_east'
#url_RTOFS1 = url_RTOFS + tend.strftime('%Y%m%d') + '/rtofs_glo_3dz_nowcast_daily_temp'
url_RTOFS_temp = url_RTOFS + tend.strftime('%Y%m%d') + '/rtofs_glo_3dz_nowcast_daily_temp'
url_RTOFS_salt = url_RTOFS + tend.strftime('%Y%m%d') + '/rtofs_glo_3dz_nowcast_daily_salt'
RTOFS_temp = xr.open_dataset(url_RTOFS_temp ,decode_times=False)
RTOFS_salt = xr.open_dataset(url_RTOFS_salt ,decode_times=False)
    
latRTOFS = RTOFS_temp.lat[:]
lonRTOFS = RTOFS_temp.lon[:]
depthRTOFS = RTOFS_temp.lev[:]
ttRTOFS = RTOFS_temp.time[:]
tRTOFS = netCDF4.num2date(ttRTOFS[:],ttRTOFS.units) 

#tmin = datetime.datetime.strptime(date_ini,'%Y-%m-%dT%H:%M:%SZ')
#tmax = datetime.datetime.strptime(date_end,'%Y-%m-%dT%H:%M:%SZ')

tmin = tini
tmax = tend
oktimeRTOFS = np.where(np.logical_and(tRTOFS >= tmin, tRTOFS <= tmax))   
timeRTOFS = mdates.num2date(mdates.date2num(tRTOFS[oktimeRTOFS]))

#%% Reading bathymetry data

ncbath = xr.open_dataset(bath_file)
bath_lat = ncbath.variables['lat'][:]
bath_lon = ncbath.variables['lon'][:]
bath_elev = ncbath.variables['elevation'][:]

'''
oklatbath = np.logical_and(bath_lat >= lat_lim[0],bath_lat <= lat_lim[-1])
oklonbath = np.logical_and(bath_lon >= lon_lim[0],bath_lon <= lon_lim[-1])

bath_latsub = bath_lat[oklatbath]
bath_lonsub = bath_lon[oklonbath]
bath_elevs = bath_elev[oklatbath,:]
bath_elevsub = bath_elevs[:,oklonbath] 
'''  
  
#%%   

for id in gliders:
    print('Reading ' + id )
    e.dataset_id = id
    e.constraints = constraints
    e.variables = variables
    
    # Converting glider data to data frame
    df = e.to_pandas(
            index_col='time (UTC)',
            parse_dates=True,
            skiprows=(1,)  # units information can be dropped.
            ).dropna()
    
    # Coverting glider vectors into arrays
    timeg, ind = np.unique(df.index.values,return_index=True)
    latg = np.unique(df['latitude (degrees_north)'].values)
    long = np.unique(df['longitude (degrees_east)'].values)

    dg = df['depth (m)'].values
    #vg = df['temperature (degree_Celsius)'].values
    tg = df[df.columns[3]].values
    sg = df[df.columns[4]].values
    
    delta_z = 0.3
    zn = np.int(np.round(np.max(dg)/delta_z))

    depthg = np.empty((zn,len(timeg)))
    depthg[:] = np.nan
    tempg = np.empty((zn,len(timeg)))
    tempg[:] = np.nan
    saltg = np.empty((zn,len(timeg)))
    saltg[:] = np.nan
    
    # Grid variables
    depthg_gridded = np.arange(0,np.nanmax(dg),delta_z)
    tempg_gridded = np.empty((len(depthg_gridded),len(timeg)))
    tempg_gridded[:] = np.nan
    saltg_gridded = np.empty((len(depthg_gridded),len(timeg)))
    saltg_gridded[:] = np.nan
    
    for i,ii in enumerate(ind):
        if i < len(timeg)-1:
            depthg[0:len(dg[ind[i]:ind[i+1]]),i] = dg[ind[i]:ind[i+1]] 
            tempg[0:len(tg[ind[i]:ind[i+1]]),i] = tg[ind[i]:ind[i+1]]
            saltg[0:len(sg[ind[i]:ind[i+1]]),i] = sg[ind[i]:ind[i+1]]
        else:
            depthg[0:len(dg[ind[i]:len(dg)]),i] = dg[ind[i]:len(dg)] 
            tempg[0:len(tg[ind[i]:len(tg)]),i] = tg[ind[i]:len(tg)]
            saltg[0:len(sg[ind[i]:len(sg)]),i] = sg[ind[i]:len(sg)]

    for t,tt in enumerate(timeg):
        depthu,oku = np.unique(depthg[:,t],return_index=True)
        tempu = tempg[oku,t]
        saltu = saltg[oku,t]
        okdd = np.isfinite(depthu)
        depthf = depthu[okdd]
        tempf = tempu[okdd]
        saltf = saltu[okdd]
        
        okt = np.isfinite(tempf)
        if np.sum(okt) < 3:
            tempg_gridded[:,t] = np.nan
        else:
            okd = depthg_gridded < np.max(depthf[okt])
            tempg_gridded[okd,t] = np.interp(depthg_gridded[okd],depthf[okt],tempf[okt])
            
        oks = np.isfinite(saltf)
        if np.sum(oks) < 3:
            saltg_gridded[:,t] = np.nan
        else:
            okd = depthg_gridded < np.max(depthf[oks])
            saltg_gridded[okd,t] = np.interp(depthg_gridded[okd],depthf[oks],saltf[oks])
    
    # Conversion from glider longitude and latitude to GOFS convention
    target_lon = np.empty((len(long),))
    target_lon[:] = np.nan
    for i,ii in enumerate(long):
        if ii < 0: 
            target_lon[i] = 360 + ii
        else:
            target_lon[i] = ii
    target_lat = latg
    
    #oktimeGOFS = np.where(np.logical_and(mdates.date2num(tGOFS) >= mdates.date2num(timeg[0]),\
    #                                     mdates.date2num(tGOFS) <= mdates.date2num(timeg[-1])))
    #timeGOFS = tGOFS[oktimeGOFS]
    #
    #oktimeRTOFS = np.where(np.logical_and(mdates.date2num(tRTOFS) >= mdates.date2num(timeg[0]),\
    #                                      mdates.date2num(tRTOFS) <= mdates.date2num(timeg[-1])))
    #timeRTOFS = mdates.num2date(mdates.date2num(tRTOFS[oktimeRTOFS]))

    # Changing times to timestamp
    tstamp_glider = [mdates.date2num(timeg[i]) for i in np.arange(len(timeg))]
    tstamp_GOFS = [mdates.date2num(timeGOFS[i]) for i in np.arange(len(timeGOFS))]
    tstamp_RTOFS = [mdates.date2num(timeRTOFS[i]) for i in np.arange(len(timeRTOFS))]

    # interpolating glider lon and lat to lat and lon on GOFS 3.1 time
    sublonGOFS=np.interp(tstamp_GOFS,tstamp_glider,target_lon)
    sublatGOFS=np.interp(tstamp_GOFS,tstamp_glider,target_lat)

    # getting the model grid positions for sublonm and sublatm
    oklonGOFS=np.round(np.interp(sublonGOFS,lonGOFS,np.arange(len(lonGOFS)))).astype(int)
    oklatGOFS=np.round(np.interp(sublatGOFS,latGOFS,np.arange(len(latGOFS)))).astype(int)
    
    # Getting glider transect from GOFS 3.1
    print('Getting glider transect from GOFS 3.1. If it breaks is because GOFS 3.1 server is not responding')
    target_tempGOFS = np.empty((len(depthGOFS),len(oktimeGOFS[0])))
    target_tempGOFS[:] = np.nan
    for i in range(len(oktimeGOFS[0])):
        print(len(oktimeGOFS[0]),' ',i)
        target_tempGOFS[:,i] = GOFS31.variables['water_temp'][oktimeGOFS[0][i],:,oklatGOFS[i],oklonGOFS[i]]
    target_tempGOFS[target_tempGOFS < -100] = np.nan
    
    target_saltGOFS = np.empty((len(depthGOFS),len(oktimeGOFS[0])))
    target_saltGOFS[:] = np.nan
    for i in range(len(oktimeGOFS[0])):
        print(len(oktimeGOFS[0]),' ',i)
        target_saltGOFS[:,i] = GOFS31.variables['salinity'][oktimeGOFS[0][i],:,oklatGOFS[i],oklonGOFS[i]]
    target_saltGOFS[target_saltGOFS < -100] = np.nan
    
    # interpolating glider lon and lat to lat and lon on RTOFS time
    sublonRTOFS=np.interp(tstamp_RTOFS,tstamp_glider,target_lon)
    sublatRTOFS=np.interp(tstamp_RTOFS,tstamp_glider,target_lat)

    # getting the model grid positions for sublonm and sublatm
    oklonRTOFS=np.round(np.interp(sublonRTOFS,lonRTOFS,np.arange(len(lonRTOFS)))).astype(int)
    oklatRTOFS=np.round(np.interp(sublatRTOFS,latRTOFS,np.arange(len(latRTOFS)))).astype(int)    
    
    # Getting glider transect from RTOFS
    print('Getting glider transect from RTOFS')
    target_tempRTOFS = np.empty((len(depthRTOFS),len(oktimeRTOFS[0])))
    target_tempRTOFS[:] = np.nan
    for i in range(len(oktimeRTOFS[0])):
        print(len(oktimeRTOFS[0]),' ',i)
        target_tempRTOFS[:,i] = RTOFS_temp.variables['temperature'][oktimeRTOFS[0][i],:,oklatRTOFS[i],oklonRTOFS[i]]
    target_tempRTOFS[target_tempRTOFS < -100] = np.nan
     
    target_saltRTOFS = np.empty((len(depthRTOFS),len(oktimeRTOFS[0])))
    target_saltRTOFS[:] = np.nan
    for i in range(len(oktimeRTOFS[0])):
        print(len(oktimeRTOFS[0]),' ',i)
        target_saltRTOFS[:,i] = RTOFS_salt.variables['salinity'][oktimeRTOFS[0][i],:,oklatRTOFS[i],oklonRTOFS[i]]
    target_saltRTOFS[target_saltRTOFS < -100] = np.nan    
    
    min_temp = np.floor(np.min([np.nanmin(df[df.columns[3]]),np.nanmin(target_tempGOFS),np.nanmin(target_tempRTOFS)]))
    max_temp = np.ceil(np.max([np.nanmax(df[df.columns[3]]),np.nanmax(target_tempGOFS),np.nanmax(target_tempRTOFS)]))
    
    min_salt = np.floor(np.min([np.nanmin(df[df.columns[4]]),np.nanmin(target_saltGOFS),np.nanmin(target_saltRTOFS)]))
    max_salt = np.ceil(np.max([np.nanmax(df[df.columns[4]]),np.nanmax(target_saltGOFS),np.nanmax(target_saltRTOFS)]))

    # plot temperature
    fig, ax = plt.subplots(figsize=(14, 12))
    folder = '/Users/aristizabal/Desktop/MARACOOS_project/Maria_scripts/Figures/Model_glider_comp/'
        
    grid = plt.GridSpec(4, 5, wspace=0.4, hspace=0.3)

    # Scatter plot
    ax = plt.subplot(grid[0, :4])
    kw = dict(s=30, c=df[df.columns[3]], marker='*', edgecolor='none')
    cs = ax.scatter(df.index, -df['depth (m)'], **kw, cmap=cmocean.cm.thermal)
    cs.set_clim(min_temp,max_temp)
    ax.set_xlim(tini,tend)
    #ax.set_xlim(df.index[0], df.index[-1])
    xfmt = mdates.DateFormatter('%H:%Mh\n%d-%b')
    ax.xaxis.set_major_formatter(xfmt)
    ax.set_xticklabels(' ')        
    cbar = fig.colorbar(cs, orientation='vertical')
    cbar.ax.set_ylabel('($^oC$)',fontsize=14,labelpad=15)
    ax.set_ylabel('Depth (m)',fontsize=14)
    plt.title('Along Track Temperature ' + id)
      
    
    nlevels = max_temp - min_temp + 1
    kw = dict(levels = np.linspace(min_temp,max_temp,nlevels))
    ax = plt.subplot(grid[1, :4])
    #plt.contour(timeg,-depthg_gridded,varg_gridded,colors = 'lightgrey',**kw)
    cs = plt.contourf(timeg,-depthg_gridded,tempg_gridded,cmap=cmocean.cm.thermal,**kw)
    if np.logical_and(min_temp<=26.0,max_temp>=26.0): 
        plt.contour(timeg,-depthg_gridded,tempg_gridded,levels=[26],colors='k')
    cs = fig.colorbar(cs, orientation='vertical') 
    cs.ax.set_ylabel('($^oC$)',fontsize=14,labelpad=15)        
    ax.set_xlim(tini,tend)
    ax.set_ylabel('Depth (m)',fontsize=14)
    ax.set_xticklabels(' ')
    plt.title('Along Track Temperature ' + id)
    
    
    ax = plt.subplot(grid[2, :4])    
    #plt.contour(timeg,-depthg_gridded,varg_gridded,colors = 'lightgrey',**kw)
    cs = plt.contourf(timeGOFS,-depthGOFS,target_tempGOFS,cmap=cmocean.cm.thermal,**kw)
    if np.logical_and(min_temp<=26.0,max_temp>=26.0): 
        plt.contour(timeGOFS,-depthGOFS,target_tempGOFS,[26],colors='k')
    cs = fig.colorbar(cs, orientation='vertical') 
    cs.ax.set_ylabel('($^oC$)',fontsize=14,labelpad=15)
    ax.set_xlim(tini,tend)
    ax.set_ylim(-np.max(df['depth (m)']), 0)
    ax.set_ylabel('Depth (m)',fontsize=14)
    xfmt = mdates.DateFormatter('%H:%Mh\n%d-%b')
    ax.xaxis.set_major_formatter(xfmt)
    ax.set_xticklabels(' ')  
    plt.title('Along Track Temperature GOFS 3.1')
    
    ax = plt.subplot(grid[3, :4])    
    #plt.contour(timeg,-depthg_gridded,varg_gridded,colors = 'lightgrey',**kw)
    cs = plt.contourf(tstamp_RTOFS,-depthRTOFS,target_tempRTOFS,cmap=cmocean.cm.thermal,**kw)
    if np.logical_and(min_temp<=26.0,max_temp>=26.0): 
        plt.contour(tstamp_RTOFS,-depthRTOFS,target_tempRTOFS,[26],colors='k')

    cs = fig.colorbar(cs, orientation='vertical') 
    cs.ax.set_ylabel('($^oC$)',fontsize=14,labelpad=15)
    ax.set_xlim(tini,tend)
    ax.set_ylim(-np.max(df['depth (m)']), 0)
    ax.set_ylabel('Depth (m)',fontsize=14)
    xfmt = mdates.DateFormatter('%H:%Mh\n%d-%b')
    ax.xaxis.set_major_formatter(xfmt)
    plt.title('Along Track Temperature RTOFS')
    
    oklatbath = np.logical_and(bath_lat >= np.min(latg)-5,bath_lat <= np.max(latg)+5)
    oklonbath = np.logical_and(bath_lon >= np.min(long)-5,bath_lon <= np.max(long)+5)

    bath_latsub = bath_lat[oklatbath]
    bath_lonsub = bath_lon[oklonbath]
    bath_elevs = bath_elev[oklatbath,:]
    bath_elevsub = bath_elevs[:,oklonbath] 
    
    ax = plt.subplot(grid[1, 4:])
    plt.contour(bath_lonsub,bath_latsub,bath_elevsub,[0],colors='k')
    plt.contourf(bath_lonsub,bath_latsub,bath_elevsub,cmap='Blues_r')
    plt.contourf(bath_lonsub,bath_latsub,bath_elevsub,[0,10000],colors='seashell')
    #plt.yticks([])
    #plt.xticks([])
    plt.axis([np.min(long)-5,np.max(long)+5,np.min(latg)-5,np.max(latg)+5])
    plt.plot(long,latg,'.k')
    plt.title('Track ' + id)
    #plt.axis('equal')
    
    #folder = '/Users/aristizabal/Desktop/MARACOOS_project/Maria_scripts/Figures/Model_glider_comp/'
    folder = '/Volumes/hurricane/Hurricane_season_2019/' + (ti+timedelta(1)).strftime('%b-%d') + '/'
    file = folder + 'along_track_temp_' + id + '_' + str(tini).split()[0] + '_' + str(tend).split()[0]
    #plt.savefig(file,bbox_inches = 'tight',pad_inches = 0.1) 
        
     
    # plot salinity
    fig, ax = plt.subplots(figsize=(14, 12))
    folder = '/Users/aristizabal/Desktop/MARACOOS_project/Maria_scripts/Figures/Model_glider_comp/'
        
    grid = plt.GridSpec(4, 5, wspace=0.4, hspace=0.3)

    # Scatter plot
    ax = plt.subplot(grid[0, :4])
    kw = dict(s=30, c=df[df.columns[4]], marker='*', edgecolor='none')
    cs = ax.scatter(df.index, -df['depth (m)'], **kw, cmap=cmocean.cm.haline)
    cs.set_clim(min_salt,max_salt)
    ax.set_xlim(tini,tend)
    #ax.set_xlim(df.index[0], df.index[-1])
    xfmt = mdates.DateFormatter('%H:%Mh\n%d-%b')
    ax.xaxis.set_major_formatter(xfmt)
    ax.set_xticklabels(' ')        
    cbar = fig.colorbar(cs, orientation='vertical')
    ax.set_ylabel('Depth (m)',fontsize=14)
    plt.title('Along Track Salinity ' + id)
      
    
    nlevels = np.int((max_salt - min_salt + 1)*3)
    kw = dict(levels = np.linspace(min_salt,max_salt,nlevels))
    ax = plt.subplot(grid[1, :4])
    #plt.contour(timeg,-depthg_gridded,varg_gridded,colors = 'lightgrey',**kw)
    cs = plt.contourf(timeg,-depthg_gridded,saltg_gridded,cmap=cmocean.cm.haline,**kw)
    cs = fig.colorbar(cs, orientation='vertical') 
    cs.set_clim(min_salt,max_salt)    
    ax.set_xlim(tini,tend)
    ax.set_ylabel('Depth (m)',fontsize=14)
    ax.set_xticklabels(' ')
    plt.title('Along Track Salinity ' + id)
    
    
    ax = plt.subplot(grid[2, :4])    
    #plt.contour(timeg,-depthg_gridded,varg_gridded,colors = 'lightgrey',**kw)
    cs = plt.contourf(timeGOFS,-depthGOFS,target_saltGOFS,cmap=cmocean.cm.haline,**kw)
    cs = fig.colorbar(cs, orientation='vertical') 
    ax.set_xlim(tini,tend)
    ax.set_ylim(-np.max(df['depth (m)']), 0)
    ax.set_ylabel('Depth (m)',fontsize=14)
    xfmt = mdates.DateFormatter('%H:%Mh\n%d-%b')
    ax.xaxis.set_major_formatter(xfmt)
    ax.set_xticklabels(' ')  
    plt.title('Along Track Salinity GOFS 3.1')
    
    ax = plt.subplot(grid[3, :4])    
    #plt.contour(timeg,-depthg_gridded,varg_gridded,colors = 'lightgrey',**kw)
    cs = plt.contourf(tstamp_RTOFS,-depthRTOFS,target_saltRTOFS,cmap=cmocean.cm.haline,**kw)
    cs = fig.colorbar(cs, orientation='vertical') 
    ax.set_xlim(tini,tend)
    ax.set_ylim(-np.max(df['depth (m)']), 0)
    ax.set_ylabel('Depth (m)',fontsize=14)
    xfmt = mdates.DateFormatter('%H:%Mh\n%d-%b')
    ax.xaxis.set_major_formatter(xfmt)
    plt.title('Along Track Salinity RTOFS')
    
    oklatbath = np.logical_and(bath_lat >= np.min(latg)-5,bath_lat <= np.max(latg)+5)
    oklonbath = np.logical_and(bath_lon >= np.min(long)-5,bath_lon <= np.max(long)+5)

    bath_latsub = bath_lat[oklatbath]
    bath_lonsub = bath_lon[oklonbath]
    bath_elevs = bath_elev[oklatbath,:]
    bath_elevsub = bath_elevs[:,oklonbath] 
    
    ax = plt.subplot(grid[1, 4:])
    plt.contour(bath_lonsub,bath_latsub,bath_elevsub,[0],colors='k')
    plt.contourf(bath_lonsub,bath_latsub,bath_elevsub,cmap='Blues_r')
    plt.contourf(bath_lonsub,bath_latsub,bath_elevsub,[0,10000],colors='seashell')
    #plt.yticks([])
    #plt.xticks([])
    plt.axis([np.min(long)-5,np.max(long)+5,np.min(latg)-5,np.max(latg)+5])
    plt.plot(long,latg,'.k')
    plt.title('Track ' + id)
    #plt.axis('equal')
    
    #folder = '/Users/aristizabal/Desktop/MARACOOS_project/Maria_scripts/Figures/Model_glider_comp/'
    folder = '/Volumes/hurricane/Hurricane_season_2019/' + (ti+timedelta(1)).strftime('%b-%d') + '/'
    file = folder + 'along_track_salt_' + id + '_' + str(tini).split()[0] + '_' + str(tend).split()[0]
    #plt.savefig(file,bbox_inches = 'tight',pad_inches = 0.1) 
