"""
Language Teacher App
Copyright (C) 2024 Robert Füllemann

This work is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License.
You may use this project for personal or educational purposes only.
For more details about the license, visit: https://creativecommons.org/licenses/by-nc/4.0/

For commercial use or inquiries, please contact: robert.fuellemann@gmail.com
"""

import os
import json
import re
import gradio as gr
import speech_recognition as sr
import copy
from openai import OpenAI
import gtts
from io import BytesIO
import base64
from googletrans import Translator
from time import time
from time import sleep
from dotenv import load_dotenv
from pydub import AudioSegment

GPT_MODEL = "gpt-4o"  # {"gpt-3.5-turbo", "gpt-4o-mini", "gpt-4o"} 

BEGINNER_DEF = "beginner (easy reader level 1-2)"
ADVANCED_DEF = "advanced (easy reader level 3-4)"

# --------
beginner_teacher = f"""You are a language teacher using language level {BEGINNER_DEF.split('(')[1].split(')')[0]}.  
Respond concisely with short **1 to 2 sentences**.
Encourage simple conversations, do not ask too many questions.  
Do not reveal unnecessary information unless the user asks directly.  
Use **emojis** when appropriate to make the conversation engaging!"""


advanced_teacher = f"""You are a language teacher using language level {ADVANCED_DEF.split('(')[1].split(')')[0]}.  
Respond in **2 to 3 sentences**, using more complex sentence structures and vocabulary.  
Encourage meaningful discussions but do not reveal details unless the user explicitly asks.  
Use **emojis** when appropriate to make the conversation engaging!"""

