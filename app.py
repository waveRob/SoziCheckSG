"""
Language Teacher App
Copyright (C) 2024 Robert Füllemann
This work is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License.
You may use this project for personal or educational purposes only.
For more details about the license, visit: https://creativecommons.org/licenses/by-nc/4.0/
For commercial use or inquiries, please contact: robert.fuellemann@gmail.com
"""

import os
import gradio as gr
import speech_recognition as sr
import copy
from openai import OpenAI
from googletrans import Translator
from time import time
from time import sleep
from dotenv import load_dotenv
import yaml
import tempfile
from datetime import datetime

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_LEFT

from assets.auxiliary_prompts import prompt_beginner_teacher, prompt_advanced_teacher, prompt_analysis
from assets.auxiliary_functions import remove_emojis
from assets.auxiliary_classes import TextToSpeechCloud as TextToSpeech

GPT_MODEL_CHAT = "gpt-4o"
GPT_MODEL_ANALYSIS = "gpt-4o" # "gpt-5.1-2025-11-13"
GPT_MODEL_TRANSLATE = "gpt-3.5-turbo"

BEGINNER_DEF = "beginner (CEFR level A1)"
ADVANCED_DEF = "advanced (CEFR level B1)"

MAX_TOKEN_CHAT = 100
MAX_TOKEN_ANALYSIS = 200

LOGO_PATH = "./assets/logo_stgallen.png"

# --------
beginner_teacher = prompt_beginner_teacher(BEGINNER_DEF)
advanced_teacher = prompt_advanced_teacher(ADVANCED_DEF)

teacher_prompt = {BEGINNER_DEF:beginner_teacher, ADVANCED_DEF: advanced_teacher}

# Loading Scenarios
with open("prompts.yaml", "r", encoding="utf-8") as file:
    scenarios = yaml.safe_load(file)

# Dictionary with all languages
language_dict = {
    "german":["de", "de-DE", "German","🇩🇪"],
    "english":["en", "en-US", "English", "🇺🇸"],
    "ukrainian": ["ua", "ua-UA", "Ukrainian", "🇺🇦"],
    "french":["fr", "fr-FR", "French", "🇫🇷"],
    "italian": ["it", "it-IT", "Italian", "🇮🇹"],
    "spanish":["es", "es-ES", "Spanish", "🇪🇸"],
    "portugese(BR)":["pt", "pt-BR", "Portugese", "🇧🇷"],
    "swedish":["sv", "sv-SV", "Swedish", "🇸🇪"],
    }

#---- init ---- 
translator = Translator()
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) 
# --------

def audio2text(file_path, language):
    start = time()
    r = sr.Recognizer()
    try:
        # Use the context manager to ensure the file gets closed after processing
        with sr.AudioFile(file_path) as source:
            audio = r.record(source) # read the entire audio file

        rec_text = r.recognize_google(audio, language=language)
        end = time()
        print(f"Time audio2text: {end-start}")
        return rec_text
    except Exception as e:
        print(f"Unexpected error in audio2text: {e}")
        return " "
        

def text2bot(messages, max_length):
    start = time()
    completion = client.chat.completions.create(model=GPT_MODEL_CHAT, messages=messages, max_completion_tokens=max_length)
    answere = completion.choices[0].message.content
    end = time()
    print(f"Time text2bot: {end-start}")
    return answere


def gpt_translate(text, text_language, target_language):
    messages = [
        {"role": "system", "content": "You are a translation assistant. Always respond with only the translated text."},
        {"role": "user", "content": f"Translate the following text from {text_language} to {target_language}. Only return the translated text, without any additional information:\n\n{text}"}
    ]

    completion = client.chat.completions.create(
        model=GPT_MODEL_TRANSLATE,
        messages=messages,
        max_tokens=MAX_TOKEN_ANALYSIS,
        temperature=0
    )

    return completion.choices[0].message.content.strip()


# --------


def initialize_scenario(level, selected_scenario, target_language, msg_history):

    teacher_text = teacher_prompt[level]
    context_text = scenarios[selected_scenario]["context"]
    role_text = scenarios[selected_scenario]["role"]

    # Sets up the situation and plays the introduction
    msg_history = [
        {"role": "system", "content": teacher_text},
        {"role": "system", "content": role_text},
        ]
    
    msg_history[0]["content"] = translator.translate(msg_history[0]["content"], dest=language_dict[target_language][0]).text
    msg_history[1]["content"] = translator.translate(msg_history[1]["content"], dest=language_dict[target_language][0]).text

    if context_text:
        context_text = gpt_translate(context_text, "english", target_language)

    return msg_history, context_text

