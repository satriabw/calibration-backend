import numpy as np
from PIL import Image
import cv2
import io
import scipy.optimize as opt
import math
import base64
import os

from .camera_model import CameraModel
from pyproj import Transformer
from pyproj.aoi import AreaOfInterest
from pyproj.database import query_utm_crs_info

LOCATION_SCALING_FACTOR = 111318.84502145034
LOCATION_SCALING_FACTOR_INV = 0.000008983204953368922

# ----- Callibration Functions -----
#  Inspired from https://github.com/AubreyC/trajectory-extractor/blob/master/traj_ext/
def get_scale_longitude_factor(lat):
    scale = math.cos(math.radians(lat))
    return scale

def latlon_to_NED(latlon_origin, latlon_point):
    origin = latlon_origin[0]
    lat_diff = latlon_point[:, 0] - origin[0]
    lon_diff = latlon_point[:, 1] - origin[1]

    north = lat_diff * LOCATION_SCALING_FACTOR
    east = lon_diff * LOCATION_SCALING_FACTOR * get_scale_longitude_factor(origin[0])

    return np.column_stack((north, east))

def convert_latlon_F(latlon_origin, latlon_points):
    # Convert lat/lon points to NED coordinates
    ned_2d = latlon_to_NED(latlon_origin, latlon_points)
    # Add a zero column for the vertical component
    ned_3d = np.column_stack([ned_2d, np.zeros((ned_2d.shape[0], 1))])
    return ned_3d

def xyz_to_NED(origin_xyz, points_xyz):
    """
    Convert 3D points (x, y, z) in meters to NED coordinates relative to origin.
    """
    # Calculate differences from origin
    diff = points_xyz - origin_xyz
    
    # Convert to NED coordinates:
    # North = difference in Y direction (positive Y is North)
    # East = difference in X direction (positive X is East)  
    # Down = negative difference in Z direction (positive Z is Up, but NED uses Down)
    ned_coordinates = np.column_stack([
        diff[:, 1],   # North (Y difference)
        diff[:, 0],   # East (X difference)
        np.zeros(diff.shape[0])  # Down (negative Z difference)
    ])
    
    return ned_coordinates

def convert_xyz_to_NED(origin_xyz, points_xyz):
    """
    Convert 3D points (x, y, z) in meters to NED coordinates.
    This is a wrapper function that matches the naming convention of convert_latlon_F.
    """
    return xyz_to_NED(origin_xyz, points_xyz)

# Source: https://github.com/SoccerNet/sn-calibration/blob/main/src/camera.py
# Algorithm 8.2 of Multiple View Geometry in computer vision, p225
def get_K_from_homography(H, image_size):
        H = np.reshape(H, (9,))
        A = np.zeros((5, 6))
        A[0, 1] = 1.
        A[1, 0] = 1.
        A[1, 2] = -1.
        A[2, 3] = image_size[0] / image_size[1] # Principal point set to image center
        A[2, 4] = -1.0
        A[3, 0] = H[0] * H[1]
        A[3, 1] = H[0] * H[4] + H[1] * H[3]
        A[3, 2] = H[3] * H[4]
        A[3, 3] = H[0] * H[7] + H[1] * H[6]
        A[3, 4] = H[3] * H[7] + H[4] * H[6]
        A[3, 5] = H[6] * H[7]
        A[4, 0] = H[0] * H[0] - H[1] * H[1]
        A[4, 1] = 2 * H[0] * H[3] - 2 * H[1] * H[4]
        A[4, 2] = H[3] * H[3] - H[4] * H[4]
        A[4, 3] = 2 * H[0] * H[6] - 2 * H[1] * H[7]
        A[4, 4] = 2 * H[3] * H[6] - 2 * H[4] * H[7]
        A[4, 5] = H[6] * H[6] - H[7] * H[7]

        # May not converge
        u, s, vh = np.linalg.svd(A)
        w = vh[-1]
        W = np.zeros((3, 3))
        W[0, 0] = w[0] / w[5]
        W[0, 1] = w[1] / w[5]
        W[0, 2] = w[3] / w[5]
        W[1, 0] = w[1] / w[5]
        W[1, 1] = w[2] / w[5]
        W[1, 2] = w[4] / w[5]
        W[2, 0] = w[3] / w[5]
        W[2, 1] = w[4] / w[5]
        W[2, 2] = w[5] / w[5]

        try:
            Ktinv = np.linalg.cholesky(W)
            K = np.linalg.pinv(Ktinv.T)
            K /= K[2, 2]


            fx = K[0, 0]
            fy = K[1, 1]
        except np.linalg.LinAlgError:
            # Fallback values in case of failure
            fx = image_size[1]
            fy = image_size[1]
            
        cx = image_size[1] / 2.0
        cy = image_size[0] / 2.0
        return fx, fy, cx, cy

def estimate_camera_intrinsics(image_size, image_points, model_points_3d, bev_mode=False, objective_func=None, guess_focal=False):
    if bev_mode:
        # Set focal length to image height for bev mode
        return image_size[0], (image_size[1] / 2, image_size[0] / 2)
    
    # Initial guess
    if guess_focal:
        initial_focal = [image_size[1]]
        cx, cy = image_size[1] / 2, image_size[0] / 2
    else:
        H, _ = cv2.findHomography(model_points_3d[:, :2], image_points, method=cv2.RANSAC)
        fx, fy, cx, cy = get_K_from_homography(H, image_size)
        initial_focal = [(fx + fy) / 2.0]

    # Constraint: focal length must be positive
    constraints = {'type': 'ineq', 'fun': (lambda x: x[0])}
    
    # Run optimization
    result = opt.minimize(
        objective_func,
        initial_focal,
        constraints=constraints,
        args=((cx, cy), image_points, model_points_3d)
    )
    focal_length = result.x[0]
    
    return focal_length, (cx, cy)

