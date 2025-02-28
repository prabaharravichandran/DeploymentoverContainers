# Building Containers for the Deployment of Django Applications in AWS

<figure style="text-align: center;">
  <img src="https://prabahar.s3.ca-central-1.amazonaws.com/static/articles/ApplicationUI.png" alt="Alt Text" style="max-width:100%;">
    <div style="text-align: center;">Django application user interface.</div>
</figure>

## Recipes for base images are located @ Images/Base Images

### Apptainer

makefile and make.sbatch files to build sandbox @ HPC / GPSC (General Purpose Science Cluster),

```bash
sbatch make.sbatch
```

To build .sif from sandbox,

```bash
singularity build apptainer.sif apptainer_sandbox/
```

To make changes to sandbox (i.e. writable), use --writable, better to contain and avoid binding as well,

```bash
export SINGULARITY_BINDPATH=""
export APPTAINER_BINDPATH=""
singularity shell --writable --contain --no-home apptainer_sandbox
```

If you have to move sandbox to remotes, please archive,


```bash
tar -czvf apptainer_blankDjango+Gunicorn.tar.gz apptainer_sandbox
```

```bash
tar -xzvf apptainer_blankDjango+Gunicorn.tar.gz
```


### Docker

Create Dockerfile (i.e. recipe), build and run,

```bash
docker build -t ufps-apptainer .
docker run -p 8000:8000 ufps-apptainer
```

to archive/save the image,

```bash
docker save -o ufps-apptainer.tar ufps-apptainer:latest
```

to push them to ecr, (may have to install aws cli and configure on host)

```bash
docker tag ufps/apptainer:latest 637423168372.dkr.ecr.ca-central-1.amazonaws.com/ufps/apptainer:latest
aws ecr get-login-password --region ca-central-1 | docker login --username AWS --password-stdin 637423168372.dkr.ecr.ca-central-1.amazonaws.com
docker push 637423168372.dkr.ecr.ca-central-1.amazonaws.com/ufps/apptainer:latest
```
## Preparing AWS

We have AWS image for web development, we can use that to launch an instance.

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential libseccomp-dev pkg-config squashfs-tools cryptsetup curl git
```

Install Go,

```bash
sudo apt install golang-go
go version
```

Install Apptainer,

```bash
sudo git clone https://github.com/apptainer/apptainer.git
cd apptainer
git checkout v1.4.0  # Replace with the latest stable version
```

Build and install,

```bash
 sudo sh -c 'echo "1.0.0" > VERSION'
sudo ./mconfig && make -C builddir && sudo make -C builddir install
```

## Building Containers

Building a sandbox container,

```bash
sudo apptainer build --sandbox AWS_apptainer singularity.def
```

If single-file image (SIF),

```bash
sudo apptainer build AWS_apptainer.sif AWS_apptainer/
```

If Nginx is required, lets keep it away from containers. Container just holds Django and Gunicorn.


## Setup NGINX

Install nginx,

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install nginx -y
```

Prepare config for application (ufps),

```bash
sudo nano /etc/nginx/sites-available/ufps
```

add,

```text
server {
    listen 80;
    server_name localhost;  # Important replace with Elastic IP

    location / {
        proxy_pass http://127.0.0.1:8000;  # Gunicorn will be listening here
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    }
```

create a symbolic link,

```bash
sudo ln -s /etc/nginx/sites-available/ufps /etc/nginx/sites-enabled/
```

Reload systemd (service files), enable them (to start automatically on boot), and start service.

```bash
sudo systemctl daemon-reload
sudo systemctl enable nginx
sudo systemctl restart nginx
```
### Create an apptainer service

```bash
sudo nano /etc/systemd/system/apptainer.service
```
add

```text
[Unit]
Description=One-shot Apptainer Job
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/apptainer run /home/ubuntu/AWS/AWS_apptainer
RemainAfterExit=no

[Install]
WantedBy=multi-user.target
```
reload, enable, and start.

```bash
sudo systemctl daemon-reload
sudo systemctl enable apptainer.service
sudo systemctl start apptainer.service
```

## Local development of web application in Django

Just to start Gunicorn for dev; Make sure the venv is active and one the ufps django project.

```bash
# Start Gunicorn in the background with 3 workers
gunicorn --workers 3 ufps.wsgi:application
```

To run Gunicorn as a daemon,

```bash
# Start Gunicorn in the background with 3 workers
gunicorn --workers 3 --daemon ufps.wsgi:application
```

To kill it,

```bash
kill $(pgrep gunicorn)
```

let us create a home app...

```bash
python manage.py startapp home
```

```bash
INSTALLED_APPS = [
    # ... other installed apps
    'home',
]
```
add this to home's views.py

```python
from django.shortcuts import render

def index(request):
    return render(request, 'index.html')
```

add urls,
```python
# home/urls.py
from django.urls import path
from .views import index

urlpatterns = [
    path('', index, name='index'),
]
```

make changes to project/urls,

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('home.urls')),
]
```

add templates and index.html in it. make changes to settings.py
```python
import os
from pathlib import Path

# Assuming BASE_DIR is already defined as the project root
BASE_DIR = Path(__file__).resolve().parent.parent

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # Add your global templates directory here
        'DIRS': [],
        'APP_DIRS': True,  # This will look for templates in each app's templates folder
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]
```

make and apply migration,

```bash
python manage.py makemigrations
python manage.py migrate
```

```bash
STATIC_URL = '/static/'
# Optionally define STATICFILES_DIRS if you have a custom directory:
STATICFILES_DIRS = [
    BASE_DIR / "static",
]
```

in production, run

```bash
python manage.py collectstatic
```

```text
(venv) prr000@vis-07:/gpfs/fs7/aafc/phenocart/PhenomicsProjects/DeploymentoverContainers/Assets/ufps$ python manage.py collectstatic

127 static files copied to '/gpfs/fs7/aafc/phenocart/PhenomicsProjects/DeploymentoverContainers/Assets/ufps/staticfiles'.
```

Install WhiteNoise,
WhiteNoise allows your web app to serve its own static files, making it a self-contained unit that can be deployed anywhere without relying on nginx, Amazon S3 or any other external service

```python
MIDDLEWARE = [
    # ...
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    # ...
]
```
```python
STORAGES = {
    # ...
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
```

add this to wsgi.py

```python

import os
from whitenoise import WhiteNoise
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ufps.settings')

application = get_wsgi_application()
application = WhiteNoise(application, root="/gpfs/fs7/aafc/phenocart/PhenomicsProjects/DeploymentoverContainers/Assets/ufps/static")
application.add_files("/gpfs/fs7/aafc/phenocart/PhenomicsProjects/DeploymentoverContainers/Assets/ufps/static", prefix="more-files/")
```
