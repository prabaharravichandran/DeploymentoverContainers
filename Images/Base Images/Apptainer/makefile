# Makefile for managing a Singularity container for a TensorFlow project with CUDA

# Configuration
IMAGE_NAME = apptainer.sif
SANDBOX_NAME = apptainer_sandbox
DEF_FILE = Singularity.def
BUILD_DIR = /gpfs/fs7/aafc/phenocart/PhenomicsProjects/DeploymentoverContainers/Images/Base Images/Apptainer
TMP_DIR = /tmp/$(SANDBOX_NAME)

.PHONY: all build sandbox clean

all: build

# Build a Singularity .sif image (Recommended)
build: $(DEF_FILE)
	# Build in a writable sandbox first
	unset LD_PRELOAD && singularity build --fakeroot --sandbox $(TMP_DIR) $(DEF_FILE)

	# Ensure TMP_DIR exists before syncing
	if [ -d "$(TMP_DIR)" ]; then \
	    rsync -av --ignore-errors -vv $(TMP_DIR)/ $(BUILD_DIR)/$(SANDBOX_NAME)/; \
	else \
	    echo "Error: Temporary sandbox directory $(TMP_DIR) not found!"; \
	    exit 1; \
	fi

	# Clean up temporary sandbox to save space
	rm -rf $(TMP_DIR)

# Clean up the Singularity images
clean:
	rm -f $(BUILD_DIR)/$(IMAGE_NAME)
	rm -rf $(BUILD_DIR)/$(SANDBOX_NAME)
	rm -f $(BUILD_DIR)/$(OVERLAY_NAME)  # Remove overlay file
