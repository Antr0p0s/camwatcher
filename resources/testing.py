import cv2
import numpy as np
import os

# --- SETUP ---
script_dir = os.path.dirname(os.path.abspath(__file__))
data_path = os.path.join(script_dir, 'data.npz')
data = np.load(data_path)
all_frames = data['frames']
h, w = all_frames[0].shape

REF_VMIN, REF_VMAX = 251.0, 443.0

WIN_CTRL = 'Controls'
WIN_DET  = 'Detection'
WIN_REF  = 'Reference'
WIN_PROC = 'Processed'

# --- WINDOWS ---
cv2.namedWindow(WIN_CTRL, cv2.WINDOW_NORMAL)
cv2.resizeWindow(WIN_CTRL, 600, 900)

cv2.namedWindow(WIN_DET)
cv2.namedWindow(WIN_REF)
cv2.namedWindow(WIN_PROC)

def nothing(x): pass

# --- TRACKBARS ---
cv2.createTrackbar('Frame', WIN_CTRL, 673, len(all_frames)-1, nothing)
cv2.createTrackbar('Vmin', WIN_CTRL, 275, 1000, nothing)
cv2.createTrackbar('Vmax', WIN_CTRL, 1000, 1000, nothing)
cv2.createTrackbar('P2 (sens)', WIN_CTRL, 47, 100, nothing)
cv2.createTrackbar('MinDist', WIN_CTRL, 67, 200, nothing)
cv2.createTrackbar('MinRad', WIN_CTRL, 10, 100, nothing)
cv2.createTrackbar('MaxRad', WIN_CTRL, 60, 200, nothing)
cv2.createTrackbar('GaussBlur', WIN_CTRL, 11, 25, nothing)
cv2.createTrackbar('MedBlur', WIN_CTRL, 10, 25, nothing)
cv2.createTrackbar('MorphK', WIN_CTRL, 4, 15, nothing)
cv2.createTrackbar('MorphIter', WIN_CTRL, 1, 10, nothing)
cv2.createTrackbar('CannyLow', WIN_CTRL, 28, 255, nothing)
cv2.createTrackbar('CannyHigh', WIN_CTRL, 55, 255, nothing)
cv2.createTrackbar('MinComp%', WIN_CTRL, 30, 100, nothing)
cv2.createTrackbar('MaxComp%', WIN_CTRL, 100, 100, nothing)
cv2.createTrackbar('MaskX', WIN_CTRL, 428, w, nothing)
cv2.createTrackbar('MaskY', WIN_CTRL, 398, h, nothing)
cv2.createTrackbar('MaskRad', WIN_CTRL, 350, max(h, w), nothing)

# --- EXPLANATIONS ---
explanations = {
    'Frame': 'Select frame index',
    'Vmin': 'Lower intensity bound (contrast)',
    'Vmax': 'Upper intensity bound (contrast)',
    'P2 (sens)': 'Hough sensitivity (higher = stricter)',
    'MinDist': 'Min distance between circles',
    'MinRad': 'Minimum circle radius',
    'MaxRad': 'Maximum circle radius',
    'GaussBlur': 'Smooth noise (strong blur)',
    'MedBlur': 'Remove salt/pepper noise',
    'MorphK': 'Kernel size for cleanup',
    'MorphIter': 'Number of cleanup passes',
    'CannyLow': 'Edge detection low threshold',
    'CannyHigh': 'Edge detection high threshold',
    'MinComp%': 'Minimum arc completeness (%)',
    'MaxComp%': 'Maximum arc completeness (%)',
    'MaskX': 'Mask center X',
    'MaskY': 'Mask center Y',
    'MaskRad': 'Mask radius'
}

font = cv2.FONT_HERSHEY_SIMPLEX