scenarios = {
    "Uppgift 1: Möt Sabrina": {
        "context": """  
        You are meeting your friend Sabrina in the city.  
        The two of you have known each other since childhood.  
        You decide to ask her about her job.  
        """,
        
        "role": """  
        You are now **Sabrina**, a 35-year-old nurse.  
        You are friendly and open but do not reveal details about yourself unless explicitly asked.  
        You like your job because you can help people, but you sometimes struggle with night shifts and paperwork.  
        You enjoy the cafeteria food and have time next Tuesday at 3 PM for a coffee with Maria.  
        Answer as **Sabrina** would, revealing details gradually, only when asked.

        You will be in conversation good old childhood friend.
        You are meeting this friend in the city.

        The task of the user will be to figure out things about you Sabrina, by asking questions.
        Use **emojis** where appropriate!
        """
    }
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


# --------


def initialize_scenario(level, selected_scenario, target_language, msg_history):

    teacher_prompt = setup[level]["teacher"]
    role_prompt    = setup[level]["scenarios"][selected_scenario]["role"]  # Role-play instruction
    context_prompt = setup[level]["scenarios"][selected_scenario]["context"]  # Only intro context

    
    # Sets up the situation and plays the introduction
    msg_history = [
        {"role": "system", "content": teacher_prompt},
        {"role": "system", "content": role_prompt},
        ]
    
    msg_history[0]["content"] = translator.translate(msg_history[0]["content"], dest=language_dict[target_language][0]).text
    msg_history[1]["content"] = translator.translate(msg_history[1]["content"], dest=language_dict[target_language][0]).text
    context_prompt = translator.translate(context_prompt, dest=language_dict[target_language][0]).text

    return msg_history, context_prompt

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
    audio_player, _ = text2speach(respons, language_dict[target_language][0])

    # Creating a list of tuples, each containing a user's message and corresponding bot's response
    msg_chat = [(msg_history[i]["content"], msg_history[i+1]["content"]) for i in range(2, len(msg_history)-1, 2)]
    return msg_chat, audio_player, None, None, msg_history

def translator_main(preview_text, target_language):
    # Translates the preview text to the target language and returns the translated text and the audio

    # Translating the preview text
    translated_text = translator.translate(preview_text, dest=language_dict[target_language][0]).text

    # Converting bot's text response to speech in German
    audio_player, _ = text2speach(translated_text, language_dict[target_language][0])
    return translated_text, audio_player

def reset_history(target_language, level, scenario, msg_history):
    # Clears the message history and chat
    new_msg_history, _ = initialize_scenario(level, scenario, target_language, msg_history)
    msg_history = new_msg_history.copy()
    return None, msg_history

def setup_main(target_language, level, scenario, msg_history):
    # Initialize the scenario and play the introduction
    init_msg_history, context_promt = initialize_scenario(level, scenario, target_language, msg_history)
    msg_history = init_msg_history.copy()

    audio_player, duration = text2speach(context_promt, language_dict[target_language][0])

    return audio_player, duration, context_promt, msg_history

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
    audio_player, _ = text2speach(response_target_lang,language_dict[target_language][0])

    return response_target_lang, response_native_lang, audio_player

# Function to generate chat analysis
def chat_analysis(target_language, native_language, chat_history, max_length=500):

    english_prompt = f"""
You are an expert in the {target_language} language and a language coach specializing in helping learners improve their {target_language}.

Your task is to analyze a user's spoken (casual) {target_language} conversation, focusing only on:
- **Grammar** (e.g., incorrect verb conjugation, word gender, possessive pronouns)
- **Word choice** (e.g., incorrect vocabulary usage)
- **Word order** (e.g., incorrect sentence structure)
- **Spelling errors** (e.g., typos or incorrect spellings)

**Ignore** any issues related to:
- Punctuation (periods, commas, question marks, etc.)
- Capitalization (upper/lower case usage)
- Missing sentence separations

Because the user is speaking casually and cannot set punctuation or capitalization, these are **not** considered mistakes for this evaluation.

---

### **Language Proficiency Rating (1-5)**
- **1**: Beginner: No knowledge of the language.
- **2**: Basic: Can answer simple questions, but the conversation leads nowhere or feels awkward.
- **3**: Basic Plus: Can hold a simple conversation however using short sentences and alot of mistakes.
- **4**: Intermediate: Can hold a natural conversation but makes frequent mistakes while using shorter sentences.
- **5**: Intermediate Plus: Can hold a natural conversation with frequent mistakes however builds longer sentences and uses diverse, vocabulary.

Be **generous** with this rating. If the user shows little to no grammatical or spelling errors, they should receive the highest rating excellent (6/5).

---

### **Output Requirements**
**Write your entire response in {native_language}.**  
If the conversation has **no mistakes** (apart from disregarded punctuation/capitalization issues), then simply **congratulate** the user with a short message. **Do not** list any mistakes in that case.

Otherwise, for each mistake:
1. **Highlight the incorrect phrase** using quotation marks.
2. **Provide a corrected version** of the phrase.
3. **Explain why it is incorrect** (e.g., grammatical rule, word choice, word order).
4. **Summarize common mistakes** made by the user at the end.

### ❌ Mistake: ...
✅ Correction: **...**
📝 *Mistake:* ...

After listing mistakes (if any), include:

## 🔍 **Short Overall Observations**

## 🤓 **Language proficiency**
Laguage score: x/5

Where x is your generous estimate of the user's language level based on the conversation.

Now, analyze the following chat conversation and provide your response entirely in {native_language}.  
Keep your answer concise but **detailed** enough to be **informative**.  
Try to keep your answer **under {max_length - 100} tokens**.
"""


    # Translate the prompt into the target language
    translated_prompt = translator.translate(english_prompt, dest=native_language).text


    # Remove the first two messages (system messages)
    chat_only_history = chat_history[2:]

    # Add chat history to the prompt
    chat_text = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in chat_only_history])

    messages = [
        {"role": "system", "content": translated_prompt},

        {"role": "user", "content": chat_text},
    ]

    completion = client.chat.completions.create(model=GPT_MODEL, messages=messages, max_tokens=max_length)
    answere = completion.choices[0].message.content

    return answere


