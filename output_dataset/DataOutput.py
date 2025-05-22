import os, sys, json, inspect, re
from importlib import reload

import qcodes as qc
import xarray as xr

from ._parameter_handler import *
from ._autoplot import *

current_file_path = os.path.abspath(__file__)
current_directory = os.path.dirname(current_file_path)
sys.path.append(current_directory)

import _plotting
import _processing

import ultraplot as pplt
pplt.rc['colorbar.width'] = 0.05
pplt.rc['cmap.discrete'] = False
pplt.rc['grid'] = False


def save_process(func):
    """Write or overwrite a function in the processing file."""
    filename = get_file_path('_processing.py')
    func_name = func.__name__
    func_code = inspect.getsource(func)

    try:
        # Read the current content of the file
        with open(filename, "r") as f:
            content = f.read()
    except FileNotFoundError:
        content = ""

    # Check if the function is already defined
    pattern = rf"def {func_name}\(.*?\):[\s\S]*?(?=\ndef |\Z)"
    if re.search(pattern, content):
        # Replace the existing function
        content = re.sub(pattern, func_code, content)
    else:
        # Add a newline if the file is not empty, then append the new function
        content += ("\n\n" if content else "") + func_code

    # Write the updated content back to the file
    with open(filename, "w") as f:
        f.write(content)
    reload(_processing)

def save_plotting(func):
    """Write or overwrite a function in the plotting file."""
    filename = get_file_path('_plotting.py')
    func_name = func.__name__
    func_code = inspect.getsource(func)

    try:
        # Read the current content of the file
        with open(filename, "r") as f:
            content = f.read()
    except FileNotFoundError:
        content = ""

    # Check if the function is already defined
    pattern = rf"def {func_name}\(.*?\):[\s\S]*?(?=\ndef |\Z)"
    if re.search(pattern, content):
        # Replace the existing function
        content = re.sub(pattern, func_code, content)
    else:
        # Add a newline if the file is not empty, then append the new function
        content += ("\n\n" if content else "") + func_code

    # Write the updated content back to the file
    with open(filename, "w") as f:
        f.write(content)
    reload(_plotting)

def load_xarray_snapshot(ds:xr.Dataset) -> List[dict]:
	"""
		In conversion from qcodes to xarray the snapshot 
		containing all parameter and instrument info is converted to a string
		This function converts it back to a dictionary
	"""
	return json.loads('{' + ds.snapshot[1:-1] + '}')

def load_qcodes_as_xarray(run_id:int)->xr.Dataset:
	"""
		Load a dataset from a QCoDeS database and convert it to 
		an xarray Dataset object
		Args:
			run_id (int): the id to load, needs to exist in the database
		Returns:
			xr.Dataset: the converted dataset in xarray format
	"""
	dset = qc.load_by_id(run_id)
	ds = dset.to_xarray_dataset()
	return ds

