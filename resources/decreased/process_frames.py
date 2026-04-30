import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import cv2
import concurrent.futures
import asyncio
import os

def count_bubbles(a, b, c):
    return None

MAX_PLOT_FRAMES = 300 # sliding graphs to not compress them

# ================================
# FRAME RENDER WORKER
# ================================
def render_frame_worker(
    i,
    timestamp,
    pixel_totals,
    derivative,
    temps,
    pressures,
    timestamps,
    img_norm,
    bubbles
):
    bubbles = None
    bubble_bgr = cv2.cvtColor((img_norm * 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
    
    if bubbles is not None:
        bubbles = np.uint16(np.around(bubbles))
        for pt in bubbles[0, :]:
            x, y, r = pt[0], pt[1], pt[2]
            # Draw thin red circle at edges
            cv2.circle(bubble_bgr, (x, y), r, (255, 0, 0), 1)
            # Draw red dot at center
            cv2.circle(bubble_bgr, (x, y), 2, (255, 0, 0), -1)

    # 1. Calculate the window bounds
    # If we have more frames than the limit, slide the window to the right
    start_idx = max(0, i - MAX_PLOT_FRAMES)
    end_idx = i + 1
    
    # 2. Slice all data for the current view
    view_ts = timestamps[start_idx:end_idx]
    view_pixel = pixel_totals[start_idx:end_idx]
    view_deriv = derivative[start_idx:end_idx]
    view_temps = temps[start_idx:end_idx]
    view_press = pressures[start_idx:end_idx]

    fig, (ax1, ax3, ax4) = plt.subplots(
        3, 1,
        figsize=(9, 12),
        dpi=80,
        gridspec_kw={"height_ratios": [1, 1, 1]},
    )

    # ----- Intensity & Derivative -----
    ax1.set_ylabel("Intensity", color="tab:blue")
    ax1.plot(view_ts, view_pixel, color="tab:blue", linewidth=1.5)

    ax2 = ax1.twinx()
    ax2.set_ylabel("d/dt", color="tab:green")
    ax2.plot(view_ts, view_deriv, color="tab:green", linewidth=1, alpha=0.5)

    ax1.axvline(x=timestamp, color="red", linestyle="--", linewidth=2)
    ax1.set_title(f"Frame {i} - Time: {timestamp:.2f}s (Showing last {len(view_ts)} frames)")

    # ----- Temperature Plot -----
    colors = ["#ff4d4d", "#ff9933", "#33cc33", "#3399ff", "#b700ff"]
    labels = ["TC 1 (center)", "TC 2", "TC 3", "TC 4 (outer)", "TC 5 (ambient)"]

    if view_temps.ndim == 1:
        view_temps = view_temps[:, np.newaxis]

    num_probes = view_temps.shape[1]
    for j in range(min(5, num_probes)):
        ax3.plot(
            view_ts,
            view_temps[:, j],
            color=colors[j],
            linewidth=1.2,
            label=labels[j] if j < len(labels) else f"TC {j+1}",
        )

    ax3.set_ylabel("Temp (°C)")
    ax3.axvline(x=timestamp, color="red", linestyle="--", linewidth=2)
    ax3.grid(True, alpha=0.3)
    ax3.legend(loc="upper left", fontsize="x-small", ncol=2)

    # ----- Pressure Plot -----
    ax4.plot(view_ts, view_press, color="#9400D3", linewidth=1.5)
    ax4.set_xlabel("Time (s)")
    ax4.set_ylabel("Pressure (mbar)")
    ax4.axvline(x=timestamp, color="red", linestyle="--", linewidth=2)
    ax4.grid(True, alpha=0.3)

    # 3. Force the X-axis to stay consistent in size
    # This prevents the "jitters" when labels change length
    if i > MAX_PLOT_FRAMES:
        ax4.set_xlim(view_ts[0], view_ts[-1])
        ax3.set_xlim(view_ts[0], view_ts[-1])
        ax1.set_xlim(view_ts[0], view_ts[-1])

    fig.tight_layout(pad=3.0)
    fig.subplots_adjust(hspace=0.4)

    # Render to BGR as before...
    fig.canvas.draw()
    plot_img = np.frombuffer(fig.canvas.buffer_rgba(), dtype=np.uint8)
    plot_img = plot_img.reshape(fig.canvas.get_width_height()[::-1] + (4,))
    plot_img = cv2.cvtColor(plot_img, cv2.COLOR_RGBA2BGR)
    plt.close(fig)

    bubble_h = bubble_bgr.shape[0]
    plot_h, plot_w = plot_img.shape[:2]
    new_plot_w = int(plot_w * (bubble_h / plot_h))
    plot_resized = cv2.resize(plot_img, (new_plot_w, bubble_h))

    return i, np.hstack((bubble_bgr, plot_resized))

# ================================
# BACKGROUND FRAME PROCESSOR
# ================================
async def process_frames(compilation_state, in_memory_store, sequence_control, img_lims):
    if compilation_state["lock"].locked():
        return
    async with compilation_state["lock"]:
        await process_frames_unsafe(compilation_state, in_memory_store, sequence_control, img_lims)

async def process_frames_unsafe(compilation_state, in_memory_store, sequence_control, img_lims):
    if not compilation_state["is_active"]:
        return
    start_idx = compilation_state["processed_until_index"]

    total_frames = min(
        len(in_memory_store["frames"]),
        len(in_memory_store["timestamps"]),
        len(in_memory_store["temperatures"]), 
        len(in_memory_store['pressures'])
    )

    if total_frames <= start_idx:
        return

    frames = in_memory_store["frames"]
    timestamps = np.array(in_memory_store["timestamps"][:total_frames])
    temps = np.array(in_memory_store["temperatures"][:total_frames])
    pressures = np.array(in_memory_store["pressures"][:total_frames])


    pixel_totals = np.stack(frames[:total_frames]).astype(np.float64).sum(axis=(1, 2)) / 1e8

    raw_diffs = np.diff(pixel_totals, prepend=pixel_totals[0]) * 30
    derivative = np.convolve(raw_diffs, np.ones(24)/24, mode="same")

    if img_lims:
        vmn, vmx = img_lims
    else:
        vmn, vmx = np.percentile(frames[:10], [2, 85])

    denom = float(vmx - vmn) if vmx > vmn else 1.0

    num_workers = min(64, os.cpu_count() or 4)
    loop = asyncio.get_event_loop()

    with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = []

        for i in range(start_idx, total_frames):
            frame = frames[i]
            img_norm = np.clip((frame.astype(np.float32) - vmn) / denom, 0, 1)
            bubbles = count_bubbles(frame, vmn, vmx)

            futures.append( 
                executor.submit(
                    render_frame_worker,
                    i,
                    timestamps[i],
                    pixel_totals,
                    derivative,
                    temps,
                    pressures,
                    timestamps,
                    img_norm,
                    bubbles
                )
            )

        def gather(futs):
            ordered = [None] * len(futs)
            for f in concurrent.futures.as_completed(futs):
                idx, frame = f.result()
                ordered[idx - start_idx] = (idx, frame) # Store tuple to keep track of index
            return ordered

        results = await loop.run_in_executor(None, gather, futures)

        for result in results:
            if result is not None:
                idx, frame = result
                
                # 1. Write to video file
                if compilation_state["writer"] is not None:
                    compilation_state["writer"].append_data(frame)


    compilation_state["processed_until_index"] = total_frames