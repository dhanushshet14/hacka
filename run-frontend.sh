#!/bin/bash

# Default values
MODE="dev"

# Help function
function show_help {
    echo "Usage: ./run-frontend.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -m, --mode     Mode to run the frontend (dev, build, start) - default: dev"
    echo "  -h, --help     Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./run-frontend.sh                   # Run in development mode"
    echo "  ./run-frontend.sh -m build          # Build for production"
    echo "  ./run-frontend.sh -m start          # Start production server"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -m|--mode)
            MODE="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Validate mode
if [[ "$MODE" != "dev" && "$MODE" != "build" && "$MODE" != "start" ]]; then
    echo "Error: Mode must be one of: dev, build, start"
    exit 1
fi

# Run the appropriate command based on mode
case $MODE in
    dev)
        echo "Starting development server..."
        npm run dev
        ;;
    build)
        echo "Building for production..."
        npm run build
        ;;
    start)
        echo "Starting production server..."
        npm run start
        ;;
esac 