import numpy as np
import cv2
from django.shortcuts import render
from io import BytesIO
from datetime import datetime
from sklearn.decomposition import PCA
import tifffile
import tensorflow as tf

# Load the model with custom objects
model = tf.keras.models.load_model(
    "/gpfs/fs7/aafc/phenocart/PhenomicsProjects/DeploymentoverContainers/Assets/ufps/static/assets/models/maturity.h5",
    custom_objects={"mse": tf.keras.losses.MeanSquaredError()}
)

def get_julian_day(date_str):
    """
    Convert a date in YYYY-MM-DD format to Julian Day (1–365/366).
    E.g., "2025-02-27" -> 58 in a non-leap year.
    """
    if not date_str:
        return None
    date = datetime.strptime(date_str, "%Y-%m-%d")
    return date.timetuple().tm_yday

def projection3x(lidar_raw):
    # Verify sufficient data for PCA
    if lidar_raw.shape[0] < 2 or lidar_raw.shape[1] < 2:
        raise ValueError(
            f"Insufficient lidar data: {lidar_raw.shape[0]} samples and {lidar_raw.shape[1]} features. PCA cannot be applied.")

    x, y, z = lidar_raw[:, 0], lidar_raw[:, 1], lidar_raw[:, 2]
    x, y, z = x * 100, y * 100, z * 100
    x -= np.min(x)
    y -= np.min(y)
    z -= np.min(z)

    points = np.vstack((x, y)).T
    pca = PCA(n_components=2)
    pca.fit(points)
    angle = np.arctan2(pca.components_[0, 1], pca.components_[0, 0])
    rotation_matrix = np.array([
        [np.cos(-angle), -np.sin(-angle)],
        [np.sin(-angle),  np.cos(-angle)]
    ])
    rotated_points = points @ rotation_matrix.T
    rotated_x, rotated_y = rotated_points[:, 0], rotated_points[:, 1]

    # Flip x & y coords
    rotated_x = np.max(rotated_x) - rotated_x
    rotated_y = np.max(rotated_y) - rotated_y

    xy_resolution = 1
    xz_resolution = 1
    yz_resolution = 1

    x_min, x_max = np.min(rotated_x), np.max(rotated_x)
    y_min, y_max = np.min(rotated_y), np.max(rotated_y)
    z_min, z_max = np.min(z), np.max(z)

    grid_x_size_xy = int((x_max - x_min) / xy_resolution) + 1
    grid_y_size_xy = int((y_max - y_min) / xy_resolution) + 1
    grid_x_size_xz = int((x_max - x_min) / xz_resolution) + 1
    grid_z_size_xz = int((z_max - z_min) / xz_resolution) + 1
    grid_y_size_yz = int((y_max - y_min) / yz_resolution) + 1
    grid_z_size_yz = int((z_max - z_min) / yz_resolution) + 1

    grid_xy = np.full((grid_y_size_xy, grid_x_size_xy), np.nan, dtype=np.float32)
    grid_xz = np.full((grid_z_size_xz, grid_x_size_xz), np.nan, dtype=np.float32)
    grid_yz = np.full((grid_z_size_yz, grid_y_size_yz), np.nan, dtype=np.float32)

    # Project Z onto X-Y plane
    for i in range(len(rotated_x)):
        gx = int((rotated_x[i] - x_min) / xy_resolution)
        gy = int((rotated_y[i] - y_min) / xy_resolution)
        if np.isnan(grid_xy[gy, gx]):
            grid_xy[gy, gx] = z[i]
        else:
            grid_xy[gy, gx] = max(grid_xy[gy, gx], z[i])

    # X-Z plane
    for i in range(len(rotated_x)):
        gx = int((rotated_x[i] - x_min) / xz_resolution)
        gz = int((z[i] - z_min) / xz_resolution)
        if np.isnan(grid_xz[gz, gx]):
            grid_xz[gz, gx] = z[i]
        else:
            grid_xz[gz, gx] = max(grid_xz[gz, gx], z[i])

    # Y-Z plane
    for i in range(len(rotated_y)):
        gy = int((rotated_y[i] - y_min) / yz_resolution)
        gz = int((z[i] - z_min) / yz_resolution)
        if np.isnan(grid_yz[gz, gy]):
            grid_yz[gz, gy] = z[i]
        else:
            grid_yz[gz, gy] = max(grid_yz[gz, gy], z[i])

    grid_xy = np.nan_to_num(grid_xy, nan=0.0)
    grid_xz = np.nan_to_num(grid_xz, nan=0.0)
    grid_yz = np.nan_to_num(grid_yz, nan=0.0)

    # Resize to (width=300, height=100)
    resized_xy = cv2.resize(grid_xy, (300, 100), interpolation=cv2.INTER_NEAREST)
    resized_xz = cv2.resize(grid_xz, (300, 100), interpolation=cv2.INTER_NEAREST)
    resized_yz = cv2.resize(grid_yz, (300, 100), interpolation=cv2.INTER_NEAREST)

    # Final shape: (100, 300, 3)
    return np.dstack((resized_xy, resized_xz, resized_yz))

