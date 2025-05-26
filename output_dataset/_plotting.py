import ultraplot as pplt
import matplotlib.pyplot as plt
import numpy as np

from matplotlib.ticker import AutoMinorLocator
import matplotlib.colors as colors
from scipy.optimize import curve_fit

import os,sys
current_file_path = os.path.abspath(__file__)
current_directory = os.path.dirname(current_file_path)
sys.path.append(current_directory)
from _autoplot import _construct_auto_fig

def reverse_coords(coords):
    return list(reversed(list(coords)))




#### TO DO

## SUPPORTED PLOTTING
# plot
# scatter
# pcolormesh
# histogram?

## SUPPORTED PLOT ACTIONS
# add_colorbars
# fit datasets
# plot fits and add legend
# add/set_title?
# add/set text?

    
cblind_cycle = ['#E69F00','#56B4E9','#009E73','#F0E442','#0072B2','#D55E00','#CC79A7','#000000']
## Create a colormap using only the positive values from RdBu 
## for plotting e.g. local conductance and non-local conductance with same colorschemes
def truncate_colormap(cmap, minval=0.0, maxval=1.0, n=100):
    new_cmap = colors.LinearSegmentedColormap.from_list(
        'trunc({n},{a:.2f},{b:.2f})'.format(n=cmap.name, a=minval, b=maxval),
        cmap(np.linspace(minval, maxval, n)))
    return new_cmap



def remove_inner_ticks(axs, rem_y = True,rem_x=True):
    ncols = axs.gridspec.ncols
    nrows = axs.gridspec.nrows
    for i in range(nrows):
        for j in range(ncols):
            if rem_y:
                if j != 0:
                    axs[i,j].format(ylocator = [],yminorlocator = [])
                    axs[i,j].format(ylabel = '')
            if rem_x:
                if i != nrows-1:
                    axs[i,j].format(xlocator = [],xminorlocator = [])
                    axs[i,j].format(xlabel = '')

def multidim_colormeshes(datasets,select,sel_idxs=None,**kwargs):
    try:
        fig = kwargs.pop('fig')
    except:
        raise Exception("multidim_colormeshes expects you to provide the figure hosting the axis in which to place the colormeshes")
    try:
        axs = kwargs.pop('axs')
    except:
        raise Exception("multidim_colormeshes expects you to provide the axis in which to place the colormeshes")

    ## Check if lines need to be overlayed
    lines = None
    if 'lines' in kwargs.keys():
        lines = kwargs.pop('lines')
        
    for ax in axs:
        ax.xaxis.set_minor_locator(AutoMinorLocator(2))
        ax.yaxis.set_minor_locator(AutoMinorLocator(2))

    dataset = datasets[0]

    ims = []
    sel_coord = dataset[select]

    
    if sel_idxs is not None:
        sel_values = []
        for i in range(len(sel_coord.values)):
            if i in sel_idxs:
                sel_values.append(sel_coord.values[i])
    else:
        sel_values = sel_coord.values

    for idx,sel_value in enumerate(sel_values):
        ds = dataset.sel({f'{select}':sel_value})
        data = ds[list(ds.data_vars)[0]]
        im = axs[idx].pcolormesh(data, **kwargs)
        ims.append(im)
        if lines is not None:
            
            for line in lines:
                axs[idx].plot(line[0],line[1], **line[2])        
    
    return ims


def add_fig_and_axes_if_not_passed(func):
    def wrapper(data_output, **kwargs):
        datasets = data_output.datasets
        if 'fig' in kwargs and 'axs' in kwargs:
            fig = kwargs.pop('fig')
            axs = kwargs.pop('axs')
        else:
            n_axs = np.sum([len(ds.data_vars) for ds in datasets])
            fig, axs = _construct_auto_fig(n_axs)
        return func(data_output,fig=fig,axs=axs, **kwargs)
    return wrapper    