def conv_preview_recording(file_path, target_language):
    if file_path is not None:
        rec_text = audio2text(file_path, language_dict[target_language][1])
    else:
        rec_text = ""
    return rec_text

def trans_preview_recording(file_path, native_language):
    if file_path is not None:
        rec_text = audio2text(file_path, language_dict[native_language][1])
    else:
        rec_text = ""
    return rec_text

def main(preview_text, msg_history):
    # Main function for the chatbot. It takes the preview text and the message history and 
    # returns the chat history, the audio player and the message history
    
    # Converting the audio message to text
    message = preview_text
    msg_history.append({"role": "user", "content":message})

    # Generating a response from the bot using the conversation history
    respons = text2bot(msg_history, max_length=MAX_TOKEN_CHAT)
    msg_history.append({"role": "assistant", "content":respons})

    # Converting bot's text response to audio speech
    audio_player, _ = tts.create_audio(respons)

    # Creating a list of tuples, each containing a user's message and corresponding bot's response
    msg_chat = [(msg_history[i]["content"], msg_history[i+1]["content"]) for i in range(2, len(msg_history)-1, 2)]
    return msg_chat, audio_player, None, None, msg_history

def translator_main(preview_text, native_language, target_language):
    # Translates the preview text to the target language and returns the translated text and the audio

    # Translating the preview text
    translated_text = gpt_translate(preview_text, native_language, target_language)

    # Converting bot's text response to speech in German
    audio_player, _ = tts.create_audio(translated_text)
    return translated_text, None, audio_player

def reset_history(target_language, level, selected_scenario, msg_history):
    # Clears the message history and chat
    new_msg_history, _ = initialize_scenario(level, selected_scenario, target_language, msg_history)
    msg_history = new_msg_history.copy()
    return None, msg_history

def setup_main(target_language, level, selected_scenario, def_usr_scenario, msg_history):
    global scenarios, tts

    # Insert the user defined scenario if selected
    if selected_scenario == "User Defined Scenario":
        scenarios["User Defined Scenario"]["role"] = def_usr_scenario

    # Initialize Text to Speech
    tts = TextToSpeech(language_dict, target_language)

    # Initialize the scenario and play the introduction
    init_msg_history, context_promt = initialize_scenario(level, selected_scenario, target_language, msg_history)
    msg_history = init_msg_history.copy()

    if context_promt:
        audio_player, duration = tts.create_audio(context_promt)
    else:
        audio_player, duration = None, 0.0

    return audio_player, duration, context_promt, msg_history

def trans_chat(target_language, native_language, trans_status, trans_msg_history, msg_history):

    trans_status = not trans_status  # Toggle translation state

    if trans_status:
        for i in range(2, len(msg_history) - 1, 2):
            # Check if message was already translated
            if i > len(trans_msg_history)-1:
                trans_msg_history.append({"role": "user", "content": gpt_translate(msg_history[i]["content"], target_language, native_language)})
            if i + 1 > len(trans_msg_history)-1:
                trans_msg_history.append({"role": "assistant", "content": gpt_translate(msg_history[i + 1]["content"], target_language, native_language)})

        # Create tuple pairs for translated chat
        msg_chat = [(trans_msg_history[i]["content"], trans_msg_history[i + 1]["content"]) for i in range(2, len(trans_msg_history) - 1, 2)]

    else:
        # Return original chat history
        msg_chat = [(msg_history[i]["content"], msg_history[i + 1]["content"]) for i in range(2, len(msg_history) - 1, 2)]

    return msg_chat, trans_msg_history, trans_status

def propose_answer(target_language, native_language, msg_history):
    # Proposes an answer to the user
    switched_msg_history = copy.deepcopy(msg_history[1:])
    for i in range(2, len(switched_msg_history)-1, 2):
        switched_msg_history[i]["role"] = 'assistant'
        switched_msg_history[i+1]["role"] = 'user'

    # Generating a response from the bot using the conversation history
    response_target_lang = text2bot(switched_msg_history, max_length=MAX_TOKEN_CHAT)

    # Translating the text
    response_native_lang = gpt_translate(response_target_lang, target_language, native_language)

    # Converting bot's text response to speech
    audio_player, _ = tts.create_audio(response_target_lang)

    return response_target_lang, response_native_lang, audio_player

