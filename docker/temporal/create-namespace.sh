#!/bin/sh
# Waits for the Temporal frontend, then ensures the `default` namespace exists.
set -eu
ADDR="${TEMPORAL_ADDRESS:-temporal:7233}"
for i in $(seq 1 60); do
  temporal operator cluster health --address "$ADDR" >/dev/null 2>&1 && break
  echo "waiting for temporal ($i)"; sleep 2
done
temporal operator namespace describe -n default --address "$ADDR" >/dev/null 2>&1 \
  || temporal operator namespace create -n default --retention 72h --address "$ADDR"
echo "namespace default ready"
