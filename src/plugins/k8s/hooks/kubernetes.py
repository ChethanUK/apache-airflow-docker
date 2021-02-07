import tempfile
from typing import Any, Generator, Optional, Tuple, Union

import yaml
from airflow import AirflowException
from airflow.hooks.base_hook import BaseHook
from cached_property import cached_property
from kubernetes import client, config, watch


def _load_body_to_dict(body):
    try:
        body_dict = yaml.safe_load(body)
    except yaml.YAMLError as e:
        raise AirflowException("Exception when loading resource definition: %s\n" % e)
    return body_dict


class KubernetesHook(BaseHook):
    """
    Creates Kubernetes API connection.
    :param conn_id: the connection to Kubernetes cluster
    """

    def __init__(
            self,
            conn_id="kubernetes_default"
    ):
        self.connection = self.get_connection(conn_id)
        self.conn_id = conn_id
        self.extras = self.connection.extra_dejson

    def get_conn(self):
        """
        Returns kubernetes api session for use with requests
        """
        if self._get_field(("in_cluster")):
            self.log.debug("loading kube_config from: in_cluster configuration")
            config.load_incluster_config()
        elif self._get_field("kube_config") is None or self._get_field("kube_config") == '':
            self.log.debug("loading kube_config from: default file")
            config.load_kube_config()
        else:
            with tempfile.NamedTemporaryFile() as temp_config:
                self.log.debug("loading kube_config from: connection kube_config")
                temp_config.write(self._get_field("kube_config").encode())
                temp_config.flush()
                config.load_kube_config(temp_config.name)
                temp_config.close()
        return client.ApiClient()

    def get_namespace(self):
        """
        Returns the namespace that defined in the connection
        """
        return self._get_field("namespace", default="default")

    def _get_field(self, field_name, default=None):
        """
        Fetches a field from extras, and returns it. This is some Airflow
        magic. The kubernetes hook type adds custom UI elements
        to the hook page, which allow admins to specify in_cluster configutation, kube_config, namespace etc.
        They get formatted as shown below.
        """
        full_field_name = 'extra__kubernetes__{}'.format(field_name)
        print(field_name)
        if full_field_name in self.extras:
            return self.extras[full_field_name]
        else:
            return default

    @cached_property
    def api_client(self) -> Any:
        """Cached Kubernetes API client"""
        return self.get_conn()

    def create_custom_object(
            self, group: str, version: str, plural: str, body: Union[str, dict], namespace: Optional[str] = None
    ):
        """
        Creates custom resource definition object in Kubernetes

        :param group: api group
        :type group: str
        :param version: api version
        :type version: str
        :param plural: api plural
        :type plural: str
        :param body: crd object definition
        :type body: Union[str, dict]
        :param namespace: kubernetes namespace
        :type namespace: str
        """
        api = client.CustomObjectsApi(self.api_client)
        if namespace is None:
            namespace = self.get_namespace()
        if isinstance(body, str):
            body = _load_body_to_dict(body)
        try:
            response = api.create_namespaced_custom_object(
                group=group, version=version, namespace=namespace, plural=plural, body=body
            )
            self.log.debug("Response: %s", response)
            return response
        except client.rest.ApiException as e:
            raise AirflowException("Exception when calling -> create_custom_object: %s\n" % e)

    def get_custom_object(
            self, group: str, version: str, plural: str, name: str, namespace: Optional[str] = None
    ):
        """
        Get custom resource definition object from Kubernetes

        :param group: api group
        :type group: str
        :param version: api version
        :type version: str
        :param plural: api plural
        :type plural: str
        :param name: crd object name
        :type name: str
        :param namespace: kubernetes namespace
        :type namespace: str
        """
        api = client.CustomObjectsApi(self.api_client)
        if namespace is None:
            namespace = self.get_namespace()
        try:
            response = api.get_namespaced_custom_object(
                group=group, version=version, namespace=namespace, plural=plural, name=name
            )
            return response
        except client.rest.ApiException as e:
            raise AirflowException("Exception when calling -> get_custom_object: %s\n" % e)

    def get_namespace(self) -> str:
        """Returns the namespace that defined in the connection"""
        connection = self.get_connection(self.conn_id)
        extras = connection.extra_dejson
        namespace = extras.get("extra__kubernetes__namespace", "default")
        return namespace

    def get_pod_log_stream(
            self,
            pod_name: str,
            container: Optional[str] = "",
            namespace: Optional[str] = None,
    ) -> Tuple[watch.Watch, Generator[str, None, None]]:
        """
        Retrieves a log stream for a container in a kubernetes pod.

        :param pod_name: pod name
        :type pod_name: str
        :param container: container name
        :param namespace: kubernetes namespace
        :type namespace: str
        """
        api = client.CoreV1Api(self.api_client)
        watcher = watch.Watch()
        return (
            watcher,
            watcher.stream(
                api.read_namespaced_pod_log,
                name=pod_name,
                container=container,
                namespace=namespace if namespace else self.get_namespace(),
            ),
        )

    def get_pod_logs(
            self,
            pod_name: str,
            container: Optional[str] = "",
            namespace: Optional[str] = None,
    ):
        """
        Retrieves a container's log from the specified pod.

        :param pod_name: pod name
        :type pod_name: str
        :param container: container name
        :param namespace: kubernetes namespace
        :type namespace: str
        """
        api = client.CoreV1Api(self.api_client)
        return api.read_namespaced_pod_log(
            name=pod_name,
            container=container,
            _preload_content=False,
            namespace=namespace if namespace else self.get_namespace(),
        )
