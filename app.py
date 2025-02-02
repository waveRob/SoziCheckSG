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
from time import sleep
import re
from dotenv import load_dotenv

GPT_MODEL = "gpt-4o"  # {"gpt-3.5-turbo", "gpt-4o-mini", "gpt-4o"} 

BEGINNER_DEF = "beginner (easy reader level 1-2)"
ADVANCED_DEF = "advanced (easy reader level 3-4)"

# --------
beginner_teacher = f"""Your are a language teacher using language level {BEGINNER_DEF.split('(')[1].split(')')[0]} respond with 1 sentence max 2 sentences. You are stepping into the role of a person called Sabrina. Imagine Sabrina a 35 years old nurse. Sabrina 
is a friendly and open person. She is someone who likes here job because she can help people. She does not like about here job that she has sometimes night shifts. Sabrina has time next week on Tuesday at 3pm for a coffee with Maria. Your task is to answer the questions of Maria.
Stay in your role playing Sabrina, only reveal things from you that are directly asked, use emojis!"""

advanced_teacher = f"""Your are a language teacher using language level {ADVANCED_DEF.split('(')[1].split(')')[0]} respond with 2 sentences max 3 sentences. You are stepping into the role of a person called Sabrina. Imagine Sabrina, a 35-year-old nurse.  
Sabrina is a friendly and open person. She loves her job because she can help people and enjoys working closely with her colleagues as a team player. However, she dislikes that she sometimes has night shifts and finds paperwork frustrating.  
One thing she really enjoys is the food in the mensa, especially when they serve something warm and homemade-style.  
Sabrina has time next week on Tuesday at 3 PM for a coffee with Maria ☕.  
Your task is to answer Marias questions. Stay in your role playing Sabrina, only reveal things step by step about yourself that are directly asked. Use emojis!"""

scenarios = {
    "Uppgift 1: Möt Sabrina": "You are meeting your friend Sabrina in the city. you know each other from childhood. You ask her about her job.",
}


setup = {BEGINNER_DEF: {"teacher": beginner_teacher, "scenarios": scenarios},
         ADVANCED_DEF: {"teacher": advanced_teacher, "scenarios": scenarios}}    

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
    teacher_prompt = setup[level]["teacher"]
    role_prompt = setup[level]["scenarios"][selected_scenario]

    
    # Sets up the situation and plays the introduction
    msg_history = [
        {"role": "system", "content": teacher_prompt}, # check whats happening here
        {"role": "system", "content": role_prompt}
        ]
    
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

def delay():
    sleep(1)
    return None

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

    with gr.Tab("Introduktion"):
        gr.Markdown("### Välkommen!")
        gr.Markdown("Loqui är ett interaktivt språkinlärningsverktyg som hjälper dig att öva både dina aktiva och passiva språkkunskaper. För att komma igång, välj nivå, språk och scenario och bekräfta med 'Spela Introduktion'. Fortsätt sedan med fliken 'Konversation' ovan.")
        with gr.Row():
            with gr.Column():
                setup_level_rad = gr.Radio([BEGINNER_DEF, ADVANCED_DEF], label="Nivå")
            with gr.Column():
                with gr.Row():
                    setup_target_language_rad = gr.Radio([list(language_dict.keys())[0]], label="Målspråk")
                    setup_native_language_rad = gr.Radio(list(language_dict.keys()), label="Modersmål")
        setup_scenario_rad = gr.Radio(list(scenarios.keys()), label="Scenarion")
        setup_intr_btn = gr.Button("Spela Introduktion", variant="primary")
        setup_intr_text = gr.Textbox(placeholder="Introduktion...", interactive=False)
        
    with gr.Tab("Konversation"):
        chatbot = gr.Chatbot()
        with gr.Row():
            trans_chat_btn = gr.Button("Översätt Chatt")
        with gr.Row():
            conv_preview_text = gr.Textbox(placeholder="Förhandsgranskning: ändra mig", interactive=True)
        with gr.Row():
            with gr.Column():
                conv_file_path = gr.Audio(sources="microphone", type="filepath", label="Spela in ljud")
            with gr.Column():
                conv_submit_btn = gr.Button("Skicka", elem_id="conv-submit-btn", variant="primary", interactive=False)
            with gr.Column():
                conv_clear_btn = gr.Button("Rensa")

        trans_tb_target = gr.Textbox(placeholder="Målspråk", interactive=False)
        trans_tb_native = gr.Textbox(placeholder="Modersmål: ändra mig", interactive=True)

        with gr.Row():
            with gr.Column():
                trans_file_path = gr.Audio(sources="microphone", type="filepath", label="Spela in ljud")
            with gr.Column():
                trans_submit_btn = gr.Button("Översätt ljud", variant="primary", interactive=False)
            with gr.Column():
                trans_clear_btn = gr.Button("Rensa")
        with gr.Row():
            trans_propose_btn = gr.Button("Förslag")

        conv_reset_btn = gr.Button("Återställ konversation", variant="stop")

    # General
    html = gr.HTML()
    state = gr.State([])
    trans_state = gr.State(False)
 

    # Introduction tab
    setup_intr_btn.click(fn=setup_main, inputs=[setup_target_language_rad, setup_level_rad, setup_scenario_rad, state], outputs=[html, setup_intr_text, state])
    
    # Conversation tab
    conv_file_path.change(fn=conv_preview_recording, inputs=[conv_file_path, setup_target_language_rad], outputs=[conv_preview_text]).then(fn=lambda: gr.update(interactive=True), inputs=None, outputs=conv_submit_btn)
    conv_submit_btn.click(fn=main, inputs=[conv_preview_text, setup_target_language_rad, state], outputs=[chatbot, html, conv_file_path, conv_preview_text, state]).then(fn=delay, inputs=None, outputs=None).then(fn=lambda: gr.update(interactive=False), inputs=None, outputs=conv_submit_btn)
    conv_clear_btn.click(lambda : [None, None], inputs=None, outputs=[conv_file_path, conv_preview_text])
    conv_reset_btn.click(fn=reset_history, inputs=[setup_target_language_rad, setup_level_rad, setup_scenario_rad, state], outputs=[chatbot, state])

    # Help tab
    trans_file_path.change(fn=trans_preview_recording, inputs=[trans_file_path, setup_native_language_rad], outputs=[trans_tb_native]).then(fn=lambda: gr.update(interactive=True), inputs=None, outputs=trans_submit_btn)
    trans_submit_btn.click(fn=translator_main, inputs=[trans_tb_native, setup_target_language_rad], outputs=[trans_tb_target, html]).then(fn=delay, inputs=None, outputs=None).then(fn=lambda: gr.update(interactive=False), inputs=None, outputs=trans_submit_btn)
    trans_clear_btn.click(lambda : [None, None, None], None, [trans_file_path, trans_tb_native, trans_tb_target])
    trans_chat_btn.click(fn=trans_chat, inputs=[setup_native_language_rad, trans_state ,state], outputs=[chatbot, trans_state, state])
    trans_propose_btn.click(fn= propose_answer,inputs=[setup_target_language_rad, setup_native_language_rad, state], outputs=[trans_tb_target, trans_tb_native, html])

if __name__ == "__main__":
    app.launch()
