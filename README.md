# Aetherion AR Platform

Aetherion AR is an advanced augmented reality platform leveraging cutting-edge AI technologies including LangGraph, vector databases, and multi-agent systems to provide a seamless integration of digital information into the physical world.

## Project Structure

```
aetherion/
├── backend/          # Python backend with FastAPI, MongoDB, Redis, and Kafka
├── k8s/              # Kubernetes manifests for deployment
├── deploy.sh         # Bash deployment script
├── deploy.ps1        # PowerShell deployment script
└── skaffold.yaml     # Skaffold configuration for continuous development
```

## Features

- **Agent-based Architecture**: Multi-agent system for distributed processing
- **MCP Server**: Master Control Program for orchestrating AR experiences
- **Speech Integration**: Real-time speech-to-text and text-to-speech capabilities
- **Document Processing**: Advanced document analysis and extraction
- **LangGraph Integration**: Complex workflow orchestration for AI agents
- **JWT Authentication**: Secure authentication system

## Deployment Options

### Local Development with Docker Compose

For local development and testing, use Docker Compose:

```bash
# Using the deployment script (Bash)
./deploy.sh --local

# Using the deployment script (PowerShell)
# For Windows users, you may need to bypass execution policy:
powershell -ExecutionPolicy Bypass -File .\deploy.ps1 -Local

# Or manually:
cd backend
docker-compose up -d
```

### Kubernetes Deployment

For production deployment using Kubernetes:

```bash
# Using the deployment script (Bash)
./deploy.sh

# Using the deployment script (PowerShell)
# For Windows users, you may need to bypass execution policy:
powershell -ExecutionPolicy Bypass -File .\deploy.ps1

# With custom options:
./deploy.sh --registry your-registry.io --tag v1.0.0

# Manual deployment:
# 1. Build Docker image
cd backend
docker build -t aetherion-backend:latest .

# 2. Apply Kubernetes manifests
kubectl apply -f k8s/
```

### Continuous Development with Skaffold

For continuous development with Kubernetes:

```bash
# Start development with Skaffold
skaffold dev
```

## Deployment Scripts

Two deployment scripts are provided for flexibility:

### Bash Script (deploy.sh)

For Linux/macOS/Git Bash users:

```bash
# Show help
./deploy.sh --help

# Common options:
# --build-only     Only build the Docker image
# --deploy-only    Only deploy Kubernetes manifests
# --local          Use Docker Compose for local development
# --minikube       Deploy to Minikube
# --registry       Specify Docker registry (default: none)
# --tag            Specify image tag (default: latest)
```

### PowerShell Script (deploy.ps1)

For Windows users:

```powershell
# Show help (may need to bypass execution policy)
powershell -ExecutionPolicy Bypass -File .\deploy.ps1 -Help

# Common options:
# -BuildOnly       Only build the Docker image
# -DeployOnly      Only deploy Kubernetes manifests
# -Local           Use Docker Compose for local development
# -Minikube        Deploy to Minikube
# -Registry        Specify Docker registry (default: none)
# -Tag             Specify image tag (default: latest)
```

## API Documentation

When the application is running:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Environment Variables

See `.env.example` in the backend directory for required environment variables.

---

© 2023 Aetherion AR Project 