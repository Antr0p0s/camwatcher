import numpy as np
import cv2

# Global state
points = []
img_display = None
img_base = None

def mouse_callback(event, x, y, flags, param):
    global points, img_display, img_base
    if event == cv2.EVENT_LBUTTONDOWN:
        if len(points) == 0:
            # First click: Top-Left corner
            points.append((x, y))
            print(f"Top-left corner set at {x}, {y}. Click again for bottom-right.")
        elif len(points) >= 1:
            # Subsequent clicks: Update Bottom-Right corner
            if len(points) == 2:
                points[1] = (x, y)
            else:
                points.append((x, y))
            
        # Refresh display
        img_display = img_base.copy()
        
        # Draw the first point
        cv2.circle(img_display, points[0], 3, (0, 255, 0), -1)
        
        # Draw the Rectangle if we have two points
        if len(points) == 2:
            p1 = points[0]
            p2 = points[1]
            
            # Draw the selection box
            cv2.rectangle(img_display, p1, p2, (0, 0, 255), 2)
            cv2.putText(img_display, "Selection Active | 'r' to Reset | 'Enter' to Confirm", 
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
        cv2.imshow("Area Selector", img_display)

def get_manual_bubble_mask(camera): # Change input to camera object
    global points, img_display, img_base
    points = [] 

    cv2.namedWindow("Area Selector")
    cv2.setMouseCallback("Area Selector", mouse_callback)

    print("\n--- LIVE AREA SELECTOR ---")
    
    while True:
        # 1. GRAB LIVE FRAME
        latest_frame = camera.get_latest_frame()
        if not latest_frame is None:
            h_img, w_img = latest_frame.shape[:2]

            # 2. NORMALIZE LIVE LATEST_FRAME
            img_min, img_max = np.percentile(latest_frame, [1, 99])
            img_8bit = np.clip((latest_frame - img_min) / (max(1, img_max - img_min)) * 255, 0, 255).astype(np.uint8)
            # img_8bit = cv2.equalizeHist(img_8bit)
            img_base = cv2.cvtColor(img_8bit, cv2.COLOR_GRAY2BGR)
            
            
            # 3. DRAW OVERLAY ON LIVE IMAGE
            img_display = img_base.copy()
            if len(points) >= 1:
                cv2.circle(img_display, points[0], 3, (0, 255, 0), -1)
            if len(points) == 2:
                cv2.rectangle(img_display, points[0], points[1], (0, 0, 255), 2)
                cv2.putText(img_display, "Snapped Multi-16 Mode", (10, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            cv2.imshow("Area Selector", img_display)

        # 4. HANDLE KEYS
        key = cv2.waitKey(1) & 0xFF
        if key == ord('r'):
            points = []
        elif key == 13 or key == 32: # Enter or Space
            if len(points) == 2: break
        elif key == 27: # ESC
            cv2.destroyAllWindows()
            return None

    cv2.destroyAllWindows()
    
    # ... [Keep your snapping logic (points[0], points[1]) here at the end] ...
    # (Same snapping code as your original function)

    p1, p2 = points[0], points[1]
    y_min, y_max = sorted([p1[1], p2[1]])
    x_min, x_max = sorted([p1[0], p2[0]])

    # 1. Calculate raw width and height
    raw_w = x_max - x_min
    raw_h = y_max - y_min

    # 2. Round to nearest multiple of 16
    snap_w = round(raw_w / 16) * 16
    snap_h = round(raw_h / 16) * 16
    
    # Ensure they are at least 16 pixels
    snap_w = max(16, snap_w)
    snap_h = max(16, snap_h)

    # 3. Recalculate max coordinates based on snapped size
    # We expand/shrink from the top-left corner
    new_x_max = x_min + snap_w
    new_y_max = y_min + snap_h

    # 4. Final Safety: If snapping pushed us off the image, shift the whole box back
    if new_x_max > w_img:
        shift = new_x_max - w_img
        x_min -= shift
        new_x_max -= shift
    if new_y_max > h_img:
        shift = new_y_max - h_img
        y_min -= shift
        new_y_max -= shift

    # Keep coordinates positive
    x_min, y_min = max(0, x_min), max(0, y_min)

    print(f"Original: {raw_w}x{raw_h} -> Snapped: {snap_w}x{snap_h}")
    return (int(x_min), int(y_min), int(new_x_max), int(new_y_max)), (img_min, img_max)