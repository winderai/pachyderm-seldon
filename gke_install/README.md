# Pachyderm-Seldon Demo on GKE

We will install:

1. A GKE Cluster with enough resources to host all components
1. Ad-hoc GCP firewall rule
1. Pachyderm 1.13
1. Istio 1.7.3
1. Knative Serving
1. Seldon Core 1.5.2
1. Seldon Core Analytics 1.5.2
1. Seldon Deploy 1.1.2
1. Knative Eventing 0.18.3
1. Elastic 7.6.0
1. Fluentd 8.0.0
1. Kibana 7.6.0

Estimated time to complete: 30 minutes.

## Prerequisites

1. `brew install google-cloud-sdk` [or equivalent](https://cloud.google.com/sdk/docs/install)
1. `gcloud auth login`
1. Enough quota to create the cluster and machine(s)
1. Docker installed (required to extract files for Seldon Deploy)

## Create a GKE Cluster

To avoid duplication, please set the following options:

```
export CLOUDSDK_CORE_PROJECT=your-project-id CLOUDSDK_COMPUTE_ZONE=europe-west1-d NAME=demo
```

> :warning: This creates a GKE cluster with PUBLIC nodes, to simplify the demo. Nodes are connected directly to the internet. This is not safe and should not be used for production deployments. :warning:

Create GKE cluster (three-node, machine type `e2-standard-8`, disk size 100gb, will be created in a default network/subnet):

```
gcloud container clusters create $NAME \
  --machine-type=e2-standard-8 \
  --disk-size=100GB \
  --num-nodes=3 \
  --preemptible \
  --issue-client-certificate \
  --no-enable-basic-auth \
  --scopes storage-rw
```

Then obtain the credentials with:

```
gcloud container clusters get-credentials $NAME
```

## Installing Istio and Knative via Anthos

Enabling Cloud Run for Anthos installs Istio and Knative Serving into the cluster to connect and manage your stateless workloads.

```
gcloud container clusters update $NAME \
  --update-addons=CloudRun=ENABLED,HttpLoadBalancing=ENABLED
```

*Ref.: https://cloud.google.com/anthos/run/docs/setup#existing_cluster*

## Configure Istio for Seldon

```
kubectl apply -n gke-system -f seldon-gateway.yaml
```

*Ref.: https://deploy-v1-1.seldon.io/docs/getting-started/production-installation/istio/*

## Firewall Rule (Private Networks ONLY)

> :warning: If you are following these instructions, please skip to the next step. This is for private-node GKE clusters only. :warning:

By default, GKE private clusters only allow the master to access Services at port 443 or 80. The Knative Serving webhook uses port 8443, so that needs to be added to the firewall. This is not in the Seldon documentation.

```
export GKE_MASTER_CIDR_BLOCK=$(gcloud container clusters describe $NAME --format="value(privateClusterConfig.masterIpv4CidrBlock.scope())")

export GKE_TARGET_TAGS=$(gcloud compute firewall-rules list \
    --filter "name~^gke-$NAME" \
    --format 'table(
        targetTags.list():label=TARGET_TAGS
    )' | tail -n 1)

export GKE_NETWORK=$(gcloud container clusters describe $NAME --format="value(networkConfig.network)")

echo $GKE_MASTER_CIDR_BLOCK
echo $GKE_TARGET_TAGS
echo $GKE_NETWORK

# Make sure the following firewall rule doesn't exist already
gcloud compute firewall-rules create "gke-$NAME-knativewebhook" \
    --action ALLOW \
    --direction INGRESS \
    --source-ranges ${GKE_MASTER_CIDR_BLOCK} \
    --rules tcp:8443 \
    --target-tags ${GKE_TARGET_TAGS} \
    --network ${GKE_NETWORK}
```

*Ref.: https://cloud.google.com/kubernetes-engine/docs/how-to/private-clusters#add_firewall_rules*

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

*Ref.: https://deploy-v1-1.seldon.io/docs/getting-started/production-installation/request-logging/*

## Configure Knative Event broker

```
kubectl create namespace seldon-logs

kubectl create -f - <<EOF
apiVersion: eventing.knative.dev/v1
kind: Broker
metadata:
  name: default
  namespace: seldon-logs
EOF
```

## Install Seldon Core

```
kubectl create namespace seldon
kubectl create namespace seldon-system
kubectl config set-context $(kubectl config current-context) --namespace=seldon

helm install seldon-core seldon-core-operator \
    --version 1.5.2 \
    --repo https://storage.googleapis.com/seldon-charts \
    --set usageMetrics.enabled=true \
    --namespace seldon-system \
    --set executor.defaultEnvSecretRefName="seldon-init-container-secret" \
    --set executor.requestLogger.defaultEndpoint="http://broker-ingress.knative-eventing.svc.cluster.local/seldon-logs/default" \
    --set predictiveUnit.defaultEnvSecretRefName="seldon-init-container-secret" \
    --set istio.enabled=true \
    --set istio.gateway="gke-system/seldon-gateway"

kubectl rollout status deploy/seldon-controller-manager -n seldon-system
```

*Ref.: https://docs.seldon.io/projects/seldon-core/en/latest/examples/seldon_core_setup.html*

## Download Seldon Deploy

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
kubectl create namespace seldon-logs

helm repo update

helm upgrade --install elasticsearch elasticsearch \
    --version 7.6.0 \
    --namespace seldon-logs \
    --set service.type=ClusterIP \
    --set antiAffinity="soft" \
    --repo https://helm.elastic.co \
    --set replicas=1 \
    --set image=docker.elastic.co/elasticsearch/elasticsearch-oss

kubectl rollout status statefulset/elasticsearch-master -n seldon-logs
```

*Ref.: https://deploy-v1-1.seldon.io/docs/getting-started/production-installation/request-logging/#fluentd-and-kibana*

## Fluentd and Kibana

```
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
    --set ingressGateway.seldonIngressService="istio-ingress" \
    --set ingressGateway.kfServingIngressService="istio-ingress" \
    --set ingressGateway.ingressNamespace="gke-system" \
    --set virtualService.create=true \
    --set virtualService.gateways={gke-system/seldon-gateway} \
    --install

kubectl rollout status deployment/seldon-deploy -n seldon-system
```

*Ref.: https://deploy-v1-1.seldon.io/docs/getting-started/production-installation/seldon/*

## Ensuring visibility on namespaces

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
    --version 1.5.2 \
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

## Install Pachyderm client

macOS:
```
brew tap pachyderm/tap && brew install pachyderm/tap/pachctl@1.13
```

Linux:
```
curl -o /tmp/pachctl.deb -L https://github.com/pachyderm/pachyderm/releases/download/v1.13.2/pachctl_1.13.2_amd64.deb && sudo dpkg -i /tmp/pachctl.deb
```

Verify pachctl installation:

```
pachctl version --client-only
```

## Create storage resources for Pachyderm

```
STORAGE_SIZE=<volume size, in GBs. e.g. "50">
BUCKET_NAME=<bucket name>
BUCKET_LOCATION=<bucket location, e.g. "EUROPE-WEST1">

gsutil mb -l ${BUCKET_LOCATION} gs://${BUCKET_NAME}
```

## Install Pachyderm

Grant *your user account* the privileges needed to create the clusterrolebindings for Pachyderm deploy.

```
kubectl create clusterrolebinding cluster-admin-binding --clusterrole=cluster-admin --user=$(gcloud config get-value account)
```

Launch the deployment.

```
kubectl create ns pachyderm

pachctl deploy google \
	${BUCKET_NAME} \
	${STORAGE_SIZE} \
	--dynamic-etcd-nodes=1 \
	--no-expose-docker-socket \
	--namespace pachyderm
	
kubectl rollout status deployment -n pachyderm pachd
```

*Ref.: https://docs.pachyderm.com/latest/deploy-manage/deploy/google_cloud_platform/*

#### Port forward Pachyderm

Run in a separate terminal:

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

Delete your cluster with the following command:

```
gcloud container clusters delete $NAME
gsutil -m rm -r gs://${BUCKET_NAME}
```

## Credits

This project was created by [Winder Research, an ML consultancy](https://WinderResearch.com), and funded by [Pachyderm](https://pachyderm.com).
