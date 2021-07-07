#!/bin/sh

sleep 10
kubectl rollout status deployment -n seldon pachyderm-default-0-pachyderm-container
kubectl rollout status deployment -n seldon pachyderm-default-explainer
kubectl rollout status deployment -n seldon-logs $(kubectl get deployments.apps -n seldon-logs | grep "seldon-seldondeployment-pachyderm-drift" | awk '{print $1}' | head -n 1)
kubectl rollout status deployment -n seldon-logs $(kubectl get deployments.apps -n seldon-logs | grep "seldon-seldondeployment-pachyderm-outlier" | awk '{print $1}' | head -n 1)