import os
import queue
import threading
import time
from pathlib import Path

import gradio as gr

from chatmulate.api.chat import generate_chat
from chatmulate.ui.lang import get_system_language, LANGUAGES
from chatmulate.utils.env_loader import get_openai_api_key, set_openai_api_key, get_openai_api_models, \
    get_openai_api_model, set_openai_api_model

MAX_QUEUE_SIZE = 5
vo_queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)

running = False
image_buffer = []
chat_logs = []
system_logs = []

image_buffer_lock = threading.Lock()
chat_logs_lock = threading.Lock()
system_logs_lock = threading.Lock()


def capture_video_frame(frame):
    global image_buffer
    timestamp = time.time()
    with image_buffer_lock:
        image_buffer.append((timestamp, frame))
        cutoff = timestamp - 10
        image_buffer[:] = [(t, img) for (t, img) in image_buffer if t >= cutoff]


def capture_audio(audio_file):
    global image_buffer

    end_time = time.time()
    start_time = end_time - 10
    with image_buffer_lock:
        images_in_period = [img for (t, img) in image_buffer if start_time <= t <= end_time]

    if len(images_in_period) >= 3:
        n = len(images_in_period)
        idx1 = 0
        idx2 = n // 2
        idx3 = n - 1
        selected_images = [images_in_period[idx1], images_in_period[idx2], images_in_period[idx3]]

        if vo_queue.full():
            vo_queue.get()
        vo_queue.put({"images": selected_images, "audio": Path(audio_file)})
        with image_buffer_lock:
            image_buffer[:] = []
    else:
        with system_logs_lock:
            system_logs.append("[Skip] Insufficient images in last 10 seconds.")


def process_queue(user_prompt, chat_language, chat_count):
    global running, chat_logs, system_logs
    while running:
        if not vo_queue.empty():
            vo_data = vo_queue.get()
            images, audio_file = vo_data["images"], vo_data["audio"]

            try:
                generated_chat = generate_chat(user_prompt, chat_language, audio_file, images, chat_count)
                messages_to_add = []
                for message in generated_chat.messages:
                    messages_to_add.append(message)
                with chat_logs_lock:
                    chat_logs.extend(messages_to_add)
            except Exception as e:
                with system_logs_lock:
                    system_logs.append(f"[Failed to generate chat messages]\n{e}")

            try:
                os.remove(audio_file)
            except Exception as e:
                with system_logs_lock:
                    system_logs.append(f"[Failed to delete audio file]\n{e}")

        time.sleep(1)


def poll_chat_output():
    with chat_logs_lock:
        return "\n".join(chat_logs)


def poll_system_output():
    with system_logs_lock:
        return "\n".join(system_logs)


def toggle_chat(user_prompt, chat_language_key, chat_count):
    global running, chat_logs

    while vo_queue.qsize() > 1:
        vo_queue.get()

    running = not running

    if running:
        button_label = "Stop"
        with chat_logs_lock:
            chat_logs.clear()
        threading.Thread(
            target=process_queue,
            args=(user_prompt, LANGUAGES.get(chat_language_key), chat_count),
            daemon=True
        ).start()
    else:
        button_label = "Start"

    with chat_logs_lock:
        logs_str = "\n".join(chat_logs)
    return button_label, logs_str


def create_ui():
    with gr.Blocks() as chatmulate:
        gr.Markdown("# Chatmulate")
        with gr.Sidebar(position="left"):
            with gr.Row():
                api_key = gr.Textbox(value=get_openai_api_key(), label="OpenAI API Key", type="password")
                api_key.change(set_openai_api_key, inputs=api_key)

                api_model_dropdown = gr.Dropdown(
                    choices=[(m, m) for m in get_openai_api_models()],
                    value=get_openai_api_model(),
                    label="OpenAI API Model"
                )
                api_model_dropdown.change(fn=set_openai_api_model, inputs=api_model_dropdown)

                user_prompt_input = gr.Textbox(label="Chat Behavior Rules",
                                               placeholder="Describe how AI should behave...",
                                               lines=5, max_lines=5)

                language_dropdown = gr.Dropdown(
                    choices=[(v, k) for k, v in LANGUAGES.items()],
                    value=get_system_language(),
                    label="Chat Language"
                )

                chat_count_slider = gr.Slider(minimum=1, maximum=50, step=1, value=10, label="Number of Chat Messages")

                start_stop_button = gr.Button("Start")

        with gr.Row():
            with gr.Accordion("Input Devices"):
                video_input = gr.Image(sources=["webcam"], label="Video Input",
                                       mirror_webcam=False,
                                       webcam_constraints={
                                           "video": {
                                               "width": 1920,
                                               "height": 1080
                                           }
                                       })
                video_input.stream(capture_video_frame, video_input, stream_every=2)

                audio_input = gr.Audio(sources=["microphone"], type="filepath", label="Microphone Input")
                audio_input.stream(capture_audio, audio_input, stream_every=10)

        with gr.Row():
            with gr.Column():
                system_output = gr.Textbox(label="System Logs", lines=10, max_lines=10)
            with gr.Column():
                chat_output = gr.Textbox(label="Chat Messages", lines=10, max_lines=10)

        start_stop_button.click(
            toggle_chat,
            inputs=[user_prompt_input, language_dropdown, chat_count_slider],
            outputs=[start_stop_button, chat_output]
        )

        timer = gr.Timer(1)
        timer.tick(fn=poll_chat_output, outputs=chat_output)
        timer.tick(fn=poll_system_output, outputs=system_output)

    return chatmulate
