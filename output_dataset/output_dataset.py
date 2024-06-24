import xarray as xr
import json
import qcodes as qc
import os
import proplot as pplt
import numpy as np
from matplotlib.ticker import AutoMinorLocator

from typing import List, Tuple, Dict
from typing import Optional, Union,Callable


from IPython.display import display, Math,Markdown


def get_file_path(filename:str)->str:
	""" 
		Retrieve a file path relative to package location, with correct os format
		Ensures parameters and configs are saved in correct location

		Args:
			filename (string): the name of the file whose path to obtain
		Returns:
			String containing the path to the file
	"""
	module_dir = os.path.dirname(os.path.abspath(__file__))
	return os.path.join(module_dir, filename)

filename_params = "verbose_params.json" ## Hardcoded parameter filename
filename_config = "plot_configs.json" ## Hardcoded config filename

def load_dictionary(filename:str = filename_params)->dict:
	"""
		Reads the data from an existing json file, 
		or creates a file with default settings

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
			if filename == filename_config:
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
			else:
				default = {}
			json.dump(default, f)
			return default

## Load the parameters and config file into the namespace
param_verbose = load_dictionary(filename_params)
configs = load_dictionary(filename_config)

def load_data(run_id:int)->xr.Dataset:
	"""
		Loads a dataset from a QCoDeS database and converts it to 
		an xarray Dataset object
		Args:
			run_id (int): the id to load, needs to exist in the database
		Returns:
			xr.Dataset: the converted dataset in xarray format
	"""
	dset = qc.load_by_id(run_id)
	ds = dset.to_xarray_dataset()
	return ds

def list_parameters():
	"""
		Loops over all parameters and displays their verbose name
	"""
	for param_key in param_verbose:
		info = parameter_info(param_key)
		display(Markdown(f'{param_key}'+ ' (' + info['verbose_name']+')'))

def save_dictionary(dictionary:dict, file_path:str)->None:
	"""
		Save a dictionary to a json file
		Args:
			dictionary: the dict with values to save
			file_path: str containing path to json file to store data
	"""
	with open(file_path, 'w') as f:
		json.dump(dictionary, f)

def save_configs(dictionary:dict)->None:
	"""
		Store new configuration settings to the correct json file
		Args:
			dictionary: the dict with values to store

	"""
	file_path = get_file_path(filename_config)
	save_dictionary(dictionary, file_path)
	configs.update(load_dictionary(filename_config))

def save_params(dictionary:dict)->None:
	"""
		Store new parameter settings to the correct json file
		Args:
			dictionary: the dict with values to store

	"""
	file_path = get_file_path(filename_params)
	save_dictionary(dictionary,file_path)
	param_verbose.update(load_dictionary(filename_params))

def construct_label(param_key: str, add_unit: bool=True)->str:
	"""
		Construct the label for a certain parameter
		by combining its verbose name and its unit

		Args:
			param_key (string): the dictionary key value of the parmater to load
			add_unit (bool)
	"""
	if add_unit:
		return  f"{parameter_info(param_key)['verbose_name']} ({parameter_info(param_key)['unit']})"
	else:
		return f"{parameter_info(param_key)['verbose_name']}"

def reformat_dataset(dataset)-> xr.Dataset:
	"""
		Go over all variables in a dataset and rename the labels
		+ rescale the data to desired units 
		Settings are provided in the verbose_params dictionary
		If a new variable is encountered a default entry is created in the dictionary


		Args:
			dataset (xarray DataSet): the dataset to be reformatted
		Returns:
			xarray DataSet: the reformatted dataset
			
	"""
	coord_keys = dataset.coords
	## Obtain rescaled data coordinates
	for key in coord_keys:
		if key not in param_verbose.keys():
			update_parameter(key, verbose_name = dataset[key].attrs['long_name'], unit = dataset[key].attrs['units'])
		old_attrs = dataset[key].attrs
		dataset = dataset.assign_coords({f'{key}': dataset[key].values*param_verbose[key]['scale']})
		dataset[key].attrs = old_attrs

	## Rename the rescaled coordinates
	for key in coord_keys:
		dataset[key].attrs['long_name'] = param_verbose[key]['verbose_name']
		dataset[key].attrs['unit'] = param_verbose[key]['unit']
		dataset[key].attrs['units'] = param_verbose[key]['unit']

	## Rescale and rename the data variables
	for key in dataset.data_vars:
		if key not in param_verbose.keys():
			update_parameter(key,verbose_name = dataset[key].attrs['long_name'], unit = dataset[key].attrs['units'])
		dataset[key].attrs['long_name'] = param_verbose[key]['verbose_name']
		dataset[key].attrs['unit'] = param_verbose[key]['unit']
		dataset[key].attrs['units'] = param_verbose[key]['unit']
		dataset[key][:] = dataset[key].values*param_verbose[key]['scale']
	return dataset

def display_parameter_info(param_key:str):
	"""
		Display stored parameter info in markdown
		Args:
			param_key (string): the dictionary key value of the parameter to display
	"""
	try:
		info = parameter_info(param_key)
		display(Markdown(r'Name: '+info['verbose_name']))
		display(Markdown(r'Scale: '+ f"{info['scale']}"))
		display(Markdown(r'Unit: ' + info['unit']))

	except Exception as e:
		print(f"Could not display variable: {e}")

def parameter_info(param_key:str)->dict:
	"""
		Extract stored parameter info from the param_verbose dictionary
		Args:
			param_key (string): the dictionary key value of the parameter to display
		Returns:
			dict:  dictionary containing the settings for the specific parameter
	"""
	try:
		return param_verbose[param_key]

	except Exception as e:
		print(f"Could not return variable: {e}")

def update_config(config_category:str,config_key:str,new_value):
	"""
		Update a setting for the auto_plot config dictionary and save to
		the json file
		Args:
			config_category (string): dictionary key of the main category 
			config_key (string): dictionary key of the subcategory
			new_value (any): new values to store. Must be Json serializable
	"""
	if config_key in configs[config_category].keys():
		print(f"Updating known setting")
	else:
		print(f"Creating new setting")
	configs[config_category][config_key] = new_value
	save_configs(configs)

def update_parameter(param_key:str, verbose_name:Optional[str] = None, scale:Optional[int] = 1,unit:Optional[str] = None ):
	"""
		Update a parameter in the verbose_params dictionary and save to the 
		json file
		Args:
			param_key (string): dictionary key of the parameter to retrieve
			verbose_name (string): desired parameter name to display in figures
			scale (int): rescaling factor to apply the the parameter
			unit (string): correct unit after rescaling, to display in figures

	"""
	try:
		if param_key in param_verbose.keys():
			print(f"Updating known parameter: {param_key}")
			if verbose_name is None:
				verbose_name = param_verbose[param_key]['verbose_name']
			if unit is None:
				unit = param_verbose[param_key]['unit']
		else:
			print(f"Adding new parameter: {param_key}")
			if verbose_name is None:
				verbose_name = param_key
			if unit is None:
				unit = '-'
		info = {
			'verbose_name': verbose_name,
			'scale':scale,
			'unit':unit,
		}
		param_verbose[param_key] = info
		save_params(param_verbose)

	except Exception as e:
		print(f"Could not update parameter:{e}")


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

	dim = np.sum(len_coords)

	## Set the minor ticks to the default config 
	ax.xaxis.set_minor_locator(AutoMinorLocator(configs['figs']['minorticks']))
	ax.yaxis.set_minor_locator(AutoMinorLocator(configs['figs']['minorticks']))
	if dim == 2:
		im = ax.pcolormesh(data_array,**configs['2D'])
		if configs['figs']['add_colorbars']:
			cbar = ax.colorbar(im, **{**configs['colorbar'],'locator': pplt.MaxNLocator(2)})

	if dim == 1:
		ax.plot(data_array, **configs['1D'])

def construct_auto_fig(N:int):
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
	fig,axs = pplt.subplots(array,figwidth = figwidth, figheight = figheight, grid=False,sharex=False,sharey=False)
	return fig,axs


def auto_plot(datasets: list[xr.Dataset]):
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
	n_datasets = len(datasets)
	n_datavars = []
	for ds in datasets:
		n_datavars.append(len(ds.data_vars))

	## When receiving multiple datasets with multiple vars,
	## create multiple figures recursively by calling auto_plot for each dataset
	if n_datasets > 1 and any(n > 1 for n in n_datavars):
		plot_output = {
			'fig':[],
			'axs':[],
		}
		for dataset in datasets:
			sub_output = auto_plot([dataset])
			plot_output['fig'].append(sub_output['fig'])
			plot_output['axs'].append(sub_output['axs'])
		return plot_output

	## Multiple datasets with each 1 variable: create a single figure
	## with an axis per dataset
	elif n_datasets > 1:
		n_axs = n_datasets
		fig,axs = construct_auto_fig(n_axs)
		title = 'Datasets '
		for idx,dset in enumerate(datasets):
			handle_plot(dset[list(dset.data_vars)[0]],ax=axs[idx])
			title += f'{dset.run_id},'
		if configs['figs']['set_title']:
			fig.format(suptitle = title[:-1])
		plot_output = {
			'fig': [fig],
			'axs': [axs],
		}
		return plot_output

	## A single dataset with multiple varibales: create a single figure
	## with an axis per data variable
	else:
		dataset = datasets[0]
		n_axs = n_datavars[0]
		fig,axs = construct_auto_fig(n_axs)
		if configs['figs']['set_title']:
			fig.format(suptitle = f'Dataset {dataset.run_id}')

		for idx,var in enumerate(dataset.data_vars):
			handle_plot(dataset[var],ax = axs[idx])

		plot_output = {
			'fig': [fig],
			'axs': [axs],
		}
		return plot_output
                   
def output_dataset(datas:list[Union[int,xr.Dataset]],data_keys:Optional[list[list[str]]]=None, plot_func:Optional[Callable]=None,  plot: bool=True, reformat:bool=True, process_funcs:Optional[list[Callable]] = [],)->list[xr.Dataset]:
	"""
		The main functionality of the package that loads datasets from a qcodes database
		Optionally:
			- Relable and rescale extracted datasets
			- Pass datasets to processing functions
			- Pass datasets to plotting functions
			- Use the auto_plot functionaility

		Args:
			data (List of ints or DataSets): a list specifying what data to process. 
			data_keys (opt: list of string): list of string specifying what subset of datavariables to extract for a dataset
			reformat (bool): specifies whether the dataset should be reformatted
			plot (bool): specifies whether the data should be plotted
			plot_func (Callable): a plotting function to which a list of extracted datasets will be passed
								if plot=True, but no function is supplied, the auto_plot function will be used
			proccess_funcs (list of callables): optional list of processing functions to which the datasets will be passed
												before entering the plotting section. Every processing function must return
												a list of xarray datasets.
	"""
	## Assert that data to be supplies is of correct format
	assert isinstance(datas,list), "data to be loaded must be provided as a list"
	message = "Data must be supplied as run_ids (int) to load, or as xarray datasets"
	assert all([isinstance(data,(int,xr.Dataset)) for data in datas]), message

	output = {}
    ### Extracting the relevant data into array
	datasets = []
	### Duplicate data_keys if needed for correct shape and assert typing
	if data_keys:
		message = "Data keys must be provided as a nested list of strings"
		assert isinstance(data_keys,list),message
		if len(data_keys) != len(datas):
			data_keys = [data_keys[0] for i in range(len(datas))]
		assert all([isinstance(inner_keys,list) for inner_keys in data_keys]),message
		for data_inner in data_keys:
			assert all([isinstance(data_string,str) for data_string in data_inner]), message

    ### Loop over the run_ids and get the data as given by data_keys	
	for data_idx,data in enumerate(datas):
		if isinstance(data, int):
			dataset = load_data(data)
		else:
			dataset = data
        ## Optionally relabels and rescale all variables
		if reformat:
			dataset = reformat_dataset(dataset)
	
		try:
			## New_dataset is subset of previous dataset
			if data_keys:
				new_dataset = dataset[data_keys[data_idx]]
				datasets.append(new_dataset)
			## Pass entire dataset if data_keys filter is not supplied
			else:
				datasets.append(dataset)
		except KeyError as e:
			if isinstance(data,int):
				run_id = data
			else:
				run_id = data.run_id
			raise KeyError(f"Could not load data in run {run_id}: {e}")
		
            
    ### Process the data in order of process_funcs	
	for func in process_funcs:
		try:
			datasets = func(datasets)
		except Exception as e:
			print(f"Error while running {func}: {e}")
			return output

	output['datasets'] = datasets # add datasets to the output

	if plot:      
		## If a plotting function has been provided, pass all the datasets there
		if plot_func is not None:
			try:
				plot_output = plot_func(datasets)
				output['plots'] = plot_output
				return output
			except Exception as e:
				print(f"Unable to plot the data: {e}")
				return output
    
        ## If a plotting function has not been provided, pass the datasets
        ## to the default autoplot function
		else:
			## Pass along the figure and axs (whether they or provided or not)
			try:
				plot_output = auto_plot(datasets)
				output['plots'] = plot_output
				return output
			except Exception as e:
				print(f"Unable to automatically plot your data: {e}")
				raise
	return output

	