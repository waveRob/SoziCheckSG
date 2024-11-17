"""
Language Teacher App
Copyright (C) 2024 Robert Füllemann

This work is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License.
You may use this project for personal or educational purposes only.
For more details about the license, visit: https://creativecommons.org/licenses/by-nc/4.0/

For commercial use or inquiries, please contact: robert.fuellemann@gmail.com
"""


import gradio as gr
import speech_recognition as sr
import copy
from openai import OpenAI
import gtts
import os
from io import BytesIO
import base64
from googletrans import Translator
from time import time
import re
from dotenv import load_dotenv

GPT_MODEL = "gpt-4o"  # {"gpt-3.5-turbo", "gpt-4o-mini", "gpt-4o"} 

BEGINNER_DEF= "beginner (easy reader level 1-2)"
ADVANCED_DEF= "advanced (easy reader level 3-4)"

#--------
beginner_teacher = f"Your role is to play a language teacher. You are in a conversation on beginner level with your student. Hence only use simple language, easy reader level 1-2. Show interest and emotions in the conversation use emojis. Stay on the initial topic help the student to make progress!"
advanced_teacher = f"You are a language teacher on easy reader level 3-4 ude emojis. Stay on the initial topic help the student to make progress!"

beginner_scenarios = {"restaurant": "You're in a small village at a friendly, old restaurant. The people here are nice and the place is calm. You're going to order some food, so think about what you want to eat.",
           "present your house": "Your are inviting a friend to your house. You want to show them around and describe the rooms, the furniture and how are things positioned to each other.",
           "last vecations": "You are talking to a friend about your last vacation. You want to tell them about the place you visited, the things you did.",
           "plans for the weekend": "You are talking to a friend about your plans for the weekend. You want to tell them where you are going and what you are going to do."
           }

advanced_scenarios = {
    "restaurant": "You’re in a small, cozy restaurant in a village. The waiter smiles and hands you a menu. The smell of tasty food is in the air, and you decide what you’d like to eat. It’s a calm and friendly place.",
    "present your house": "Your friend visits your house, and you show them around. First, the living room with a comfy couch and a big window. Then, the kitchen, where you like to cook. You point out your favorite things in each room.",
    "last_vacation": "You tell your friend about your last vacation. You went to a place with beaches and clear blue water. You hiked, tried new food, and watched bright sunsets. You share happy memories from the trip.",
    "plans for the weekend": "You are talking to a friend about your plans for the weekend. You want to tell them what you are going to do and why you are looking forward to it."
    }


setup = {BEGINNER_DEF: {"teacher": beginner_teacher, "scenarios": beginner_scenarios},
         ADVANCED_DEF: {"teacher": advanced_teacher, "scenarios": advanced_scenarios}}    

# Dictionary with all languages
language_dict = {"swedish":["sv", "sv-SV"], "english":["en", "en-EN"], "german":["de", "de-DE"], "french":["fr", "fr-FR"], "spanish":["es", "es-ES"], "portugese(BR)":["pt", "pt-BR"], "hindi":["hi", "hi-IN"]}

#---- init ---- 
translator = Translator()
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) 
# --------

def audio2text(file_path,language):
    start = time()
    r = sr.Recognizer()
    # Use the context manager to ensure the file gets closed after processing
    with sr.AudioFile(file_path) as source:
        audio = r.record(source) # read the entire audio file

    rec_text = r.recognize_google(audio, language=language)
    end = time()
    print(f"Time audio2text: {end-start}")
    return rec_text

def text2bot(messages, max_length=100):
    start = time()
    completion = client.chat.completions.create(model=GPT_MODEL, messages=messages, max_tokens=max_length)
    answere = completion.choices[0].message.content
    end = time()
    print(f"Time text2bot: {end-start}")
    return answere

def text2speach(rec_text, language):
    start = time()
    # Make request to google to get synthesis
    rec_text_filtered = remove_emojis(rec_text)
    tts = gtts.gTTS(rec_text_filtered, lang=language)


    audio_bytes = BytesIO()
    tts.write_to_fp(audio_bytes)
    audio_bytes.seek(0)

    audio = base64.b64encode(audio_bytes.read()).decode("utf-8")
    audio_player = f'<audio src="data:audio/mpeg;base64,{audio}" controls autoplay></audio>'
    end = time()
    print(f"Time text2speach: {end-start}")
    return audio_player


# --------


