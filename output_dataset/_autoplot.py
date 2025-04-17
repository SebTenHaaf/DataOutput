
import ultraplot as pplt
import xarray as xr
import numpy as np 
from matplotlib.ticker import AutoMinorLocator

import os,sys,json

current_file_path = os.path.abspath(__file__)
current_directory = os.path.dirname(current_file_path)
sys.path.append(current_directory)
from _parameter_handler import Parameter

def get_file_path(filename:str)->str:
	""" 
		Retrieve file path relative to package location, with correct os format
		Ensures parameters and configs are saved in correct location

		Args:
			filename (string): the name of the file whose path to obtain
		Returns:
			String containing the path to the file
	"""
	module_dir = os.path.dirname(os.path.abspath(__file__))
	return os.path.join(module_dir, filename)

def load_dictionary(filename:str)->dict:
	"""
		Reads the data from json files, 
		or create file with default settings

		Args:
			filename (string): name of the file to load, including extension
		Returns:
			dictionary: content of the file if it existed, default values otherwise
	"""
	file_path = get_file_path(filename)
	if os.path.exists(file_path):
		with open(file_path, 'r') as f:
			return json.load(f)

	else:
		with open(file_path, 'w') as f:
			## Content of a default config file
			default = configs_template = {
				'figs':{
					'max_cols': 3,
					'row_height': 2,
					'col_width': 2,   
					'minorticks':2,
					'majorticks':2,
					'add_colorbars': True,
					'set_title':True,
				},
				'colorbar':{
					'length': 0.8,
					'width': 0.05,
					'align':'right',
					'location':'top',
					'pad':-1,
					'ticklabelsize':7,
				},
				'2D':{
					'levels':1000,
					'cmap':'magma',
				},
				'1D':{
					'linewidth': 1,
				}
			}
			json.dump(default, f)
			return default
		

def save_dictionary(dictionary:dict, filename:str)->None:
	"""
		Save a dictionary to a json file
		Args:
			dictionary: the dict with values to save
			file_path: str containing path to json file to store data
	"""
	file_path = get_file_path(filename)
	with open(file_path, 'w') as f:
		json.dump(dictionary, f,indent=4)

def save_configs(dictionary:dict)->None:
	"""
		Store new configuration settings to the correct json file
		Args:
			dictionary: the dict with values to store
	"""
	file_path = get_file_path(filename_config)
	save_dictionary(dictionary, file_path)
	configs.update(load_dictionary(filename_config))

filename_config = "plot_configs.json" ## Hardcoded config filename
configs = load_dictionary(filename_config)

def handle_plot(data_array: xr.DataArray,ax:pplt.axes.Axes):
	"""
		Handle plotting for the auto_plot function
		of a data_array with arbitrary number of dimensions
	
		First checks the dimension of the data and then passes data to the
		correct plotting_functions
		Args:
			data_array (xr.DataArray): DataArray object to be plotted
			ax (matplot.Axes): axis object in which the data should be plotted
	"""
	coords = list(data_array.coords)
	len_coords = [data_array[key].values.size > 1 for key in coords ]
	filt_coords = [key for key in coords if data_array[key].values.size > 1]
	dim = np.sum(len_coords)
	## Set the minor ticks to the default config 
	ax.xaxis.set_minor_locator(AutoMinorLocator(configs['figs']['minorticks']))
	ax.yaxis.set_minor_locator(AutoMinorLocator(configs['figs']['minorticks']))
	
	if dim == 2:
		im = ax.pcolormesh(data_array,**configs['2D'])
		if len(coords) > len(filt_coords):
			ax.format(xlabel = Parameter[filt_coords[1]].as_label(), ylabel = Parameter[filt_coords[0]].as_label())

		if configs['figs']['add_colorbars']:
			cbar = ax.colorbar(im, **{**configs['colorbar'],'locator': pplt.MaxNLocator(2)},)
			cbar.set_label(Parameter[data_array.name].as_label())

	if dim == 1:
		ax.plot(data_array, **configs['1D'])

