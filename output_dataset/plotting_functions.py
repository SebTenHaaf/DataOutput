import proplot as pplt
import matplotlib.pyplot as plt
import numpy as np

from matplotlib.ticker import AutoMinorLocator
import matplotlib.colors as colors
from scipy.optimize import curve_fit


def reverse_coords(coords):
    return list(reversed(list(coords)))
    
cblind_cycle = ['#E69F00','#56B4E9','#009E73','#F0E442','#0072B2','#D55E00','#CC79A7','#000000']
## Create a colormap using only the positive values from RdBu 
## for plotting e.g. local conductance and non-local conductance with same colorschemes
def truncate_colormap(cmap, minval=0.0, maxval=1.0, n=100):
    new_cmap = colors.LinearSegmentedColormap.from_list(
        'trunc({n},{a:.2f},{b:.2f})'.format(n=cmap.name, a=minval, b=maxval),
        cmap(np.linspace(minval, maxval, n)))
    return new_cmap


def plot_lines(datasets,**kwargs):
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



def remove_inner_ticks(axs):
    ncols = axs.gridspec.ncols
    nrows = axs.gridspec.nrows
    for i in range(nrows):
        for j in range(ncols):
            if j != 0:
                axs[i,j].format(ylocator = [],yminorlocator = [])
                axs[i,j].format(ylabel = '')

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

def plot_colormeshes(datasets,**kwargs):
    try:
        fig = kwargs.pop('fig')
    except:
        raise Exception("plot_colormeshes expects you to provide the figure hosting the axis in which to place the colormeshes")
    try:
        axs = kwargs.pop('axs')
    except:
        raise Exception("plot_colormeshes expects you to provide the axis in which to place the colormeshes")

    #for dataset in datasets:
    #    if len(list(dataset.coords)) > 2:
    #        raise Exception("Plot Colormeshes expects a list of 2D datasets")

    for ax in axs:
        ax.xaxis.set_minor_locator(AutoMinorLocator(2))
        ax.yaxis.set_minor_locator(AutoMinorLocator(2))

    ## Check if lines need to be overlayed
    lines = None
    if 'lines' in kwargs.keys():
        lines = kwargs.pop('lines')
        
    ims = []
    for idx,ds in enumerate(datasets):     
        data = ds[list(ds.data_vars)[0]]
        im = axs[idx].pcolormesh(data, **kwargs)
        ims.append(im)
        if lines is not None:
            
            for line in lines:
                axs[idx].plot(line[0],line[1], **line[2])
    
    return ims

def default_colorbar(im,axs,fig, label=False,location= 'top'):
    if location=='top':
        cbar = axs.colorbar(im, location='top', width = 0.04, length = 0.4, align='right', locator = pplt.MaxNLocator(2), pad = -1, ticklabelsize = 6)
        cbar.set_label('')
    
        if label:
            fig.text(0,1.05, label, transform = axs.transAxes, fontsize = 7)
    elif location=='right':
        cbar = axs.colorbar(im, location='right', width = 0.04, length = 0.4, align='bottom', locator = pplt.MaxNLocator(2), pad = -1, ticklabelsize = 6)
        cbar.set_label('')

        if label:
            fig.text(1,0.85, label, transform = axs.transAxes, fontsize = 7)

    return cbar