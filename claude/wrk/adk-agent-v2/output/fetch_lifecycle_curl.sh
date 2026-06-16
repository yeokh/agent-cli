#!/bin/bash

# Fetch Red Hat lifecycle pages using curl and extract key information

echo "Fetching RHEL lifecycle data..."
curl -s "https://access.redhat.com/product-life-cycles/?product=Red%20Hat%20Enterprise%20Linux" > rhel_lifecycle.html

echo "Fetching OpenShift lifecycle data..."
curl -s "https://access.redhat.com/support/policy/updates/openshift" > openshift_lifecycle.html

echo "Fetching Ansible lifecycle data..."
curl -s "https://access.redhat.com/support/policy/updates/ansible-automation-platform" > ansible_lifecycle.html

echo "Fetching Satellite lifecycle data..."
curl -s "https://access.redhat.com/support/policy/updates/satellite" > satellite_lifecycle.html

echo "Done fetching lifecycle pages"
