import cv2
import pytesseract
import numpy as np

# If on Windows, set path like:
# pytesseract.pytesseract.tesseract_cmd = r'C:/Program Files/Tesseract-OCR/tesseract.exe'

video_path = "D:/Jelmer/Documents/OneDrive/Stage UT/camwatcher/data/compiled/thermocouple_3/2-75.mp4"

points = []

def click_event(event, x, y, flags, param):
    global points, frame_display

    if event == cv2.EVENT_LBUTTONDOWN:
        points.append((x, y))
        print(f"Point {len(points)}: ({x}, {y})")

        cv2.circle(frame_display, (x, y), 5, (0, 255, 0), -1)
        cv2.imshow("Select Regions", frame_display)


# --- Load first frame ---
cap = cv2.VideoCapture(video_path)
ret, frame = cap.read()
if not ret:
    print("Failed to load video")
    exit()

frame_display = frame.copy()

print("Click TOP-LEFT and BOTTOM-RIGHT for each digit")
print("Press 'q' when done")

cv2.imshow("Select Regions", frame_display)
cv2.setMouseCallback("Select Regions", click_event)

while True:
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()

# Convert to boxes
boxes = []
for i in range(0, len(points), 2):
    (x1, y1) = points[i]
    (x2, y2) = points[i+1]
    boxes.append((x1, y1, x2, y2))

print("Boxes:", boxes)


# --- Slider window ---
cv2.namedWindow("Controls", cv2.WINDOW_NORMAL)

cv2.createTrackbar("Contrast", "Controls", 10, 30, lambda x: None)   # alpha = val/10
cv2.createTrackbar("Brightness", "Controls", 0, 100, lambda x: None) # beta = val-50
cv2.createTrackbar("Threshold", "Controls", 150, 255, lambda x: None)


def preprocess(roi):
    contrast = cv2.getTrackbarPos("Contrast", "Controls") / 10.0
    brightness = cv2.getTrackbarPos("Brightness", "Controls") - 50
    thresh_val = cv2.getTrackbarPos("Threshold", "Controls")

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    # Apply contrast + brightness
    adjusted = cv2.convertScaleAbs(gray, alpha=contrast, beta=brightness)

    # Threshold
    _, thresh = cv2.threshold(adjusted, thresh_val, 255, cv2.THRESH_BINARY_INV)

    return thresh


def read_digit(roi):
    processed = preprocess(roi)

    config = "--psm 10 -c tessedit_char_whitelist=0123456789.-"
    text = pytesseract.image_to_string(processed, config=config)

    return text.strip(), processed


# --- Calibration loop ---
print("Adjust sliders. Press 's' to start processing video.")

while True:
    preview = frame.copy()
    
    # Just to keep the window alive and visible
    # We create a small blank canvas so the sliders have a background
    ctrl_bg = np.zeros((10, 400, 3), np.uint8) 
    cv2.imshow("Controls", ctrl_bg)

    for (x1, y1, x2, y2) in boxes:
        roi = frame[y1:y2, x1:x2]
        digit, processed = read_digit(roi)

        # Show the processed version of the LAST digit box
        cv2.imshow("Processed ROI", processed)

        cv2.rectangle(preview, (x1, y1), (x2, y2), (0, 255, 0), 1)
        cv2.putText(preview, digit, (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1)

    cv2.imshow("Preview", preview)

    key = cv2.waitKey(30) & 0xFF # Increased wait slightly for UI stability
    if key == ord('s'):
        break

cv2.destroyAllWindows()


# --- Process full video ---
cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

frame_idx = 0
results = []

while True:
    ret, frame = cap.read()
    if not ret:
        break

    digits = []

    for (x1, y1, x2, y2) in boxes:
        roi = frame[y1:y2, x1:x2]
        digit, _ = read_digit(roi)
        digits.append(digit)

    temp_str = "".join(digits)

    try:
        temp_val = float(temp_str)
    except:
        temp_val = None

    print(f"Frame {frame_idx}: {temp_val}")
    results.append((frame_idx, temp_val))

    frame_idx += 1

cap.release()

# Save results
with open("temperatures.csv", "w") as f:
    f.write("frame,temperature\n")
    for frame_idx, temp in results:
        f.write(f"{frame_idx},{temp}\n")

print("Done.")