def _construct_auto_fig(N:int):
	"""
		Create a proplot figure for a given number of required axis,
		by considering the default maximum columns and the default
		heights and widths.

		Args:
			N (int): the number of required axis
		Returns:
			fig: the created proplot Figure container object
			axs: the list of created proplot Axes objects
	"""
	# Create the array shape to pass to proplot subplots 
	max_cols = configs['figs']['max_cols']
	full_rows = N//max_cols
	last_row = N - full_rows*max_cols
	total_rows = full_rows + 1 if last_row != 0 else full_rows
	array = []
	for row_count in range(full_rows):
		array.append([i+1+max_cols*row_count for i in range(max_cols)])
	if last_row !=0:
		last_row_array = [i+1+max_cols*full_rows if i < last_row else 0 for i in range(max_cols)]
		array.append(last_row_array)
	if full_rows == 0:
		array = [i+1 for i in range(N)]

	figwidth = N*configs['figs']['col_width'] if N<max_cols else max_cols*configs['figs']['col_width'] 
	figheight = total_rows*configs['figs']['row_height']
	fig,axs = pplt.subplots(array,figwidth = figwidth, figheight = figheight, grid=False,sharex=False,sharey=False,tight=True,pad=0.5)

	return fig,axs

def autoplot(datasets: list[xr.Dataset]):
	"""
		Automatically plot data, based on the number of datasets,
		and the number of data variables within each dataset.
		Handles the following possibilities:
		1. N_datasets = 1,  N_variables >= 1
			- Create a single figure with an axis for each data variable
		2. N_datasets > 1,  N_variables > 1 (for atleast one dataset)
			- Recursively call auto_plot for each dataset, to create a figure
			  for each containing en axis for each data variable
		3. N_datasets > 1, N_variables = 1
			- Create a single figure with an axis for each dataset, 
			to plot the single data variable for each.
	"""
	## Reload Parameter class to make sure latest config is used
	## TODO check if this becomes a speed bottleneck for large number of parameters
	Parameter.reload()

	## Check the contents of the supplied datasets
	n_datasets = len(datasets)
	n_datavars = []
	n_dims = []
	for ds in datasets:
		n_datavars.append(len(ds.data_vars))
		coords = list(ds.coords)
		n_dims = [len(ds[key].coords) for key in ds.data_vars ]
	

	## When receiving multiple datasets with multiple vars,
	## create multiple figures recursively by calling auto_plot for each dataset
	if n_datasets > 1 and any(n > 1 for n in n_datavars):
		plot_output = {
			'fig':[],
			'axs':[],
		}
		for dataset in datasets:
			sub_output = autoplot([dataset])
			plot_output['fig'].append(sub_output['fig'])
			plot_output['axs'].append(sub_output['axs'])
		return plot_output

	## Multiple datasets with each 1 variable: create a single figure
	## with an axis per dataset
	elif n_datasets > 1:
		if any(n > 2 for n in n_dims):
			raise ValueError("Auto-plotting is not supported for the requested number of datasets and dimensions")

		n_axs = n_datasets
		fig,axs = _construct_auto_fig(n_axs)
		title = 'Datasets '
		for idx,dset in enumerate(datasets):
			handle_plot(dset[list(dset.data_vars)[0]],ax=axs[idx])
			if hasattr(dset, 'run_id'):
				title += f'{dset.run_id},'
		if configs['figs']['set_title']:
			fig.format(suptitle = title[:-1])
		plot_output = {
			'fig': [fig],
			'axs': [axs],
		}
		return plot_output

	## A single dataset with multiple variables: create a single figure
	## with an axis per data variable
	else:
		dataset = datasets[0]
		if (n_dims[0] > 3):
			raise ValueError("Auto-plotting data with more than 3 coordinates is not supported.")
		if (n_dims[0] > 2) and (n_datavars[0] > 1):
			raise ValueError("Auto-plotting a multidimensional dataset with multiple variables is not supported. Select a single variable to ouput")

		if n_dims[0] < 3:
			n_axs = n_datavars[0]
			fig,axs = _construct_auto_fig(n_axs)
			if configs['figs']['set_title']:
				if hasattr(dataset,'run_id'):
					fig.format(suptitle = f'Dataset {dataset.run_id}')

			for idx,var in enumerate(dataset.data_vars):
				handle_plot(dataset[var],ax = axs[idx])
		else:
			n_axs = len(dataset[coords[0]].values)
			fig,axs = _construct_auto_fig(n_axs)

			for idx,coord_val in enumerate(dataset[coords[0]].values):
				coord = coords[0]
				axs[idx].format(title = f'{Parameter[coord].verbose_name} = {Parameter[coord].as_label()})',fontsize = 7)
				cut_dataset = dataset.sel({f'{coords[0]}':coord_val}, method = 'nearest')
				handle_plot(cut_dataset[list(dataset.data_vars)[0]], ax = axs[idx])

		plot_output = {
			'fig': [fig],
			'axs': [axs],
		}
		return plot_output