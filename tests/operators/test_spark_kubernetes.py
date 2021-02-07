import json
import unittest
from unittest.mock import patch

from airflow import DAG
from airflow.models import Connection
from airflow.utils import db, timezone

from k8s.operators.spark_kubernetes import SparkKubernetesOperator

TEST_VALID_APPLICATION_YAML = \
    """
apiVersion: "sparkoperator.k8s.io/v1beta2"
kind: SparkApplication
metadata:
  name: spark-pi
  namespace: default
spec:
  type: Scala
  mode: cluster
  image: "gcr.io/spark-operator/spark:v2.4.5"
  imagePullPolicy: Always
  mainClass: org.apache.spark.examples.SparkPi
  mainApplicationFile: "local:///opt/spark/examples/jars/spark-examples_2.11-2.4.5.jar"
  sparkVersion: "2.4.5"
  restartPolicy:
    type: Never
  volumes:
    - name: "test-volume"
      hostPath:
        path: "/tmp"
        type: Directory
  driver:
    cores: 1
    coreLimit: "1200m"
    memory: "512m"
    labels:
      version: 2.4.5
    serviceAccount: spark
    volumeMounts:
      - name: "test-volume"
        mountPath: "/tmp"
  executor:
    cores: 1
    instances: 1
    memory: "512m"
    labels:
      version: 2.4.5
    volumeMounts:
      - name: "test-volume"
        mountPath: "/tmp"
"""
TEST_VALID_APPLICATION_JSON = \
    """
{
   "apiVersion":"sparkoperator.k8s.io/v1beta2",
   "kind":"SparkApplication",
   "metadata":{
      "name":"spark-pi",
      "namespace":"default"
   },
   "spec":{
      "type":"Scala",
      "mode":"cluster",
      "image":"gcr.io/spark-operator/spark:v2.4.5",
      "imagePullPolicy":"Always",
      "mainClass":"org.apache.spark.examples.SparkPi",
      "mainApplicationFile":"local:///opt/spark/examples/jars/spark-examples_2.11-2.4.5.jar",
      "sparkVersion":"2.4.5",
      "restartPolicy":{
         "type":"Never"
      },
      "volumes":[
         {
            "name":"test-volume",
            "hostPath":{
               "path":"/tmp",
               "type":"Directory"
            }
         }
      ],
      "driver":{
         "cores":1,
         "coreLimit":"1200m",
         "memory":"512m",
         "labels":{
            "version":"2.4.5"
         },
         "serviceAccount":"spark",
         "volumeMounts":[
            {
               "name":"test-volume",
               "mountPath":"/tmp"
            }
         ]
      },
      "executor":{
         "cores":1,
         "instances":1,
         "memory":"512m",
         "labels":{
            "version":"2.4.5"
         },
         "volumeMounts":[
            {
               "name":"test-volume",
               "mountPath":"/tmp"
            }
         ]
      }
   }
}
"""
TEST_APPLICATION_DICT = \
    {'apiVersion': 'sparkoperator.k8s.io/v1beta2',
     'kind': 'SparkApplication',
     'metadata': {'name': 'spark-pi', 'namespace': 'default'},
     'spec': {'driver': {'coreLimit': '1200m',
                         'cores': 1,
                         'labels': {'version': '2.4.5'},
                         'memory': '512m',
                         'serviceAccount': 'spark',
                         'volumeMounts': [{'mountPath': '/tmp',
                                           'name': 'test-volume'}]},
              'executor': {'cores': 1,
                           'instances': 1,
                           'labels': {'version': '2.4.5'},
                           'memory': '512m',
                           'volumeMounts': [{'mountPath': '/tmp',
                                             'name': 'test-volume'}]},
              'image': 'gcr.io/spark-operator/spark:v2.4.5',
              'imagePullPolicy': 'Always',
              'mainApplicationFile': 'local:///opt/spark/examples/jars/spark-examples_2.11-2.4.5.jar',
              'mainClass': 'org.apache.spark.examples.SparkPi',
              'mode': 'cluster',
              'restartPolicy': {'type': 'Never'},
              'sparkVersion': '2.4.5',
              'type': 'Scala',
              'volumes': [{'hostPath': {'path': '/tmp', 'type': 'Directory'},
                           'name': 'test-volume'}]}}


