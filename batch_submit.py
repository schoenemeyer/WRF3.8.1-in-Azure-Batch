# batch.py - Batch Python SDK generic application script 
#
# Copyright (c) Microsoft Corporation
#
# All rights reserved.
#
# MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED *AS IS*, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

from __future__ import print_function
import datetime
import os
import sys, getopt
import time

try:
    input = raw_input
except NameError:
    pass

import azure.storage.blob as azureblob
import azure.batch.batch_service_client as batch
import azure.batch.batch_auth as batchauth
import azure.batch.models as batchmodels

sys.path.append('.')
sys.path.append('..')
import common.helpers  # noqa

# Update the Batch and Storage account credential strings below with the values
# unique to your accounts. These are used when constructing connection strings
# for the Batch and Storage client objects.
_BATCH_ACCOUNT_NAME = 'mybatchaccount'
_BATCH_ACCOUNT_KEY = 'rtl.................bu2Q=='
_BATCH_ACCOUNT_URL = 'https://batchaccount.northeurope.batch.azure.com'

_STORAGE_ACCOUNT_NAME = 'mystorageaccount'
_STORAGE_ACCOUNT_KEY = '5bL...............2yKw=='

_POOL_ID = 'Pool{}'.format(datetime.datetime.now().strftime("-%y%m%d-%H%M%S"))
_POOL_NODE_COUNT = 4 
#_POOL_VM_SIZE = 'BASIC_A2'
_POOL_VM_SIZE = 'Standard_H16r'
#_NODE_OS_PUBLISHER = 'Canonical'
_NODE_OS_PUBLISHER = 'Openlogic'
_NODE_OS_OFFER = 'CentOS-HPC'
_NODE_OS_SKU = '7.4'

_JOB_ID = 'Job{}'.format(datetime.datetime.now().strftime("-%y%m%d-%H%M%S"))

_TUTORIAL_TASK_FILE = 'task.py'
_TUTORIAL_EXECUTABLE = 'wrf.zip'
_TUTORIAL_MPI = 'mpi_small.zip'
_TUTORIAL_SCRIPT = 'runscript.sh'
_TUTORIAL_PREPSCRIPT = 'prepscript.sh'
_MESH_COUNT = '1'



def query_yes_no(question, default="yes"):
    """
    Prompts the user for yes/no input, displaying the specified question text.

    :param str question: The text of the prompt for input.
    :param str default: The default if the user hits <ENTER>. Acceptable values
    are 'yes', 'no', and None.
    :rtype: str
    :return: 'yes' or 'no'
    """
    valid = {'y': 'yes', 'n': 'no'}
    if default is None:
        prompt = ' [y/n] '
    elif default == 'yes':
        prompt = ' [Y/n] '
    elif default == 'no':
        prompt = ' [y/N] '
    else:
        raise ValueError("Invalid default answer: '{}'".format(default))

    while 1:
        choice = input(question + prompt).lower()
        if default and not choice:
            return default
        try:
            return valid[choice[0]]
        except (KeyError, IndexError):
            print("Please respond with 'yes' or 'no' (or 'y' or 'n').\n")


def print_batch_exception(batch_exception):
    """
    Prints the contents of the specified Batch exception.

    :param batch_exception:
    """
    print('-------------------------------------------')
    print('Exception encountered:')
    if batch_exception.error and \
            batch_exception.error.message and \
            batch_exception.error.message.value:
        print(batch_exception.error.message.value)
        if batch_exception.error.values:
            print()
            for mesg in batch_exception.error.values:
                print('{}:\t{}'.format(mesg.key, mesg.value))
    print('-------------------------------------------')


def upload_file_to_container(block_blob_client, container_name, file_path):
    """
    Uploads a local file to an Azure Blob storage container.

    :param block_blob_client: A blob service client.
    :type block_blob_client: `azure.storage.blob.BlockBlobService`
    :param str container_name: The name of the Azure Blob storage container.
    :param str file_path: The local path to the file.
    :rtype: `azure.batch.models.ResourceFile`
    :return: A ResourceFile initialized with a SAS URL appropriate for Batch
    tasks.
    """
    blob_name = os.path.basename(file_path)

    print('Uploading file {} to container [{}]...'.format(file_path,
                                                          container_name))

    block_blob_client.create_blob_from_path(container_name,
                                            blob_name,
                                            file_path)

    sas_token = block_blob_client.generate_blob_shared_access_signature(
        container_name,
        blob_name,
        permission=azureblob.BlobPermissions.READ,
        expiry=datetime.datetime.utcnow() + datetime.timedelta(hours=8))

    sas_url = block_blob_client.make_blob_url(container_name,
                                              blob_name,
                                              sas_token=sas_token)

    return batchmodels.ResourceFile(file_path=blob_name,
                                    blob_source=sas_url)