def chat_analysis(target_language, native_language, language_level, chat_history, max_length=500):
    # Prompts in English
    english_prompt_analysis = prompt_analysis(target_language, language_level)

    # Translate prompts into the native language for the system message
    translated_prompt_analysis = translator.translate(
        english_prompt_analysis,
        dest=language_dict[native_language][0]
    ).text

    # Remove the first two messages (system messages)
    chat_only_history = chat_history[2:]

    # Turn chat into plain text
    chat_text = "\n".join([
        f"{msg['role'].capitalize()}: {msg['content']}"
        for msg in chat_only_history
    ])

    messages_analysis = [
        {"role": "system", "content": translated_prompt_analysis},
        {"role": "user", "content": chat_text},
    ]

    completion = client.chat.completions.create(
        model=GPT_MODEL_ANALYSIS,
        messages=messages_analysis,
        max_completion_tokens=max_length
    )
    answere = completion.choices[0].message.content

    return answere


def delay(seconds):
    sleep(seconds)
    return None

def toggle_start_button(level, target_lang, native_lang, scenario):
    # Button is only clickable if BOTH are selected
    if level and target_lang and native_lang and scenario:
        return gr.update(interactive=True)
    return gr.update(interactive=False)

def toggle_user_scenario_interface(scenario):
    # Interfaces are only visible if selected
    if scenario == "User Defined Scenario":
        return [gr.update(visible=True), gr.update(visible=True)]
    return [gr.update(visible=False), gr.update(visible=False)]

def add_header_and_page_number(canvas, doc):
    canvas.saveState()
    
    # Page number (bottom center)
    page_num = canvas.getPageNumber()
    canvas.setFont("Helvetica", 9)
    canvas.drawCentredString(A4[0] / 2, 1 * cm, f"Seite {page_num}")
    
    # Header logo (top left)
    if hasattr(doc, "logo_path") and doc.logo_path and os.path.exists(doc.logo_path):
        canvas.drawImage(doc.logo_path, 1 * cm, A4[1] - 2.5 * cm, width=40, height=40, preserveAspectRatio=True)
    
    # Header line
    canvas.line(1 * cm, A4[1] - 3 * cm, A4[0] - 1 * cm, A4[1] - 3 * cm)

    canvas.restoreState()


def create_analysis_file(scenario, target_language, native_language, msg_history, analysis_text, logo_path=LOGO_PATH):
    if not analysis_text:
        return gr.update(value=None, visible=False)
    
    timestamp = datetime.now().strftime("%Y-%m-%d")

    # Create temp PDF
    _, path = tempfile.mkstemp(suffix=".pdf")

    doc = SimpleDocTemplate(path, pagesize=A4,
                            topMargin=3.5 * cm, bottomMargin=2 * cm,
                            leftMargin=2 * cm, rightMargin=2 * cm)

    doc.logo_path = logo_path  # store for canvas callback

    styles = getSampleStyleSheet()
    user_style = ParagraphStyle(name="UserChat",parent=styles["Normal"],alignment=TA_LEFT,fontSize=10,leading=13,spaceAfter=5,leftIndent=0)
    assistant_style = ParagraphStyle(name="AssistantChat",parent=styles["Normal"],alignment=TA_LEFT,fontSize=10,leading=13,spaceAfter=5,leftIndent=25)
    flow = []
    
    flow.append(Paragraph(f"<b>Szenario:</b> {scenario}", styles['Normal']))
    flow.append(Paragraph(f"<b>Lernsprache:</b> {target_language}", styles['Normal']))
    flow.append(Paragraph(f"<b>Muttersprache:</b> {native_language}", styles['Normal']))
    flow.append(Paragraph(f"<b>Exportdatum:</b> {timestamp}", styles['Normal']))
    flow.append(Spacer(1, 12))

    flow.append(Paragraph("<b>Unterhaltung</b>", styles['Heading2']))
    for msg in msg_history[2:]:
        text = remove_emojis(msg["content"]).replace("\n", "<br/>")
        if msg["role"] == "user":
            flow.append(Paragraph(f"<b>Lernende:r:</b> {text}", user_style))
        else:
            flow.append(Paragraph(f"<b>Loqui:</b> {text}", assistant_style))
    flow.append(Spacer(1, 12))

    flow.append(Paragraph("<b>Analyse</b>", styles['Heading2']))
    flow.append(Paragraph(remove_emojis(analysis_text).replace("\n", "<br/>"), styles['Normal']))

    # Build with custom header/footer for each page
    doc.build(flow,
              onFirstPage=add_header_and_page_number,
              onLaterPages=add_header_and_page_number)

    return gr.update(value=path, visible=True)

def load_user_scenario_from_file(file):
    if file is None:
        return ""
    # Gradio File can be a tempfile or dict-like; handle both
    try:
        with open(file, "r", encoding="utf-8") as f:
            content = f.read()
        return content
    except Exception as e:
        print(f"Error reading file: {e}")
        return "Error reading file"
    
