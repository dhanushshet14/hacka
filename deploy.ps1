# Aetherion AR Deployment Script (PowerShell Version)

param(
    [switch]$Help,
    [switch]$BuildOnly,
    [switch]$DeployOnly,
    [switch]$Local,
    [switch]$Minikube,
    [string]$Registry = "",
    [string]$Tag = "latest"
)

# Default values
$buildImage = -not $DeployOnly
$deployK8s = -not $BuildOnly
$useLocal = $Local
$useMiniKube = $Minikube
$registry = $Registry
$tag = $Tag

# Override if both BuildOnly and DeployOnly are specified
if ($BuildOnly -and $DeployOnly) {
    $buildImage = $true
    $deployK8s = $true
}

function Show-Help {
    Write-Host "===== Aetherion AR Deployment Script ====="
    Write-Host ""
    Write-Host "Usage: ./deploy.ps1 [options]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Help                 Display this help message"
    Write-Host "  -BuildOnly            Only build the Docker image"
    Write-Host "  -DeployOnly           Only deploy Kubernetes manifests"
    Write-Host "  -Local                Use Docker Compose for local development"
    Write-Host "  -Minikube             Deploy to Minikube"
    Write-Host "  -Registry REGISTRY    Specify Docker registry (default: none)"
    Write-Host "  -Tag TAG              Specify image tag (default: latest)"
    Write-Host ""
    exit 0
}

if ($Help) {
    Show-Help
}

# Function to build Docker image
function Build-Image {
    Write-Host "🔨 Building Docker image..."
    
    # Determine image name based on registry
    $imageName = "aetherion-backend:$tag"
    if ($registry -ne "") {
        $imageName = "$registry/aetherion-backend:$tag"
    }
    
    # Navigate to backend directory and build image
    Push-Location backend
    try {
        docker build -t $imageName .
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ Docker build failed"
            exit 1
        }
        
        # Push to registry if specified
        if ($registry -ne "") {
            Write-Host "📤 Pushing image to registry: $registry"
            docker push $imageName
            if ($LASTEXITCODE -ne 0) {
                Write-Host "❌ Failed to push image to registry"
                exit 1
            }
        }
        
        Write-Host "✅ Image built successfully: $imageName"
    } finally {
        Pop-Location
    }
}

# Function to deploy to Kubernetes
function Deploy-K8s {
    Write-Host "🚀 Deploying to Kubernetes..."
    
    # Determine image name based on registry
    $imageName = "aetherion-backend:$tag"
    if ($registry -ne "") {
        $imageName = "$registry/aetherion-backend:$tag"
    }
    
    # Update the backend deployment YAML with the current image
    Write-Host "📝 Updating deployment manifest with image: $imageName"
    $backendFile = "k8s/06-backend.yaml"
    $content = Get-Content $backendFile -Raw
    
    # Use regex to replace the image in the backend deployment
    $content = $content -replace "image: .*aetherion-backend:.*", "image: $imageName"
    Set-Content -Path $backendFile -Value $content
    
    # Apply Kubernetes manifests
    Write-Host "📦 Applying Kubernetes manifests..."
    kubectl apply -f k8s/00-namespace.yaml
    kubectl apply -f k8s/01-configmap.yaml
    kubectl apply -f k8s/02-secrets.yaml
    kubectl apply -f k8s/03-mongodb.yaml
    kubectl apply -f k8s/04-redis.yaml
    kubectl apply -f k8s/05-kafka.yaml
    kubectl apply -f k8s/06-backend.yaml
    
    # Wait for deployments to be ready
    Write-Host "⏳ Waiting for deployments to be ready..."
    kubectl wait --namespace aetherion --for=condition=available deployment --all --timeout=300s
    
    # If using Minikube, show service URL
    if ($useMiniKube) {
        Write-Host "🔍 Getting service URL from Minikube..."
        minikube service aetherion-backend-service -n aetherion --url
    }
    
    Write-Host "✅ Deployment complete!"
}

# Function to start local development environment with Docker Compose
function Start-Local {
    Write-Host "🐳 Starting local development environment with Docker Compose..."
    
    Push-Location backend
    try {
        docker-compose up -d
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ Failed to start Docker Compose services"
            exit 1
        }
        
        Write-Host "✅ Local environment started successfully!"
        Write-Host "📊 Backend API available at: http://localhost:8000"
        Write-Host "📚 API Documentation (Swagger UI): http://localhost:8000/docs"
        Write-Host "📘 API Documentation (ReDoc): http://localhost:8000/redoc"
    } finally {
        Pop-Location
    }
}

# Execute requested actions
if ($useLocal) {
    Start-Local
} else {
    if ($buildImage) {
        Build-Image
    }
    
    if ($deployK8s) {
        Deploy-K8s
    }
}

Write-Host "✨ Done!" 