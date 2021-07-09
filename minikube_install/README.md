# Pachyderm-Seldon Demo on Minikube

With this installation you can conveniently run through the tutorial directly on a laptop assuming it has enough resources.
It has been tested on a 6 cores machine, `x86-64` architecture with 32GB RAM.
Minikube provides a single-node local cluster, so this installation is meant just for testing purposes; to save on resources, we install Pachyderm in local mode which uses local storage on disk and does not create a PersistentVolume (PV). For a multi-node cluster, we provide installation instructions for GKE.

We will install:

1. A single-node Minikube cluster
1. Pachyderm 1.13
1. Istio 1.7.3
1. Knative Serving 0.18.3
1. Seldon Core 1.5.0
1. Seldon Core Analytics 1.4.0
1. Seldon Deploy 1.1.2
1. Knative Eventing 0.18.3
1. Elastic 7.6.0
1. Fluentd 8.0.0
1. Kibana 7.6.0

## Prerequisites

1. [`brew` package manager](https://brew.sh/)
1. [`minikube` v1.18](https://minikube.sigs.k8s.io/docs/)
1. Docker installed (required to extract files for Seldon Deploy)

Estimated time to complete: 30 minutes.

## Minikube

```
minikube start --cpus 10 --memory 27000 --disk-size=200g
```


## Istio setup

```
export ISTIO_VERSION=1.7.3
curl -L https://istio.io/downloadIstio | ISTIO_VERSION=${ISTIO_VERSION} sh -

export PATH="$PATH:$(pwd)/istio-1.7.3/bin"

istioctl version

istioctl install -f local-cluster-gateway.yaml

kubectl apply -n istio-system -f seldon-gateway.yaml
```

*Ref.: https://deploy-v1-1.seldon.io/docs/getting-started/production-installation/istio/*

## Install Knative Eventing

```
KNATIVE_EVENTING_URL=https://github.com/knative/eventing/releases/download
EVENTING_VERSION=v0.18.3
kubectl apply --filename ${KNATIVE_EVENTING_URL}/${EVENTING_VERSION}/eventing-crds.yaml
kubectl apply --filename ${KNATIVE_EVENTING_URL}/${EVENTING_VERSION}/eventing-core.yaml
kubectl apply --filename ${KNATIVE_EVENTING_URL}/${EVENTING_VERSION}/in-memory-channel.yaml
kubectl apply --filename ${KNATIVE_EVENTING_URL}/${EVENTING_VERSION}/mt-channel-broker.yaml
kubectl rollout status -n knative-eventing deployment/imc-controller
```

*Ref.: https://deploy-v1-1.seldon.io/docs/getting-started/production-installation/request-logging/#install-knative-eventing*

## Configure Knative Event broker

```
kubectl create namespace seldon-logs || echo "namespace seldon-logs exists"

kubectl create -f - <<EOF
apiVersion: eventing.knative.dev/v1
kind: Broker
metadata:
  name: default
  namespace: seldon-logs
EOF
```

*Ref.: https://deploy-v1-1.seldon.io/docs/getting-started/production-installation/request-logging/#configure-knative-event-broker*

## Install Seldon Core
```
kubectl create namespace seldon
kubectl config set-context $(kubectl config current-context) --namespace=seldon
kubectl create namespace seldon-system

helm install seldon-core seldon-core-operator \
    --version 1.5.0 \
    --repo https://storage.googleapis.com/seldon-charts \
    --set usageMetrics.enabled=true \
    --namespace seldon-system \
    --set executor.defaultEnvSecretRefName="seldon-init-container-secret" \
    --set executor.requestLogger.defaultEndpoint="http://broker-ingress.knative-eventing.svc.cluster.local/seldon-logs/default" \
    --set predictiveUnit.defaultEnvSecretRefName="seldon-init-container-secret" \
    --set istio.enabled=true \
    --set istio.gateway="istio-system/seldon-gateway"

kubectl rollout status deploy/seldon-controller-manager -n seldon-system
```

*Ref.: https://deploy-v1-1.seldon.io/docs/getting-started/production-installation/seldon/#seldon-core-installation*

## Install Knative Eventing

```
KNATIVE_EVENTING_URL=https://github.com/knative/eventing/releases/download
EVENTING_VERSION=v0.18.3

kubectl apply --filename ${KNATIVE_EVENTING_URL}/${EVENTING_VERSION}/eventing-crds.yaml

kubectl apply --filename ${KNATIVE_EVENTING_URL}/${EVENTING_VERSION}/eventing-core.yaml

kubectl apply --filename ${KNATIVE_EVENTING_URL}/${EVENTING_VERSION}/in-memory-channel.yaml

kubectl apply --filename ${KNATIVE_EVENTING_URL}/${EVENTING_VERSION}/mt-channel-broker.yaml

kubectl rollout status -n knative-eventing deployment/imc-controller
```

*Ref.: https://deploy-v1-1.seldon.io/docs/getting-started/production-installation/request-logging/#install-knative-eventing*

## Dowload Seldon Deploy repo:

```
TAG=1.1.2 && \
    docker create --name=tmp-sd-container seldonio/seldon-deploy-server:$TAG && \
    docker cp tmp-sd-container:/seldon-deploy-dist/seldon-deploy-install.tar.gz . && \
    docker rm -v tmp-sd-container

tar -xzf seldon-deploy-install.tar.gz

cp ./seldon-deploy-install/prerequisites-setup/efk/fluentd-values.yaml fluentd-values.yaml
```

## Elastic

```
helm upgrade --install elasticsearch elasticsearch \
    --version 7.6.0 \
    --namespace seldon-logs \
    --set service.type=ClusterIP \
    --set antiAffinity="soft" \
    --repo https://helm.elastic.co \
    --set image=docker.elastic.co/elasticsearch/elasticsearch-oss \
    --set replicas=1 \
    --set clusterHealthCheckParams="wait_for_status=green&timeout=50s"

kubectl rollout status statefulset/elasticsearch-master -n seldon-logs
```

*Ref.: https://deploy-v1-1.seldon.io/docs/getting-started/production-installation/request-logging/#elasticsearch*

## Fluentd and Kibana

```
helm repo update

helm upgrade --install fluentd fluentd-elasticsearch \
    --version 8.0.0 \
    --namespace seldon-logs -f fluentd-values.yaml \
    --repo https://kiwigrid.github.io

helm upgrade --install kibana kibana \
    --version 7.6.0 \
    --namespace seldon-logs \
    --set service.type=ClusterIP \
    --repo https://helm.elastic.co \
    --set image=docker.elastic.co/kibana/kibana-oss

kubectl rollout status deployment/kibana-kibana -n seldon-logs
```

*Ref.: https://deploy-v1-1.seldon.io/docs/getting-started/production-installation/request-logging/#fluentd-and-kibana*

## Configure Knative Event broker

```
kubectl create namespace seldon-logs || echo "namespace seldon-logs exists"

kubectl create -f - <<EOF
apiVersion: eventing.knative.dev/v1
kind: Broker
metadata:
  name: default
  namespace: seldon-logs
EOF
```

*Ref.: https://deploy-v1-1.seldon.io/docs/getting-started/production-installation/request-logging/#configure-knative-event-broker*

## Knative Serving

```
kubectl apply -f https://github.com/knative/serving/releases/download/v0.18.3/serving-crds.yaml
kubectl apply -f https://github.com/knative/serving/releases/download/v0.18.3/serving-core.yaml
kubectl apply -f https://github.com/knative-sandbox/net-istio/releases/download/v0.22.0/istio.yaml
kubectl apply -f https://github.com/knative-sandbox/net-istio/releases/download/v0.18.0/net-istio.yaml
kubectl --namespace istio-system get service istio-ingressgateway
kubectl get pods --namespace knative-serving
```

*Ref.: https://deploy-v1-1.seldon.io/docs/getting-started/production-installation/standalone-kfserving/#install-knative-serving*

## Seldon Deploy

```
kubectl create secret docker-registry regcred \
    --namespace=seldon-system \
    --docker-server=index.docker.io \
    --docker-username=foo \
    --docker-password=foo \
    --docker-email=foo@foo.com \
    --dry-run -o yaml | kubectl apply -f -

helm upgrade seldon-deploy ./seldon-deploy-install/sd-setup/helm-charts/seldon-deploy/ \
    --set image.image=seldonio/seldon-deploy-server:1.1.2 \
    --set virtualService.create=false \
    --set requestLogger.create=true \
    --set gitops.argocd.enabled=false \
    --set enableAppAuth=false \
    --namespace=seldon-system \
    --set executor.defaultEnvSecretRefName="seldon-init-container-secret" \
    --set predictiveUnit.defaultEnvSecretRefName="seldon-init-container-secret" \
    --set ingressGateway.seldonIngressService="istio-ingressgateway" \
    --set ingressGateway.kfServingIngressService="istio-ingressgateway" \
    --set ingressGateway.ingressNamespace="istio-system" \
    --set virtualService.create=true \
    --set virtualService.gateways={istio-system/seldon-gateway} \
    --install

kubectl rollout status deployment/seldon-deploy -n seldon-system
```

*Ref.: https://deploy-v1-1.seldon.io/docs/getting-started/production-installation/seldon/*

## Ensure visibility on namespaces

```
kubectl label ns seldon seldon.restricted=false --overwrite=true
```

*Ref.: https://deploy-v1-1.seldon.io/docs/getting-started/production-installation/seldon/#ensuring-visibility-on-namespaces*

## Seldon Analytics

Needed to collect and process monitoring logs such as drift and outlier detections.

```
helm repo add seldonio https://storage.googleapis.com/seldon-charts
helm repo update

kubectl create configmap -n seldon-system model-usage-rules --from-file=model-usage.rules.yml --dry-run -o yaml | kubectl apply -f -

helm upgrade seldon-core-analytics seldonio/seldon-core-analytics \
    --version 1.4.0 \
    --namespace seldon-system \
    --install \
    -f analytics-values.yaml
```

*Ref.: https://deploy-v1-1.seldon.io/docs/getting-started/production-installation/metrics/*


## Port forward Seldon Deploy dashboard and activate with licence key

Run in a separate terminal:
```
export POD_NAME=$(kubectl get pods --namespace seldon-system -l "app.kubernetes.io/name=seldon-deploy,app.kubernetes.io/instance=seldon-deploy" -o jsonpath="{.items[0].metadata.name}") && kubectl port-forward $POD_NAME 8000:8000 --namespace seldon-system
```

Now activate Seldon Deploy with your licence key at: http://127.0.0.1:8000/seldon-deploy/deployments?ns=seldon

## Install Pachyderm

```
brew tap pachyderm/tap && brew install pachyderm/tap/pachctl@1.13

pachctl version --client-only

kubectl create ns pachyderm

pachctl deploy local --namespace pachyderm

kubectl rollout status deployment -n pachyderm pachd
```

*Ref.: https://docs.pachyderm.com/1.13.x/getting_started/local_installation/*

#### Port forward Pachyderm

Run in a different terminal: 

```
pachctl port-forward --namespace pachyderm
```

Check whether `pachd` is reachable:

```
pachctl version
```

To access and activate the Pachyderm Dashboard visit: http://localhost:30080

Allow Pachyderm workers to create cluster Secret:

> :warning: This grants `system:anonymous` user extended privileges, don't use in production. See https://kubernetes.io/docs/reference/access-authn-authz/rbac/#user-facing-roles for more details. :warning:

```
kubectl create clusterrolebinding pachyderm-worker --clusterrole=edit --user=system:anonymous
```


## Clean Up

Delete your local cluster with the following command:

```
minikube delete
```

## Credits

This project was created by [Winder Research, an ML consultancy](https://WinderResearch.com), and funded by [Pachyderm](https://pachyderm.com).
