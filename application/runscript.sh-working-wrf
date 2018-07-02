#!/bin/bash

# some comments to make sure the file is a little over 1K since otherwise it seems that the blob upload does not really understand it....
# some comments to make sure the file is a little over 1K since otherwise it seems that the blob upload does not really understand it....
# some comments to make sure the file is a little over 1K since otherwise it seems that the blob upload does not really understand it....
# some comments to make sure the file is a little over 1K since otherwise it seems that the blob upload does not really understand it....
# some comments to make sure the file is a little over 1K since otherwise it seems that the blob upload does not really understand it....

#http://www.advancedclustering.com/act_kb/tune-hpl-dat-file/
export SCRIPT_NAME=$0
export INPUT_FILE=$1
export PROJECT_NAME=$2
export SHORT_NAME=${PROJECT_NAME::-4}
echo "# full line"
echo $0 $1 $2
echo "# input file: $INPUT_FILE"
echo "# project: $PROJECT_NAME $SHORT_NAME"

export LD_LIBRARY_PATH=$AZ_BATCH_NODE_SHARED_DIR:$LD_LIBRARY_PATH
export PATH=./:$PATH
#export I_MPI_FABRICS=tcp  #no rdma so using tcp here...
export I_MPI_FABRICS=shm:dapl  #no rdma so using tcp here...
export I_MPI_DAPL_PROVIDER=ofa-v2-ib0
export I_MPI_DYNAMIC_CONNECTION=0

env

cd $AZ_BATCH_TASK_SHARED_DIR
cd share
cp $AZ_BATCH_NODE_SHARED_DIR/* .

export HPL_N=108288
export HPL_P=4
export HPL_Q=8
export HPL_NB=88
#mpirun -hosts $AZ_BATCH_HOST_LIST -np 8 ./fds circular_burner.fds 
#mpirun -hosts $AZ_BATCH_HOST_LIST -np 8 -ppn 4 ./fds $PROJECT_NAME 
#mpirun -hosts $AZ_BATCH_HOST_LIST -np 32 -ppn 16 ./xhpl_intel64_static -n $HPL_N -p $HPL_P -q $HPL_Q -nb $HPL_NB >> xhpl.out
ulimit -s unlimited
echo "Load Restart File and Boundary Data for WRF Run"
rm wrfbdy_d01 wrfrst_d01_2001-10-25_00_00_00
wget https://hpccenth2lts.blob.core.windows.net/wrf/wrfrst_d01_2001-10-25_00_00_00
wget https://hpccenth2lts.blob.core.windows.net/wrf/wrfbdy_d01
export LD_LIBRARY_PATH=$(pwd):/usr/lib64:$LD_LIBRARY_PATH
echo "Start WRF Run CONUS 12km"
pwd
ls  -lrt *
export OMP_NUM_THREADS=1
echo $OMP_NUM_THREADS
mpirun -np 16 ./wrf.exe 
#mpirun -hosts $AZ_BATCH_HOST_LIST -np 32 -ppn 16 ./wrf.exe
grep 'Timing for main' rsl.error.0000 | tail -149 | awk '{print $9}' | awk -f ./stats.awk >> wrf.out
zip wrf_results.zip wrf.out rsl.error.0000 ${SHORT_NAME}* 
cp wrf_results.zip ../wd/
echo "Finished WRF Run CONUS 12km"
