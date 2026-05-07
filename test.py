import cv2
import numpy as np

video_path = "D:/Jelmer/Documents/OneDrive/Stage UT/camwatcher/data/compiled/thermocouple_3/2-75.mp4"
cap = cv2.VideoCapture(video_path)

# ----------------------------
# WINDOWS
# ----------------------------
cv2.namedWindow("Controls", cv2.WINDOW_NORMAL)

dummy = np.zeros((100, 400), dtype=np.uint8)
cv2.imshow("Controls", dummy)
cv2.waitKey(1)

# ----------------------------
# TRACKBARS
# ----------------------------
cv2.createTrackbar("CLAHE", "Controls", 20, 50, lambda x: None)
cv2.createTrackbar("Brightness", "Controls", 50, 100, lambda x: None)
cv2.createTrackbar("BlockSize", "Controls", 11, 50, lambda x: None)
cv2.createTrackbar("C", "Controls", 50, 100, lambda x: None)

# ----------------------------
# PREPROCESS FUNCTION
# ----------------------------
def preprocess(frame, clahe_val, brightness, block_size, c_val):

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # CLAHE contrast enhancement
    clip = max(1, clahe_val / 10.0)
    clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    # brightness
    beta = brightness - 50
    enhanced = cv2.convertScaleAbs(enhanced, alpha=1.0, beta=beta)

    # adaptive threshold settings
    block_size = max(3, block_size)
    if block_size % 2 == 0:
        block_size += 1

    thresh = cv2.adaptiveThreshold(
        enhanced,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        block_size,
        c_val
    )

    # cleanup noise
    kernel = np.ones((2, 2), np.uint8)
    cleaned = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

    return cleaned


# ----------------------------
# LOAD FIRST FRAME
# ----------------------------
ret, frame = cap.read()
if not ret:
    print("Could not load video")
    exit()

cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

print("Press 's' to start processing, 'q' to quit")

# ----------------------------
# TUNING LOOP
# ----------------------------
while True:

    clahe_val = cv2.getTrackbarPos("CLAHE", "Controls")
    brightness = cv2.getTrackbarPos("Brightness", "Controls")
    block_size = cv2.getTrackbarPos("BlockSize", "Controls")
    c_raw = cv2.getTrackbarPos("C", "Controls")
    c_val = (c_raw / 100.0) * 1.0

    processed = preprocess(frame, clahe_val, brightness, block_size, c_val)

    # original frame
    orig_vis = cv2.resize(frame, (320, 240))

    # preprocessing steps split for debugging
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    clahe_val = cv2.getTrackbarPos("CLAHE", "Controls")
    brightness = cv2.getTrackbarPos("Brightness", "Controls")
    block_size = cv2.getTrackbarPos("BlockSize", "Controls")
    c_val = cv2.getTrackbarPos("C", "Controls")
    c_offset = (c_raw / 100.0) * 10.0

    # CLAHE
    clip = max(1, clahe_val / 10.0)
    clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    # brightness
    beta = brightness - 50
    enhanced = cv2.convertScaleAbs(enhanced, alpha=1.0, beta=beta)

    # adaptive threshold safety fix
    block_size = max(3, block_size)
    if block_size % 2 == 0:
        block_size += 1

    thresh = cv2.adaptiveThreshold(
        enhanced,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        block_size,
        c_offset
    )

    # IMPORTANT: show enhanced grayscale (not just binary)
    enhanced_vis = cv2.resize(enhanced, (320, 240))
    enhanced_vis = cv2.cvtColor(enhanced_vis, cv2.COLOR_GRAY2BGR)

    # threshold view
    thresh_vis = cv2.resize(thresh, (320, 240))
    thresh_vis = cv2.cvtColor(thresh_vis, cv2.COLOR_GRAY2BGR)

    # combine 3 views
    combined = np.hstack((orig_vis, enhanced_vis, thresh_vis))

    cv2.imshow("Original | Enhanced | Threshold", combined)

    key = cv2.waitKey(30) & 0xFF

    if key == ord('q'):
        cap.release()
        cv2.destroyAllWindows()
        exit()

    if key == ord('s'):
        break


# ----------------------------
# PROCESS FULL VIDEO
# ----------------------------
cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

frame_idx = 0
results = []

while True:

    ret, frame = cap.read()
    if not ret:
        break

    clahe_val = cv2.getTrackbarPos("CLAHE", "Controls")
    brightness = cv2.getTrackbarPos("Brightness", "Controls")
    block_size = cv2.getTrackbarPos("BlockSize", "Controls")
    c_val = cv2.getTrackbarPos("C", "Controls")

    processed = preprocess(frame, clahe_val, brightness, block_size, c_val)

    # display both views during processing
    orig_vis = cv2.resize(frame, (320, 240))
    proc_vis = cv2.cvtColor(cv2.resize(processed, (320, 240)), cv2.COLOR_GRAY2BGR)
    combined = np.hstack((orig_vis, proc_vis))

    cv2.imshow("Preview (Original | Processed)", combined)

    results.append((frame_idx, None))

    print(f"Frame {frame_idx}")

    frame_idx += 1

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

# ----------------------------
# SAVE OUTPUT
# ----------------------------
with open("output.csv", "w") as f:
    f.write("frame,temperature\n")
    for r in results:
        f.write(f"{r[0]},\n")

print("Done. Saved to output.csv")