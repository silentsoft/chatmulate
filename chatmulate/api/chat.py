import base64
from io import BytesIO

from PIL import Image
from openai import OpenAI
from pydantic import BaseModel

from chatmulate.utils.env_loader import get_openai_api_key, get_openai_api_model, get_base_system_prompt


class GeneratedChat(BaseModel):
    messages: list[str]


def generate_chat(user_prompt, chat_language, audio_file, images, chat_count) -> GeneratedChat:
    client = OpenAI(api_key=get_openai_api_key())

    with open(audio_file, "rb") as f:
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
    transcription_text = transcription.text

    base64_images = []
    for image in images:
        bytes_image = BytesIO()
        Image.fromarray(image.astype("uint8")).save(bytes_image, "jpeg")
        base64_image = base64.b64encode(bytes_image.getvalue()).decode("utf-8")
        base64_images.append(base64_image)

    def generate_prompt():
        prompt = get_base_system_prompt()
        if user_prompt:
            prompt += f"\n\nAdditionally, follow the specific chat rules defined by the user:\n{user_prompt}"
        prompt += f"\n\nGenerate exactly {chat_count} messages in {chat_language}."
        return prompt

    system_prompt = generate_prompt()

    messages = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": system_prompt
                }
            ]
        },
        {
            "role": "user",
            "content": [
                           {
                               "type": "text",
                               "text": f"Transcription: {transcription_text}"
                           }
                       ] + [
                           {
                               "type": "image_url",
                               "image_url": {
                                   "url": f"data:image/jpeg;base64,{base64_image}"
                               }
                           } for base64_image in base64_images
                       ]
        }
    ]

    response = client.beta.chat.completions.parse(
        model=get_openai_api_model(),
        messages=messages,
        max_tokens=300,
        response_format=GeneratedChat
    )
    return response.choices[0].message.parsed
