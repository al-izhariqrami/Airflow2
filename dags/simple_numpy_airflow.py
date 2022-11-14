from airflow import DAG, settings
from airflow.contrib.hooks.gcs_hook import GoogleCloudStorageHook
from airflow.operators.python_operator import PythonOperator
from airflow.models import Connection
from airflow.providers.google.cloud.operators.bigquery import BigQueryCreateExternalTableOperator

import pandas as pd
import numpy as np
from datetime import datetime
import json

def add_gcp_connection(**kwargs):
    new_conn = Connection(
            conn_id="google_cloud_default",
            conn_type='google_cloud_platform',
    )
    extra_field = {
        "extra__google_cloud_platform__scope": "https://www.googleapis.com/auth/cloud-platform",
        "extra__google_cloud_platform__project": "fellowship_77",
        "extra__google_cloud_platform__key_path": '/.google/credentials/google_credentials.json'
    }
#/.google/credentials/google_credentials.json
    session = settings.Session()

    #checking if connection exist
    if session.query(Connection).filter(Connection.conn_id == new_conn.conn_id).first():
        my_connection = session.query(Connection).filter(Connection.conn_id == new_conn.conn_id).one()
        my_connection.set_extra(json.dumps(extra_field))
        session.add(my_connection)
        session.commit()
    else: #if it doesn't exit create one
        new_conn.set_extra(json.dumps(extra_field))
        session.add(new_conn)
        session.commit()


default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2020, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1
}

# dag = DAG("AddGCPConnection", default_args=default_args, schedule_interval="@once")



def simpleNumpyToGCS(csv_name: str, folder_name: str,
                   bucket_name="fellowship_77", **kwargs):
    hook = GoogleCloudStorageHook()
    
    # data = {'col1': [1, 2], 'col2': [3, 4]}
    # df = pd.DataFrame(data=data)
    # df.to_csv('example1.csv', index=False)

    hook.upload(bucket_name, 
                object_name='{}/{}.csv'.format(folder_name, csv_name), 
                filename='/.google/credentials/bank_marketing.csv', 
                mime_type='text/csv')


dag = DAG('exampleDag',
          default_args=default_args,
          catchup=False)

with dag:

    # activateGCP = PythonOperator(
    #     task_id='add_gcp_connection_python',
    #     python_callable=add_gcp_connection,
    #     provide_context=True,
    # )

    simpleNumpyToGCS_task = PythonOperator(
        task_id='simpleNumpyToGCS',
        python_callable=simpleNumpyToGCS,
        provide_context=True,
        op_kwargs={'csv_name': 'example_airflow', 'folder_name': 'airflow'},
    )

    bigquery_external_table_task = BigQueryCreateExternalTableOperator(
        task_id="bigquery_external_table_task",
        table_resource={
            "tableReference": {
                "projectId": "applied-well-362908",
                "datasetId": "bank_marketing",
                "tableId": "external_table",
            },
            "externalDataConfiguration": {
                "sourceFormat": "CSV",
                "sourceUris": [f"gs://fellowship_77/airflow/example_airflow.csv"],
                #D:\13. Iykra Data Felowship\Project\Kelompok
                "autodetect": True,   
            },
            "location": "US",
        },
    )

    # activateGCP >> simpleNumpyToGCS_task
    simpleNumpyToGCS_task >> bigquery_external_table_task