def get_container_sas_token(block_blob_client,
                            container_name, blob_permissions):
    """
    Obtains a shared access signature granting the specified permissions to the
    container.

    :param block_blob_client: A blob service client.
    :type block_blob_client: `azure.storage.blob.BlockBlobService`
    :param str container_name: The name of the Azure Blob storage container.
    :param BlobPermissions blob_permissions:
    :rtype: str
    :return: A SAS token granting the specified permissions to the container.
    """
    # Obtain the SAS token for the container, setting the expiry time and
    # permissions. In this case, no start time is specified, so the shared
    # access signature becomes valid immediately.
    container_sas_token = \
        block_blob_client.generate_container_shared_access_signature(
            container_name,
            permission=blob_permissions,
            expiry=datetime.datetime.utcnow() + datetime.timedelta(hours=2))

    return container_sas_token


def create_pool(batch_service_client, pool_id,
                resource_files, publisher, offer, sku):
    """
    Creates a pool of compute nodes with the specified OS settings.

    :param batch_service_client: A Batch service client.
    :type batch_service_client: `azure.batch.BatchServiceClient`
    :param str pool_id: An ID for the new pool.
    :param list resource_files: A collection of resource files for the pool's
    start task.
    :param str publisher: Marketplace image publisher
    :param str offer: Marketplace image offer
    :param str sku: Marketplace image sku
    """
    print('Creating pool [{}]...'.format(pool_id))

    # Create a new pool of Linux compute nodes using an Azure Virtual Machines
    # Marketplace image. For more information about creating pools of Linux
    # nodes, see:
    # https://azure.microsoft.com/documentation/articles/batch-linux-nodes/

    # Specify the commands for the pool's start task. The start task is run
    # on each node as it joins the pool, and when it's rebooted or re-imaged.
    # We use the start task to prep the node for running our task script.
    task_commands = [
        # Copy the python_tutorial_task.py script to the "shared" directory
        # that all tasks that run on the node have access to. Note that
        # we are using the -p flag with cp to preserve the file uid/gid,
        # otherwise since this start task is run as an admin, it would not
        # be accessible by tasks run as a non-admin user.
        'cp -p {} $AZ_BATCH_NODE_SHARED_DIR'.format(_TUTORIAL_TASK_FILE),
        'cp -p {} $AZ_BATCH_NODE_SHARED_DIR'.format(_TUTORIAL_EXECUTABLE),
        'cp -p {} $AZ_BATCH_NODE_SHARED_DIR'.format(_TUTORIAL_MPI),
        'cp -p {} $AZ_BATCH_NODE_SHARED_DIR'.format(_TUTORIAL_SCRIPT),
        'cp -p {} $AZ_BATCH_NODE_SHARED_DIR'.format(_TUTORIAL_PREPSCRIPT),
        'chmod +x $AZ_BATCH_NODE_SHARED_DIR/{}'.format(_TUTORIAL_EXECUTABLE),
        #'sudo yum -y install update',
        #'sudo yum -y install zip unzip libdapl2 libmlx4-1 bc wget libgomp1 ',
        #'sudo yum -y -q install wget 2>&1',
        #'tar zxvf $AZ_BATCH_NODE_SHARED_DIR/{} --directory=$AZ_BATCH_NODE_SHARED_DIR/'.format(_TUTORIAL_EXECUTABLE),
        'unzip -u $AZ_BATCH_NODE_SHARED_DIR/{} -d $AZ_BATCH_NODE_SHARED_DIR/'.format(_TUTORIAL_EXECUTABLE),
        'unzip -u $AZ_BATCH_NODE_SHARED_DIR/{} -d $AZ_BATCH_NODE_SHARED_DIR/'.format(_TUTORIAL_MPI),
        'chmod +x $AZ_BATCH_NODE_SHARED_DIR/{}'.format(_TUTORIAL_SCRIPT),
        'chmod +x $AZ_BATCH_NODE_SHARED_DIR/{}'.format(_TUTORIAL_PREPSCRIPT)
        # Install pip
        ##'curl -fSsL https://bootstrap.pypa.io/get-pip.py | sudo python',
        # Install the azure-storage module so that the task script can access
        # Azure Blob storage, pre-cryptography version
        ##'pip install azure-storage==0.32.0'
	# make sure MPI is allowed to run in Ubuntu, without this, this is seen as a security attack....
	#'sudo sed -i -e "s/kernel.yama.ptrace_scope = 1/kernel.yama.ptrace_scope = 0/" /etc/sysctl.d/10-ptrace.conf',
	#'sudo sysctl -w kernel.yama.ptrace_scope=0',
	#'bash -c sudo "echo \"*           hard    memlock         unlimited\" >> /etc/security/limits.conf"', 
	#'bash -c sudo "echo \"*           soft    memlock         unlimited\" >> /etc/security/limits.conf"', 
	]

    # Get the node agent SKU and image reference for the virtual machine
    # configuration.
    # For more information about the virtual machine configuration, see:
    # https://azure.microsoft.com/documentation/articles/batch-linux-nodes/
    sku_to_use, image_ref_to_use = \
        common.helpers.select_latest_verified_vm_image_with_node_agent_sku(
            batch_service_client, publisher, offer, sku)
    #user = batchmodels.AutoUserSpecification(
    #    scope=batchmodels.AutoUserScope.pool,
    #    elevation_level=batchmodels.ElevationLevel.admin)
    new_pool = batch.models.PoolAddParameter(
        id=pool_id,
        virtual_machine_configuration=batchmodels.VirtualMachineConfiguration(
            image_reference=image_ref_to_use,
            node_agent_sku_id=sku_to_use),
        vm_size=_POOL_VM_SIZE,
        target_dedicated_nodes=_POOL_NODE_COUNT,
	enable_inter_node_communication=1,
        start_task=batch.models.StartTask(
            command_line=common.helpers.wrap_commands_in_shell('linux',
                                                               task_commands),
            #user_identity=batchmodels.UserIdentity(auto_user=user),
	    #user_identity=batch.models.UserIdentity(user_name='myuser'),
	    user_identity=batch.models.UserIdentity(user_name='myuser'),
            wait_for_success=True,
            resource_files=resource_files),
	user_accounts=[batch.models.UserAccount('myuser', 'makethisaverysecureandrandompassword', elevation_level='admin', linux_user_configuration=None)],
    )


    try:
        batch_service_client.pool.add(new_pool)
    except batchmodels.batch_error.BatchErrorException as err:
        print_batch_exception(err)
        raise


