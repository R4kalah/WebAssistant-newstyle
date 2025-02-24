from openai import OpenAI
from dotenv import dotenv_values

# para imprimir en terminal escribir logger("%s","tu mensaje")
import logging

logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# OPENAI
env_values = dotenv_values(".env")
openaikey = env_values["OPENAI_API_KEY"]


# modelo de voz a texto
class voice2text:
    def __init__(self) -> None:
        self.openai_key = openaikey
        self.client = OpenAI(api_key=self.openai_key)

    def transcribe_audio_file(self, record_name):
        with open(record_name, "rb") as audio_file:
            transcript = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text",
                language="es",
            )
        logger.info(transcript)
        return transcript
