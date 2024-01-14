#!/bin/sh

primary="primary"
nodes=("node1" "node2")
context="k3s-cluster"

if [[ -z "$PUBLIC_SSH_KEY_PATH" ]]; then
    echo "Must provide PUBLIC_SSH_KEY_PATH in environment" 1>&2
    exit 1
fi

if [[ -z "$PRIVATE_SSH_KEY_PATH" ]]; then
    echo "Must provide PRIVATE_SSH_KEY_PATH in environment" 1>&2
    exit 1
fi

createInstance () {
    multipass launch -n "$1" --cpus 4 --memory 8g --disk 15G --cloud-init - <<EOF
users:
- name: ${USER}
  groups: sudo
  sudo: ALL=(ALL) NOPASSWD:ALL
  ssh_authorized_keys: 
  - $(cat "$PUBLIC_SSH_KEY_PATH")
EOF
}

getNodeIP() {
    echo $(multipass list | grep $1 | awk '{print $3}')
}

installK3sPrimaryNode() {
    PRIMARY_IP=$(getNodeIP $1)
    k3sup install --ip "$PRIMARY_IP" --context "$context" --user "$USER" --ssh-key  "${PRIVATE_SSH_KEY_PATH}" --local-path ~/.kube/config
}

joinK3sNode() {
    NODE_IP=$(getNodeIP $1)
    k3sup join --server-ip "$PRIMARY_IP" --ip "$NODE_IP" --user "$USER" --ssh-key "${PRIVATE_SSH_KEY_PATH}"
}

createInstance $primary

for node in "${nodes[@]}"
do
    createInstance "$node"
done

installK3sPrimaryNode $primary

for node in "${nodes[@]}"
do
    joinK3sNode "$node"
done
