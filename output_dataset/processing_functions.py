import xarray as xr
import numpy as np
from typing import List, Tuple, Dict
from typing import Optional, Union,Callable

from .output_dataset import load_dictionary


filename_offsets = "data_offsets.json"
offset_dict = load_dictionary(filename_offsets)

def reverse_coords(coords):
    return list(reversed(list(coords)))
    
def transpose(datasets:list[xr.Dataset])->list[xr.Dataset]:
    """
        Transpose the data variables using xarrays
        build-in transpose funciton
        Args:
            datasets: list of xarray Datasets 
        Returns:
            list of xarray datasets: tranposed data
    """
    transposed_datasets = []
    for dataset in datasets:
        transposed_datasets.append(dataset.transpose())
    return transposed_datasets


def normalize_G(datasets):
    new_datasets = []
    for dataset in datasets:
        data_key = list(dataset.data_vars)[0]
        data_array = dataset[data_key]
        old_attrs = dataset[data_key].attrs
        data_array = (data_array - np.min(data_array))
        data_array = data_array/np.max(data_array)
        dataset[data_key] = data_array
        dataset[data_key].attrs = old_attrs
        new_datasets.append(dataset)
    return new_datasets


def normalize_S21(datasets):
    for dataset in datasets:
        for data_key in dataset.data_vars:
            data_array = dataset[data_key]
            if data_key != 'S21_M_Amplitude':
                data_array = data_array - np.min(data_array)
                data_array = data_array/np.max(data_array)
            else:
                data_array = -(data_array - np.max(data_array))
                data_array = data_array/np.max(data_array)
            dataset[data_key] = data_array
    return datasets


def get_corr_S21(datasets):
    new_datasets = []
    for dataset in datasets:
        data_vars = list(dataset.data_vars)
        new_da = np.sqrt(abs(dataset[data_vars[0]]*dataset[data_vars[1]]))
        dataset['S21_correlated'] = xr.DataArray(new_da.values, coords = dataset.coords, attrs = dataset[data_vars[0]].attrs)
        dataset = dataset.drop_vars(data_vars)
        new_datasets.append(dataset)

    return new_datasets


def get_corr_G(datasets):
    new_datasets = []
    for dataset in datasets:
        data_vars = list(dataset.data_vars)
        new_da = np.sqrt(abs(dataset[data_vars[0]]*dataset[data_vars[1]]))
        dataset['G_correlated'] = xr.DataArray(new_da, coords = dataset.coords, attrs = dataset[data_vars[0]].attrs)
        dataset = dataset.drop_vars(data_vars)
        new_datasets.append(dataset)
    return new_datasets


def select_data(datasets:list[xr.Dataset], sel_dict)->list[xr.Dataset]:
    """
        Take a cut along a dimension using xarrays build-in sel function
        Args:
            datasets (list of Datasets): the data to which the sel operation is applied
            sel_dict: dictionary to pass to the .sel() function that specifies the coordinate and value
        Returns:
            list of xarray datasets with reduced dimensionality
    """
    method = 'nearest'
    for key in sel_dict:
        if isinstance(sel_dict[key], slice):
            method = None
    
    new_datasets = []
    for dataset in datasets:
        new_dataset = dataset.sel(sel_dict, method = method)
        new_datasets.append(new_dataset)
    return new_datasets


def average_outerdim(datasets):
    for dataset in datasets:
        outer_coord = list(dataset.coords)[0]
        data_coord = list(dataset.data_vars)[0]
    
        output_values = np.zeros(dataset[data_coord].shape[1:])  
    
        for outer_val in dataset[outer_coord].values:
            subset = dataset.sel({f'{outer_coord}':outer_val}, method = 'nearest')
            output_values += subset[data_coord].values
        output_values = output_values/len(dataset[outer_coord].values)
        dataset[f'average_{data_coord}'] = xr.DataArray(output_values, coords = subset.coords, attrs = dataset[data_coord].attrs)
    return datasets

def centre_axis(values:list):
    return values - (values[0]+values[-1])/2



def adjust_axis(datasets:list[xr.Dataset], mapping:Callable, adjust:Optional[int] = 'all')->list[xr.Dataset]:
    """
        Map one or more axis of datasets to new values
        Args:
            datasets (list of Datasets): the data to which the sel operation is applied
            mapping (Callable): function to which to pass the coordinate that should be adjused
            adjust (int): optional, the axis to pass to mapping. By defauly all axis are processed
        Returns:
            list of xarray datasets with new axis


    """
    new_datasets = []
    for dataset in datasets:
        if adjust == 'all':
            data_coords = reverse_coords(dataset.coords)
        else:
            data_coords = np.array(reverse_coords(dataset.coords))[adjust]
        
        new_coord_dict = {}
        for coord_key in data_coords:
            old_coord_da= dataset[coord_key]
            old_coord_attrs = dataset[coord_key].attrs
            coord_values = old_coord_da.values
            new_values = mapping(coord_values)
            #new_coord_dict[coord_key] = new_values
            new_coord_dict[coord_key] = (f'{coord_key}',new_values,old_coord_attrs)

            #new_coord_da = xr.DataArray(new_values, coords = {f'{coord_key}':new_values}, attrs = old_coord_da.attrs)
        old_attrs = dataset.attrs
        new_dataset = dataset.assign_coords(new_coord_dict)
        new_dataset.attrs = old_attrs
        new_datasets.append(new_dataset)

    return new_datasets


def adjust_coordinate_offset(dataset, coord_key, offset):
    new_coord_dict = {}
    old_coord_da= dataset[coord_key]
    old_coord_attrs = dataset[coord_key].attrs
    coord_values = old_coord_da.values
    new_values = coord_values - offset
    new_coord_dict[coord_key] = (f'{coord_key}',new_values,old_coord_attrs)
    old_attrs = dataset.attrs
    new_dataset = dataset.assign_coords(new_coord_dict)
    new_dataset.attrs = old_attrs
    return new_dataset

## Adjusting the data offsets is simpler due to how xarray structures the coordinates
def adjust_data_offset(dataset,data_key,offset):
    data_array = dataset[data_key]
    old_attrs = dataset[data_key].attrs
    data_array = data_array - offset
    dataset[data_key] = data_array
    dataset[data_key].attrs = old_attrs
    return dataset

def apply_offset_corrections(datasets, only_data=False):
    corrected_datasets = []
    for dataset in datasets:
        if not only_data:
            for coord_key in dataset.coords:
                if coord_key in offset_dict:
                    dataset = adjust_coordinate_offset(dataset, coord_key, offset_dict[coord_key])

        for data_key in dataset.data_vars:
            if data_key in offset_dict:
                dataset = adjust_data_offset(dataset, data_key, offset_dict[data_key])

        corrected_datasets.append(dataset)
    return corrected_datasets
                