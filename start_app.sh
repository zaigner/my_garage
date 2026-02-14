#!/bin/bash

# Start MongoDB
echo "Starting MongoDB..."
pixi run mongo

# Trap SIGINT (Ctrl+C) to stop all background processes
trap 'echo "Stopping services..."; kill $(jobs -p); pixi run mongo-stop; exit' SIGINT SIGTERM

# Run Migrations
echo "Running Database Migrations..."
pixi run migrate

echo "Starting Django Server..."
pixi run server &

echo "Starting Celery Worker..."
pixi run worker &

echo "Starting Celery Beat..."
pixi run beat &

echo "Starting FastAPI..."
pixi run fastapi &

echo "All services started. Press Ctrl+C to stop."
wait