def analyze_words(target_language, msg_history, word_dict):
    print("---> Analyzing words...")
    text = msg_history[-2]["content"]
    english_prompt = f"""
    Analyze the following spoken text and categorize words into nouns, verbs, and adjectives.
    Ignore missing punctuation and capitalization, as this is a transcription of a casual spoken conversation.
    Return words in their base form (lemma) to avoid duplicates.

    **Rules:**
    - **Nouns**: Include only proper nouns and common nouns. Exclude pronouns.
    - **Verbs**: Include action words and state-of-being verbs.
    - **Adjectives**: Include only descriptive words modifying nouns.
    - **DO NOT include** pronouns, adverbs, interjections, determiners, conjunctions, or prepositions.
    """
    prompt = translator.translate(english_prompt, dest=target_language).text

    prompt += f"""
    Text: "{text}"
    
    {{
        "nouns": ["word1", "word2"],
        "verbs": ["word3", "word4"],
        "adjectives": ["word5", "word6"]
    }}
    """

    messages = [
        {"role": "system", "content": "You are a linguistic expert analyzing spoken language."},
        {"role": "user", "content": prompt}
    ]

    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=200,
        temperature=0
    )

    # Extract response
    response_text = completion.choices[0].message.content
    print(text)
    print(response_text)

    try:
        parsed_response = json.loads(extract_json(response_text))

        # Append new words to existing sets
        word_dict["nouns"].update(parsed_response.get("nouns", []))
        word_dict["verbs"].update(parsed_response.get("verbs", []))
        word_dict["adjectives"].update(parsed_response.get("adjectives", []))
        print(word_dict)

    except json.JSONDecodeError:
        print ("Error, Invalid response from GPT model. Try again.")
    
    return word_dict

def extract_json(text):
    """Find and extract JSON from a GPT response using regex."""
    match = re.search(r'\{[\s\S]*\}', text)  # Find JSON structure
    if match:
        return match.group(0)  # Return only the JSON part
    return None
    
def viz_word_score(word_dict):
    """Generates a Markdown table with word counts and a star visualization."""
    
    # Table Header
    table = "| Category   | Count | Visualization |\n"
    table += "|------------|-------|---------------|\n"
    
    # Categories to process
    categories = ["nouns", "verbs", "adjectives"]
    
    for category in categories:
        count = len(word_dict.get(category, []))  # Get word count
        stars = "⭐️" * count if count > 0 else "—"  # Show stars or a dash if empty
        
        table += f"| {category.capitalize():<10} |  {count:^5} | {stars:<15} |\n"
    
    return table

def viz_word_dict(word_dict):
    """Visualizes the words used in each category with fun milestone emojis."""
    
    # Define milestone achievements
    milestones = {
        0:  "🌱 Starting out!      ",
        5:  "🎖️ Growing vocabulary!",
        10: "🏆 Impressive range!  ",
        15: "📯 Mastery achieved!  ",
    }

    # Start Markdown table
    table = "\n\n## 📊 Word Analysis Overview\n\n"
    table += "| Category   | Count | Words Used |\n"
    table += "|------------|-------|------------|\n"

    # Process each category
    for category in ["nouns", "verbs", "adjectives"]:
        words = sorted(word_dict.get(category, []))  # Sort words alphabetically for readability
        count = len(words)  # Get word count
        
        # Get milestone emoji (if applicable)
        milestone_emoji = ""
        for threshold, emoji in sorted(milestones.items()):
            if count >= threshold:
                milestone_emoji = emoji
        
        # Convert word list to string or show a dash if empty
        words_str = ", ".join(words) if words else "—"

        # Add row to table
        table += f"| {category.capitalize():<10} | {milestone_emoji} -> {count:^5} | {words_str} |\n"

    return table
    
def delay(seconds):
    sleep(seconds)
    return None

def display_waiting_text():
    return "### Detta kan ta några sekunder..."

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

def change_tab(id):
    return gr.Tabs(selected=id)

