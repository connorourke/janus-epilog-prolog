#! /apps/mambaforge/bin/python
import mysql.connector
import json
import argparse
import urllib
import urllib.error
import urllib.request
import os
import subprocess
import time
import logging
from multiprocessing import Lock
import daemon
import re
import subprocess
#from  JanAcc import database,mysql_slurm
from mysql.connector import errorcode

def parse_args():
    '''
    Parse command line arguments.
    '''
    parser = argparse.ArgumentParser(description="Sample code for getting scheduled events.")
    parser.add_argument('--use_registry', action="store_true",
                        help="Get the IP address from Windows registry.")
    parser.add_argument('--ip_address', type=str,
                        help="The IP address of scheduled events endpoint.")
    return parser.parse_args()

def check_ip_address(address, headers):
    '''
    Checks whether the address of the scheduled event endpoint is valid.
    '''
    try:
        response = get_scheduled_events(address, headers)
        return 'Events' in json.loads(response.read().decode('utf-8'))
    except (urllib.error.URLError, UnicodeDecodeError, json.decoder.JSONDecodeError) as _:
        return False

def get_address(arg_ip_address, use_registry, headers):

    '''

    Gets the address of the Scheduled Events endpoint.

    '''

    ip_address = None
    address = None

    if arg_ip_address:
        # use IP address provided in parameter.
        ip_address = arg_ip_address

    else:
        # use default IP address for machines in VNET.
        ip_address = '169.254.169.254'

    ip_address = '169.254.169.254'

    # Check if the IP address is valid. If not, try getting the IP address from registry

    # or environment. Exits if no IP address is valid.

    address = make_address(ip_address)

    if not check_ip_address(address, headers):
        print("The provided IP address is invalid or VM is not in VNET. " +
              "Trying registry and environment.")

        ip_address = os.getenv('SCHEDULEDEVENTSIP')
        address = make_address(ip_address)
        if not check_ip_address(address, headers):
            print("Could not find a valid IP address. Please create your VM within a VNET " +

                  "or run discovery.py first")

            exit(1)
    return address


def get_scheduled_events(address, headers):

    '''

    Make a GET request and return the response received.

    '''

    request = urllib.request.Request(address, headers=headers)
    return urllib.request.urlopen(request)



def post_scheduled_events(address, data, headers):

    '''

    Make a POST request.

    '''
    request = urllib.request.Request(address, data=str.encode(data), headers=headers)
    urllib.request.urlopen(request)

def make_address(ip_address):
    '''
    Returns the address for scheduled event endpoint from the IP address provided.
    '''
    return 'http://' + ip_address + '/metadata/scheduledevents?api-version=2020-07-01'

def write_to_log(lock,logger,job_id):
    '''
    Use multiprocess to lock access to log file and to write
    the premption event to it
    
    Args:
        lock (Lock): multiprocessing Lock
        logger (logger): the logger
        job_id (str): the job id number
    '''
    lock.acquire()
    logger.warning("Premption event on job: "+str(job_id))
    lock.release()

def get_std_err(job_id):
    '''
    Get the stderr for the job from the job id
    as SLURM_STD_ERR isnt set for the prolog

    Args:
       job_id (str): id number of the job

    Returns:
       stderr file (str): location of the stderror file
    '''
    cmd="scontrol show job " + str(job_id) + " | grep StdErr"
    output = subprocess.check_output(cmd, shell=True)
    std_err = str(output).split("=")[1].split("\\")[0]

    return std_err

def get_db_connection():
    '''
    Get a connection to the db to log evictions

    Args:
        None
    Returns:
        cnx (mysql.connector.connection):  Connection to slurmdb
    '''


    config = { 'user': 'exampleuser@res-prd-research-slurm-db-1',
                   'password': 'examplepassword',
                   'auth_plugin':'mysql_native_password',
                   'host':'examplehost.mariadb.database.azure.com'
                 }

    not_connected=True
    try:
        cnx=mysql.connector.connect(**config)
    except mysql.connector.Error as err:
        print("Error getting mysql connection {}".format(err))
        exit(1)

    while not_connected:
        #try:
        #    cls.connection=mysql.connector.connect(**config)
        if cnx.is_connected():
            not_connected=False
        #except mysql.connector.Error as err:
        time.sleep(0.1)
        #    pass
    return cnx

def create_mysql_database(db_name,connection):
    '''
    Creates a database given a mysql server connection

    Args:
        dbname (str): Name of database to create
        connection (mysql.connector.connect): mysql connection to server
    Returns:
        None
    '''
    mysql_query = "CREATE DATABASE IF NOT EXISTS {}".format(db_name)
    mycursor = connection.cursor()
    try:
        mycursor.execute(mysql_query)
    except mysql.connector.Error as err:
        print("Error creating database: {}".format(err))