def display_waiting_text():
    return "### This may take a few seconds..."

def change_tab(id):
    return gr.Tabs(selected=id)

# Choices format for radio button
radio_choices = [
    (f"{v[3]} {v[2]}", key) 
    for key, v in language_dict.items()
]

with gr.Blocks(theme="soft") as app:
    gr.Image(LOGO_PATH, show_label=False, container=False, width=10, show_download_button=False, show_fullscreen_button=False, show_share_button=False)

    with gr.Tabs() as tabs:

        # --------------- INTRODUCTION TAB ---------------
        with gr.TabItem("▶️ Start", id=0):
            gr.Markdown("### Welcome!")
            gr.Markdown("Loqui is an interactive language learning tool that helps you practice both your active and passive language skills. To get started, select your level, language, and scenario, then confirm by clicking 'Start'.") 
            
            with gr.Row():
                with gr.Column():
                    setup_level_rad = gr.Radio([BEGINNER_DEF, ADVANCED_DEF], interactive=True, label="Level")
                with gr.Column():
                    with gr.Row():
                        setup_target_language_rad = gr.Radio(radio_choices, interactive=True, label="Target Language")
                        setup_native_language_rad = gr.Radio(radio_choices, interactive=True, label="Native Language")
            
            setup_scenario_rad = gr.Radio(list(scenarios.keys()), interactive=True, label="Scenarios")
            with gr.Row():
                setup_usr_scenario_text = gr.Textbox(visible=False, interactive=True, label="User definded scenario", lines=8, scale=5)
                setup_usr_scenario_file = gr.File(visible=False, interactive=True, scale=1, file_types=[".txt"])

            with gr.Row():
                setup_intr_text = gr.Textbox(interactive=False, label="Introduction", lines=3, max_lines=30)

            with gr.Row():
                setup_intr_btn = gr.Button("▶️ Start", variant="primary", interactive=False)

        # --------------- CONVERSATION TAB ---------------
        with gr.TabItem("🗣️ Conversation", id=1):
            gr.Markdown("## 🗣️ Conversation")
            with gr.Group():
                chatbot = gr.Chatbot(show_share_button=False)
                conv_preview_text = gr.Textbox(placeholder="edit me", interactive=False, label="Preview", container=False, lines=2, submit_btn=False)
            with gr.Row():
                with gr.Column():
                    conv_file_path = gr.Audio(sources="microphone", interactive=False, type="filepath", label="🎙️ Record")
                with gr.Column():
                    conv_chattrans_btn = gr.Button("🌐 Translate Chat", interactive=False)
                with gr.Column():
                    conv_clear_btn = gr.Button("🗑️ Clear", interactive=False)

            gr.Markdown("## 🎧 Translation")
            with gr.Group():
                trans_tb_target = gr.Textbox(interactive=False, container=False, lines=2, label="Target Language")
                trans_tb_native = gr.Textbox(placeholder="edit me", interactive=True, container=False, lines=2, label="Native Language", submit_btn=False)
            with gr.Row():
                with gr.Column():
                    trans_file_path = gr.Audio(sources="microphone", interactive=False, type="filepath", label="🎙️Record")
                with gr.Column():
                    trans_clear_btn = gr.Button("🗑️ Clear", interactive=False)
            with gr.Row():
                trans_propose_btn = gr.Button("💡 Suggest", interactive=False, visible=False)

            reset_btn = gr.Button("🔄 Reset Conversation", variant="stop", interactive=False, visible=False)

        # --------------- ANALYSIS TAB --------------- 
        with gr.TabItem("📊 Analysis", id=2):
            gr.Markdown("## 📊 Analysis")

            analysis_markdown = gr.Markdown()
            viz_word_dict_markdown = gr.Markdown()
            analysis_chat_btn = gr.Button("Generate Analysis", variant="primary", interactive=False)
            analysis_download_file = gr.File(visible=False, label="⬇️ Download analysis",)


    # General
    html = gr.HTML()
    msg_history = gr.State([])
    trans_msg_history = gr.State([{}, {}])
    trans_status = gr.State(False)
    speach_duration = gr.Number(0.0, visible=False)


    # Introduction tab
    setup_level_rad.change(fn=toggle_start_button, inputs=[setup_level_rad, setup_target_language_rad, setup_native_language_rad, setup_scenario_rad], outputs=setup_intr_btn)
    setup_target_language_rad.change(fn=toggle_start_button, inputs=[setup_level_rad, setup_target_language_rad, setup_native_language_rad, setup_scenario_rad], outputs=setup_intr_btn)
    setup_native_language_rad.change(fn=toggle_start_button, inputs=[setup_level_rad, setup_target_language_rad, setup_native_language_rad, setup_scenario_rad], outputs=setup_intr_btn)
    setup_scenario_rad.change(fn=toggle_start_button, inputs=[setup_level_rad, setup_target_language_rad, setup_native_language_rad, setup_scenario_rad], outputs=setup_intr_btn)
    setup_scenario_rad.change(fn=toggle_user_scenario_interface, inputs=setup_scenario_rad, outputs=[setup_usr_scenario_text, setup_usr_scenario_file])
    setup_usr_scenario_file.change(fn=load_user_scenario_from_file, inputs=setup_usr_scenario_file, outputs=setup_usr_scenario_text)
    setup_intr_btn.click(lambda: gr.update(visible=False), inputs=None, outputs=setup_intr_btn).then(lambda: [gr.update(interactive=False)]*6, inputs=None, outputs=[setup_level_rad, setup_target_language_rad, setup_native_language_rad, setup_scenario_rad, setup_usr_scenario_text, setup_usr_scenario_file]).then(fn=lambda: [gr.update(interactive=True)]*8, inputs=None, outputs=[conv_file_path, conv_chattrans_btn, conv_clear_btn, trans_file_path, trans_clear_btn, trans_propose_btn, reset_btn, analysis_chat_btn]).then(fn=setup_main, inputs=[setup_target_language_rad, setup_level_rad, setup_scenario_rad, setup_usr_scenario_text, msg_history], outputs=[html, speach_duration, setup_intr_text, msg_history]).then(fn=delay, inputs=speach_duration, outputs=None).then(change_tab, gr.Number(1, visible=False), tabs)
    
    # Conversation tab
    conv_file_path.change(fn=conv_preview_recording, inputs=[conv_file_path, setup_target_language_rad], outputs=[conv_preview_text]).then(fn=lambda: gr.update(submit_btn=True, interactive=True), inputs=None, outputs=conv_preview_text)
    conv_preview_text.submit(fn=main, inputs=[conv_preview_text, msg_history], outputs=[chatbot, html, conv_file_path, conv_preview_text, msg_history]).then(fn=delay, inputs=gr.Number(0.5, visible=False), outputs=None).then(fn=lambda: gr.update(submit_btn=False, interactive=False), inputs=None, outputs=conv_preview_text)
    conv_clear_btn.click(lambda : [None, None], inputs=None, outputs=[conv_file_path, conv_preview_text])

    # Help tab
    conv_chattrans_btn.click(fn=trans_chat, inputs=[setup_target_language_rad ,setup_native_language_rad, trans_status, trans_msg_history ,msg_history], outputs=[chatbot, trans_msg_history, trans_status])
    trans_file_path.change(fn=trans_preview_recording, inputs=[trans_file_path, setup_native_language_rad], outputs=[trans_tb_native])
    trans_tb_native.change(fn=lambda: gr.update(submit_btn=True), inputs=None, outputs=trans_tb_native)
    trans_tb_native.submit(fn=translator_main, inputs=[trans_tb_native, setup_native_language_rad, setup_target_language_rad], outputs=[trans_tb_target, trans_file_path, html]).then(fn=delay, inputs=gr.Number(0.5, visible=False), outputs=None).then(fn=lambda: gr.update(submit_btn=False), inputs=None, outputs=trans_tb_native)
    trans_clear_btn.click(lambda : [None, None, None], None, [trans_file_path, trans_tb_native, trans_tb_target])
    trans_propose_btn.click(fn= propose_answer,inputs=[setup_target_language_rad, setup_native_language_rad, msg_history], outputs=[trans_tb_target, trans_tb_native, html])
    reset_btn.click(fn=reset_history, inputs=[setup_target_language_rad, setup_level_rad, setup_scenario_rad, setup_usr_scenario_text, msg_history], outputs=[chatbot, msg_history])
    
    # Analysis tab
    analysis_chat_btn.click(lambda: gr.update(interactive=False, visible=False), inputs=None, outputs=analysis_chat_btn).then(fn=display_waiting_text, inputs=None, outputs=analysis_markdown).then(fn=chat_analysis, inputs=[setup_target_language_rad, setup_native_language_rad, setup_level_rad, msg_history], outputs=analysis_markdown).then(fn=create_analysis_file, inputs=[setup_scenario_rad, setup_target_language_rad, setup_native_language_rad, msg_history, analysis_markdown], outputs=analysis_download_file).then(fn=lambda: gr.update(interactive=False), inputs=None, outputs=conv_file_path)


if __name__ == "__main__":
    app.launch(ssr_mode=False, share=True, debug=True)

