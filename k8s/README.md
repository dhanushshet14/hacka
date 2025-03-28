# Aetherion AR Kubernetes Deployment

This directory contains Kubernetes manifests for deploying the Aetherion AR backend infrastructure.

## Components

The deployment consists of:

- **Aetherion Backend**: The main FastAPI application
- **MongoDB**: For persistent data storage
- **Redis**: For session management and caching
- **Kafka**: For asynchronous messaging and event streaming
- **Zookeeper**: Required for Kafka operation

## Prerequisites

- Kubernetes cluster (local development or cloud provider)
- kubectl CLI configured to access your cluster
- Docker and container registry access (if building custom images)

## Building the Container Image

From the root of the project:

```bash
# Navigate to backend directory
cd backend

# Build the Docker image
docker build -t aetherion-backend:latest .

# For production, tag and push to your container registry
# docker tag aetherion-backend:latest your-registry/aetherion-backend:latest
# docker push your-registry/aetherion-backend:latest
```

## Deployment

Before deploying, customize the configuration:

1. Edit `01-configmap.yaml` for application settings
2. Edit `02-secrets.yaml` for secret values (consider using a secrets management solution in production)
3. Edit `06-backend.yaml` to set the correct image name if you're using a container registry

Deploy the application:

```bash
# Create namespace and deploy all components
kubectl apply -f k8s/

# Alternatively, deploy components in order
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/01-configmap.yaml
kubectl apply -f k8s/02-secrets.yaml
kubectl apply -f k8s/03-mongodb.yaml
kubectl apply -f k8s/04-redis.yaml
kubectl apply -f k8s/05-kafka.yaml
kubectl apply -f k8s/06-backend.yaml
```

## Accessing the Application

For local development with Minikube:

```bash
minikube service aetherion-backend-service -n aetherion
```

For production:
- Configure your DNS to point to the ingress controller IP address
- Use the hostname specified in the ingress resource: `api.aetherion-ar.example.com`

## Scaling

```bash
# Scale the backend replicas
kubectl scale deployment aetherion-backend -n aetherion --replicas=3
```

## Cleanup

```bash
# Remove all resources
kubectl delete -f k8s/
```

## Monitoring

Consider adding Prometheus and Grafana for monitoring your deployment. 