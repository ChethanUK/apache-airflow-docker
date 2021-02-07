import json
import tempfile
import unittest
from unittest.mock import patch

import kubernetes

from airflow.models import Connection
from airflow.utils import db

from k8s.hooks.kubernetes import KubernetesHook


class TestKubernetesHook(unittest.TestCase):
    def setUp(self):
        db.merge_conn(
            Connection(
                conn_id='kubernetes_in_cluster', conn_type='kubernetes',
                extra=json.dumps({'extra__kubernetes__in_cluster': True})))
        db.merge_conn(
            Connection(
                conn_id='kubernetes_kube_config', conn_type='kubernetes',
                extra=json.dumps({'extra__kubernetes__kube_config': '{"test": "kube"}'})))
        db.merge_conn(
            Connection(
                conn_id='kubernetes_default_kube_config', conn_type='kubernetes',
                extra=json.dumps({})))
        db.merge_conn(
            Connection(
                conn_id='kubernetes_with_namespace', conn_type='kubernetes',
                extra=json.dumps({'extra__kubernetes__namespace': 'mock_namespace'})))

    @patch("kubernetes.config.incluster_config.InClusterConfigLoader")
    def test_in_cluster_connection(self, mock_kube_config_loader):
        kubernetes_hook = KubernetesHook(conn_id='kubernetes_in_cluster')
        api_conn = kubernetes_hook.get_conn()
        mock_kube_config_loader.assert_called_once()
        self.assertIsInstance(api_conn, kubernetes.client.api_client.ApiClient)

    @patch("kubernetes.config.kube_config.KubeConfigLoader")
    @patch("kubernetes.config.kube_config.KubeConfigMerger")
    @patch.object(tempfile, 'NamedTemporaryFile')
    def test_kube_config_connection(self,
                                    mock_kube_config_loader,
                                    mock_kube_config_merger,
                                    mock_tempfile):
        kubernetes_hook = KubernetesHook(conn_id='kubernetes_kube_config')
        api_conn = kubernetes_hook.get_conn()
        mock_tempfile.is_called_once()
        mock_kube_config_loader.assert_called_once()
        mock_kube_config_merger.assert_called_once()
        self.assertIsInstance(api_conn, kubernetes.client.api_client.ApiClient)

    @patch("kubernetes.config.kube_config.KubeConfigLoader")
    @patch("kubernetes.config.kube_config.KubeConfigMerger")
    @patch("kubernetes.config.kube_config.KUBE_CONFIG_DEFAULT_LOCATION", "/mock/config")
    def test_default_kube_config_connection(self,
                                            mock_kube_config_loader,
                                            mock_kube_config_merger,
                                            ):
        kubernetes_hook = KubernetesHook(conn_id='kubernetes_default_kube_config')
        api_conn = kubernetes_hook.get_conn()
        mock_kube_config_loader.assert_called_once_with("/mock/config")
        mock_kube_config_merger.assert_called_once()
        self.assertIsInstance(api_conn, kubernetes.client.api_client.ApiClient)

    def test_get_namespace(self):
        kubernetes_hook_with_namespace = KubernetesHook(conn_id='kubernetes_with_namespace')
        kubernetes_hook_without_namespace = KubernetesHook(conn_id='kubernetes_default_kube_config')
        self.assertEqual(kubernetes_hook_with_namespace.get_namespace(), 'mock_namespace')
        self.assertEqual(kubernetes_hook_without_namespace.get_namespace(), 'default')


if __name__ == '__main__':
    unittest.main()