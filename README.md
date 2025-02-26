# Building Containers for the Deployment of Django Applications in AWS

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