def create_job(batch_service_client, job_id, pool_id):
    """
    Creates a job with the specified ID, associated with the specified pool.

    :param batch_service_client: A Batch service client.
    :type batch_service_client: `azure.batch.BatchServiceClient`
    :param str job_id: The ID for the job.
    :param str pool_id: The ID for the pool.
    """
    print('Creating job [{}]...'.format(job_id))

    job = batch.models.JobAddParameter(
        job_id,
        batch.models.PoolInformation(pool_id=pool_id))

    try:
        batch_service_client.job.add(job)
    except batchmodels.batch_error.BatchErrorException as err:
        print_batch_exception(err)
        raise


def add_tasks(batch_service_client, job_id, input_files,
              output_container_name, output_container_sas_token):
    """
    Adds a task for each input file in the collection to the specified job.

    :param batch_service_client: A Batch service client.
    :type batch_service_client: `azure.batch.BatchServiceClient`
    :param str job_id: The ID of the job to which to add the tasks.
    :param list input_files: A collection of input files. One task will be
     created for each input file.
    :param output_container_name: The ID of an Azure Blob storage container to
    which the tasks will upload their results.
    :param output_container_sas_token: A SAS token granting write access to
    the specified Azure Blob storage container.
    """

    task_commands = [
	'$AZ_BATCH_NODE_SHARED_DIR/{}'.format(_TUTORIAL_PREPSCRIPT)
	]


    print('Adding {} tasks to job [{}]...'.format(len(input_files), job_id))

    tasks = list()

    for idx, input_file in enumerate(input_files):

        command = ['python $AZ_BATCH_NODE_SHARED_DIR/{} '
                   '--filepath {} --numwords {} --storageaccount {} '
                   '--storagecontainer {} --sastoken "{}"'.format(
                       _TUTORIAL_TASK_FILE,
                       input_file.file_path,
                       '10',
                       _STORAGE_ACCOUNT_NAME,
                       output_container_name,
                       output_container_sas_token)]

        tasks.append(batch.models.TaskAddParameter(
                'topNtask{}'.format(idx),
                common.helpers.wrap_commands_in_shell('linux', command),
                resource_files=[input_file],
		multi_instance_settings=(batch.models.MultiInstanceSettings(
			coordination_command_line=common.helpers.wrap_commands_in_shell('linux',task_commands),
			number_of_instances=_POOL_NODE_COUNT)
			),
		user_identity=batch.models.UserIdentity(user_name='myuser'),
                )
        )

    batch_service_client.task.add_collection(job_id, tasks)