while True:
    # --- READ VALUES ---
    values = {k: cv2.getTrackbarPos(k, WIN_CTRL) for k in explanations.keys()}

    f_idx = values['Frame']
    vmn, vmx = values['Vmin'], values['Vmax']
    p2 = max(1, values['P2 (sens)'])

    md, mr, mx = values['MinDist'], values['MinRad'], values['MaxRad']

    g_blur = values['GaussBlur']
    g_blur = g_blur if g_blur % 2 else g_blur + 1
    g_blur = max(1, g_blur)

    m_blur = values['MedBlur']
    m_blur = m_blur if m_blur % 2 else m_blur + 1
    m_blur = max(1, m_blur)

    k = max(1, values['MorphK'])
    kernel = np.ones((k, k), np.uint8)
    morph_iter = values['MorphIter']

    canny_low, canny_high = values['CannyLow'], values['CannyHigh']

    min_comp = values['MinComp%'] / 100.0
    max_comp = values['MaxComp%'] / 100.0

    mx_pos, my_pos, m_rad = values['MaskX'], values['MaskY'], values['MaskRad']

    raw_frame = all_frames[f_idx].astype(np.float32)

    # --- PROCESSING (UNCHANGED) ---
    ref_range = REF_VMAX - REF_VMIN
    img_ref_gray = (np.clip((raw_frame - REF_VMIN) / ref_range, 0, 1) * 255).astype(np.uint8)
    img_ref = cv2.cvtColor(img_ref_gray, cv2.COLOR_GRAY2BGR)

    tune_range = float(vmx - vmn) if vmx > vmn else 1.0
    img_tune = (np.clip((raw_frame - vmn) / tune_range, 0, 1) * 255).astype(np.uint8)

    mask = np.zeros_like(img_tune)
    cv2.circle(mask, (mx_pos, my_pos), m_rad, 255, -1)
    masked = cv2.bitwise_and(img_tune, mask)

    masked = cv2.equalizeHist(masked)

    if g_blur > 1:
        masked = cv2.GaussianBlur(masked, (g_blur, g_blur), 0)
    if m_blur > 1:
        masked = cv2.medianBlur(masked, m_blur)

    edges = cv2.Canny(masked, canny_low, canny_high)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=morph_iter)

    circles = cv2.HoughCircles(
        edges, cv2.HOUGH_GRADIENT, 1.2, md,
        param1=canny_high, param2=p2,
        minRadius=mr, maxRadius=mx
    )

    det_out = cv2.cvtColor(img_tune, cv2.COLOR_GRAY2BGR)
    proc_view = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)

    semi_count = 0

    if circles is not None:
        for cx, cy, cr in circles[0]:
            pts = 0
            for angle in range(0, 360, 15):
                px = int(cx + cr * np.cos(np.radians(angle)))
                py = int(cy + cr * np.sin(np.radians(angle)))

                if 0 <= px < w and 0 <= py < h:
                    if edges[py, px] > 0:
                        pts += 1

            comp = pts / 24
            if min_comp <= comp <= max_comp:
                semi_count += 1
                ix, iy, ir = np.uint16(np.around([cx, cy, cr]))

                cv2.circle(det_out, (ix, iy), ir, (0, 0, 255), 2)
                cv2.circle(det_out, (ix, iy), 3, (255, 255, 0), -1)

                cv2.circle(img_ref, (ix, iy), 3, (255, 255, 0), -1)
                cv2.circle(proc_view, (ix, iy), 3, (255, 255, 0), -1)

    cv2.putText(det_out, f"Detected: {semi_count}", (20, 40),
                font, 0.8, (0, 0, 255), 2)

    cv2.imshow(WIN_DET, det_out)
    cv2.imshow(WIN_REF, img_ref)
    cv2.imshow(WIN_PROC, proc_view)

    # --- DRAW HELP PANEL INSIDE CONTROL WINDOW ---
    help_img = np.zeros((900, 600, 3), dtype=np.uint8)

    y = 20
    for name, desc in explanations.items():
        val = values[name]
        text = f"{name:10} = {val:4}  | {desc}"
        cv2.putText(help_img, text, (10, y), font, 0.45, (0, 255, 0), 1)
        y += 25

    cv2.imshow(WIN_CTRL, help_img)

    key = cv2.waitKey(1) & 0xFF

    if key == ord('c'):
        filename = f"frame_{f_idx}.png"
        cv2.imwrite(filename, det_out)
        print(f"[INFO] Saved {filename}")

    if key in [ord('q'), 27]:
        break

cv2.destroyAllWindows()