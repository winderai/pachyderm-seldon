import argparse
import time
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from seldon_deploy_sdk import (
    Configuration,
    ApiClient,
    SeldonDeploymentsApi,
    SeldonDeployment,
    ObjectMeta,
    SeldonDeploymentSpec,
    PredictorSpec,
    PredictiveUnit,
    Logger,
    SeldonPodSpec,
    PodSpec,
    Container,
    Explainer,
    EnvVar,
    DriftDetectorApi,
    AlibiDetectServerParams,
    AlibiDetectorData,
    OutlierDetectorApi
)
from seldon_deploy_sdk.rest import ApiException
from kubernetes import client as kclient

parser = argparse.ArgumentParser(
    description="Deploy a model for income classification."
)

parser.add_argument("bucket_uri", type=str, help="Income classifier URI")
parser.add_argument("kubernetes_service_host", type=str, help="Kubernetes host")
parser.add_argument("s3_endpoint", type=str, help="Pachyderm S3 gateway")
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


########## MODEL + EXPLAINER ###########

config = Configuration()
config.host = (
    "http://seldon-deploy.seldon-system.svc.cluster.local:80/seldon-deploy/api/v1alpha1"
)
api_client = ApiClient(config)
seldon_api_instance = SeldonDeploymentsApi(api_client)
namespace = "seldon"

mldeployment = SeldonDeployment(
    api_version="machinelearning.seldon.io/v1",
    kind="SeldonDeployment",
    metadata=ObjectMeta(
        name=deployment_name, namespace=namespace, labels={"fluentd": "true"}
    ),
    spec = SeldonDeploymentSpec(
        name=deployment_name,
        protocol="seldon",
        annotations={
            "seldon.io/engine-seldon-log-messages-externally": "true"},
        predictors=[
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
                name="default",
                replicas=1,
                graph=PredictiveUnit(
                    children=[],
                    implementation="SKLEARN_SERVER",
                    model_uri=bucket_uri + "/dir",
                    env_secret_ref_name="seldon-init-container-secret",
                    name="{}-container".format(deployment_name),
                    logger=Logger(mode="all"),
                ),
                explainer=Explainer(
                    type="AnchorTabular",
                    model_uri=bucket_uri + "/dir",
                    env_secret_ref_name="seldon-init-container-secret",
                    config={
                        "seed": "112",
                        "threshold": "0.85", 
                        "coverage_samples": "10", 
                        "batch_size": "10"
                    }
                ),
                traffic=100,
            )
        ],
    ),
)


try:
    api_response=seldon_api_instance.delete_seldon_deployment(
        deployment_name, namespace)
except ApiException as e:
    pass

try:
    time.sleep(2)
    api_response=seldon_api_instance.create_seldon_deployment(
        namespace, mldeployment)
    print("create_seldon_deployment OK")
except ApiException as e:
    print(
        "Exception when calling SeldonDeploymentsApi->create_seldon_deployment: %s\n"
        % e
    )

########## DRIFT DETECTOR ###########

drift_api_instance = DriftDetectorApi(api_client)
drift_detector = AlibiDetectorData(
    deployment=deployment_name,
    namespace="seldon-logs",
    params=AlibiDetectServerParams(
        model_name=model_version,
        event_type='io.seldon.serving.inference.drift',
        event_source='io.seldon.serving.seldon-seldondeployment-{}-drift'.format(deployment_name),
        drift_batch_size='10',
        storage_uri=bucket_uri + '/dir/drift_detector_dir',
        env_secret_ref='seldon-init-container-secret',
        reply_url='http://seldon-request-logger.seldon-logs',
        protocol='seldon.http',
        http_port='8080',
        user_permission=8888
    ),
)

try:
    api_response = drift_api_instance.delete_drift_detector_seldon_deployment(
        deployment_name, namespace)
except ApiException as e:
    pass

try:
    time.sleep(5)
    api_response = drift_api_instance.create_drift_detector_seldon_deployment(
        deployment_name, namespace, drift_detector)
    print("create_drift_detector_seldon_deployment OK")
except ApiException as e:
    print(
        "Exception when calling SeldonDeploymentsApi->create_drift_detector_seldon_deployment: %s\n"
        % e
    )

########## OUTLIER DETECTOR ###########

outlier_api_instance = OutlierDetectorApi(api_client)

outlier_detector = AlibiDetectorData(
    deployment=deployment_name,
    namespace="seldon-logs",
    params=AlibiDetectServerParams(
        model_name=model_version,
        event_type='io.seldon.serving.inference.outlier',
        event_source='io.seldon.serving.seldon-seldondeployment-{}-outlier'.format(deployment_name),
        drift_batch_size='2',
        storage_uri=bucket_uri + '/dir/outlier_detector_dir',
        env_secret_ref='seldon-init-container-secret',
        reply_url='http://seldon-request-logger.seldon-logs',
        protocol='seldon.http',
        http_port='8080',
        user_permission=8888
    ),
)


try:
    api_response = outlier_api_instance.delete_outlier_detector_seldon_deployment(
        deployment_name, namespace)
except ApiException as e:
    pass


try:
    time.sleep(5)
    api_response = outlier_api_instance.create_outlier_detector_seldon_deployment(
        deployment_name, namespace, outlier_detector)
    print("create_outlier_detector_seldon_deployment OK")
except ApiException as e:
    print(
        "Exception when calling SeldonDeploymentsApi->create_outlier_detector_seldon_deployment: %s\n"
        % e
    )

######### WAIT UNTIL SeldonDeployment is Available ###########
try:
    while True:
        api_response = seldon_api_instance.read_seldon_deployment(deployment_name, namespace)
        if api_response.status.state == "Available":
            print('SeldonDeployment is ready!')
            break
        else:
            print('SeldonDeployment not ready yet')
            time.sleep(10)
    time.sleep(5)
except ApiException as e:
    pass


print("DONE")

# Run indefinitely to keep the sidecar S3 gateway open
while True: time.sleep(0.5)