def wait_for_tasks_to_complete(batch_service_client, job_id, timeout):
    """
    Returns when all tasks in the specified job reach the Completed state.

    :param batch_service_client: A Batch service client.
    :type batch_service_client: `azure.batch.BatchServiceClient`
    :param str job_id: The id of the job whose tasks should be to monitored.
    :param timedelta timeout: The duration to wait for task completion. If all
    tasks in the specified job do not reach Completed state within this time
    period, an exception will be raised.
    """
    timeout_expiration = datetime.datetime.now() + timeout

    print("Monitoring all tasks for 'Completed' state, timeout in {}..."
          .format(timeout), end='')

    while datetime.datetime.now() < timeout_expiration:
        print('.', end='')
        sys.stdout.flush()
        tasks = batch_service_client.task.list(job_id)

        incomplete_tasks = [task for task in tasks if
                            task.state != batchmodels.TaskState.completed]
        if not incomplete_tasks:
            print()
            return True
        else:
            time.sleep(1)

    print()
    raise RuntimeError("ERROR: Tasks did not reach 'Completed' state within "
                       "timeout period of " + str(timeout))


def download_blobs_from_container(block_blob_client,
                                  container_name, directory_path):
    """
    Downloads all blobs from the specified Azure Blob storage container.

    :param block_blob_client: A blob service client.
    :type block_blob_client: `azure.storage.blob.BlockBlobService`
    :param container_name: The Azure Blob storage container from which to
     download files.
    :param directory_path: The local directory to which to download the files.
    """
    print('Downloading all files from container [{}]...'.format(
        container_name))

    container_blobs = block_blob_client.list_blobs(container_name)

    for blob in container_blobs.items:
        destination_file_path = os.path.join(directory_path, blob.name)

        block_blob_client.get_blob_to_path(container_name,
                                           blob.name,
                                           destination_file_path)

        print('  Downloaded blob [{}] from container [{}] to {}'.format(
            blob.name,
            container_name,
            destination_file_path))

    print('  Download complete!')

def main(argv):
   inputfile = ''
   #outputfile = ''
   try:
      opts, args = getopt.getopt(argv,"hi:m:",["inputfile=", "mesh="])
   except getopt.GetoptError:
      print('submit_batch.py -i <inputfile> [-m <meshcount>]')
      sys.exit(2)
   for opt, arg in opts:
      if opt == '-h':
         print('submit_batch.py -i <inputfile> [-m <meshcount>]')
         sys.exit()
      elif opt in ("-i", "--inputfile"):
         inputfile = arg
      elif opt in ("-m", "--mesh"):
         _MESH_COUNT = arg
   if inputfile == '':
     print ("please provide an inputfile: submit_batch.py -i <inputfile> [-m <meshcount>]")
     sys.exit()
   print ('Input file is ', inputfile)
   return inputfile



