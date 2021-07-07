#!/bin/sh
echo "copy_models commits:"
pachctl list commit copy_models
echo "\n"
echo "copy_models branches:"
pachctl list branch copy_models
echo "\n"
echo "Production main-model version:"
kubectl get deployment -n seldon pachyderm-default-0-pachyderm-container -o jsonpath='{.spec.template.spec.containers[0].env[1].value}'
echo "\nDrift version:"
kubectl get pod -n seldon-logs $(kubectl get pod -n seldon-logs -l serving.knative.dev/service=seldon-seldondeployment-pachyderm-drift --sort-by=.metadata.creationTimestamp | grep Running | awk '{print $1}' | tail -n 1) -o jsonpath='{.spec.containers[0].args[1]}'
echo "\nOutlier version:"
kubectl get pod -n seldon-logs $(kubectl get pod -n seldon-logs -l serving.knative.dev/service=seldon-seldondeployment-pachyderm-outlier --sort-by=.metadata.creationTimestamp | grep Running | awk '{print $1}' | tail -n 1) -o jsonpath='{.spec.containers[0].args[1]}'


if [ -n "$1" ];
then
    SHADOW_VERSION=$(kubectl get sdep pachyderm -n seldon -o jsonpath='{.spec.predictors[1].componentSpecs[0].spec.containers[0].env[1].value}')
    echo "\n"
    echo "\nStaging version:"
    echo $SHADOW_VERSION
else
    :
fi