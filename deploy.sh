#!/bin/bash

# Exit on error
set -e

echo "===== Aetherion AR Deployment Script ====="
echo ""

# Function to display help
display_help() {
  echo "Usage: ./deploy.sh [options]"
  echo ""
  echo "Options:"
  echo "  --help                Display this help message"
  echo "  --build-only          Only build the Docker image"
  echo "  --deploy-only         Only deploy Kubernetes manifests"
  echo "  --local               Use Docker Compose for local development"
  echo "  --minikube            Deploy to Minikube"
  echo "  --registry REGISTRY   Specify Docker registry (default: none)"
  echo "  --tag TAG             Specify image tag (default: latest)"
  echo ""
}

# Default values
BUILD=true
DEPLOY=true
LOCAL=false
MINIKUBE=false
REGISTRY=""
TAG="latest"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --help)
      display_help
      exit 0
      ;;
    --build-only)
      BUILD=true
      DEPLOY=false
      shift
      ;;
    --deploy-only)
      BUILD=false
      DEPLOY=true
      shift
      ;;
    --local)
      LOCAL=true
      BUILD=false
      DEPLOY=false
      shift
      ;;
    --minikube)
      MINIKUBE=true
      shift
      ;;
    --registry)
      REGISTRY="$2"
      shift 2
      ;;
    --tag)
      TAG="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      display_help
      exit 1
      ;;
  esac
done

# Set image name
if [ -z "$REGISTRY" ]; then
  IMAGE_NAME="aetherion-backend:$TAG"
else
  IMAGE_NAME="$REGISTRY/aetherion-backend:$TAG"
fi

# Function to build Docker image
build_image() {
  echo "Building Docker image: $IMAGE_NAME"
  cd backend
  docker build -t "$IMAGE_NAME" .
  
  if [ ! -z "$REGISTRY" ]; then
    echo "Pushing Docker image to registry: $REGISTRY"
    docker push "$IMAGE_NAME"
  fi
  
  cd ..
}

# Function to deploy to Kubernetes
deploy_k8s() {
  echo "Deploying to Kubernetes..."
  
  # If using custom registry, update the image in backend.yaml
  if [ ! -z "$REGISTRY" ] || [ "$TAG" != "latest" ]; then
    echo "Updating image in Kubernetes manifests..."
    sed -i.bak "s|image: aetherion-backend:latest|image: $IMAGE_NAME|g" k8s/06-backend.yaml
    rm -f k8s/06-backend.yaml.bak
  fi
  
  # If using Minikube, point Docker to Minikube's Docker daemon
  if [ "$MINIKUBE" = true ]; then
    echo "Using Minikube Docker daemon..."
    eval $(minikube docker-env)
  fi
  
  # Apply Kubernetes manifests
  kubectl apply -f k8s/
  
  echo "Waiting for deployments to be ready..."
  kubectl wait --for=condition=available --timeout=300s deployment/aetherion-backend -n aetherion
  
  # If using Minikube, show service URL
  if [ "$MINIKUBE" = true ]; then
    echo "Service URL: $(minikube service aetherion-backend-service -n aetherion --url)"
  fi
}

# Function to start local development with Docker Compose
start_local() {
  echo "Starting local development environment with Docker Compose..."
  cd backend
  docker-compose up -d
  echo "Local environment started. Access the API at http://localhost:8000"
  cd ..
}

# Execute requested actions
if [ "$LOCAL" = true ]; then
  start_local
else
  if [ "$BUILD" = true ]; then
    build_image
  fi
  
  if [ "$DEPLOY" = true ]; then
    deploy_k8s
  fi
fi

echo ""
echo "===== Deployment Completed =====" 