from PIL import Image

from google.genai import types

from app.genai_client import get_genai_client


class GenAIClientProxy:
    """Lazy proxy so `from app.llm.gemini import client` keeps working."""

    def __getattr__(self, name):
        return getattr(get_genai_client(), name)


client = GenAIClientProxy()


def generate_answer(
    prompt: str,
    image_paths: list = None
):
    client = get_genai_client()
    contents = [prompt]

    if image_paths:

        for path in image_paths[:5]:

            try:

                image = Image.open(path)

                contents.append(image)

            except Exception:
                pass

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",

        contents=contents,

        config=types.GenerateContentConfig(
            temperature=0.6,
            max_output_tokens=8192,
        ),
    )

    return response.text


def stream_answer(
    prompt: str,
    image_paths: list = None
):
    client = get_genai_client()
    contents = [prompt]

    if image_paths:

        for path in image_paths[:5]:

            try:

                image = Image.open(path)

                contents.append(image)

            except Exception:
                pass

    response = client.models.generate_content_stream(
        model="gemini-3.1-flash-lite",

        contents=contents,

        config=types.GenerateContentConfig(
            temperature=0.6,
            max_output_tokens=8192,
        ),
    )

    for chunk in response:

        if chunk.text:

            yield chunk.text


async def generate_answer_async(
    prompt: str,
    image_paths: list = None
):
    client = get_genai_client()
    contents = [prompt]

    if image_paths:
        for path in image_paths[:5]:
            try:
                image = Image.open(path)
                contents.append(image)
            except Exception:
                pass

    response = await client.aio.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=contents,
        config=types.GenerateContentConfig(
            temperature=0.6,
            max_output_tokens=8192,
        ),
    )

    return response.text


async def stream_answer_async(
    prompt: str,
    image_paths: list = None
):
    client = get_genai_client()
    contents = [prompt]

    if image_paths:
        for path in image_paths[:5]:
            try:
                image = Image.open(path)
                contents.append(image)
            except Exception:
                pass

    response = await client.aio.models.generate_content_stream(
        model="gemini-3.1-flash-lite",
        contents=contents,
        config=types.GenerateContentConfig(
            temperature=0.6,
            max_output_tokens=8192,
        ),
    )

    async for chunk in response:
        if chunk.text:
            yield chunk.text