@patch('k8s.operators.spark_kubernetes.KubernetesHook.get_conn')
class TestSparkKubernetesOperator(unittest.TestCase):
    def setUp(self):
        db.merge_conn(
            Connection(
                conn_id='kubernetes_default_kube_config', conn_type='kubernetes',
                extra=json.dumps({})))
        db.merge_conn(
            Connection(
                conn_id='kubernetes_with_namespace', conn_type='kubernetes',
                extra=json.dumps({'extra__kubernetes__namespace': 'mock_namespace'})))
        args = {
            'owner': 'airflow',
            'start_date': timezone.datetime(2020, 2, 1)
        }
        self.dag = DAG('test_dag_id', default_args=args)

    @patch('kubernetes.client.apis.custom_objects_api.CustomObjectsApi.create_namespaced_custom_object')
    def test_create_application_from_yaml(self, mock_create_namespaced_crd, mock_kubernetes_hook):
        op = SparkKubernetesOperator(application_file=TEST_VALID_APPLICATION_YAML,
                                     dag=self.dag,
                                     conn_id='kubernetes_default_kube_config',
                                     task_id='test_task_id')
        op.execute(None)
        mock_kubernetes_hook.assert_called_once_with()
        mock_create_namespaced_crd.assert_called_with(body=TEST_APPLICATION_DICT,
                                                      group='sparkoperator.k8s.io',
                                                      namespace='default',
                                                      plural='sparkapplications',
                                                      version='v1beta2')

    @patch('kubernetes.client.apis.custom_objects_api.CustomObjectsApi.create_namespaced_custom_object')
    def test_create_application_from_json(self, mock_create_namespaced_crd, mock_kubernetes_hook):
        op = SparkKubernetesOperator(application_file=TEST_VALID_APPLICATION_JSON,
                                     dag=self.dag,
                                     conn_id='kubernetes_default_kube_config',
                                     task_id='test_task_id')
        op.execute(None)
        mock_kubernetes_hook.assert_called_once_with()
        mock_create_namespaced_crd.assert_called_with(body=TEST_APPLICATION_DICT,
                                                      group='sparkoperator.k8s.io',
                                                      namespace='default',
                                                      plural='sparkapplications',
                                                      version='v1beta2')

    @patch('kubernetes.client.apis.custom_objects_api.CustomObjectsApi.create_namespaced_custom_object')
    def test_namespace_from_operator(self, mock_create_namespaced_crd, mock_kubernetes_hook):
        op = SparkKubernetesOperator(application_file=TEST_VALID_APPLICATION_JSON,
                                     dag=self.dag,
                                     namespace='operator_namespace',
                                     conn_id='kubernetes_with_namespace',
                                     task_id='test_task_id')
        op.execute(None)
        mock_kubernetes_hook.assert_called_once_with()
        mock_create_namespaced_crd.assert_called_with(body=TEST_APPLICATION_DICT,
                                                      group='sparkoperator.k8s.io',
                                                      namespace='operator_namespace',
                                                      plural='sparkapplications',
                                                      version='v1beta2')

    @patch('kubernetes.client.apis.custom_objects_api.CustomObjectsApi.create_namespaced_custom_object')
    def test_namespace_from_connection(self, mock_create_namespaced_crd, mock_kubernetes_hook):
        op = SparkKubernetesOperator(application_file=TEST_VALID_APPLICATION_JSON,
                                     dag=self.dag,
                                     conn_id='kubernetes_with_namespace',
                                     task_id='test_task_id')
        op.execute(None)
        mock_kubernetes_hook.assert_called_once_with()
        mock_create_namespaced_crd.assert_called_with(body=TEST_APPLICATION_DICT,
                                                      group='sparkoperator.k8s.io',
                                                      namespace='mock_namespace',
                                                      plural='sparkapplications',
                                                      version='v1beta2')


if __name__ == '__main__':
    unittest.main()