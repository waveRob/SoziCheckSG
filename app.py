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

from assets.auxiliary_prompts import analysis_prompt, create_summary_prompt
from assets.auxiliary_functions import remove_emojis
from assets.auxiliary_classes import TextToSpeechCloud as TextToSpeech

GPT_MODEL_CHAT = "gpt-4o"
GPT_MODEL_ANALYSIS = "gpt-4o" # "gpt-5.1-2025-11-13"
GPT_MODEL_TRANSLATE = "gpt-3.5-turbo"

MAX_TOKEN_CHAT = 100
MAX_TOKEN_ANALYSIS = 200

LOGO_PATH = "./assets/logo_stgallen.png"

# --------
# Loading Scenarios
with open("prompts.yaml", "r", encoding="utf-8") as file:
    scenarios = yaml.safe_load(file)

# Dictionary with all languages
language_dict = { 
    "italian": ["it", "it-IT", "Italian", "🇮🇹"], 
    "german": ["de", "de-DE", "German", "🇩🇪"], 
    "portuguese": ["pt", "pt-PT", "Portuguese", "🇵🇹"], 
    "french": ["fr", "fr-FR", "French", "🇫🇷"], 
    "albanian": ["sq", "sq-AL", "Albanian", "🇽🇰"], 
    "spanish": ["es", "es-ES", "Spanish", "🇪🇸"], 
    "turkish": ["tr", "tr-TR", "Turkish", "🇹🇷"], 
    "macedonian": ["mk", "mk-MK", "Macedonian", "🇲🇰"], 
    "ukrainian": ["uk", "uk-UA", "Ukrainian", "🇺🇦"],
    "english":["en", "en-US", "English", "🇺🇸"], 
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


def initialize_scenario(selected_scenario, target_language, msg_history):

    context_text = scenarios[selected_scenario]["context"]
    role_text = scenarios[selected_scenario]["role"]

    # Sets up the situation and plays the introduction
    msg_history = [
        {"role": "system", "content": role_text},
        ]
    
    msg_history[0]["content"] = translator.translate(msg_history[0]["content"], dest=language_dict[target_language][0]).text

    if context_text and target_language != "german":
        context_text = gpt_translate(context_text, "german", target_language)

    return msg_history, context_text

def conv_preview_recording(file_path, target_language):
    if file_path is not None:
        rec_text = audio2text(file_path, language_dict[target_language][1])
    else:
        rec_text = ""
    return rec_text

def main(preview_text, msg_history, tts_instance):
    # Main function for the chatbot. It takes the preview text and the message history and 
    # returns the chat history, the audio player and the message history
    
    # Converting the audio message to text
    message = preview_text
    msg_history.append({"role": "user", "content":message})

    # Generating a response from the bot using the conversation history
    respons = text2bot(msg_history, max_length=MAX_TOKEN_CHAT)
    msg_history.append({"role": "assistant", "content":respons})

    # Converting bot's text response to audio speech
    audio_player = None
    if tts_instance is not None:
        audio_player, _ = tts_instance.create_audio(respons)
    else:
        print("Warning: TextToSpeech instance not initialized before calling main().")

    # Creating a list of tuples, each containing a user's message and corresponding bot's response
    msg_chat = [(msg_history[i]["content"], msg_history[i+1]["content"]) for i in range(1, len(msg_history)-1, 2)]
    return msg_chat, audio_player, None, None, msg_history

def setup_main(target_language, selected_scenario, def_usr_scenario, msg_history):
    global scenarios

    # Insert the user defined scenario if selected
    if selected_scenario == "User Defined Scenario":
        scenarios["User Defined Scenario"]["role"] = def_usr_scenario

    # Initialize Text to Speech
    tts_instance = TextToSpeech(language_dict, target_language)

    # Initialize the scenario and play the introduction
    init_msg_history, context_promt = initialize_scenario(selected_scenario, target_language, msg_history)
    msg_history = init_msg_history.copy()

    if context_promt:
        audio_player, duration = tts_instance.create_audio(context_promt)
    else:
        audio_player, duration = None, 0.0

    return audio_player, duration, context_promt, msg_history, tts_instance

def conversation_concluded(chat_history, max_length=30):
    """Return True when the Sozialhilfe dialog already reached its final result."""
    if len(chat_history) <= 2:
        return False

    chat_text = "\n".join([
        f"{msg['role'].capitalize()}: {msg['content']}"
        for msg in chat_history[2:]
    ])

    messages_analysis = [
        {
            "role": "system",
            "content": analysis_prompt,
        },
        {"role": "user", "content": chat_text},
    ]

    completion = client.chat.completions.create(
        model=GPT_MODEL_ANALYSIS,
        messages=messages_analysis,
        max_completion_tokens=max_length,
        temperature=0
    )

    answer = completion.choices[0].message.content.strip().lower()
    return answer.startswith("true")


def delay(seconds):
    sleep(seconds)
    return None

def toggle_start_button(target_lang, scenario):
    # Button is only clickable if BOTH are selected
    if target_lang and scenario:
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
        canvas.drawImage( doc.logo_path, 1 * cm, A4[1] - 3 * cm, width=3 * cm, height=3 * cm, preserveAspectRatio=True, mask="auto")

    
    # Header line
    canvas.line(1 * cm, A4[1] - 3.2 * cm, A4[0] - 1 * cm, A4[1] - 3.2 * cm)

    canvas.restoreState()

def create_summary(chat_history):
    chat_text = "\n".join([
        f"{msg['role'].capitalize()}: {msg['content']}"
        for msg in chat_history[1:]
    ])

    messages_summary = [
        {
            "role": "system",
            "content": create_summary_prompt
        },
        {
            "role": "user",
            "content": chat_text
        },
    ]

    completion = client.chat.completions.create(
        model=GPT_MODEL_ANALYSIS,
        messages=messages_summary,
        max_completion_tokens=200,
        temperature=0.2
    )

    return completion.choices[0].message.content.strip()


def create_analysis_file(msg_history, target_language, logo_path=LOGO_PATH):
    
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

    flow.append(Paragraph(f"<b>Exportdatum:</b> {timestamp}", styles['Normal']))
    flow.append(Spacer(1, 12))

    flow.append(Paragraph("<b>Sozialhilfe-Check St.Gallen</b>", styles['Heading2']))
    flow.append(Spacer(1, 12))

    flow.append(Paragraph("<b>DEUTSCH</b>", styles['Heading3']))
    flow.append(Paragraph("<b>Übersicht:</b>"))
    flow.append(Spacer(1, 8))
    summary = create_summary(msg_history)
    for line in summary.split("\n"):
        if line.strip():
            flow.append(Paragraph(line.strip(), styles["Normal"]))
            flow.append(Spacer(1, 4))

    flow.append(Spacer(1, 12))
    flow.append(Spacer(1, 12))
    for msg in msg_history[2:]:
        text = remove_emojis(msg["content"]).replace("\n", "<br/>")
        if target_language != "german":
            text = gpt_translate(text, target_language, "german")
        if msg["role"] == "user":
            flow.append(Paragraph(f"<b>Beantragende:r:</b> {text}", user_style))
        else:
            flow.append(Paragraph(f"<b>Sozi-Bot:</b> {text}", assistant_style))
    flow.append(Spacer(1, 12))
    if target_language != 'german':
        flow.append(Paragraph(f"<b>{target_language.capitalize()}</b>", styles['Heading3']))
        for msg in msg_history[2:]:
            text = remove_emojis(msg["content"]).replace("\n", "<br/>")
            if msg["role"] == "user":
                flow.append(Paragraph(f"<b>Beantragende:r:</b> {text}", user_style))
            else:
                flow.append(Paragraph(f"<b>Sozi-Bot:</b> {text}", assistant_style))
        flow.append(Spacer(1, 12))

    # Build with custom header/footer for each page
    doc.build(flow,
              onFirstPage=add_header_and_page_number,
              onLaterPages=add_header_and_page_number)

    return path

def update_analysis_visibility(chat_history, target_language):
    """Return a UI update that toggles the analysis download visibility."""
    if conversation_concluded(chat_history):
        path = create_analysis_file(chat_history, target_language, logo_path=LOGO_PATH)
        return gr.update(value=path, visible=True)
    else:
        return gr.update(visible=False)

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

def change_tab(id):
    return gr.Tabs(selected=id)

# Choices format for radio button
radio_choices = [
    (f"{v[3]} {v[2]}", key) 
    for key, v in language_dict.items()
]
theme = gr.themes.Soft(
    primary_hue="gray",
    secondary_hue="red",
    font=["Helvetica", "system-ui", "sans-serif"],
)

with gr.Blocks(theme=theme) as app:
    gr.Image(LOGO_PATH, show_label=False, container=False, width=10, show_download_button=False, show_fullscreen_button=False, show_share_button=False)

    with gr.Tabs() as tabs:

        # --------------- INTRODUCTION TAB ---------------
        with gr.TabItem("▶️ Start", id=0):
            gr.Markdown("### Willkommen zum Sozialhilfe-Check!")
            
            with gr.Row():
                    setup_target_language_rad = gr.Radio(radio_choices, interactive=True, label="Your Language",)
            setup_scenario_rad = gr.Radio(list(scenarios.keys()), interactive=True, label="Scenarios", value="Social hilfe check", visible=False)
            with gr.Row():
                setup_usr_scenario_text = gr.Textbox(visible=False, interactive=True, label="User definded scenario", lines=8, scale=5)
                setup_usr_scenario_file = gr.File(visible=False, interactive=True, scale=1, file_types=[".txt"])

            with gr.Row():
                setup_intr_text = gr.Textbox(interactive=False, label="Introduction", lines=3, max_lines=30)

            with gr.Row():
                setup_intr_btn = gr.Button("▶️ Start", variant="primary", interactive=False)

        # --------------- CONVERSATION TAB ---------------
        with gr.TabItem("🗣️ Sozialhilfe-Check", id=1):
            with gr.Group():
                chatbot = gr.Chatbot(show_share_button=False)
                conv_preview_text = gr.Textbox(placeholder="edit me", interactive=True, label="Preview", container=False, lines=2, submit_btn=True)
            with gr.Row():
                conv_file_path = gr.Audio(sources="microphone", interactive=False, type="filepath", label="🎙️ Record")
            with gr.Row():
                conv_clear_btn = gr.Button("🗑️ Clear", interactive=False)

        # --------------- ANALYSIS TAB ---------------
            analysis_download_file = gr.File(visible=False, label="⬇️ Download analysis")


    # General
    html = gr.HTML()
    msg_history = gr.State([])
    tts_state = gr.State(None)
    speach_duration = gr.Number(0.0, visible=False)


    # Introduction tab
    setup_target_language_rad.change(fn=toggle_start_button, inputs=[setup_target_language_rad, setup_scenario_rad], outputs=setup_intr_btn)
    setup_scenario_rad.change(fn=toggle_start_button, inputs=[setup_target_language_rad, setup_scenario_rad], outputs=setup_intr_btn)
    setup_scenario_rad.change(fn=toggle_user_scenario_interface, inputs=setup_scenario_rad, outputs=[setup_usr_scenario_text, setup_usr_scenario_file])
    setup_usr_scenario_file.change(fn=load_user_scenario_from_file, inputs=setup_usr_scenario_file, outputs=setup_usr_scenario_text)
    setup_intr_btn.click(lambda: gr.update(visible=False), inputs=None, outputs=setup_intr_btn).then(lambda: [gr.update(interactive=False)]*4, inputs=None, outputs=[setup_target_language_rad, setup_scenario_rad, setup_usr_scenario_text, setup_usr_scenario_file]).then(fn=lambda: [gr.update(interactive=True)]*2, inputs=None, outputs=[conv_file_path, conv_clear_btn]).then(fn=setup_main, inputs=[setup_target_language_rad, setup_scenario_rad, setup_usr_scenario_text, msg_history], outputs=[html, speach_duration, setup_intr_text, msg_history, tts_state]).then(fn=delay, inputs=speach_duration, outputs=None).then(change_tab, gr.Number(1, visible=False), tabs)
    
    # Conversation tab
    conv_file_path.change(fn=conv_preview_recording, inputs=[conv_file_path, setup_target_language_rad], outputs=[conv_preview_text]).then(fn=lambda: gr.update(submit_btn=True, interactive=True), inputs=None, outputs=conv_preview_text)
    conv_preview_text.submit(fn=main, inputs=[conv_preview_text, msg_history, tts_state], outputs=[chatbot, html, conv_file_path, conv_preview_text, msg_history]).then(fn=update_analysis_visibility, inputs=[msg_history, setup_target_language_rad], outputs=analysis_download_file)
    conv_clear_btn.click(lambda : [None, None], inputs=None, outputs=[conv_file_path, conv_preview_text])


if __name__ == "__main__":
    app.launch(ssr_mode=False, share=True, debug=True)

