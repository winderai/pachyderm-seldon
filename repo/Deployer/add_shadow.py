import argparse
import time
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from seldon_deploy_sdk.rest import ApiException
from pprint import pprint
from seldon_deploy_sdk import (
    Configuration,
    ApiClient,
    SeldonDeploymentsApi,
    PredictorSpec,
    PredictiveUnit,
    Logger,
    SeldonPodSpec,
    PodSpec,
    Container,
    EnvVar
)
from kubernetes import client as kclient

parser = argparse.ArgumentParser(
    description="Deploy a shadow model for income classification."
)

parser.add_argument("bucket_uri", type=str, help="Income classifier URI")
parser.add_argument("kubernetes_service_host", type=str, help="K8s host")
parser.add_argument("s3_endpoint", type=str, help="Pachyderm sidecar S3 gateway")
parser.add_argument("deployment_name", type=str, help="Name of the resulting SeldonDeployment")
parser.add_argument("model_version", type=str, help="Commit hash of the deployment")
args = parser.parse_args()

bucket_uri = args.bucket_uri
kubernetes_service_host = args.kubernetes_service_host
s3_endpoint = args.s3_endpoint
deployment_name = args.deployment_name
model_version = args.model_version
print("Models bucket URI: {}".format(bucket_uri))
print("Model version: {}".format(model_version))
print("K8s service host: {}".format(kubernetes_service_host))
print("S3 endpoint: {}".format(s3_endpoint))
print("Deployment name: {}".format(deployment_name))

########## Inject secret to Seldon namespaces ###########

k_config = kclient.Configuration()
k_config.host = "https://" + kubernetes_service_host + ":443"
k_config.verify_ssl = False
aApiClient = kclient.ApiClient(k_config)
v1 = kclient.CoreV1Api(aApiClient)
try:
    v1.delete_namespaced_secret(namespace="seldon", name="seldon-init-container-secret")
    v1.delete_namespaced_secret(namespace="seldon-logs", name="seldon-init-container-secret")
except:
    pass
sec  = kclient.V1Secret()
sec.metadata = kclient.V1ObjectMeta(name="seldon-init-container-secret")
sec.type = "Opaque"
sec.string_data = {
    "AWS_ACCESS_KEY_ID": "noauth", 
    "AWS_SECRET_ACCESS_KEY": "noauth", 
    "AWS_ENDPOINT_URL": s3_endpoint, 
    "USE_SSL": "false"
}
v1.create_namespaced_secret(namespace="seldon", body=sec)
v1.create_namespaced_secret(namespace="seldon-logs", body=sec)

########## SHADOW MODEL ###########

config = Configuration()
config.host = (
    "http://seldon-deploy.seldon-system.svc.cluster.local:80/seldon-deploy/api/v1alpha1"
)
api_client = ApiClient(config)
api_instance = SeldonDeploymentsApi(api_client)
namespace = "seldon"
action = 'Shadow created'

try:
    mldeployment = api_instance.read_seldon_deployment(deployment_name, namespace)
except ApiException as e:
    print("Exception when calling SeldonDeploymentsApi->read_seldon_deployment: %s\n" % e)

try:
    mldeployment.spec.predictors.append(
        PredictorSpec(
                component_specs=[
                    SeldonPodSpec(
                        spec=PodSpec(
                            containers=[
                                Container(
                                    name="{}-container".format(
                                        deployment_name),
                                    env=[
                                        EnvVar(name="MODEL_URI",
                                               value=bucket_uri),
                                        EnvVar(
                                            name="MODEL_COMMIT_HASH",
                                            value=model_version,
                                        ),
                                        EnvVar(name="AWS_ACCESS_KEY_ID",
                                               value="noauth"),
                                        EnvVar(name="AWS_SECRET_ACCESS_KEY",
                                               value="noauth"),
                                        EnvVar(name="AWS_ENDPOINT_URL",
                                               value=s3_endpoint),
                                        EnvVar(name="USE_SSL",
                                               value="false"),
                                    ],
                                )
                            ]
                        )
                    )
                ],
                name="shadow",
                traffic=0,
                shadow=True,
                replicas=1,
                annotations={
                    "seldon.io/canary":"false"
                },
                graph=PredictiveUnit(
                    children=[],
                    implementation="SKLEARN_SERVER",
                    model_uri=bucket_uri + "/dir",
                    env_secret_ref_name="seldon-init-container-secret",
                    name="{}-container".format(deployment_name),
                    logger=Logger(mode="all"),
                )
            )
    )
except Exception as e:
    print(e)

try:
    api_response = api_instance.update_seldon_deployment(deployment_name, namespace, mldeployment, action=action)
    print("update_seldon_deployment OK")
except ApiException as e:
    print("Exception when calling SeldonDeploymentsApi->update_seldon_deployment: %s\n" % e)


def _wait_for_deployment_complete(deployment_name, namespace, timeout=120):
    api = kclient.AppsV1Api(aApiClient)
    start = time.time()
    while time.time() - start < timeout:
        time.sleep(2)
        response = api.read_namespaced_deployment_status("{}-shadow-0-{}-container".format(deployment_name, deployment_name), namespace)
        s = response.status
        if (s.updated_replicas == response.spec.replicas and
                s.replicas == response.spec.replicas and
                s.available_replicas == response.spec.replicas and
                s.observed_generation >= response.metadata.generation):
            return True
        else:
            pass
            # print(f'[updated_replicas:{s.updated_replicas},replicas:{s.replicas}'
            #       ',available_replicas:{s.available_replicas},observed_generation:{s.observed_generation}] waiting...')

    raise RuntimeError(f'Waiting timeout for deployment {deployment_name}')

########## WAIT UNTIL SeldonDeployment is Available ###########
try:
    _wait_for_deployment_complete(deployment_name, namespace)
    time.sleep(5)
except ApiException as e:
    pass

print("DONE")

# Run indefinitely to keep the sidecar S3 gateway open
while True: time.sleep(0.5)