class DataOutput():
    def __init__(self, datas, data_keys = None, reformat=True):
        ## Load data (depending on input)
        self.datasets = self._assemble_datasets(datas,data_keys)

        ## Reformat data labels and scale if desired
        if reformat:
            self.reformat()

    @staticmethod
    def parse_data_input(datas):
        ## Ensure that data to be loaded is of correct format
        if not isinstance(datas,list):
            if isinstance(datas,(int,xr.Dataset)):
                datas = [datas]
            elif isinstance(datas,int):
                datas = [datas]
            else:
                raise ValueError("Data to be loaded must be provided as an int, xarray.Dataset or list of these")

        if not all([isinstance(data,(int,xr.Dataset)) for data in datas]):
            raise ValueError("Data must be supplied as QCodes run_ids to load (int), or as xarray datasets")
        
        return datas
    
    @staticmethod
    def parse_data_keys(datas,data_keys):
        if isinstance(data_keys,str):
                data_keys = [[data_keys]]
        elif isinstance(data_keys, list):
            if all([isinstance(data_key, str) for data_key in data_keys]):
                data_keys = [data_keys]
            elif not all([isinstance(data_key,list) for data_key in data_keys]):
                raise ValueError("Data keys must be provided as strings or lists of strings")
            
        if len(data_keys) != len(datas):
            data_keys = [data_keys[0] for i in range(len(datas))]

        for data_inner in data_keys:
            if not all([isinstance(data_string,str) for data_string in data_inner]):
                raise ValueError("Data keys must be provided as strings or lists of strings")
        return data_keys
		
    def _assemble_datasets(self,datas, data_keys=None):
        ## Parse datas and data_keys into correct format
        datas = self.parse_data_input(datas)
        if data_keys is not None:
            data_keys = self.parse_data_keys(datas,data_keys)
            
        datasets = []
        ### Loop over the run_ids and get the data as given by data_keys	
        for data_idx,data in enumerate(datas):
            if isinstance(data, int):
                dataset = load_qcodes_as_xarray(data)
            else:
                dataset = data
        
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
        return datasets
    
    ## Autoplot the dataset
    def show(self):
        output = autoplot(self.datasets)
        setattr(self,'plots',output)
    
    def __getattr__(self, name):
        # Check if the function exists in _plotting file
        if hasattr(_plotting, name):
            func = getattr(_plotting, name)
            # Return a callable that passes the datasets to the plotting function
            def wrapper(*args, **kwargs):
                return func(self, *args, **kwargs)
            return wrapper

        # Check if the function exists in _processing file
        if hasattr(_processing,name):
            func = getattr(_processing,name)
            # Return a callable that passes the datasets to the processing function
            def wrapper(*args, **kwargs):


                return func(self, *args, **kwargs)
            return wrapper
        
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    _getitem_handlers = {
        slice:'_get_slice',
        tuple:'_get_tuple',
        int: '_get_int',
        str: '_get_str',
        list:'_get_list'
    }

    def __getitem__(self,indexing):
        handler_func_name = self._getitem_handlers.get(type(indexing), '_handle_get_default')
        handler_func = getattr(self,handler_func_name)
        subset = handler_func(indexing)
        return subset
    
    def _handle_get_default(self,indexing):
        raise TypeError(f"Getting subsets of data by {type(indexing).__name__} not supported")
    
    def _get_list(self,indexing:list):
        #if all([isinstance(index,int) for index in indexing]):   
        print(f"Getting subset by list is not yet supported")
        return self

    def _get_slice(self,indexing: slice):
        subset = DataOutput(self.datasets[indexing], reformat=False)
        return subset
        
    def _get_tuple(self,indexing: tuple):
        subset = DataOutput([self.datasets[i] for i in indexing], reformat=False)
        return subset
    
    def _get_int(self,indexing: int):
        if indexing > (len(self.datasets)) - 1:
            raise KeyError(f"Requested index ({indexing}) out of range for DataOutput with {len(self.datasets)} dataset(s)")
        subset = DataOutput([self.datasets[indexing]], reformat=False)
        return subset

    def _get_str(self,indexing: str):
        new_datasets = []
        for dataset in self.datasets:
            if indexing in dataset.data_vars:
                new_datasets.append(dataset[[indexing]])
        subset = DataOutput(new_datasets, reformat=False)
        if len(subset.datasets) < 1:
            raise KeyError(f"No data found for query: '{indexing}'")
        return subset
    
    def reformat(self) -> None:
        """
            Go over all variables in each dataset and rename the labels
            + rescale the data to the desired units 
            Settings are obtained from the data loaded into the Parameter class 
            If a new variable is encountered a new parameter will be created with default settings
        """

        for idx,dataset in enumerate(self.datasets):
            coord_keys = dataset.coords
            ## Obtain rescaled data coordinates
            for key in coord_keys:
                if key not in Parameter._instances.keys():
                    Parameter(key, verbose_name = dataset[key].attrs.get('long_name'), unit = dataset[key].attrs.get('units'))
                    Parameter.save()

                parameter = Parameter[key]
                old_attrs = dataset[key].attrs
                dataset = dataset.assign_coords({f'{key}': (dataset[key].values - parameter.offset)*parameter.scale})
                dataset[key].attrs = old_attrs

            ## Rename the rescaled coordinates
            for key in coord_keys:
                parameter = Parameter[key]
                dataset[key].attrs['long_name'] = parameter.verbose_name
                #dataset[key].attrs['label'] = parameter.verbose_name

                dataset[key].attrs['unit'] = parameter.unit
                dataset[key].attrs['units'] = parameter.unit

            ## Rescale and rename the data variables
            for key in dataset.data_vars:
                if key not in Parameter._instances.keys():
                    Parameter(key, verbose_name = dataset[key].attrs.get('long_name'), unit = dataset[key].attrs.get('units'))
                    Parameter.save()
                parameter = Parameter[key]
                dataset[key].attrs['long_name'] = parameter.verbose_name
                #dataset[key].attrs['label'] = parameter.verbose_name

                dataset[key].attrs['unit'] = parameter.unit
                dataset[key].attrs['units'] = parameter.unit
                dataset[key].values -= parameter.offset
                dataset[key].values *= parameter.scale
            self.datasets[idx] = dataset

    def snapshots(self):
        all_snapshots = []
        for dataset in self.datasets:
            all_snapshots.append(load_xarray_snapshot(dataset))
        return all_snapshots


            
            
       