def initialize_scenario(level, selected_scenario, target_language, msg_history):
    # Sets up the situation and plays the introduction
    msg_history = [{"role": "system", "content": setup[level]["teacher"]}, # check whats happening here
                {"role": "system", "content": setup[level]["scenarios"][selected_scenario]}]
    
    msg_history[0]["content"] = translator.translate(msg_history[0]["content"], dest=language_dict[target_language][0]).text
    msg_history[1]["content"] = translator.translate(msg_history[1]["content"], dest=language_dict[target_language][0]).text
    return msg_history

def conv_preview_recording(file_path, target_language):
    if file_path is not None:
        rec_text = audio2text(file_path, language_dict[target_language][1])
    else:
        rec_text = ""
    return rec_text

def trans_preview_recording(file_path, native_language):
    rec_text = audio2text(file_path, language_dict[native_language][1])
    return rec_text

def main(preview_text, target_language, msg_history):
    # Main function for the chatbot. It takes the preview text and the message history and 
    # returns the chat history, the audio player and the message history
    
    # Converting the audio message to text
    message = preview_text
    msg_history.append({"role": "user", "content":message})

    # Generating a response from the bot using the conversation history
    respons = text2bot(msg_history, max_length=50)
    msg_history.append({"role": "assistant", "content":respons})

    # Converting bot's text response to audio speech
    audio_player = text2speach(respons, language_dict[target_language][0])

    # Creating a list of tuples, each containing a user's message and corresponding bot's response
    msg_chat = [(msg_history[i]["content"], msg_history[i+1]["content"]) for i in range(2, len(msg_history)-1, 2)]
    return msg_chat, audio_player, None, None, msg_history

def translator_main(preview_text, target_language):
    # Translates the preview text to the target language and returns the translated text and the audio

    # Translating the preview text
    translated_text = translator.translate(preview_text, dest=language_dict[target_language][0]).text

    # Converting bot's text response to speech in German
    audio_player = text2speach(translated_text, language_dict[target_language][0])
    return translated_text, audio_player

def reset_history(target_language, level, scenario, msg_history):
    # Clears the message history and chat
    msg_history = initialize_scenario(level, scenario, target_language, msg_history).copy()
    return None, msg_history

def setup_main(target_language, level, scenario, msg_history):
    # Initialize the scenario and play the introduction
    init_msg = initialize_scenario(level, scenario, target_language, msg_history).copy()

    msg_history = init_msg.copy()
    intr_text = init_msg[1]["content"]
    audio_player = text2speach(intr_text, language_dict[target_language][0])

    return audio_player, intr_text, msg_history

def trans_chat(native_language, trans_state ,msg_history):
    # Translates the chat history and returns the translated chat history and the translation state
    trans_state = not trans_state
    if trans_state:
        trans_msg_history = copy.deepcopy(msg_history)
        for i in range(2, len(msg_history)-1, 2):
            trans_msg_history[i]["content"] = translator.translate(msg_history[i]["content"], dest=language_dict[native_language][0]).text
            trans_msg_history[i+1]["content"] = translator.translate(msg_history[i+1]["content"], dest=language_dict[native_language][0]).text
            msg_chat = [(trans_msg_history[i]["content"], trans_msg_history[i+1]["content"]) for i in range(2, len(trans_msg_history)-1, 2)]
    else:
        msg_chat = [(msg_history[i]["content"], msg_history[i+1]["content"]) for i in range(2, len(msg_history)-1, 2)]

    return msg_chat, trans_state, msg_history

def propose_answer(target_language, native_language, msg_history):
    # Proposes an answer to the user

    for i in range(2, len(msg_history)-1, 2):
        switched_msg_history = copy.deepcopy(msg_history)
        switched_msg_history[i]["role"] = 'assistant'
        switched_msg_history[i+1]["role"] = 'user'

    # Generating a response from the bot using the conversation history
    response_target_lang = text2bot(switched_msg_history,max_length=100)

    # Translating the text
    response_native_lang = translator.translate(response_target_lang, dest=language_dict[native_language][0]).text

    # Converting bot's text response to speech
    audio_player = text2speach(response_target_lang,language_dict[target_language][0])

    return response_target_lang, response_native_lang, audio_player

