import cv2, torch
import os
import json
from pathlib import Path
from sklearn.preprocessing import MinMaxScaler
from scipy.signal import medfilt
from scipy.ndimage import gaussian_filter1d
import numpy as np
from PIL import Image, ImageEnhance
from statistics import quantiles
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from collections import Counter
from natsort import natsorted
import torch.nn as nn
import torch.nn.functional as F
from transformers import AutoImageProcessor, AutoModelForImageClassification
from joblib import load as joblib_load
from pprint import pprint
import torch, gc
from utils import config

def vid_to_frames_save(video_path, vid_to_frames_save_path, flip_frame = False):
    video = cv2.VideoCapture(video_path)
    frame_count = 0
    
    while True:
        ret, frame = video.read()
        if not ret:
            break    
                 
        resized_frame = cv2.resize(frame, (320,240)) 
        gray = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2GRAY)
        
        if np.average(gray) < 45:
            continue
        else:
            if frame_count % 1 == 0:
                save_path = os.path.join(vid_to_frames_save_path, f"frames_{frame_count}.jpg")
                if flip_frame== True:
                    cv2.imwrite(save_path, cv2.rotate(frame, cv2.ROTATE_180))
                else:
                    cv2.imwrite(save_path, frame)
            
        frame_count+=1

    video.release()
    return vid_to_frames_save_path, frame_count

def load_files(frames_path, idx):
    
    _,_,files = next(os.walk(frames_path))
    files_sorted = natsorted(files)
    file_count = len(files_sorted)
    start_idx = idx
    end_idx = file_count-idx
    clipped_files = files_sorted.copy()
    clipped_files = clipped_files[start_idx:end_idx]
    file_count_updated = len(clipped_files)
    return clipped_files, file_count_updated

def load_frames(files, file_count, frames_path):

    empty_arr = np.empty([file_count, 480, 640, 3], dtype=np.uint8)
    for idx, file in enumerate(files):
        image = cv2.imread(os.path.join(frames_path, file))
        image = cv2.resize(image, (640,480))
        empty_arr[idx] = image
    return empty_arr

def crop_affine_roi(img, bbox_pts):

    top_left, top_right, bottom_right, bottom_left = bbox_pts

    src_pts = np.float32([top_left, top_right, bottom_left])
    width  = int(np.linalg.norm(np.array(top_right) - np.array(top_left)))
    height = int(np.linalg.norm(np.array(bottom_left) - np.array(top_left)))

    dst_pts = np.float32([[0, 0], [width, 0], [0, height]])

    M = cv2.getAffineTransform(src_pts, dst_pts)
    cropped = cv2.warpAffine(img, M, (width, height))

    return cropped, M

def iterate_over_images(images_dir, clipped_files):
    for idx, file in enumerate(clipped_files):
        img_path = os.path.join(images_dir, file)
        img = cv2.imread(img_path)
        yield idx, img

def resize_and_crop_frames(images_dir, clipped_files ,bbox_pts, cropped_frames):
    for idx, img in iterate_over_images(images_dir, clipped_files):
        if idx <=2:
            _, affine_matrix = crop_affine_roi(img, bbox_pts )
        resized_img = cv2.resize(img, (320,240))
        cropped_frame, _ = crop_affine_roi(resized_img, bbox_pts)
        cropped_frames.append(cropped_frame)
        
    return cropped_frames, affine_matrix

def get_diff_and_canny_images(cropped_frames):
    cropped_frames = np.array(cropped_frames)
    N = cropped_frames.shape[0] - 1 
    W, H = cropped_frames.shape[1], cropped_frames.shape[2]
    subtracted_images = np.empty((N,W,H), dtype = np.float32)
    sub_canny_images = np.empty((N,W,H), dtype = np.float32)
    images_for_centroids = np.empty((N,W,H), dtype=np.uint8)
    
    for i in range(N):
        
        current_frame = cropped_frames[i]
        next_frame = cropped_frames[i+1]
        gs_current_frame = (cv2.cvtColor(current_frame,cv2.COLOR_BGR2GRAY))
        gs_current_frame_normalized = gs_current_frame/255.0

        gs_next_frame = (cv2.cvtColor(next_frame,cv2.COLOR_BGR2GRAY))
        gs_next_frame_normalized = gs_next_frame/255.0

        kernel = np.ones((5,5),np.float32)/25
        gaussian_blur_curr = cv2.filter2D(gs_current_frame_normalized,-1,kernel)
        gaussian_blur_next = cv2.filter2D(gs_next_frame_normalized, -1, kernel)
        
        sub_img_non_Norm = cv2.absdiff(cv2.filter2D(gs_current_frame,-1,kernel), cv2.filter2D(gs_next_frame, -1, kernel))

        # canny_on_sub_img = cv2.Canny(canny_subtracted_image, 10, 200)
        _, thres_on_sub_img = cv2.threshold(sub_img_non_Norm,10,200,cv2.THRESH_BINARY)
        
        subtracted_images[i] = cv2.absdiff(gaussian_blur_curr, gaussian_blur_next)
        images_for_centroids[i] = thres_on_sub_img
        
        # Canny Edge applied here and then taking the difference of the Canny frames to get a estimate of the object.
        edges_current_frame = cv2.Canny(gs_current_frame, 100, 200)
        edges_next_frame = cv2.Canny(gs_next_frame, 100, 200)
        filtered_image = cv2.absdiff(edges_current_frame, edges_next_frame)        
        sub_canny_images[i] = cv2.medianBlur(filtered_image, 3)
    
    return subtracted_images, sub_canny_images, images_for_centroids    

def map_point_to_original(pt_cropped, M_affine):
    M_inv = cv2.invertAffineTransform(M_affine)
    pt = np.array([pt_cropped], dtype=np.float32).reshape(-1, 1, 2)
    pt_original = cv2.transform(pt, M_inv)
    return tuple(map(int, pt_original[0][0]))