with gr.Blocks() as app:
    gr.Markdown("# Loqui för SFI")

    with gr.Tabs() as tabs:

        # --------------- INTRODUCTION TAB ---------------
        with gr.TabItem("Start", id=0):
            gr.Markdown("### Välkommen!")
            gr.Markdown("Loqui är ett interaktivt språkinlärningsverktyg som hjälper dig att öva både dina aktiva och passiva språkkunskaper. För att komma igång, välj nivå, språk och scenario och bekräfta med 'Start'.") 
            
            with gr.Row():
                with gr.Column():
                    setup_level_rad = gr.Radio([BEGINNER_DEF, ADVANCED_DEF], label="Nivå")
                with gr.Column():
                    with gr.Row():
                        setup_target_language_rad = gr.Radio(list(language_dict.keys())[0:-1], label="Målspråk")
                        setup_native_language_rad = gr.Radio(list(language_dict.keys())[1:], label="Modersmål")  
            setup_scenario_rad = gr.Radio(list(scenarios.keys()), label="Scenarion")

            with gr.Row():
                setup_intr_text = gr.Textbox(placeholder="Introduktion...", interactive=False)

            with gr.Row():
                setup_intr_btn = gr.Button("Start", variant="primary", interactive=True)

        # --------------- KONVERSATION TAB ---------------
        with gr.TabItem("Konversation", id=1):
            gr.Markdown("## Konversation")
            word_scor_markdown = gr.Markdown()
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

            gr.Markdown("## Översättning")
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

        # --------------- ANALYSIS TAB --------------- 
        with gr.TabItem("Analys", id=2):
            gr.Markdown("## Analys")

            analysis_markdown = gr.Markdown()
            viz_word_dict_markdown = gr.Markdown()
            analyze_chat_btn = gr.Button("Generera analys", variant="primary", interactive=True)

            



    # General
    html = gr.HTML()
    state = gr.State([])
    trans_state = gr.State(False)
    speach_duration = gr.Number(0.0, visible=False)
    word_dict = gr.State({
        "nouns": set(),
        "verbs": set(),
        "adjectives": set()
    })

 

    # Introduction tab
    setup_intr_btn.click(lambda: gr.update(interactive=False, visible=False), inputs=None, outputs=setup_intr_btn).then(fn=setup_main, inputs=[setup_target_language_rad, setup_level_rad, setup_scenario_rad, state], outputs=[html, speach_duration, setup_intr_text, state]).then(fn=delay, inputs=speach_duration, outputs=None).then(change_tab, gr.Number(1, visible=False), tabs)
    
    # Conversation tab
    conv_file_path.change(fn=conv_preview_recording, inputs=[conv_file_path, setup_target_language_rad], outputs=[conv_preview_text]).then(fn=lambda: gr.update(interactive=True), inputs=None, outputs=conv_submit_btn)
    conv_submit_btn.click(fn=main, inputs=[conv_preview_text, setup_target_language_rad, state], outputs=[chatbot, html, conv_file_path, conv_preview_text, state]).then(fn=delay, inputs=gr.Number(0.5, visible=False), outputs=None).then(fn=lambda: gr.update(interactive=False), inputs=None, outputs=conv_submit_btn).then(fn=analyze_words, inputs=[setup_target_language_rad, state, word_dict], outputs=[word_dict]).then(fn=viz_word_score, inputs=[word_dict], outputs=[word_scor_markdown])
    conv_clear_btn.click(lambda : [None, None], inputs=None, outputs=[conv_file_path, conv_preview_text])
    conv_reset_btn.click(fn=reset_history, inputs=[setup_target_language_rad, setup_level_rad, setup_scenario_rad, state], outputs=[chatbot, state])

    # Help tab
    trans_file_path.change(fn=trans_preview_recording, inputs=[trans_file_path, setup_native_language_rad], outputs=[trans_tb_native]).then(fn=lambda: gr.update(interactive=True), inputs=None, outputs=trans_submit_btn)
    trans_submit_btn.click(fn=translator_main, inputs=[trans_tb_native, setup_target_language_rad], outputs=[trans_tb_target, html]).then(fn=delay, inputs=gr.Number(0.5, visible=False), outputs=None).then(fn=lambda: gr.update(interactive=False), inputs=None, outputs=trans_submit_btn)
    trans_clear_btn.click(lambda : [None, None, None], None, [trans_file_path, trans_tb_native, trans_tb_target])
    trans_chat_btn.click(fn=trans_chat, inputs=[setup_native_language_rad, trans_state ,state], outputs=[chatbot, trans_state, state])
    trans_propose_btn.click(fn= propose_answer,inputs=[setup_target_language_rad, setup_native_language_rad, state], outputs=[trans_tb_target, trans_tb_native, html])

    # Analysis tab
    analyze_chat_btn.click(lambda: gr.update(interactive=False, visible=False), inputs=None, outputs=analyze_chat_btn).then(fn=display_waiting_text, inputs=None, outputs=analysis_markdown).then(fn=chat_analysis, inputs=[setup_target_language_rad, setup_native_language_rad, state], outputs=analysis_markdown).then(fn=viz_word_dict, inputs=[word_dict], outputs=[viz_word_dict_markdown])
if __name__ == "__main__":
    app.launch(ssr_mode=False)
