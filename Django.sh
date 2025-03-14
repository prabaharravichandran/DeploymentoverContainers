#!/bin/bash
# Activate the virtual environment
. /gpfs/fs7/aafc/phenocart/PhenomicsProjects/DeploymentoverContainers/venv/bin/activate

# Move to Django project
cd /gpfs/fs7/aafc/phenocart/PhenomicsProjects/DeploymentoverContainers/Assets/ufps

# Kill existing gunicorn process
kill $(pgrep gunicorn)

# Launch gunicorn workers
gunicorn --workers 3 --daemon ufps.wsgi:application
