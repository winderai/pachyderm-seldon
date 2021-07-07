#!/bin/bash

for value in $(kubectl exec -t pod/elasticsearch-master-0  -n seldon-logs -- curl -s 'http://localhost:9200/_cat/indices' | awk '{print $3}')
do
    kubectl exec -t pod/elasticsearch-master-0  -n seldon-logs -- curl -s -X DELETE "localhost:9200/${value}?pretty"
done