def remove_emojis(text):
    # Emoji pattern covering most emojis
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # Emoticons
        "\U0001F300-\U0001F5FF"  # Symbols & Pictographs
        "\U0001F680-\U0001F6FF"  # Transport & Map Symbols
        "\U0001F700-\U0001F77F"  # Alchemical Symbols
        "\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
        "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
        "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        "\U0001FA00-\U0001FA6F"  # Chess Symbols
        "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
        "\U00002600-\U000026FF"  # Miscellaneous Symbols (includes weather symbols, hearts, stars, etc.)
        "\U00002700-\U000027BF"  # Dingbats
        "\U000024C2-\U0001F251"  # Enclosed characters
        "]+",
        flags=re.UNICODE
    )
    # Substitute matched emojis with an empty string
    return emoji_pattern.sub(r'', text)

with gr.Blocks() as app:
    gr.Markdown("# LOQUI")

    with gr.Tab("Introduction"):
        gr.Markdown("### Welcome!")
        gr.Markdown("Loqui is an interactive language tool designed for you to practice your active and passive language abilities. To get started, select level, language and scenario, confirm with 'Play Introduction'. Then continue with the 'Conversation' tab above.")
        with gr.Row():
            with gr.Column():
                setup_level_rad = gr.Radio([BEGINNER_DEF, ADVANCED_DEF], label="Level")
            with gr.Column():
                with gr.Row():
                    setup_target_language_rad = gr.Radio(list(language_dict.keys()), label="Target-Language")
                    setup_native_language_rad = gr.Radio(list(language_dict.keys()), label="Native-Language")
        setup_scenario_rad = gr.Radio(list(beginner_scenarios.keys()), label="Scenarios")
        setup_intr_btn = gr.Button("Play Introduction")
        setup_intr_text = gr.Textbox(placeholder="Introduction...",interactive=False)
        
    with gr.Tab("Conversation"):
        chatbot = gr.Chatbot()
        with gr.Row():
            trans_chat_btn = gr.Button("Translate Chat")
        with gr.Row():
            conv_preview_text = gr.Textbox(placeholder="Preview: modify me",interactive=True)
        with gr.Row():
            with gr.Column():
                conv_file_path = gr.Audio(sources="microphone", type="filepath", label="Record Audio")
            with gr.Column():
                conv_submit_btn = gr.Button("Submit")
            with gr.Column():
                conv_clear_btn = gr.Button("Clear")


        trans_tb_target = gr.Textbox(placeholder="Target language",interactive=False)
        trans_tb_native = gr.Textbox(placeholder="Native laguage: modify me",interactive=True)

        with gr.Row():
            with gr.Column():
                trans_file_path = gr.Audio(sources="microphone", type="filepath", label="Record Audio")
            with gr.Column():
                trans_submit_btn = gr.Button("Translate Audio")
            with gr.Column():
                trans_clear_btn = gr.Button("Clear")
        with gr.Row():
            trans_propose_btn = gr.Button("Proposal")

        conv_reset_btn = gr.Button("Reset Conversation")

    # General
    html = gr.HTML()
    state = gr.State([])
    trans_state = gr.State(False)


    # Introduction tab
    setup_intr_btn.click(fn=setup_main, inputs=[setup_target_language_rad, setup_level_rad, setup_scenario_rad, state], outputs=[html, setup_intr_text, state])
    
    # Conversation tab
    conv_file_path.change(fn=conv_preview_recording, inputs=[conv_file_path, setup_target_language_rad], outputs=[conv_preview_text])
    conv_submit_btn.click(fn=main, inputs=[conv_preview_text, setup_target_language_rad, state], outputs=[chatbot, html, conv_file_path, conv_preview_text, state])
    conv_clear_btn.click(lambda : [None, None], inputs=None, outputs=[conv_file_path, conv_preview_text])
    conv_reset_btn.click(fn=reset_history, inputs=[setup_target_language_rad, setup_level_rad, setup_scenario_rad, state], outputs=[chatbot, state])

    # Help tab
    trans_file_path.change(fn=trans_preview_recording, inputs=[trans_file_path, setup_native_language_rad], outputs=[trans_tb_native])
    trans_submit_btn.click(fn=translator_main, inputs=[trans_tb_native, setup_target_language_rad], outputs=[trans_tb_target, html])
    trans_clear_btn.click(lambda : [None, None, None], None, [trans_file_path, trans_tb_native, trans_tb_target])
    trans_chat_btn.click(fn=trans_chat, inputs=[setup_native_language_rad, trans_state ,state], outputs=[chatbot, trans_state, state])
    trans_propose_btn.click(fn= propose_answer,inputs=[setup_target_language_rad, setup_native_language_rad, state], outputs=[trans_tb_target, trans_tb_native, html])

if __name__ == "__main__":
    app.launch()
