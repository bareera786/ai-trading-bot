# Kubernetes Deployment for AI Trading Bot

This directory contains optimized Kubernetes manifests for deploying the AI Trading Bot in a production environment.

## 🚀 Quick Start

```bash
# Deploy everything
./deploy-k8s.sh

# Check status
kubectl get pods -n trading-bot
kubectl get svc -n trading-bot
kubectl get ingress -n trading-bot
```

## 📁 Files Overview

### Core Deployment
- **`optimized-deployment.yaml`** - Main deployment with optimized resource allocation
- **`service.yaml`** - ClusterIP service for internal communication
- **`ingress.yaml`** - External access with SSL termination

### Configuration
- **`configmap.yaml`** - Environment variables and configuration
- **`secret.yaml`** - Sensitive data (API keys, passwords)
- **`pvc.yaml`** - Persistent storage for data and logs

### Advanced Features
- **`hpa.yaml`** - Horizontal Pod Autoscaler for auto-scaling
- **`network-policy.yaml`** - Network security policies
- **`pdb.yaml`** - Pod Disruption Budget for high availability

## ⚙️ Configuration

### Resource Optimization

The deployment uses highly optimized resource requests/limits:

```yaml
resources:
  requests:
    memory: "512Mi"   # Was: 2Gi (75% reduction)
    cpu: "250m"       # Was: 1 (75% reduction)
  limits:
    memory: "1Gi"     # Was: 4Gi (75% reduction)
    cpu: "500m"       # Was: 2 (75% reduction)
```

### Health Checks

- **Liveness Probe**: Restarts unhealthy pods
- **Readiness Probe**: Routes traffic only to healthy pods
- **Health Endpoint**: `/health` provides comprehensive system status

### Auto-Scaling

Horizontal Pod Autoscaler scales based on:
- CPU utilization (70% target)
- Memory utilization (80% target)
- Scales between 3-10 replicas

## 🔧 Pre-Deployment Setup

### 1. Update Secrets

Edit `k8s/secret.yaml` with your actual credentials:

```bash
# Encode your secrets
echo -n "your-binance-api-key" | base64
echo -n "your-binance-secret-key" | base64
```

### 2. Configure Domain

Update `k8s/ingress.yaml` with your domain:

```yaml
spec:
  tls:
  - hosts:
    - your-domain.com
  rules:
  - host: your-domain.com
```

### 3. Storage Class

Update `k8s/pvc.yaml` with your cluster's storage class:

```yaml
spec:
  storageClassName: your-storage-class
```

## 📊 Monitoring

### Health Checks
```bash
# Check pod health
kubectl get pods -n trading-bot

# View detailed health
kubectl logs -f deployment/trading-bot -n trading-bot
```

### Resource Usage
```bash
# Monitor resource usage
kubectl top pods -n trading-bot

# HPA status
kubectl get hpa -n trading-bot
```

### Scaling Events
```bash
# View scaling decisions
kubectl describe hpa trading-bot-hpa -n trading-bot
```

## 🔒 Security Features

- **Network Policies**: Restricts pod-to-pod communication
- **Security Context**: Non-root user execution
- **Secrets Management**: Encrypted sensitive data
- **RBAC**: Minimal required permissions

## 🚨 Troubleshooting

### Common Issues

1. **Pods not starting**
   ```bash
   kubectl describe pod <pod-name> -n trading-bot
   kubectl logs <pod-name> -n trading-bot
   ```

2. **Health check failures**
   ```bash
   kubectl exec -it <pod-name> -n trading-bot -- curl http://localhost:5000/health
   ```

3. **Storage issues**
   ```bash
   kubectl get pvc -n trading-bot
   kubectl describe pvc trading-bot-persistence -n trading-bot
   ```

### Logs and Debugging

```bash
# View all logs
kubectl logs -f deployment/trading-bot -n trading-bot

# Debug specific pod
kubectl exec -it <pod-name> -n trading-bot -- /bin/bash

# Check events
kubectl get events -n trading-bot --sort-by=.metadata.creationTimestamp
```

## 📈 Performance Optimization

### Resource Tuning

Monitor and adjust resource limits based on your workload:

```bash
# Get resource usage
kubectl top pods -n trading-bot

# Adjust limits if needed
kubectl edit deployment trading-bot -n trading-bot
```

### Scaling Configuration

Fine-tune HPA settings based on your traffic patterns:

```yaml
metrics:
- type: Resource
  resource:
    name: cpu
    target:
      type: Utilization
      averageUtilization: 70  # Adjust based on needs
```

## 🔄 Updates and Rollbacks

### Rolling Updates
```bash
# Update deployment
kubectl apply -f k8s/optimized-deployment.yaml -n trading-bot

# Check rollout status
kubectl rollout status deployment/trading-bot -n trading-bot
```

### Rollbacks
```bash
# Rollback to previous version
kubectl rollout undo deployment/trading-bot -n trading-bot

# Rollback to specific revision
kubectl rollout undo deployment/trading-bot --to-revision=2 -n trading-bot
```

## 🌐 Production Checklist

- [ ] Update domain in ingress.yaml
- [ ] Configure SSL certificates
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Configure backups for persistent volumes
- [ ] Set up alerting for critical metrics
- [ ] Test auto-scaling behavior
- [ ] Verify network policies
- [ ] Set up log aggregation
- [ ] Configure resource quotas
- [ ] Test disaster recovery procedures

## 📞 Support

For issues with the Kubernetes deployment:

1. Check the troubleshooting section above
2. Review Kubernetes events: `kubectl get events -n trading-bot`
3. Check pod logs: `kubectl logs deployment/trading-bot -n trading-bot`
4. Verify cluster resources: `kubectl describe nodes`

---

**Note**: This setup assumes you have a Kubernetes cluster with ingress controller, cert-manager, and appropriate storage classes configured.