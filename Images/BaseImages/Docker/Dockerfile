# Use Ubuntu 24.04 as the base image
FROM ubuntu:24.04

# Set non-interactive mode for apt-get
ENV DEBIAN_FRONTEND=noninteractive

# Create necessary directories
RUN mkdir -p /fs /gpfs /space /home/ufps

# Update and install system dependencies
RUN apt-get update && apt-get install -y \
    software-properties-common \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    git \
    curl \
    libpq-dev \
    vim \
    wget \
    libsqlite3-dev \
    lsb-release \
    ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Add the deadsnakes repository and install Python 3.12 with its dependencies
RUN add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y python3.12 python3.12-venv python3.12-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Update alternatives so that python3 points to python3.12
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1

# Create a virtual environment using Python 3.12
RUN python3.12 -m venv /home/venv

# Upgrade pip and install virtualenv in the virtual environment
RUN /home/venv/bin/python -m pip install --upgrade pip && \
    /home/venv/bin/pip install virtualenv

# Add the virtual environment's bin directory to the PATH
ENV PATH="/home/venv/bin:${PATH}"

# Copy the requirements file into the container (adjust the source path as needed)
COPY apptainer/requirements.txt /home/ufps/requirements.txt

# Install Python dependencies (ensure Django is included in your requirements.txt)
RUN pip install -r /home/ufps/requirements.txt

# Change working directory and create a new Django project named "ufps"
WORKDIR /home/ufps
# Use the full path to django-admin from the virtual environment
RUN /home/venv/bin/django-admin startproject ufps .

# Expose the port Gunicorn will run on (adjust if necessary)
EXPOSE 8000

# Set the default command to activate the virtual environment and start Gunicorn with 3 workers
CMD ["/bin/bash", "-c", "cd /home/ufps && gunicorn --workers 3 ufps.wsgi:application"]
