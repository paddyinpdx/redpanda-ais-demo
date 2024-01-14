Norwegian Ship Tracking Demo Using RedPanda, Postgres, and ClickHouse

## Overview

Demo was built on an M1 Macbook Air w/ 16 GB RAM. Untested on other platforms.

## Preqrequisites

brew install:
- multipass (to set up Ubuntu VMs)
- redpanda (for RPK client)
- postgres (for psql client)
- k3sup (to set up k3s cluster)
- kubernetes-ctl (for kubectl client)
- helm

pip3 install requirements.txt

## Create K3S Cluster

Uses https://github.com/tomowatt/k3s-multipass-bootstrap.

*NOTE*: This will overwrite ~/.kube/config, so back it up if you need to.

```
# Change the path to whatever keys you want to use
export PUBLIC_SSH_KEY_PATH=~/.ssh/id_rsa.pub
export PRIVATE_SSH_KEY_PATH=~/.ssh/id_rsa
`./set-up-k3s-cluster.sh`
```
To verify installation:
```
multipass list
multipass info <node-name>
kubectl get nodes -o wide
cat ~/.kube/config
```

## Deploy RedPanda via Helm

Use [RedPanda's Helm chart](https://github.com/redpanda-data/helm-charts/) to deploy a RedPanda cluster.

Changes to the values.yaml file:
```
- external.type NodePort
- external.domain demo.local
- tls.enabled false
- monitoring.enabled true
- storage.persistentVolume.size 5Gi
- config.cluster.auto_create_topics_enabled true
```
To install:
```
helm repo add redpanda https://charts.redpanda.com
helm repo update
helm install redpanda redpanda/redpanda --values=values-demo-redpanda.yaml
```
Confirm installation with:
```
kubectl get all -o wide
# If you just want to see the RedPanda services use the following. For redpanda-external, the ports are listed in the 
# format <external-listener-port>:<advertised-port>, and from left to right, the ports are for the four RedPanda APIs: 
# Admin, Kafka, HTTP Proxy, Schema Registry.
kubectl get service
# Set up a RedPanda profile:
rpk profile create --from-profile <(kubectl get configmap redpanda-rpk -o go-template='{{ .data.profile }}') redpanda
# Verify that you can connect to the cluster:
rpk cluster info
```
To view the RP config on a pod:
```
# Substitute the pod name from the output of "kubectl get all -o wide"
kubectl exec redpanda-0 -- cat /etc/redpanda/redpanda.yaml
```
Check for any issues on each node, looking especially in the Conditions and Events sections:
```
# Substitute the pod name from the output of "kubectl get all -o wide"
kubectl describe node redpanda-0
```
Configure /etc/hosts for to access brokers (see https://docs.redpanda.com/current/deploy/deployment-option/self-hosted/kubernetes/local-guide/#configure-external-access-to-redpanda)
```
# Note that "demo.local" (external.domain, from above) is also used here. 
sudo true && kubectl get endpoints,node -A -o go-template='{{ range $_ := .items }}{{ if and (eq .kind "Endpoints") (eq .metadata.name "redpanda-external") }}{{ range $_ := (index .subsets 0).addresses }}{{ $nodeName := .nodeName }}{{ $podName := .targetRef.name }}{{ range $node := $.items }}{{ if and (eq .kind "Node") (eq .metadata.name $nodeName) }}{{ range $_ := .status.addresses }}{{ if eq .type "InternalIP" }}{{ .address }} {{ $podName }}.demo.local{{ "\n" }}{{ end }}{{ end }}{{ end }}{{ end }}{{ end }}{{ end }}{{ end }}' | envsubst | sudo tee -a /etc/hosts
# Verify
cat /etc/hosts
curl http://redpanda-0.demo.local:31644/v1/node_config | jq
```
Start port forwarding in order to use the RP console:
```
kubectl port-forward service/redpanda-console 8080:8080
```
Then open http://localhost:8080 in a browser.

Now do some basic operations with rpk:
```
rpk topic create test_topic
rpk topic describe test_topic
echo "test message" | rpk topic produce test_topic
rpk topic consume test_topic
```

## Install Prometheus and add RedPanda dashboard to Grafana
Changes to the values.yaml file:
```
serviceMonitorSelector:
  matchLabels:
   app.kubernetes.io/name: redpanda
```    
To install:
```
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install prometheus prometheus-community/kube-prometheus-stack --values=values-demo-prometheus.yaml --values=values-demo-prometheus.yaml
```
Make it accessible from outside the cluster:
`kubectl port-forward service/prometheus-operated 9090:9090`

Now open http://localhost:9090 in a browser.

Use Grafana:
```
kubectl port-forward deployment/prometheus-grafana 3000
```
Now open http://localhost:3000 in a browser and log in with admin/prom-operator.

See if you can access the RedPanda metrics:
```
curl http://redpanda-1.demo.local:31644/public_metrics | jq
curl http://redpanda-1.demo.local:31644/metrics | jq
```
Use rpk to generate a dashboard:
`rpk generate grafana-dashboard --datasource prometheus --metrics-endpoint http://redpanda-0.demo.local:9644/public_metrics > redpanda-dashboard.json`
Add the dashboard to Grafana and you should be able to see RedPanda metrics!

## Install ClickHouse
Changes to the values.yaml file:
```
- persistence.size 2Gi
```
To install:
```
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
helm install clickhouse bitnami/clickhouse --values=values-demo-clickhouse.yaml
```
Expose the ClickHouse playground app:
```
kubectl port-forward service/clickhouse 8123:8123
```
To use ClickHouse Playground in the browser you need to get the default user's password:
```
echo $(kubectl get secret --namespace default clickhouse -o jsonpath="{.data.admin-password}" | base64 -d)
```

Now open http://localhost:8123/play in a browser. Then in the upper right, enter the password. You can now run the queries that are defined in ./sql/clickhouse.sql.

## Install PostgreSQL
Changes to the values.yaml file:
```
- image.debug true
- auth.enablePostgresUser true
- auth.postgresPassword "password00"
- primary.persistence.size 1Gi
- primary.pgHbaConfiguration
- primary.initdb.scripts.init.sql
- primary.service.type NodePort
```

Install Postgres:
```
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
helm install postgres bitnami/postgresql --values=values-demo-postgresql.yaml
```
Get the NodePort for the primary service:
```
kubectl get -o jsonpath="{.spec.ports[0].nodePort}" services postgres-postgresql
# OR
kubectl describe service postgres-postgresql
```
You should now be able to connect via psql:
```
# Change the port to the NodePort from the output of the previous command
psql -U postgres -d ship_voyage -h redpanda-0.demo.local -p 31022
# Enter password "password00", which was set in values-demo-postgresql.yaml
# Then try to run the following to see the created table:
\d+ ship
# Then try to run the following to see the created users:
\du+
# `\dp+ ship` or `\dz` were not working for some reason, so run the equivalent:
SELECT grantee, privilege_type
FROM information_schema.role_table_grants
WHERE table_name='ship';
SELECT table_name, column_name, grantee, privilege_type
FROM information_schema.column_privileges
WHERE table_name = 'ship';
# To quit
\q
```
Note that if you need to tweak something in initdb, this is only run on the first install. To re-run it, you need to delete the PVC
and uninstall PG:
```
kubectl delete persistentvolumeclaim data-postgres-postgresql-0
helm uninstall postgres
```
Then you can reinstall PG.