def plot(datasets,**kwargs):
    fig = kwargs.pop('fig')
    axs = kwargs.pop('axs')
    colors=None
    if 'colors' in kwargs.keys():
        colors = kwargs.pop('colors')
    else: ## provide default
        colors = cblind_cycle

    fitting =None
    if 'fitting' in kwargs.keys():
        fitting = kwargs.pop('fitting')

    lines = []

    axs.xaxis.set_minor_locator(AutoMinorLocator(2))
    axs.yaxis.set_minor_locator(AutoMinorLocator(2))

    plot_dict = {
        'lines':[],
        'fits':[],
    }
    for ds_idx,ds in enumerate(datasets):
        if colors:
            l, = axs.plot(ds[list(ds.data_vars)[0]], **kwargs, color = colors[ds_idx])
            plot_dict['lines'].append(l)
            
            if fitting is not None:
                for key in list(ds.coords):
                    if ds[key].values.size >1:
                        xdata = ds[key].values
                ydata = ds[list(ds.data_vars)[0]].values
                
                popt,pcov = curve_fit(fitting[0], xdata,ydata,**fitting[1])
                fit_range = np.linspace(xdata[0],xdata[-1], num = 10*len(xdata))
                lfit, = axs.plot(fit_range, fitting[0](fit_range,*popt), **fitting[2])
                plot_dict['fits'].append({
                    'fit': lfit,
                    'popt':popt,
                    'pcov':pcov,
                })
    return plot_dict


@add_fig_and_axes_if_not_passed
def plot(data_output,fig,axs,**kwargs):
    datasets = data_output.datasets

    for ax in axs:
        ax.xaxis.set_minor_locator(AutoMinorLocator(2))
        ax.yaxis.set_minor_locator(AutoMinorLocator(2))

    lines = []
    idx = 0
    for ds in datasets:
        for data_var in ds.data_vars:
            l, = axs[idx].plot(ds[data_var],**kwargs)
            lines.append(l)
            idx+=1
    
    ## Store result
    data_output.plots = {
        'fig':[fig],
        'axs':[axs],   
        'lines':lines,
    }
    
@add_fig_and_axes_if_not_passed
def pcolormesh(data_output,fig,axs,**kwargs):
    datasets = data_output.datasets

    for ax in axs:
        ax.xaxis.set_minor_locator(AutoMinorLocator(2))
        ax.yaxis.set_minor_locator(AutoMinorLocator(2))
        
    ims = []
    idx = 0
    for ds in datasets:
        for data_var in ds.data_vars:
            im = axs[idx].pcolormesh(ds[data_var], **kwargs)
            ims.append(im)
            idx+=1

    ## Store result
    data_output.plots = {
        'fig':[fig],
        'axs':[axs],
        'ims':ims,
    }


def colorbar(data_output, **kwargs):
    premade_axs = data_output.plots['axs']
    premade_ims = data_output.plots['ims']

    axs_count = 0
    for axs in premade_axs:
        for ax in axs:
            ax.colorbar(premade_ims[axs_count],**kwargs)
            axs_count += 1


def colorbar_default(data_output, label=True,location= 'top',h_offset=0,v_offset=1.1):
    premade_axs = data_output.plots['axs']
    premade_fig = data_output.plots['fig']
    premade_ims = data_output.plots['ims']

    axs_count = 0
    for fig,axs in zip(premade_fig,premade_axs):
        for ax in axs:
            image = premade_ims[axs_count]
            if location=='top':
                cbar = ax.colorbar(image, location='top', width = 0.04, length = 0.4, align='right', locator = pplt.MaxNLocator(2), pad = -1, ticklabelsize = 7)
                cbar.set_label('')
                if label:
                    fig.text(h_offset,v_offset, image._colorbar_kw['title'], transform = ax.transAxes, fontsize = 7)
            elif location=='right':
                cbar = ax.colorbar(image, location='right', width = 0.04, length = 0.4, align='bottom', locator = pplt.MaxNLocator(2), pad = -1, ticklabelsize = 7)
                if label:
                    cbar.set_label(image._colorbar_kw['title'])
            axs_count += 1
