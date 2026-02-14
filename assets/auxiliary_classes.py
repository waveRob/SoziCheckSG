import os
import json
import random
from io import BytesIO
import base64
import gtts
from google.cloud import texttospeech
from google.oauth2 import service_account
from pydub import AudioSegment
from time import time

from assets.auxiliary_functions import remove_emojis


class TextToSpeechCloud():
    def __init__(self, language_dict, target_language):
        self.language_dict = language_dict
        self.target_language = target_language
        self.lang_code = self.language_dict[self.target_language][1]
        self.tts_conf_state = {}
        self.tts_client = None

        self.initialize_client()
        self.initialize_voice()

    def initialize_client(self):
        creds_json = os.getenv("GOOGLE_CREDENTIALS").replace("\n", "\\n")
        google_api_key = json.loads(creds_json)
        credentials = service_account.Credentials.from_service_account_info(google_api_key)
        self.tts_client = texttospeech.TextToSpeechClient(credentials=credentials)

    def initialize_voice(self):
        voices = self.tts_client.list_voices().voices
        filtered_voices = [
            voice
            for voice in voices
            if self.lang_code in voice.language_codes and "WAVENET" in voice.name.upper()  # Premium voice: "STUDIO"
        ]  # Filter for standard voices
        selected_voice = random.choice(filtered_voices)

        self.tts_conf_state["voice"] = texttospeech.VoiceSelectionParams(
            language_code=self.lang_code, name=selected_voice.name
        )  # Use the selected voice name

        self.tts_conf_state["audo_config"] = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1,
            pitch=1,
        )
        print(
            f"Selected voice: {selected_voice.name}, pitch: {self.tts_conf_state['audo_config'].pitch}, speaking rate: {self.tts_conf_state['audo_config'].speaking_rate}"
        )
    
    def create_audio(self, rec_text):
        start = time()
        rec_text = remove_emojis(rec_text)
        synthesis_input = texttospeech.SynthesisInput(text=rec_text)
        response = self.tts_client.synthesize_speech(
            input=synthesis_input,
            voice=self.tts_conf_state["voice"],
            audio_config=self.tts_conf_state["audo_config"],
        )

        # Convert the audio content to a Base64 string
        audio_bytes = BytesIO(response.audio_content)
        
        audio_bytes.seek(0)
        # tts.write_to_fp(audio_bytes)
        mp3_data = audio_bytes.getvalue()

        # Create the audio player HTML
        audio = base64.b64encode(audio_bytes.read()).decode("utf-8")
        audio_player = f'<audio src="data:audio/mpeg;base64,{audio}" controls autoplay></audio>'


        # Get duration using pydub
        audio_segment = AudioSegment.from_file(BytesIO(mp3_data), format="mp3")
        duration = audio_segment.duration_seconds  # Duration in seconds
        print(f"Duration speach: {duration:.2f} seconds")

        print(f"Time text2speach_google: {time()-start}")

        return audio_player, duration


class TextToSpeechGTTS():
    def __init__(self, language_dict, target_language):
        self.language_dict = language_dict
        self.target_language = target_language

    def create_audio(self, rec_text):
        start = time()
        # Make request to google to get synthesis
        rec_text_filtered = remove_emojis(rec_text)
        tts = gtts.gTTS(rec_text_filtered, lang=self.language_dict[self.target_language][0])

        audio_bytes = BytesIO()
        tts.write_to_fp(audio_bytes)
        audio_bytes.seek(0)

        mp3_data = audio_bytes.getvalue()

        # Convert audio to base64
        audio = base64.b64encode(mp3_data).decode("utf-8")
        audio_player = f'<audio src="data:audio/mpeg;base64,{audio}" controls autoplay></audio>'
        
        # Get duration using pydub
        audio_segment = AudioSegment.from_file(BytesIO(mp3_data), format="mp3")
        duration = audio_segment.duration_seconds  # Duration in seconds
        print(f"Duration speach: {duration:.2f} seconds")
        
        end = time()
        print(f"Time text2speach: {end-start}")
        return audio_player, duration