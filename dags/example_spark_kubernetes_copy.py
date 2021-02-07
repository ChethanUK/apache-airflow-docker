"""
This is an example DAG which uses SparkKubernetesOperator and SparkKubernetesSensor.
In this example, we create two tasks which execute sequentially.
The first task is to submit sparkApplication on Kubernetes cluster(the example uses spark-pi application).
and the second task is to check the final state of the sparkApplication that submitted in the first state.

Spark-on-k8s operator is required to be already installed on Kubernetes
https://github.com/GoogleCloudPlatform/spark-on-k8s-operator
"""

from datetime import timedelta

import yaml
# [START import_module]
# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG
from airflow.utils.dates import days_ago

# Operators; we need this to operate!
# from airflow.providers.cncf.kubernetes.operators.spark_kubernetes import SparkKubernetesOperator
# from airflow.providers.cncf.kubernetes.sensors.spark_kubernetes import SparkKubernetesSensor
from k8s.operators.spark_kubernetes import SparkKubernetesOperator
from k8s.sensors.spark_kubernetes import SparkKubernetesSensor

# [END import_module]

# [START default_args]
# These args will get passed on to each operator
# You can override them on a per-task basis during operator initialization

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email': ['airflow@example.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'max_active_runs': 1,
}
# [END default_args]

# [START instantiate_dag]

dag = DAG(
    'spark_pi_ex_1',
    default_args=default_args,
    description='submit spark-pi as sparkApplication on kubernetes',
    schedule_interval=timedelta(days=1),
    start_date=days_ago(1),
)


def _get_full_path(filename, airflow_base_dir="/opt/airflow/"):
    return f"{airflow_base_dir}/dags/{filename}"


def load_yaml_from_file(filename):
    try:
        spec = yaml.load(open(filename))
        return spec
    except:
        print("Err loading aml")
        pass


def set_arguments_on_spark_spec(restart_policy='Never', arguments=['20000'], dynamic_allocation=False,
                                yaml_filename="spark_scala_kubernetes_template.yaml"):
    yaml_file = _get_full_path(yaml_filename)
    spark_spec = load_yaml_from_file(yaml_file)
    print(spark_spec)
    spark_spec['spec']['arguments'] = arguments

    spark_spec['spec']['restartPolicy']['type'] = restart_policy
    spark_spec['spec']['dynamicAllocation']['enabled'] = dynamic_allocation
    return yaml.dump(spark_spec)


t1 = SparkKubernetesOperator(
    task_id='spark_pi_submit',
    namespace="spark",
    application_file=set_arguments_on_spark_spec(restart_policy="OnFailure", arguments=['5000'],
                                                 dynamic_allocation=True),
    kubernetes_conn_id="kubernetes_default",
    do_xcom_push=True,
    dag=dag,
)

t2 = SparkKubernetesSensor(
    task_id='spark_pi_monitor',
    namespace="spark",
    application_name="{{ task_instance.xcom_pull(task_ids='spark_pi_submit')['metadata']['name'] }}",
    kubernetes_conn_id="kubernetes_default",
    attach_log=True,
    # poke_interval=60,
    # timeout=60 * 60 * 24 * 7,
    # soft_fail=False,
    # mode='poke',
    dag=dag,
)

t3 = SparkKubernetesOperator(
    task_id='spark_pi_submit_1',
    namespace="spark",
    application_file=set_arguments_on_spark_spec(restart_policy="OnFailure", arguments=['2000'],
                                                 dynamic_allocation=True,
                                                 yaml_filename="spark_k8s_python_template.yaml.yaml"),
    kubernetes_conn_id="kubernetes_default",
    do_xcom_push=True,
    dag=dag,
)

t4 = SparkKubernetesSensor(
    task_id='spark_pi_monitor_2',
    namespace="spark",
    application_name="{{ task_instance.xcom_pull(task_ids='spark_pi_submit_1')['metadata']['name'] }}",
    kubernetes_conn_id="kubernetes_default",
    attach_log=True,
    # timeout=60 * 60 * 24 * 7,
    # poke_interval=60,
    # timeout=60 * 60 * 24 * 7,
    # soft_fail=False,
    # mode='poke',
    dag=dag,
)
t1 >> t2 >> t3 >> t4