def execute_mysql_query(mysql_query,db_name,connection):
    '''
    Execute a mysql query on a table

    Args:
        mysql_query (string): query to execute
        table (string): table to execute on
        db_name (string): database to use
        connection (mysql.connector.connection): mysql connection to server
    Returns:
        None
    '''

    with connection.cursor() as mycursor:
        try:
            mycursor.execute("USE "+db_name+";")
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_BAD_DB_ERROR:
                print("Attempted to use database {}, but it doesn't exist. Ceating it.".format(err))
                create_mysql_database(db_name,connection)
            else:
                print("Error selecting database in execute_mysql_query: {}".format(err))
                exit(1)

        try:
            mycursor.execute(mysql_query)
        except mysql.connector.Error as err:            
            if err.errno == errorcode.ER_TABLE_EXISTS_ERROR:
                print("Warning: attempted table creation but table already exists.")
            else:
                print("Error executing mysql query in execute_mysql_query: {}".format(err))
                exit(1) 

        connection.commit()

def get_mysql_entry(select,values,table,db_name,connection):
    '''
    Return an entry from a mysql table

    Args:
        select ([str]): entries we are interested in
        values ({str,str}): values for SELECT i.e. SELECT ... WHERE values.value=values.key  
        table (str): mysql table name
        db_name (str): name of the database
        connection (mysql.connector.connection): mysql connection to server
    Returns:
        entries ((str)): tuple of entries returned
    '''
    entries=",".join(select)
    value_statement=" AND ".join([i[0]+"="+i[1] if i[1] != 'NULL'  else i[0]+" is "+i[1] for i in zip(values.keys(),values.values())] )
    mysql_query = "SELECT " + entries + " FROM "+ table + " WHERE " + value_statement + ";"

    with connection.cursor() as mycursor:
        try:
            mycursor.execute("USE "+db_name+";")
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_BAD_DB_ERROR:
                print("Attempted to use database {}, but it doesn't exist. Ceating it.".format(err))
                create_mysql_database(db_name,connection)
            else:
                print("Error selecting database in get_mysql_query: {}".format(err))
                exit(1)

        try:
            mycursor.execute(mysql_query)
        except mysql.connector.Error as err:
            raise Exception
    
        try:
            entries = mycursor.fetchall()
        
        except mysql.connector.Error as err:
            if err.msg == 'No result set to fetch from.':
                raise Exception("No result")
        connection.commit()

        return entries

def insert_mysql_entry(values,table,db_name,connection):
    '''
    Insert an entry into a mysql table

    Args:
        values ({str:str}): column,value pairs to insert 
        table (str): mysql table name
        db_name (str): name of the database
        connection (mysql.connector.connection): mysql connection to server
    Returns:
        None
    '''
    mysql_query = "INSERT into " + table + " ("+",".join(values.keys())+") VALUES("+",".join(values.values())+");"
    execute_mysql_query(mysql_query,db_name,connection)

def main():
    '''
    Sample code for getting scheduled events.
    '''

    user = os.getenv("SLURM_JOB_USER")
    cluster_name = os.getenv("SLURM_CLUSTER_NAME" )
   
    args = parse_args()
    headers = {'metadata':'true'}
#    logging.basicConfig(filename='/var/log/evictions.log', level=logging.DEBUG)
#    logger = logging.getLogger()
    address = get_address(args.ip_address, args.use_registry, headers)
    job_id = os.getenv("SLURM_JOB_ID")
    std_err = get_std_err(job_id)

#    lock=Lock()

    while True: 
        response = get_scheduled_events(address, headers)
        document = json.loads(response.read().decode('utf-8'))
        events = document['Events']
        for event in events:
            if event['EventType'] == 'Preempt':
                cnx = get_db_connection()
                part = get_mysql_entry(["`partition`"],{"id_job":str(job_id)},cluster_name+"_job_table","slurm_acct_db",cnx)
                values = {'id_job':str(job_id),'user':str("\""+user+"\""),'part':"\""+str(part[0][0])+"\""}
                insert_mysql_entry(values,"eviction_table","slurm_project_db",cnx)
                subprocess.run("scancel --signal=TERM "+job_id, shell=True, check=True)
                with open(std_err,"w") as f:
                    f.write("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< EVICTION NOTICE >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>\n")
                    f.write("    The job with id "+str(job_id)+ " has recieved a premption event and will now be evicted.\n")
                    f.write("                           A SIGTERM will be sent to the job.               \n")
#                write_to_log(lock,logger,job_id)
                return
        time.sleep(0.5)


if __name__ == '__main__':
    with daemon.DaemonContext():
        main()