def calculate_reprojection_rms(predicted_points, actual_points):
    squared_diffs = np.sum((predicted_points - actual_points)**2, axis=1)
    mean_squared_error = np.mean(squared_diffs)
    rms_error = np.sqrt(mean_squared_error)
    
    return rms_error

def get_reprojection_error(opti_params, center, image_points, model_points_F):
    # Camera internals
    focal_length = opti_params[0]

    # Find camera parms
    _, _, _, _, _, image_points_reproj = find_camera_params(focal_length, center, image_points, model_points_F)

    # Compute error
    error_reproj = calculate_reprojection_rms(image_points_reproj, image_points)

    return error_reproj

def find_camera_params(focal_length, center, image_points, model_points_F):
    camera_matrix = build_camera_matrix(focal_length, center)

    _, rot, trans = cv2.solvePnP(model_points_F, image_points, camera_matrix, None, flags=cv2.SOLVEPNP_ITERATIVE)

    imagePoints, _ = cv2.projectPoints(model_points_F, rot, trans, camera_matrix, None)
    image_points_reproj = imagePoints[:,0]

    return None, camera_matrix, np.zeros((4, 1), dtype=np.float32), np.array([rot], dtype=np.float32), np.array([trans], dtype=np.float32), image_points_reproj

def build_camera_matrix(focal_length, center):
    cx, cy = center
    
    # Build intrinsic matrix
    camera_matrix = np.array([
        [focal_length, 0.0, cx],
        [0.0, focal_length, cy],
        [0.0, 0.0, 1.0]
    ], dtype=np.float64)
    
    return camera_matrix

def find_camera_params_cv2(image_points, model_points_F, image_size):
    # Convert inputs to appropriate types
    image_points = np.array([image_points], dtype=np.float32)
    model_points_F = np.array([model_points_F], dtype=np.float32)

    # Calibrate camera
    ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
        model_points_F, image_points, image_size, None, None
    )

    # Project points to get reprojection
    image_points_reproj, _ = cv2.projectPoints(
        model_points_F[0], rvecs[0], tvecs[0], mtx, dist
    )
    image_points_reproj = image_points_reproj[:, 0]

    return ret, mtx, dist, rvecs, tvecs, image_points_reproj


def visualize_calibration(image, image_points, image_points_reproj):
    image_viz = cv2.cvtColor(image, cv2.COLOR_BGR2RGB).copy()
    for pt in image_points:
        cv2.circle(image_viz, (int(pt[0]), int(pt[1])), 5, (0, 255, 0), -1)  # Green for actual points
    for pt in image_points_reproj:
        cv2.circle(image_viz, (int(pt[0]), int(pt[1])), 3, (0, 0, 255), -1)  # Red for reprojected points
    return image_viz

def get_epsg_from_latlon(lat, lon):
    crs_list = query_utm_crs_info(datum_name="WGS 84", 
                                  area_of_interest=AreaOfInterest(
                                        west_lon_degree=lon,
                                        south_lat_degree=lat,
                                        east_lon_degree=lon,
                                        north_lat_degree=lat),
                                )
    return crs_list[0].code if crs_list else None

def calibrate(image, pixels, world_coordinates, origin, version):
    image = base64.b64decode(image.split(',')[1])
    image_np = np.array(Image.open(io.BytesIO(image)).convert("RGB"))
    epsg = get_epsg_from_latlon(origin[0], origin[1])

    # Transform to local EPSG
    if epsg:
        transformer = Transformer.from_crs("epsg:4326", epsg, always_xy=True)
        world_points = [transformer.transform(lon, lat) for lat, lon in world_coordinates]
        origin_points = [transformer.transform(origin[1], origin[0])] * len(world_points)

    pixel_points = np.array(pixels, dtype=np.float32)
    world_points = np.array(world_points, dtype=np.float32)
    origin_points = np.array(origin_points, dtype=np.float32)

    # Estimate camera intrinsics
    latlon_NED = convert_xyz_to_NED(origin_points, world_points) if epsg else convert_latlon_F([origin], np.array(world_coordinates))
    focal_length, center = estimate_camera_intrinsics(
        image_size=image_np.shape[:2],
        image_points=pixel_points,
        model_points_3d=latlon_NED,
        bev_mode=False,
        objective_func=get_reprojection_error
    )
    camera_matrix = build_camera_matrix(focal_length, center)
    dist = np.zeros((4, 1), dtype=np.float32)

    _, _, _, rvecs, tvecs, image_points_reproj = find_camera_params(
        focal_length=focal_length,
        center=(camera_matrix[0, 2], camera_matrix[1, 2]),
        image_points=pixel_points,
        model_points_F=latlon_NED
    )
    rot_CF_F = cv2.Rodrigues(rvecs[0])[0]
    trans_CF_F = tvecs[0]

    camera_model = CameraModel(
        camera_matrix=camera_matrix,
        dist_coeffs=dist,
        rot_matrix=rot_CF_F,
        tvec=trans_CF_F,
        homography=None
    )
    
    camera_model_path = './artifacts/camera_model_{version}.yml'.format(version=version)
    camera_model.save_to_yml(camera_model_path)

    image_viz = visualize_calibration(image_np, pixel_points, image_points_reproj)
    rms = calculate_reprojection_rms(image_points_reproj, pixel_points)
    return camera_model_path, rms, image_viz
