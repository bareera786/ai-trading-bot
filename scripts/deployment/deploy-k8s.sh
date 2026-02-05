#!/bin/bash

# Kubernetes Deployment Script for AI Trading Bot
# This script deploys the optimized trading bot to Kubernetes

set -e

echo "🚀 Deploying AI Trading Bot to Kubernetes..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    print_error "kubectl is not installed. Please install kubectl first."
    exit 1
fi

# Check if we're connected to a cluster
if ! kubectl cluster-info &> /dev/null; then
    print_error "Not connected to a Kubernetes cluster. Please configure kubectl."
    exit 1
fi

print_status "Connected to Kubernetes cluster: $(kubectl config current-context)"

# Create namespace if it doesn't exist
NAMESPACE="trading-bot"
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

print_status "Deploying to namespace: $NAMESPACE"

# Apply configurations in order
print_status "Creating PersistentVolumeClaims..."
kubectl apply -f k8s/pvc.yaml -n $NAMESPACE

print_status "Creating ConfigMap..."
kubectl apply -f k8s/configmap.yaml -n $NAMESPACE

print_status "Creating Secrets..."
kubectl apply -f k8s/secret.yaml -n $NAMESPACE

print_status "Creating NetworkPolicy..."
kubectl apply -f k8s/network-policy.yaml -n $NAMESPACE

print_status "Creating PodDisruptionBudget..."
kubectl apply -f k8s/pdb.yaml -n $NAMESPACE

print_status "Creating Service..."
kubectl apply -f k8s/service.yaml -n $NAMESPACE

print_status "Creating Deployment..."
kubectl apply -f k8s/optimized-deployment.yaml -n $NAMESPACE

print_status "Creating HorizontalPodAutoscaler..."
kubectl apply -f k8s/hpa.yaml -n $NAMESPACE

print_status "Creating Ingress..."
kubectl apply -f k8s/ingress.yaml -n $NAMESPACE

# Wait for deployment to be ready
print_status "Waiting for deployment to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/trading-bot -n $NAMESPACE

# Check pod status
print_status "Checking pod status..."
kubectl get pods -n $NAMESPACE -l app=trading-bot

# Check service status
print_status "Checking service status..."
kubectl get svc -n $NAMESPACE

# Check ingress status
print_status "Checking ingress status..."
kubectl get ingress -n $NAMESPACE

print_status "🎉 Deployment completed successfully!"
print_status "Your trading bot is now running in Kubernetes with:"
echo "  - 3 replicas with optimized resource allocation"
echo "  - Health checks and auto-scaling"
echo "  - Persistent storage for data and logs"
echo "  - Network security policies"
echo "  - High availability with PodDisruptionBudget"

print_warning "Don't forget to:"
echo "  1. Update the domain in k8s/ingress.yaml"
echo "  2. Update the secrets in k8s/secret.yaml with real values"
echo "  3. Configure SSL certificates"
echo "  4. Set up monitoring and alerting"

# Show logs of one pod to verify startup
print_status "Showing logs from one pod to verify startup..."
POD_NAME=$(kubectl get pods -n $NAMESPACE -l app=trading-bot -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
if [ ! -z "$POD_NAME" ]; then
    kubectl logs $POD_NAME -n $NAMESPACE --tail=20
fi