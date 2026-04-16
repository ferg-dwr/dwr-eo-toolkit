# Deployment Guide

## Docker Images

Push to Docker Hub:
\`\`\`bash
docker tag dwr-eo-toolkit:latest fergdwr/dwr-eo-toolkit:latest
docker push fergdwr/dwr-eo-toolkit:latest
\`\`\`

## Kubernetes on Minikube (Local)

\`\`\`bash
minikube start
kubectl apply -f kubernetes/
kubectl get pods
\`\`\`

## Cloud Deployment (Google Cloud)

\`\`\`bash
gcloud container clusters create dwr-eo-toolkit-cluster
kubectl apply -f kubernetes/
\`\`\`

See full guide: KUBERNETES_SETUP.md