if __name__ == '__main__':

    inputfile = main(sys.argv[1:])
    start_time = datetime.datetime.now().replace(microsecond=0)
    print('Sample start: {}'.format(start_time))
    print()

    # Create the blob client, for use in obtaining references to
    # blob storage containers and uploading files to containers.
    blob_client = azureblob.BlockBlobService(
        account_name=_STORAGE_ACCOUNT_NAME,
        account_key=_STORAGE_ACCOUNT_KEY)

    # Use the blob client to create the containers in Azure Storage if they
    # don't yet exist.
    app_container_name = 'application'
    input_container_name = 'input'
    output_container_name = 'output'
    blob_client.create_container(app_container_name, fail_on_exist=False)
    blob_client.create_container(input_container_name, fail_on_exist=False)
    blob_client.create_container(output_container_name, fail_on_exist=False)

    # Paths to the task script. This script will be executed by the tasks that
    # run on the compute nodes.
    application_file_paths = [os.path.realpath('./application/{}'.format(_TUTORIAL_TASK_FILE)),
			      os.path.realpath('./application/{}'.format(_TUTORIAL_EXECUTABLE)),
			      os.path.realpath('./application/{}'.format(_TUTORIAL_MPI)),
			      os.path.realpath('./application/{}'.format(_TUTORIAL_SCRIPT)),
			      os.path.realpath('./application/{}'.format(_TUTORIAL_PREPSCRIPT))]

    # The collection of data files that are to be processed by the tasks.
    print('collection of data files')
    input_file_paths = [os.path.realpath(inputfile)]

    # Upload the application script to Azure Storage. This is the script that
    # will process the data files, and is executed by each of the tasks on the
    # compute nodes.
    print('Upload the application script')
    application_files = [
        upload_file_to_container(blob_client, app_container_name, file_path)
        for file_path in application_file_paths]

    # Upload the data files. This is the data that will be processed by each of
    # the tasks executed on the compute nodes in the pool.
    print('Upload the data files.')
    input_files = [
        upload_file_to_container(blob_client, input_container_name, file_path)
        for file_path in input_file_paths]

    # Obtain a shared access signature that provides write access to the output
    # container to which the tasks will upload their output.
    print('Obtain a shared access')
    output_container_sas_token = get_container_sas_token(
        blob_client,
        output_container_name,
        azureblob.BlobPermissions.WRITE)

    # Create a Batch service client. We'll now be interacting with the Batch
    # service in addition to Storage
    print('Batch service clients')
    credentials = batchauth.SharedKeyCredentials(_BATCH_ACCOUNT_NAME,
                                                 _BATCH_ACCOUNT_KEY)

    batch_client = batch.BatchServiceClient(
        credentials,
        base_url=_BATCH_ACCOUNT_URL)

    # Create the pool that will contain the compute nodes that will execute the
    # tasks. The resource files we pass in are used for configuring the pool's
    # start task, which is executed each time a node first joins the pool (or
    # is rebooted or re-imaged).
    print('Create the pool')
    create_pool(batch_client,
                _POOL_ID,
                application_files,
                _NODE_OS_PUBLISHER,
                _NODE_OS_OFFER,
                _NODE_OS_SKU)

    # Create the job that will run the tasks.
    create_job(batch_client, _JOB_ID, _POOL_ID)

    # Add the tasks to the job. We need to supply a container shared access
    # signature (SAS) token for the tasks so that they can upload their output
    # to Azure Storage.
    add_tasks(batch_client,
              _JOB_ID,
              input_files,
              output_container_name,
              output_container_sas_token)

    # Pause execution until tasks reach Completed state.
    wait_for_tasks_to_complete(batch_client,
                               _JOB_ID,
                               datetime.timedelta(minutes=30))

    print("  Success! All tasks reached the 'Completed' state within the "
          "specified timeout period.")

    # Download the task output files from the output Storage container to a
    # local directory. Note that we could have also downloaded the output
    # files directly from the compute nodes themselves.
    download_blobs_from_container(blob_client,
                                  output_container_name,
                                  os.path.expanduser('./result/'))

    # Clean up storage resources
    print('Deleting containers...')
    blob_client.delete_container(app_container_name)
    blob_client.delete_container(input_container_name)
    blob_client.delete_container(output_container_name)

    # Print out some timing info
    end_time = datetime.datetime.now().replace(microsecond=0)
    print()
    print('Sample end: {}'.format(end_time))
    print('Elapsed time: {}'.format(end_time - start_time))
    print()

    # Clean up Batch resources (if the user so chooses).
    #if query_yes_no('Delete job?') == 'yes':
    #    batch_client.job.delete(_JOB_ID)
    #batch_client.job.delete(_JOB_ID)

    if query_yes_no('Delete pool?') == 'yes':
          batch_client.pool.delete(_POOL_ID)
    #batch_client.pool.delete(_POOL_ID)

    #print()
    #input('Press ENTER to exit...')