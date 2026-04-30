
import asyncio
import io
import imageio

from resources.decreased.process_frames import process_frames_unsafe

compilation_state = {
    "is_active": False,
    "processed_until_index": 0,
    "output_buffer": None,
    "writer": None,
    "lock": asyncio.Lock(),
    "latest_frame": {
        "index": -1,
        "timestamp": 0,
        "image": None
    }
}

in_memory_store = {
    "frames": [],
    "timestamps": [],
    "temperatures": [],
    "pressures": []
}

sequence_control = {
    "next_expected_index": 0,
    "last_received_index": 0,
    "reorder_buffer": {},
    "buffer_streak": 0 ,
    "skipped_chunks": 0
}


async def compile_video(data, output_path, fps=30):
    print('[INFO] Started compiling the video, might take a while')
    in_memory_store["frames"] = data['frames']
    in_memory_store["timestamps"] = data['timestamps']
    in_memory_store["temperatures"] = data['temperatures']
    in_memory_store["pressures"] = data['pressures']

    compilation_state["output_buffer"] = io.BytesIO()
    compilation_state["writer"] = imageio.get_writer(
        compilation_state["output_buffer"],
        format="mp4",
        fps=fps
    )
    compilation_state["is_active"] = True

    async with compilation_state['lock']:
        total_frames = len(in_memory_store["frames"])
        processed = compilation_state["processed_until_index"]

        # If some frames were not yet rendered, process them now
        if processed < total_frames:
            await process_frames_unsafe(compilation_state, in_memory_store, sequence_control, None)

        # Close the writer so the mp4 finalizes
        if compilation_state["writer"] is not None:
            compilation_state["writer"].close()
            compilation_state["writer"] = None
            compilation_state["is_active"] = False

        binary_content = compilation_state["output_buffer"].getvalue()

        with open(output_path, "wb") as f:
            f.write(binary_content)

        print(f"[VIDEO] Saved to {output_path}")