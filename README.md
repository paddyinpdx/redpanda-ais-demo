# Norwegian Ship Tracking Demo Using Redpanda and ClickHouse

## Overview

This demo application shows how to consume a [live TCP stream of maritime shipping data provided by the Norwegian Coastal Administration](https://www.kystverket.no/en/navigation-and-monitoring/ais/access-to-ais-data/), publish its data to Redpanda, consume and enrich data using a weather API, 
ingest it into ClickHouse to create materialized views, and then query ClickHouse to show the data in a Web portal that contains metrics, a grid and a map.

![demo](https://github.com/paddyinpdx/redpanda-ais-demo/assets/7103368/e004f893-7a9f-4782-b366-55239b4c0e79)

Highlights include:
* No fake data: use of real-world APIs
* No Docker Compose or minikube: three-node K3S local cluster
* Three Redpanda topics, one consumer and two producers
* Use of NodePorts instead of relying solely on port forwarding
* Apache Avro instead of JSON Schema (binary provides optimal storage and serialization)
* Dashboard shows metrics, grid with details, and interactive map
* Monitoring with Prometheus and Grafana

The Norwegian data feed consists of Automatic Identification System (AIS) messages. These are used for tracking ships:
* Ship transceivers send data about ship characteristics / position
* Vessel traffic services (e.g., Coast Guard) use w/ radar to manage

## Architecture
![Misc - Norwegian Ship Tracker POC Architecture](https://github.com/paddyinpdx/redpanda-ais-demo/assets/7103368/ad34fc09-5d74-4ebe-9361-a7fbfe97002e)

## Preqrequisites

_NOTE_: This demo was built on an M1 Macbook Air w/ 16 GB RAM. It is untested on other platforms.

brew install:

- multipass (to set up Ubuntu VMs)
- k3sup (to set up k3s cluster)
- kubernetes-ctl (for kubectl client)
- helm
- jq (for JSON parsing in the terminal)

Optional:
These are needed if you want to run commands from localhost instead of using `kubectl exec`.
brew install:

- redpanda (for rpk client)

Then install the Python dependencies:

```
pip install -r requirements.txt
```

Obtain a free API key for [WeatherAPI.com](https://rapidapi.com/weatherapi/api/weatherapi-com/) on RapidAPI. Note that you will be limited to 1000 requests per hour. If you need more, you can pay for a subscription.

## Create K3S Cluster

The script you will run is adapted from https://github.com/tomowatt/k3s-multipass-bootstrap. This will overwrite ~/.kube/config,
so either back it up if you need to, or consult the k3sup docs for how to merge the new config with the existing one.

The script requires that you have a public and private SSH key pair. If you don't have one, Google how to create one.
Then set the following environment variables:

```
# Change the path to whatever keys you want to use
export PUBLIC_SSH_KEY_PATH=~/.ssh/id_rsa.pub
export PRIVATE_SSH_KEY_PATH=~/.ssh/id_rsa
# Run the installation script:
./set-up-k3s-cluster.sh
```

To verify installation:

```
multipass list
multipass info <node-name>
kubectl get nodes -o wide
cat ~/.kube/config
```

## Install the Various Applications Using Helm

### Kube Prometheus Stack

For each of the Helm charts used for this demo, I cloned the chart's values.yaml and then made changes. For Prometheus,
I made the following changes to the values.yaml file, which allows Prometheus to target the ServiceMonitor that is created
when Redpanda is installed:

```
serviceMonitorSelector:
  matchLabels:
   app.kubernetes.io/name: redpanda
```

To install:

```
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install prometheus prometheus-community/kube-prometheus-stack --values=values-demo-prometheus.yaml
```

After about 20-30 seconds you should see output that indicates a successful deployment.

Now make it accessible from outside the cluster:

```
kubectl port-forward service/prometheus-operated 9090:9090
```

Now open http://localhost:9090 in a browser.

Do the same for the Grafana dashboard:

```
kubectl port-forward deployment/prometheus-grafana 3000
```

Now open http://localhost:3000 in a browser and log in with admin/prom-operator.

Later in this set up we will add Redpanda dashboards to Grafana.

### Redpanda

Use [Redpanda's Helm chart](https://github.com/redpanda-data/helm-charts/) to deploy a Redpanda cluster.

Changes to the values.yaml file:

```
- external.type NodePort
- external.domain demo.local
- tls.enabled false
- monitoring.enabled true
- storage.persistentVolume.size 5Gi
```

To install:

```
helm repo add redpanda https://charts.redpanda.com
helm repo update
helm install redpanda redpanda/redpanda --values=values-demo-redpanda.yaml
```

Confirm installation with:

```
kubectl get pods -o wide
```

To see the Redpanda services use the following. Note that for redpanda-external, the ports are listed in the
format <external-listener-port>:<advertised-port>, and from left to right, the ports are for the four Redpanda APIs:
Admin, Kafka, HTTP Proxy, Schema Registry.

```
kubectl get service -o wide
```

Configure /etc/hosts to access brokers using the fully qualified domain names (FQDN) instead of IP addresses (see https://docs.redpanda.com/current/deploy/deployment-option/self-hosted/kubernetes/local-guide/#configure-external-access-to-redpanda):

```
# Note that "demo.local" (external.domain, from above) is used here. 
sudo true && kubectl get endpoints,node -A -o go-template='{{ range $_ := .items }}{{ if and (eq .kind "Endpoints") (eq .metadata.name "redpanda-external") }}{{ range $_ := (index .subsets 0).addresses }}{{ $nodeName := .nodeName }}{{ $podName := .targetRef.name }}{{ range $node := $.items }}{{ if and (eq .kind "Node") (eq .metadata.name $nodeName) }}{{ range $_ := .status.addresses }}{{ if eq .type "InternalIP" }}{{ .address }} {{ $podName }}.demo.local{{ "\n" }}{{ end }}{{ end }}{{ end }}{{ end }}{{ end }}{{ end }}{{ end }}' | envsubst | sudo tee -a /etc/hosts
# Verify
cat /etc/hosts
curl http://redpanda-0.demo.local:31644/v1/node_config | jq
```

Now set up a Redpanda profile, which is useful for connecting to the cluster from localhost:

```
rpk profile create --from-profile <(kubectl get configmap redpanda-rpk -o go-template='{{ .data.profile }}') redpanda
# Verify that you can connect to the cluster:
rpk cluster info
```

Sometimes it's handy to view the Redpanda configuration file on a pod, e.g.:

```
# Substitute the pod name from the output of "kubectl get all -o wide"
kubectl exec redpanda-0 -- cat /etc/redpanda/redpanda.yaml
```

You can also check for any issues on each node, looking especially in the Conditions and Events sections:

```
# Substitute the pod name from the output of "kubectl get all -o wide", but the pod naes should just be redpanda-0, redpanda-1, etc.
kubectl describe node redpanda-0
```

Start port forwarding in order to use the RP console:

```
kubectl port-forward service/redpanda-console 8080:8080
```

Then open http://localhost:8080 in a browser.

Create the topics (you could also use set `auto_create_topics_enabled` to `true` in the values.yaml and update the cluster, but it's generally considered a best practice to manage topics manually):

```
rpk topic create ship-position-events -p 3
# Use compact b/c usually only the destination changes for any given ship, so we only need the latest.
rpk topic create ship-info-events -c cleanup.policy=compact -p 
rpk topic create ship-position-events-with-weather -p
```

Test the HTTP Proxy API (pandaproxy):

```
curl redpanda-0.demo.local:30082/topics | jq
```

Returning to Prometheus and Grafana, see if you can access the Redpanda metrics:

```
curl http://redpanda-1.demo.local:31644/public_metrics
curl http://redpanda-1.demo.local:31644/metrics
```

Use rpk to generate dashboards (see https://docs.redpanda.com/current/reference/rpk/rpk-generate/rpk-generate-grafana-dashboard/):

```
rpk generate grafana-dashboard --datasource prometheus --dashboard operations --metrics-endpoint http://redpanda-0.demo.local:9644/public_metrics > redpanda-dashboard-operations.json
rpk generate grafana-dashboard --datasource prometheus --dashboard consumer-offsets --metrics-endpoint http://redpanda-0.demo.local:9644/public_metrics > redpanda-dashboard-consumer-offsets.json
rpk generate grafana-dashboard --datasource prometheus --dashboard topic-metrics --metrics-endpoint http://redpanda-0.demo.local:9644/public_metrics > redpanda-dashboard-topic-metrics.json
```

Add the dashboards to Grafana and you should be able to see Redpanda metrics!

### ClickHouse

Changes to the values.yaml file:

```
- auth.password passwordCH!
- persistence.size 2Gi
```

To install:

```
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
helm install clickhouse bitnami/clickhouse --values=values-demo-clickhouse.yaml
```

To use ClickHouse Playground in the browser you need to get the default user's password:

```
echo $(kubectl get secret --namespace default clickhouse -o jsonpath="{.data.admin-password}" | base64 -d)
```

Expose the ClickHouse playground app:

```
kubectl port-forward service/clickhouse 8123:8123
```

Now open http://localhost:8123/play in a browser. Then in the upper right, enter the password. You can now run the queries that are defined in ./sql/clickhouse-ddl.sql.

You will return to this console a bit later to run the queries in /sql/clickhouse.sql.

### ClickHouse DDL Queries

Go to the ClickHouse Playground open in your browser (see steps above). Copy and paste the queries in ./sql/clickhouse-ddl.sql and run them one at a time.

### Handling "Can't get assignment." Errors

Currently, if you stop both worker nodes and then restart, ClickHouse appears to "lose" the tables that use a Kafka engine. If you run `select * from system.kafka_consumers` 
in ClickHouse they will be gone, but the Redpanda console will continue to show them as active assignments in their respective consumer groups. This means you cannot delete the 
consumer group. To solve this problem, look at the assignment name, which is prefixed with the ClickHouse pod name. Then run the following:
```
kubectl delete pvc data-<assignment-name>, e.g., kubectl delete pvc data-clickhouse-shard0-2
kubectl delete pod clickhouse-shard0-2
helm upgrade -i clickhouse bitnami/clickhouse --values=values-demo-clickhouse.yaml
```
This will delete the ProvisionedVolumeClaim and the pod, and then reinstall the pod. Redpanda will no longer see an active assignment, and you can then recreate the tables in ClickHouse.

## Run the Producers and Consumers

You are now ready to run the producer and consumer scripts. Run each in their own terminal window:

```
python lib/producer-from-ais-api.py
python lib/consumer-and-producer-enrich-position-with-weather.py
```

## Run the Console

```
cd lib
streamlit run console.py
```

## Uninstalling Everything

```
multipass delete primary node1 node2
multipass purge
```

## Future Enhancements
* Transform raw AIS messages into Avro messages using Redpanda Data Transforms (instead of doing so in the producer script)
* Deploy the consumer script to Kubernetes so that it can be scaled
