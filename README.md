## Introduction

The purpose of this lab is to demonstrate the possibility of running WRF3.8.1 using Azure Batch.
It uses the same source code and benchmark data as described in https://github.com/schoenemeyer/WRF3.8-in-Azure.git with Virtual Machine Scale Sets.

The picture to the right shows the domain and the temperature and pressure after the 3rd hour of the 12km CONUS weather simulation.

<img src="https://github.com/schoenemeyer/WRF3.8-in-Azure/blob/master/4-Figure2-1.png" width="252"> <img src="https://github.com/schoenemeyer/WRF3.8.1-in-Azure-Batch/blob/master/batchrunning.JPG" width="352">

## Running WRF in Azure Batch

Usually scientists want to focus on the algorithm, instead of scalability, underlying hardware infrastructure and high availability. [Azure Batch service](https://docs.microsoft.com/en-us/azure/batch/batch-technical-overview) creates and manages a pool of compute nodes (virtual machines), installs the applications you want to run, and schedules jobs to run on the nodes. There is no cluster or job scheduler software to install, manage, or scale. Instead, you use [Batch APIs and tools](https://docs.microsoft.com/en-us/azure/batch/batch-apis-tools), command-line scripts, or the Azure portal to configure, manage, and monitor your jobs.

If you are interested in just bringing up the cluster and run a Linpack HPL job for basic testing, you can clone the lab from https://github.com/hmeiland/batchprojects

## WRF CONUS 12km Benchmark
In this benchmark from (http://www2.mmm.ucar.edu/wrf/WG2/benchv3) is used. We use the input files below from http://www2.mmm.ucar.edu/WG2bench/conus12km_data_v3 which are also available on Azure Blob Storage. The files are automatically downloaded during running this lab.
```
https://hpccenth2lts.blob.core.windows.net/wrf/wrfrst_d01_2001-10-25_00_00_00
https://hpccenth2lts.blob.core.windows.net/wrf/wrfbdy_d01
```

## Performance in Azure

Here is the performance for the CONUS 12km Benchmark you can expect on our H16r series in Azure. The simulation speed can be calculated by running this command after finishing the simulation. For performance measurement you will need the file stats.awk which can be also download from this repository https://github.com/schoenemeyer/WRF3.8-in-Azure/blob/master/stats.awk 
```
grep 'Timing for main' rsl.error.0000 | tail -149 | awk '{print $9}' | awk -f stats.awk
```
This command will output the average time per time step as the mean value. Simulation speed is the model time step, 72 seconds, divided by average time per time step. You can also derive the sustained Gigaflops per second which is simulation speed times 0.418 for this case.

![After processing](https://github.com/schoenemeyer/WRF3.8-in-Azure/blob/master/wrf3.8-128.gif)

The Azure H-series virtual machines are built on the Intel Haswell E5-2667 V3 processor technology featuring DDR4 memory and SSD-based temporary storage.

In addition to the substantial CPU power, the H-series offers diverse options for low latency RDMA networking using FDR InfiniBand and several memory configurations to support memory intensive computational requirements.
https://docs.microsoft.com/en-us/azure/virtual-machines/windows/sizes-hpc


## Contents of the lab

In this lab  you will learn how to run WRF in Azure Batch using the Python SDK for Azure. Sinmply follow the steps below. The whole exercise should be finished in 30 min, if you have your account credential etc. ready.

1. Install Microsoft Azure SDK for Python  https://github.com/Azure/azure-sdk-for-python
2. Install BatchLabs for monitoring jobs in Azure Batch
    https://azure.github.io/BatchLabs/
2. Git clone of https://github.com/schoenemeyer/WRF3.8.1-in-Azure-Batch
3. Change to directory application 
```
 wget https://hpccenth2lts.blob.core.windows.net/wrf/wrf.zip
```
4. Update Batch and Storage account credential strings in batch-submit.py
> _BATCH_ACCOUNT_NAME = <br/>
> _BATCH_ACCOUNT_KEY = <br/>
> _BATCH_ACCOUNT_URL = <br/>
> _STORAGE_ACCOUNT_NAME = <br/>
> _STORAGE_ACCOUNT_KEY = <br/>
> _POOL_NODE_COUNT =  <br/>

5. Run the Python Script. It will create the pool, the job and the task on the number of nodes automatically. For this particular lab we use H16r machines and CentOS-HPC 7.4.
After the run has finished, the performance output is stored at the BLOB Storage in the folder wrf of your storage account.


```
python batch_submit.py -i data/namelist.input
```

6. Open Batchlabs and monitor the status. You can see the status of the nodes, the total cost as well as current quota. Also after this exercise, you can change your preferred settings and make a request for increased quota.

7. Install the Storage Explorer from https://azure.microsoft.com/en-us/features/storage-explorer/ to browse and easily transfer your results .


### Acknowledgement

For the WRF model and the input data
The University Corporation for Atmospheric Research
The National Center for Atmospheric Research
The UCAR Community Programs


