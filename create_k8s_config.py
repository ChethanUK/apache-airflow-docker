airflow_sa_token = "airflow_sa_tokem"
cluster_certificate_authority = ""
kubernetes_api_endpoint = ""
cluster_name = ""
context_name = ""
default_namespace = ""

# airflow_connection_extra_gen = f""" "extra__kubernetes__in_cluster": false, "extra__kubernetes__kube_config": "{\"apiVersion\":\"v1\",\"kind\":\"Config\",\"users\":[{\"name\":\"airflow-sa\",\"user\":{\"token\":\"{airflow_sa_token}\"}}],\"clusters\":[{\"cluster\":{\"certificate-authority-data\":\"{cluster_certificate_authority}\",\"server\":\"{kubernetes_api_endpoint}\"},\"name\":\"{cluster_name}\"}],\"contexts\":[{\"context\":{\"cluster\":\"{cluster_name}\",\"user\":\"airflow-sa\"},\"name\":\"{context_name}\"}],\"current-context\":\"{context_name}\"}", "extra__kubernetes__namespace": "{default_namespace}" """

# print(airflow_connection_extra_gen)