def image_processing(image_array, target_size=(512, 612), is_nir=False):
    """
    Resize TIF images to (512,612).
    """
    if len(image_array.shape) == 2 and not is_nir:
        image_array = cv2.cvtColor(image_array, cv2.COLOR_GRAY2BGR)
    resized = cv2.resize(image_array, (target_size[1], target_size[0]), interpolation=cv2.INTER_LINEAR)
    if is_nir:
        if resized.ndim == 3 and resized.shape[2] == 3:
            resized = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        if resized.ndim == 2:
            resized = np.expand_dims(resized, axis=-1)
    return resized

def index(request):
    context = {}
    if request.method == 'POST':
        # Retrieve date fields
        imaging_date_str = request.POST.get('imagingdate', '')  # "YYYY-MM-DD"
        seeding_date_str = request.POST.get('seedingdate', '')    # "YYYY-MM-DD"
        imaging_julian = get_julian_day(imaging_date_str)
        seeding_julian = get_julian_day(seeding_date_str)

        # Get file objects
        rgb_image_file = request.FILES.get('rgbimage', None)      # TIF
        nir_image_file = request.FILES.get('nirimage', None)        # TIF
        lidar_data_file = request.FILES.get('lidardata', None)      # NPY (raw point cloud)
        weather_data_file = request.FILES.get('weatherdata', None)  # NPY

        shapes_info = []

        # Process RGB TIF
        if rgb_image_file:
            rgb_bytes = rgb_image_file.read()
            rgb_array = tifffile.imread(BytesIO(rgb_bytes))
            #shapes_info.append(f"Original RGB shape: {rgb_array.shape}")
            rgb_processed = image_processing(rgb_array, target_size=(512, 612), is_nir=False)
            #shapes_info.append(f"Processed RGB shape: {rgb_processed.shape}")
            x_test_rgbimage = np.expand_dims(rgb_processed, axis=0)
        else:
            x_test_rgbimage = None

        # Process NIR TIF
        if nir_image_file:
            nir_bytes = nir_image_file.read()
            nir_array = tifffile.imread(BytesIO(nir_bytes))
            #shapes_info.append(f"Original NIR shape: {nir_array.shape}")
            nir_processed = image_processing(nir_array, target_size=(512, 612), is_nir=True)
            #shapes_info.append(f"Processed NIR shape: {nir_processed.shape}")
            x_test_nirimage = np.expand_dims(nir_processed, axis=0)
        else:
            x_test_nirimage = None

        # Process LiDAR (NPY)
        if lidar_data_file:
            lidar_array = np.load(BytesIO(np.load(lidar_data_file, allow_pickle=True)))
            #shapes_info.append(f"LiDAR raw array shape: {lidar_array.shape}")
            lidar_processed = projection3x(lidar_array)
            #shapes_info.append(f"Processed LiDAR shape: {lidar_processed.shape}")
            x_test_lidar = np.expand_dims(lidar_processed, axis=0)
        else:
            x_test_lidar = None

        # Process Weather (NPY)
        if weather_data_file:
            weather_array = np.load(BytesIO(np.load(weather_data_file, allow_pickle=True)))
            #shapes_info.append(f"Weather array shape: {weather_array.shape}")
            # If needed, transpose weather data to match expected shape
            x_test_weather = np.expand_dims(weather_array, axis=0)
        else:
            x_test_weather = None

        # Prepare additional inputs from date information.
        x_test_imagedate = np.array([imaging_julian]) if imaging_julian is not None else None
        x_test_seedingdate = np.array([seeding_julian]) if seeding_julian is not None else None

        # Construct the input dictionary for prediction.
        inputs = {}
        if x_test_rgbimage is not None:
            inputs["rgb_image"] = x_test_rgbimage
        if x_test_nirimage is not None:
            inputs["nir_image"] = x_test_nirimage
        if x_test_lidar is not None:
            inputs["lidar_data"] = x_test_lidar
        if x_test_seedingdate is not None:
            inputs["seeding_date"] = x_test_seedingdate
        if x_test_imagedate is not None:
            inputs["image_date"] = x_test_imagedate
        if x_test_weather is not None:
            inputs["weather_data"] = np.transpose(x_test_weather, (0, 2, 3, 1))

        # Log input shapes for debugging
        for key, value in inputs.items():
            shapes_info.append(f"Input '{key}' shape: {value.shape}")

        # Make prediction
        y_pred = model.predict(inputs)

        # Extract prediction values:
        # y_pred[0] -> days to flowering, y_pred[1] -> days to maturity.
        # Multiply by 100 if needed (adjust as per your scaling)
        days_to_flowering = y_pred[0][0, 0] * 100
        days_to_maturity = y_pred[1][0, 0] * 100

        # Pass predictions and other context data to the template
        context['days_to_flowering'] = days_to_flowering
        context['days_to_maturity'] = days_to_maturity
        context['shapes_info'] = shapes_info

    return render(request, 'index.html', context)
