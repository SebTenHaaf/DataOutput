<h2>Introduction</h2>
This codebase is intended for streamlining the process of extracting data from qcodes databases and consequently plotting or processing this data.

It is build on top of proplot and xarray. An environment is provided that has functioning version combinations, to be updated once proplot is maintained again.

The package focuses on the following functionality:

- Simultaneously extract different variables from different datasets, converted to xarray format
- Store parameter information, such as a preferred label and rescaling factor  
- Automatically plot and reformat data
- Streamline the processing of datasets

<h2>Installation</h2>
To get started, we suggest the following:

1. Pull the package 
2. Navigate to directory containing env.yml
3. Run conda env create -f env.yml
4. Run jupyter lab
5. Navigate to tutorial.ipybn
6. See tutorial for all examples

<h2> Contributing to the code </h2>
The ultimate aim of the package is to provide general functions that make plotting and data processing faster. If you encounter an issue please raise the issue here.