def find_centroid_and_area(frames, affine_matrix):
    
    min_area = 800.0
    N = frames.shape[0] - 1     
    centroids = np.zeros((N,2), dtype=np.int32)
    areas = np.full((N,), min_area, dtype=np.float32)    
    morph_kernel = cv2.getStructuringElement(cv2.MORPH_CROSS, (5,5))
    
    for i in range(N):
        area = []
        centroid = []
        filtered_contours = []
        good_contours = []
        morphed = cv2.morphologyEx(frames[i],cv2.MORPH_GRADIENT, morph_kernel, iterations=5)
        cnts,_ = cv2.findContours(morphed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
        for cnt in cnts:
            cnt_area = cv2.contourArea(cnt)
            if cnt_area >= min_area:
                filtered_contours.append(cnt)
                area.append(cv2.contourArea(cnt))
    
        # Compute centroids for all filtered contours
        for cnt in filtered_contours:
            M = cv2.moments(cnt)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                centroid.append((cx, cy))
                
        # If you want to visualize each contour's centroid and one average centroid:
        if len(centroid) > 0:
            avg_area = sum(area)/len(area)

            # Calculate the average of these centroids
            avg_x = int(sum(c[0] for c in centroid) / len(centroid))
            avg_y = int(sum(c[1] for c in centroid) / len(centroid))
            
            # Draw the average centroid in red
            
            tranformed_x, transformed_y = map_point_to_original((avg_x, avg_y), affine_matrix)
            centroids[i] = (tranformed_x, transformed_y)
            areas[i] = avg_area
            
        else:
            centroids[i] = (0,0)
            areas[i] = min_area
            
    return centroids, areas

def norms_sub_and_canny_images(subtracted_images, sub_canny_images):
    
    N = sub_canny_images.shape[0] 
    sub_img_norm = np.zeros((N), dtype= np.float32)
    canny_img_norm = np.zeros((N), dtype= np.float32)
    
    for i in range(N):
        sub_img_norm[i] = np.linalg.norm(subtracted_images[i]*5)
        canny_img_norm[i] = np.linalg.norm((sub_canny_images[i])/255.0)

    filtered_sub_norms = gaussian_filter1d(medfilt(sub_img_norm, kernel_size=3), sigma=2)
    filtered_canny_norms = gaussian_filter1d(medfilt(canny_img_norm, kernel_size=3), sigma=2)
    
    return filtered_sub_norms, filtered_canny_norms

def finding_digital_signal(sub_norms, canny_norms):
    
    def combine_harmonic_mean(scaled_sub, scaled_canny):
        sub_arr = scaled_sub
        canny_arr = scaled_canny
        numerator = 2.0 * sub_arr * canny_arr
        denominator = sub_arr + canny_arr + 1e-8 
        combined = numerator / denominator
        return combined
    
    sub_norm_arr = np.clip(sub_norms, 0, 30).reshape(-1,1)
    canny_norms_arr = np.clip(canny_norms, 0, 15).reshape(-1,1)
    
    scaler = MinMaxScaler(feature_range=(0,1), clip=True)
    scaled_sub_norm = scaler.fit_transform(sub_norm_arr)
    scaler1 = MinMaxScaler(feature_range=(0,1), clip=True)
    scaled_canny_norm = scaler1.fit_transform(canny_norms_arr)
    
    combined_harmonic  = combine_harmonic_mean(scaled_sub_norm, scaled_canny_norm)
    
    #--- Converting Analog Signal to Digital Signal ---#
    threshold = 0.3
    digital_signal = np.where(combined_harmonic>threshold, 1, 0)
    
    median_filtered_dg = medfilt(digital_signal.flatten(), kernel_size=7)
    processed_signal = median_filtered_dg.copy()     
    new_crucial_indices = np.where(processed_signal>0)[0]
    
    return combined_harmonic, processed_signal, new_crucial_indices[:-1]

def processing_digital_signal(total_frames, digital_signal, crucial_indices, json_file_path):
    
    json_path = Path(json_file_path)
    if not json_path.is_file():
        print(f"[INFO] {json_path} not found – skipping JSON-based processing")
        return digital_signal, crucial_indices  
    
    with open(json_file_path, 'r') as json_file:
        data = json.load(json_file)
    
    duration = data["duration"]
    FPS = (total_frames + 20) / duration #here I'm adding +20 as the frames I'm calling is clipped
    processed_signal = digital_signal.copy()
    segments = []
    individual_segment = []
    
    for i, index in enumerate(crucial_indices):
        if i == 0:
            individual_segment.append(index/FPS)
        else:
            if index - crucial_indices[i-1] != 1:
                segments.append(individual_segment)
                individual_segment = []
            individual_segment.append(index/FPS)
            
    if individual_segment:
        segments.append(individual_segment)
        
    for i in range(2, len(segments)-1):
        end_curr = segments[i - 1][-1]
        start_next = segments[i][0]
        gap = start_next-end_curr
        if gap <= 0.5:
            end_curr_idx = round(end_curr * FPS)
            start_next_idx = round(start_next * FPS)
            processed_signal[end_curr_idx+1:start_next_idx] = 1
            
    new_crucial_indices = np.where(processed_signal>0)[0]
    
    return processed_signal, new_crucial_indices[:-1]

def selecting_crucial_centroids_and_areas(crucial_indices, centroids, areas):
    print(crucial_indices)
    selected_centroids = centroids[crucial_indices]
    selected_areas = areas[crucial_indices] 
    
    mask_zero = np.all(selected_centroids == 0, axis=1)
    good_idx = np.flatnonzero(~mask_zero)       
    fill_from = np.empty_like(mask_zero, dtype=int)
    fill_from[:] = -1                                
    fill_from[good_idx] = good_idx                   
    np.maximum.accumulate(fill_from, out=fill_from)  

    need_fill = mask_zero & (fill_from != -1)
    selected_centroids[need_fill] = selected_centroids[fill_from[need_fill]]      
    return selected_centroids, selected_areas 

def processing_centroids_and_areas(crucial_indices, selected_centroids, selected_areas):
    gaps = np.diff(crucial_indices) > 1
    cnt_centroids = np.split(selected_centroids, np.nonzero(gaps)[0] + 1)
    cnt_areas = np.split(selected_areas, np.nonzero(gaps)[0] + 1)
    events = np.split(crucial_indices, np.nonzero(gaps)[0] + 1)

    print("events", len(events))

    processed_centroids = []
    processed_areas = []
    optical_flow_centroids = []

    for c, area in zip(cnt_centroids, cnt_areas):
        n = len(c)
        if n == 0:
            continue

        q1 = int(n * 0.25)
        q2 = int(n * 0.50)
        q3 = int(n * 0.75)

        # Use Q2–Q3 consistently
        area_range = [(q2, q3)] * 4
        cent_range = [(q1, q2), (q1, q2), (q2, q3), (q2, q3)]
        of_range   = [(q2, q3)] * 4

        temp_centroids = []
        temp_areas = []
        temp_OF_centroids = []

        for start, end in area_range:
            if end - start <= 0:
                continue
            avg_area = float(np.mean(area[start:end]))
            temp_areas.extend([avg_area] * (end - start))

        for start, end in cent_range:
            if end - start <= 0:
                continue
            avg_centroid = tuple(np.round(c[start:end].mean(axis=0)).astype(int))
            temp_centroids.extend([avg_centroid] * (end - start))

        for start, end in of_range:
            if end - start <= 0:
                continue
            avg_centroid = tuple(np.round(c[start:end].mean(axis=0)).astype(int))
            temp_OF_centroids.extend([avg_centroid] * (end - start))

        processed_centroids.append(temp_centroids)
        processed_areas.append(temp_areas)
        optical_flow_centroids.append(temp_OF_centroids)

    # ---------------------
    # Pad to match length of each event
    # ---------------------
    cent_grp = []
    area_grp = []
    OF_event_grp = []

    for i in range(len(events)):
        event_len = len(events[i])
        
        # Centroids
        centroids = processed_centroids[i]
        if len(centroids) < event_len:
            pad_count = event_len - len(centroids)
            last_val = centroids[-1] if centroids else (0, 0)
            centroids.extend([last_val] * pad_count)
        cent_grp.append(centroids)

        # Areas
        areas = processed_areas[i]
        if len(areas) < event_len:
            pad_count = event_len - len(areas)
            last_val = areas[-1] if areas else 0.0
            areas.extend([last_val] * pad_count)
        area_grp.append(areas)

        # Optical Flow Centroids
        of_centroids = optical_flow_centroids[i]
        if len(of_centroids) < event_len:
            pad_count = event_len - len(of_centroids)
            last_val = of_centroids[-1] if of_centroids else (0, 0)
            of_centroids.extend([last_val] * pad_count)
        OF_event_grp.append(of_centroids)

    return events, cent_grp, area_grp, OF_event_grp

def tray_region_selection(centroid_x, centroid_y, tray_region, lr_section):
    """
    Given centroid in half-res (e.g. 640x360), returns tray and section labels.
    """
    cx, cy = int(round(centroid_x)), int(round(centroid_y))
    pt = (cx, cy)

    tray_label = 'None'
    section_label = 'None'

    if tray_region:
        for name, poly in tray_region.items():
            poly_arr = np.array(poly, dtype=np.float32)
            if cv2.pointPolygonTest(poly_arr, pt, False) >= 0:
                tray_label = name
                break

    if lr_section:
        for name, poly in lr_section.items():
            poly_arr = np.array(poly, dtype=np.float32)
            if cv2.pointPolygonTest(poly_arr, pt, False) >= 0:
                section_label = name
                break

    return tray_label, section_label

def draw_bbox_original_frame(images_dir, save_dir_modified_frames, clipped_files, grouped_indices, 
                             grouped_centroids, grouped_areas, OF_centroids, tray_region, lr_section, bbox_coordinates):
    bbox_cropped_frames = []
    bbox_OF_cropped_frames = []
    frame_to_centroid = {}
    frame_to_area     = {}
    frame_to_of_centroid = {}
    labels = []
    scale = bbox_coordinates["BBOX_SCALE"]
    for indices, centroids in zip(grouped_indices, grouped_centroids):
        for idx, c in zip(indices, centroids):
            frame_to_centroid[idx] = c
            
    for indices, of_centroids in zip(grouped_indices, OF_centroids):
        for idx, of_c in zip(indices, of_centroids):
            frame_to_of_centroid[idx] = of_c

    for indices, areas in zip(grouped_indices, grouped_areas):
        for idx, a in zip(indices, areas):
            frame_to_area[idx] = a

    # -- Process all frames --
    for index, frame in iterate_over_images(images_dir, clipped_files):
        img = frame.copy()
        bbox_image = frame.copy()

        if index in frame_to_centroid:
            cx = frame_to_centroid[index][0]
            cy = frame_to_centroid[index][1]-10
            
            tray_label, section_label = tray_region_selection(cx*scale, cy*scale, tray_region, lr_section)
            
            if tray_label == "tray_1":
                cx = frame_to_centroid[index][0] - 5
                cy = frame_to_centroid[index][1] + 15
            elif tray_label == "tray_2":
                cx = frame_to_centroid[index][0]
                cy = frame_to_centroid[index][1] + 10
            else :
                cx = frame_to_centroid[index][0]
                cy = frame_to_centroid[index][1] + 10
                
            if (cx, cy) != (0, 0):    
                # area   = frame_to_area.get(i, 0)
                if tray_label == "tray_1":
                    dx1, dy1, dx2, dy2 = bbox_coordinates["BBOX_OFFSETS_TRAY_1"]
                elif tray_label == "tray_2":
                    dx1, dy1, dx2, dy2 = bbox_coordinates["BBOX_OFFSETS_TRAY_2"]
                else:
                    dx1, dy1, dx2, dy2 = bbox_coordinates["BBOX_OFFSETS_DEFAULT"]
                    
            
                # Apply offsets
                pt1 = (int(cx + dx1), int(cy + dy1))
                pt2 = (int(cx + dx2), int(cy + dy2))
                        
                h, w = img.shape[:2]
                x1, y1 = max(pt1[0], 0), max(pt1[1], 0)
                x2, y2 = min(pt2[0], w - 1), min(pt2[1], h - 1)

                if x2 > x1 and y2 > y1:
                    # Draw bounding box and annotate with area
                    cv2.rectangle(bbox_image, ((x1*2)-4, (y1*2)-4), ((x2*2)+4, (y2*2)+4), (0, 255, 0), 4)
                    # cv2.putText(bbox_image, f"{tray_label}", (100, 100),
                    #             cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    cropped_B = img[y1*scale:y2*scale, x1*scale:x2*scale]
                    bbox_cropped_frames.append(cropped_B)
                    labels.append((tray_label, section_label))
                    print(f"labels : {labels}")
                    
        #________________________________Optical_FLow_Cropped_Frames______________________________________________#            
        if index in frame_to_of_centroid:
            of_cx = frame_to_of_centroid[index][0]
            of_cy = frame_to_of_centroid[index][1]-10
            
            dx1, dy1, dx2, dy2 = bbox_coordinates["BBOX_OFFSETS_OPTICAL_FLOW"]
            
            if (of_cx, of_cy) != (0, 0):
                
                pt1 = (int(of_cx + dx1), int(of_cy + dy1))
                pt2 = (int(of_cx + dx2), int(of_cy + dy2))
   
                h, w = img.shape[:2]
                x1, y1 = max(pt1[0], 0), max(pt1[1], 0)
                x2, y2 = min(pt2[0], w - 1), min(pt2[1], h - 1)

                if x2 > x1 and y2 > y1:
                    of_cropped_B = img[y1*scale:y2*scale, x1*scale:x2*scale]
                    bbox_OF_cropped_frames.append(of_cropped_B)
        
        modified_img_path = os.path.join(save_dir_modified_frames, f"modified_frame_{index}.jpg")
        cv2.imwrite(modified_img_path, bbox_image)

    return bbox_cropped_frames, bbox_OF_cropped_frames, labels

def image_enhancement(frames, enhanced_frames, brightness=0.9, contrast=1.4, color=1.6, sharpness=1.4):
    
    def apply_pil_enhancements(img, brightness, contrast, color, sharpness):
        img = ImageEnhance.Brightness(img).enhance(brightness)
        img = ImageEnhance.Contrast(img).enhance(contrast)
        img = ImageEnhance.Color(img).enhance(color)
        img = ImageEnhance.Sharpness(img).enhance(sharpness)
        return img

    for i, frame in enumerate(frames):
        img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        img_pil = apply_pil_enhancements(img_pil, brightness, contrast, color, sharpness)
        image = np.array(img_pil)  # Still in RGB
        enhanced_frames.append(image)
        
    return enhanced_frames

def events_from_crucial_indices(cropped_frames_big, cropped_frames_OF, events, roi_labels):
    counter = 0
    group_img_big = []
    group_roi_labels = []
    group_img_optical_flow = []
    
    for event in events:
        sub_grp_img_big = []
        sub_grp_roi_label = []
        sub_grp_OF_img =[]
        for i in event:
            if counter < len(cropped_frames_big):
                sub_grp_img_big.append(cropped_frames_big[counter])
                sub_grp_roi_label.append(roi_labels[counter])
                sub_grp_OF_img.append(cropped_frames_OF[counter])
                counter+=1
            
        if sub_grp_img_big:
            group_img_big.append(sub_grp_img_big)
            group_roi_labels.append(sub_grp_roi_label)
            group_img_optical_flow.append(sub_grp_OF_img)

    # Refining ROI label events as any one label event might have both left section and right section in the same event.
    # The idea is to select the 3rd quatile, and based on the max recurring section in that quatile, change the whole event to that.
    refined_group_roi_labels = []
    for roi_label_group in group_roi_labels:
        n = len(roi_label_group)
        if n == 0:
            refined_group_roi_labels.append([])
            continue

        # 3rd quartile slice (top 25% of event frames)
        q3_start = int(0.75 * n)
        upper_quartile = roi_label_group[q3_start:]

        # Get most common ROI label in that quartile
        if upper_quartile:
            most_common_label = Counter(upper_quartile).most_common(1)[0][0]
            refined_group_roi_labels.append([most_common_label] * n)
        else:
            refined_group_roi_labels.append(roi_label_group)

    return group_img_big, group_img_optical_flow, refined_group_roi_labels

def roi_based_events_divison(group_img_big, group_img_OF, refined_group_roi_labels):
    
    # Predefined trays and sections
    tray_sections = {
        ('Tray_1', 'Left_Section'): 0,
        ('Tray_1', 'Right_Section'): 1,
        ('Tray_2', 'Left_Section'): 2,
        ('Tray_2', 'Right_Section'): 3,
        ('None'  , 'None'): 4
        
    }

    # Initialise containers
    tray_labels = [[] for _ in range(5)]
    tray_imgs_big = [[] for _ in range(5)]
    tray_OF_img = [[] for _ in range(5)]

    # Loop through the zipped items
    for img_big, img_OF, event in zip(group_img_big, group_img_OF, refined_group_roi_labels):
        tray_key = tuple(event[0])
        idx = tray_sections.get(tray_key)
        if idx is not None:
            tray_labels[idx].append(event)
            tray_imgs_big[idx].append(img_big)
            tray_OF_img[idx].append(img_OF)

    return tray_labels, tray_imgs_big, tray_OF_img

def classify_tray_images_per_section(tray_imgs, reference_dirs, batch=32):
    assert len(reference_dirs) == len(tray_imgs), "reference_dirs and tray_imgs length mismatch"
    device = "cuda" if torch.cuda.is_available() else "cpu"

    predictions_of_cropped_imgs = []  # [section][event] -> list[(label, conf)]
    with torch.inference_mode():
        for i, tray_group in enumerate(tray_imgs):
            section_preds = []
            for event_frames in tray_group:
                if not event_frames:
                    section_preds.append([])  # keep alignment
                    continue
                preds = run_model_on_frames(event_frames, reference_dirs[i], batch=batch, device=device)
                section_preds.append(preds)
            predictions_of_cropped_imgs.append(section_preds)

    return predictions_of_cropped_imgs

@torch.no_grad()
def run_model_on_frames(frames, model_id, batch=32, device="cpu"):
    # Load
    proc  = AutoImageProcessor.from_pretrained(model_id)
    model = AutoModelForImageClassification.from_pretrained(model_id).to(device).eval()
    labels = model.config.id2label

    preds = []
    n = len(frames)
    for i in range(0, n, batch):
        imgs   = [Image.fromarray(f).resize((256, 256)) for f in frames[i:i+batch]]
        inputs = proc(images=imgs, return_tensors="pt")
        # move only tensors to device
        for k in inputs:
            inputs[k] = inputs[k].to(device, non_blocking=True)

        logits = model(**inputs).logits
        probs  = F.softmax(logits, dim=-1)
        top1   = probs.max(dim=-1)
        preds.extend((labels[int(idx)], float(conf)) for idx, conf in zip(top1.indices, top1.values))

        # free per-batch tensors (helps on CPU)
        del inputs, logits, probs, top1
        if device == "cpu":
            gc.collect()

    # Unload
    del model, proc
    gc.collect()

    return preds

#____________________________________________OPTICAL FLOW FUNCTIONS______________________________________________________#

def smoothing_out_event_labels(predictions_of_cropped_imgs, tray_cropped_images):
    """
    predictions_of_cropped_imgs: list[section][event][(label, conf)]
    tray_cropped_images:         list[section][event][image]

    Returns:
        optical_flow_all_events: list[section][event][image]    # only frames with label != 'No_product'
        preds_all:               list[section][event][(label, conf)]  # cleaned preds for those frames
    """
    optical_flow_all_events = []
    preds_all = []

    for section_pred, crp_img_section in zip(predictions_of_cropped_imgs, tray_cropped_images):

        for events_pred, img_events in zip(section_pred, crp_img_section):
            smoothed = single_event_smoothing(events_pred, min_duration=3)

            of_imgs = []
            cleaned_preds = []
            for (label, conf), img in zip(smoothed, img_events):
                if label != config.no_product_label and conf>=0.98:
                    of_imgs.append(img)               # images to run optical flow on
                    cleaned_preds.append((label, conf))  # keep corresponding cleaned preds
            if cleaned_preds:
                optical_flow_all_events.append(of_imgs)
                preds_all.append(cleaned_preds)

    return optical_flow_all_events, preds_all

def single_event_smoothing(preds, min_duration=3):
    labels = [label for label, _ in preds]
    confs  = [conf for _, conf in preds]
    smoothed = labels.copy()
    length = len(labels)

    # Spike filtering
    for i in range(1, length - 1):
        prev_lbl, next_lbl = labels[i - 1], labels[i + 1]
        prev_conf, next_conf = confs[i - 1], confs[i + 1]
        curr_lbl, curr_conf = labels[i], confs[i]

        if prev_lbl == next_lbl and curr_lbl != prev_lbl:
            if curr_conf < min(prev_conf, next_conf):
                smoothed[i] = prev_lbl

    # Duration filtering
    filtered = smoothed.copy()
    i = 0
    while i < length:
        j = i
        while j < length and smoothed[j] == smoothed[i]:
            j += 1
        run_len = j - i
        if run_len < min_duration:
            # use previous label if available, else next
            fallback = smoothed[i - 1] if i > 0 else (smoothed[j] if j < length else smoothed[i])
            for k in range(i, j):
                filtered[k] = fallback
        i = j

    return [(filtered[i], confs[i]) for i in range(length)]
             
def f_mask(current_frame, next_frame):

    gs_current_frame = (cv2.cvtColor(current_frame,cv2.COLOR_BGR2GRAY))
    gs_current_frame_normalized = gs_current_frame

    gs_next_frame = (cv2.cvtColor(next_frame,cv2.COLOR_BGR2GRAY))
    gs_next_frame_normalized = gs_next_frame

    kernel = np.ones((5,5),np.float32)/25
    # gaussian_blur_curr = cv2.GaussianBlur(gs_current_frame_normalized, (5, 5), 0)

    gaussian_blur_curr = cv2.filter2D(gs_current_frame_normalized,-1,kernel)
    gaussian_blur_next = cv2.filter2D(gs_next_frame_normalized, -1, kernel)
    subtracted_image = cv2.absdiff(gaussian_blur_curr, gaussian_blur_next)
    _, canny_on_sub_img = cv2.threshold(subtracted_image,50,200,cv2.THRESH_BINARY)
    cross_kernel = cv2.getStructuringElement(cv2.MORPH_CROSS,(7,7))
    morphed_image =  cv2.morphologyEx(canny_on_sub_img, cv2.MORPH_GRADIENT, cross_kernel, iterations=3)
    contours, _ = cv2.findContours(morphed_image,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    black_canvas = np.zeros((morphed_image.shape[0], morphed_image.shape[1], 3), dtype=np.uint8)

    if contours:
        filtered_contours = max(contours, key=cv2.contourArea)

        cv2.drawContours(black_canvas, [filtered_contours], -1, (0, 255, 0), 3)

        M = cv2.moments(filtered_contours)
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
        else:
            cx, cy = 0, 0

        cv2.circle(black_canvas, (cx, cy), 6, (0, 0, 255), -1)
        cv2.putText(black_canvas, f"({cx},{cy})", (cx + 10, cy + 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
    else:
        cx, cy = 0, 0
    
    return black_canvas, cx,cy

def clamp_jumps(vec, max_jump=10):
    clamped = [vec[0]]
    for i in range(1, len(vec)):
        delta = vec[i] - clamped[-1]
        if abs(delta) > max_jump:
            clamped.append(clamped[-1] + np.sign(delta) * max_jump)
        else:
            clamped.append(vec[i])
    return clamped

def get_dominant_sign(vectors):
    v = np.array(vectors)
    pos = np.sum(v > 0)
    neg = np.sum(v < 0)
    return 1 if pos >= neg else -1

def Activity_category(vector):
    if not len(vector):
        return "UNKNOWN"
    net = np.sum(np.array(vector))
    return "USER_PICKUP" if net > 0 else "USER_PUTBACK"

def Object_tracking(new_enhnaced_image):
    sub_images = []
    centroids_per_frame = []
    activities = []

    lk_params = dict(
        winSize=(21, 21),
        maxLevel=3,
        criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01)
    )

    for group in new_enhnaced_image:
        initial_centroid = None
        initial_pts = None
        prev_gray = None
        trail = []
        vector_direction = []
        for idx in range(len(group) - 2):
            current_frame = group[idx]
            next_frame    = group[idx + 2]
            _, cx, cy     = f_mask(current_frame, next_frame)

            if (cx, cy) == (0, 0):
                initial_pts = None            
                continue             

            full_frame = next_frame.copy()
            gray_next  = cv2.cvtColor(full_frame, cv2.COLOR_BGR2GRAY)

            if initial_pts is None:           # first time we have a good centroid
                initial_centroid = (cx, cy)
                h, w            = full_frame.shape[:2]
                roi_size        = 40

                x1 = max(cx - roi_size, 0);  y1 = max(cy - roi_size, 0)
                x2 = min(cx + roi_size, w);  y2 = min(cy + roi_size, h)

                cv2.rectangle(full_frame, (x1, y1), (x2, y2), (0, 255, 0), 3)

                roi       = full_frame[y1:y2, x1:x2]
                gray_roi  = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                corners   = cv2.goodFeaturesToTrack(gray_roi, 30, 0.01, 10)

                if corners is None:
                    print(f"[WARN] no corners at frame {idx}")
                    continue                  

                corners        = corners.reshape(-1, 2) + np.array([x1, y1])
                initial_pts    = corners.reshape(-1, 1, 2).astype(np.float32)
                prev_gray      = gray_next.copy()
                for x, y in corners:
                    cv2.circle(full_frame, (int(x), int(y)), 3, (255, 0, 0), -1)

            else:
                if initial_pts is None or len(initial_pts) == 0:
                    prev_gray = gray_next.copy()
                    continue                      

                if initial_pts.dtype != np.float32:
                    initial_pts = initial_pts.astype(np.float32)
                if initial_pts.ndim == 2: 
                    initial_pts = initial_pts.reshape(-1, 1, 2)

                next_pts, status, _ = cv2.calcOpticalFlowPyrLK(
                    prev_gray, gray_next, initial_pts, None, **lk_params
                )
                good_new = next_pts[status == 1]

                if len(good_new) < 25:
                    last_cx, last_cy = trail[-1] if trail else (cx, cy)
                    x1 = max(last_cx - roi_size, 0);  y1 = max(last_cy - roi_size, 0)
                    x2 = min(last_cx + roi_size, w);  y2 = min(last_cx + roi_size, h)

                    roi       = full_frame[y1:y2, x1:x2]
                    gray_roi  = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                    corners   = cv2.goodFeaturesToTrack(gray_roi, 30, 0.01, 10)

                    if corners is None:
                        print(f"[WARN] re-init failed at frame {idx}")
                        prev_gray = gray_next.copy()
                        continue

                    good_new  = corners.reshape(-1, 2) + np.array([x1, y1])

                avg_x, avg_y   = map(int, np.mean(good_new, axis=0))
                centroid_now   = (avg_x, avg_y)
                trail.append(centroid_now)

                cv2.circle(full_frame, centroid_now, 10, (0, 0, 255), -1)
                cv2.putText(full_frame, f"({avg_x},{avg_y})",
                            (avg_x + 10, avg_y), cv2.FONT_HERSHEY_SIMPLEX,
                            0.5, (0, 0, 255), 1)

                for i in range(1, len(trail)):
                    cv2.line(full_frame, trail[i-1], trail[i], (0, 128, 255), 2)

                if initial_centroid:
                    cv2.arrowedLine(full_frame, initial_centroid, centroid_now,
                                    (0, 255, 0), 3, tipLength=0.3)
                    dx, dy   = avg_x - initial_centroid[0], avg_y - initial_centroid[1]
                    degrees  = np.degrees(np.arctan2(dy, dx))
                    vector_direction.append(int(degrees))

                prev_gray   = gray_next.copy()
                initial_pts = good_new.reshape(-1, 1, 2)

            centroids_per_frame.append(initial_centroid)
            sub_images.append(full_frame)
                
        if vector_direction:
            dom_sign  = get_dominant_sign(vector_direction)
            filtered  = [v if np.sign(v) == dom_sign else 0 for v in vector_direction]
            smoothed  = gaussian_filter1d(filtered, sigma=1)

            if len(smoothed) > 1:
                activities.append(Activity_category(smoothed))

    return sub_images, activities

#_________________________________________________________________________________________________________________________#
 
def pad_events(idxs, centroids, pad=5):
    """
    idxs : 1-D iterable of ints (frame numbers, already sorted)
    pad  : how many frames to add before & after each event
    returns np.ndarray with the padded frame numbers
    """
    idxs = np.asarray(idxs, dtype=int)
    if idxs.size == 0:
        return idxs

    # split into contiguous runs ── every run is one event
    split_points = np.where(np.diff(idxs) != 1)[0] + 1
    runs = np.split(idxs, split_points)          # list of np.arrays

    #work out how much padding each run can keep without touching its neighbour
    before = [pad] * len(runs)                   # how many frames to add before
    after  = [pad] * len(runs)                   # how many frames to add after

    for i in range(len(runs) - 1):
        gap = runs[i+1][0] - runs[i][-1] - 1     # frames sitting between two events
        extra_needed = (pad + pad) - gap         # how many frames must be trimmed
        if extra_needed > 0:                     # trim only if they would overlap
            trim_a = min(after[i], extra_needed) # trim from the left event’s tail first
            after[i] -= trim_a
            extra_needed -= trim_a
            before[i+1] -= extra_needed          # whatever is left, trim from right event’s head

    #build the final list with the (possibly reduced) padding
    padded = []
    for (run, b, a) in zip(runs, before, after):
        start = max(0, run[0] - b)               # clamp at 0 if needed
        end   = run[-1] + a
        padded.extend(range(start, end + 1))
        
    padded = np.array(sorted(set(padded)), dtype=int)
    max_len = len(centroids)

    if max_len is not None:
        padded = padded[(padded >= 0) & (padded < max_len)]
        
    return padded
      
def refining_bboxes(bbox_frames, events,frames_to_track =[]):
    counter = 0
    for event in events:
        sub_group = []
        for i in event:
            if counter < len(bbox_frames):
                sub_group.append(bbox_frames[counter])
                counter+=1
        
        if sub_group:
            frames_to_track.append(sub_group)
            
    return frames_to_track

def save_frames_for_video_creation(frames, directory):
    Path(directory).mkdir(parents=True, exist_ok=True)  # Ensure directory exists
    for idx, img in enumerate(frames):
        fname = Path(directory) / f"frame_{idx:04d}.jpg"
        cv2.imwrite(str(fname), img)
        
def iterate_over_images(images_dir, clipped_files):
    for idx, file in enumerate(clipped_files):
        img_path = os.path.join(images_dir, file)
        img = cv2.imread(img_path)
        yield idx, img


def cv_algo(logger, sub_folder_path, json_file_path, transaction_number, stream, flip_camera):
    
    # Here stream is "0" or "1" which will decide which model_path, tray_section, pnts, and lr_section 
    # to use depending on the camera whihc is getting accessed by the function
    tray_region = config.tray_region[str(stream)] 
    lr_section = config.lr_section[str(stream)]
    model_path = config.model_path[str(stream)]
    pnts = config.pnts[str(stream)]
    bbox_coordinates = config.bbox_coordinates[str(stream)]
    video_path = os.path.join(sub_folder_path, f"media_{stream}.mp4")
    
    # Default fallbacks when tray_region or lr_section are None
    # if tray_region is None:
    #     tray_region = {"Default_Tray": np.array([[0, 0], [640, 0], [640, 480], [0, 480]])}
    #     logger.info("Defaulting to whole Image as tray selection")
    # if lr_section is None:
    #     lr_section = {
    #         "Left_Section": np.array([[0, 0], [320, 0], [320, 480], [0, 480]]),
    #         "Right_Section": np.array([[320, 0], [640, 0], [640, 480], [320, 480]])
    #     }
    #     logger.info("Defaulting to whole Image as lr_section selection")
        
    t0 = time.time()
    logger.info(f"Starting CV algorithm for transaction {transaction_number}.")
    logger.info(f"Input video: {video_path}, JSON: {json_file_path}, Model: {model_path}")

    # ----- setup dirs -----
    vid_to_frames_save_path = f"output_data/video_frames_cam{stream}/{transaction_number}/Frames"
    os.makedirs(vid_to_frames_save_path, exist_ok=True)
    mod_frame_path = f"output_data/bbox_labelled_frames_cam{stream}/{transaction_number}/Frames"
    os.makedirs(mod_frame_path, exist_ok=True)
    logger.info(f"Output directories created: frames -> {vid_to_frames_save_path}, bbox -> {mod_frame_path}")

    # ----- extract frames -----
    
    frames_path, total_frames = vid_to_frames_save(video_path, vid_to_frames_save_path, flip_camera)
    kept = len([f for f in os.listdir(frames_path) if f.lower().endswith((".jpg", ".png", ".jpeg"))])
    logger.info(f"Extracted {kept} frames from the video  ")

    # ----- load frames -----
    if kept > 6000:
        logger.info("Total frames exceed the capacity, trimming them down")
        all_files, _ = load_files(frames_path, idx=10)
        trimmed_files = all_files[::2]
        clipped_files = trimmed_files
        clipped_file_count = len(clipped_files)
        logger.info(f"Total frames now {clipped_file_count}")
    else:
        logger.info("Total number of frames are within capacity, continuing normal operation.")
        clipped_files, clipped_file_count = load_files(frames_path, 10)

    
    # frames_full_size = load_frames(clipped_files, clipped_file_count, frames_path)
    logger.info(f"Loaded {clipped_file_count} frames into memory  ")
    del total_frames; gc.collect()

    # ----- crop & resize -----
    
    cropped_frames, affine_matrix = resize_and_crop_frames(vid_to_frames_save_path, clipped_files, pnts, cropped_frames=[])
    logger.info(f"Resized and cropped {len(cropped_frames)} frames  ")

    # ----- diff & canny -----
    
    subtracted_images, sub_canny_images, images_for_centroid = get_diff_and_canny_images(cropped_frames)
    logger.info(f"Generated subtraction and canny edge images  ")
    del cropped_frames; gc.collect()

    # ----- centroids & areas -----
    
    centroids, areas = find_centroid_and_area(images_for_centroid, affine_matrix)
    nz = int(np.sum(~np.all(np.asarray(centroids) == 0, axis=1)))
    logger.info(f"Calculated centroids and areas. {nz} non-zero centroids found  ")
    del images_for_centroid; del affine_matrix; gc.collect()

    # ----- signal -----
    
    sub_norms, canny_norms = norms_sub_and_canny_images(subtracted_images, sub_canny_images)
    combined_harmonic, digital_signal, indices = finding_digital_signal(sub_norms, canny_norms)
    logger.info(f"Derived digital signal with {len(indices)} crucial indices  ")
    del subtracted_images, sub_canny_images, sub_norms, canny_norms, combined_harmonic; gc.collect()

    # ----- merge with json -----
    
    x, crucial_indices = processing_digital_signal(clipped_file_count, digital_signal, indices, json_file_path
    )
    logger.info(f"Processed JSON timeline, resulting in {len(crucial_indices)} crucial indices  ")
    del digital_signal, x, indices; gc.collect()

    # ----- events -----
    
    cent_sel, area_sel = selecting_crucial_centroids_and_areas(crucial_indices, centroids, areas)
    events, g_cent, g_area, OF_centroids = processing_centroids_and_areas(crucial_indices, cent_sel, area_sel)
    logger.info(f"Grouped {len(events)} events from crucial indices  ")
    del crucial_indices, centroids, areas, cent_sel, area_sel; gc.collect()

    # ----- bbox & enhance -----
    
    # bbox_cropped_frames, bbox_cropped_OF_frames, modified_frames, roi_labels = draw_bbox_original_frame(
    #     frames_full_size, events, g_cent, g_area, OF_centroids, tray_region, lr_section
    # )
    bbox_cropped_frames, bbox_cropped_OF_frames, roi_labels = draw_bbox_original_frame(vid_to_frames_save_path, mod_frame_path, clipped_files, events, g_cent, g_area, OF_centroids, tray_region, lr_section, bbox_coordinates) 

    # ----- save frames -----
    # save_frames_for_video_creation(modified_frames, mod_frame_path)
    saved = len([f for f in os.listdir(mod_frame_path) if f.lower().endswith((".jpg",".png",".jpeg"))])
    logger.info(f"Saved {saved} modified frames into {mod_frame_path} ")
    # del modified_frames; gc.collect()
    
    enhanced_frames = image_enhancement(bbox_cropped_frames, enhanced_frames=[])
    logger.info(f"Drew bounding boxes and enhanced {len(enhanced_frames)} frames  ")
    del g_cent, g_area, OF_centroids, bbox_cropped_frames; gc.collect()

    # ----- split by ROI -----
    
    grouped_cropped_img, grouped_OF_cropped_img, grouped_roi_labels = events_from_crucial_indices(
        enhanced_frames, bbox_cropped_OF_frames, events, roi_labels
    )
    tray_labels, tray_cropped_images, tray_OF_crop_img = roi_based_events_divison(
        grouped_cropped_img, grouped_OF_cropped_img, grouped_roi_labels
    )
    per_sec = [sum(len(ev) for ev in sec) for sec in tray_cropped_images]
    logger.info(f"Split frames by ROI. Section-wise frame counts: {per_sec}")
    del enhanced_frames, bbox_cropped_OF_frames, roi_labels; gc.collect()

    # ----- classify -----
    
    reference_dirs = [model_path] * 5
    predictions_of_cropped_imgs = classify_tray_images_per_section(tray_cropped_images, reference_dirs, batch=32)
    logger.info(f"Ran classification across {len(tray_cropped_images)} tray sections  ")
    del tray_labels, grouped_cropped_img, grouped_OF_cropped_img, grouped_roi_labels; gc.collect()

    # ----- smooth labels -----
    
    optical_flow_all_events, product_bought = smoothing_out_event_labels(predictions_of_cropped_imgs, tray_OF_crop_img)
    logger.info(f"Smoothed labels and generated {len(optical_flow_all_events)} optical flow events  ")
    
    # ----- Log per-event summary -----
    logger.info("\n========== EVENT SUMMARY ==========\n")
    for i, (preds, imgs) in enumerate(zip(product_bought, optical_flow_all_events)):
        if not preds or not imgs:
            continue
        # One representative prediction
        label, conf = preds[0]
        num_frames = len(imgs)
        logger.info(f"Event {i+1}: {label} ({conf:.2f})  |  Frames: {num_frames}")
    logger.info("\n===================================\n")


    
    del predictions_of_cropped_imgs, tray_OF_crop_img; gc.collect()

    # ----- tracking -----
    
    sub_imgs, activities = Object_tracking(optical_flow_all_events)
    logger.info(f"Optical flow tracking complete: {len(sub_imgs)} frames tracked, raw activities={activities}  ")
    del optical_flow_all_events; gc.collect()

    # ----- aggregate -----
    
    activity_list = []
    for idx, sub in enumerate(activities):
        if isinstance(sub, (list, tuple)):
            most_common_name = Counter(sub).most_common(1)[0][0]
        else:
            most_common_name = sub
        entry = {most_common_name: product_bought[idx][0][0]}
        activity_list.append(entry)
    logger.info(f"Aggregated final activities: {activity_list} ")
    del sub_imgs, activities, product_bought; gc.collect()

    logger.info(f"CV algorithm finished for transaction {transaction_number} in {time.time()-t0:.2f}s.")
    
    return activity_list
