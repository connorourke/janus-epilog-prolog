#! /apps/mambaforge/bin/python
import mysql.connector
import time
from mysql.connector import errorcode

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

def create_mysql_table(table_name,attributes,db_name,connection):
    '''
    Creates a table (table_name) in the given database given a mysql connection and
    database name

    Args:
        table_name (str): name of the table to create
        attributes ([str]):  list of attributes (column headers) and type for table
        db_name (str): name of the database
        connection (mysql.connector.connect): mysql connection to server
    Returns:
        None
    '''

    mysql_query = "CREATE TABLE " + table_name + " (" + ''.join([ attribute +" , " for attribute in attributes])[0:-2] + ");"
    execute_mysql_query(mysql_query,db_name,connection)

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
        if cnx.is_connected():
            not_connected=False
        time.sleep(0.1)
    return cnx

def main():
    '''
    Sample code to set-up evictions table
    '''

    #get connection to slurmdb
    cnx = get_db_connection()
    create_mysql_database('slurm_project_db',cnx)
    attributes = ["id_job INT(11)","user VARCHAR(255)", "part VARCGAR(255)"]
    create_mysql_table('eviction_table',attributes,'slurm_project_db',cnx)


if __name__ == '__main__':
        main()