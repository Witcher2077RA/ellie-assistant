# Ellie - a private, offline chat assistant.
# The brain: personality, memory, and the call to the local model (Ollama).
# Run this file for a chat in the terminal (type bye to stop), or run EllieDesktop.py for the window.

import json
import os
from datetime import datetime

import requests

URL = "http://localhost:11434"

# ---------- Settings ----------
# Your name goes in data/settings.json (created on first run), so it stays on your computer.
PREFERRED_MODEL = "gemma3:4b"   # used if installed, otherwise the first model in Ollama


def pick_model():
    try:
        installed = [m["name"] for m in requests.get(URL + "/api/tags", timeout=5).json()["models"]]
    except requests.exceptions.RequestException:
        return PREFERRED_MODEL
    if PREFERRED_MODEL in installed or not installed:
        return PREFERRED_MODEL
    return installed[0]


MODEL = pick_model()

# ---------- Memory: kept next to the code in the "data" folder (never uploaded) ----------
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = os.path.join(HERE, "data")
CHATS_FOLDER = os.path.join(DATA_FOLDER, "chats")
FACTS_FILE = os.path.join(DATA_FOLDER, "facts.md")
SUMMARY_FILE = os.path.join(DATA_FOLDER, "last_summary.md")
SETTINGS_FILE = os.path.join(DATA_FOLDER, "settings.json")

os.makedirs(CHATS_FOLDER, exist_ok=True)
if not os.path.exists(SETTINGS_FILE):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump({"user_name": ""}, f, indent=2)
try:
    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        YOUR_NAME = str(json.load(f).get("user_name", "")).strip()
except (OSError, ValueError):
    YOUR_NAME = ""
USER_NAME = YOUR_NAME or "the user"     # how Ellie refers to you in her instructions
SPEAKER = YOUR_NAME or "You"            # your label in saved transcripts
if not os.path.exists(FACTS_FILE):
    with open(FACTS_FILE, "w", encoding="utf-8") as f:
        f.write("# Facts for Ellie\n\nWrite one fact per line, starting with a dash.\n\n- \n")


def read_file(path):
    """Returns a file's text, or an empty string if it doesn't exist yet."""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""


def ask_model(message_list, temperature=0.7):
    """Sends messages to Ollama and returns the reply text."""
    response = requests.post(URL + "/api/chat", json={
        "model": MODEL,
        "messages": message_list,
        "stream": False,
        "options": {"temperature": temperature, "num_ctx": 8192},
    }, timeout=300)
    return response.json()["message"]["content"]


# ---------- Ellie's personality ----------
SYSTEM_PROMPT = f"""
You are Ellie, a friendly AI assistant that runs privately on {USER_NAME}'s own computer.
You help with projects, planning, learning, and everyday tasks.

Personality:
- Warm, upbeat, and clear. Encouraging without being over the top.
- Practical: when {USER_NAME} is stuck, suggest one small next step.
- Honest: if you don't know something, say so. Never make up facts.
- Only mention plans, projects, or things you've done if they're in your memory below or the user said them.
  You can't do anything between chats, so never claim you were busy with something.

How you talk:
- Like a normal, friendly person today: casual, everyday modern English, the way people actually speak.
  Contractions are fine ("I'm", "you'll", "let's").
- Never use old-fashioned, medieval, or poetic language (no thee, thou, thy, hast, doth, aye, verily, milord).
- Short paragraphs. Your replies are often read aloud, so keep them easy to listen to.
- Answer what was asked, without padding.
- Ask one question at a time when something is unclear.
- No emojis and no action text in asterisks.
"""

EXAMPLES = [
    {"role": "user", "content": "Hi Ellie, I'm back."},
    {"role": "assistant", "content": f"Welcome back{', ' + YOUR_NAME if YOUR_NAME else ''}. What are we working on today?"},
    {"role": "user", "content": "I didn't get much done today."},
    {"role": "assistant", "content": "That happens. What's the one thing you'd most like to move forward? "
                                     "Let's find a ten-minute first step for it."},
    {"role": "user", "content": "How do I save a file in Python?"},
    {"role": "assistant", "content": "Use open() in 'w' mode inside a with block: "
                                     "with open('notes.txt', 'w') as f: f.write('hello'). "
                                     "The with block closes the file for you."},
]


def memory_text():
    text = ""
    facts = read_file(FACTS_FILE)
    summary = read_file(SUMMARY_FILE)
    if facts:
        text += f"\n\nWhat you know about {USER_NAME}:\n" + facts
    if summary:
        text += f"\n\nSummary of your last conversation with {USER_NAME}:\n" + summary
    if not summary and len(facts.replace("-", "").split()) <= 6:
        text += (f"\n\nYou have no memory of {USER_NAME}'s projects or plans yet. "
                 "If asked what to work on, ask what's going on instead of guessing.")
    return text


def start_messages():
    """A fresh conversation: personality, memory, and example lines."""
    return [{"role": "system", "content": SYSTEM_PROMPT + memory_text()}] + EXAMPLES


def save_chat(chat_log):
    """Saves the transcript and asks the model for a short summary to remember next time."""
    if not chat_log:
        return
    transcript = "\n\n".join(chat_log)
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    with open(os.path.join(CHATS_FOLDER, stamp + ".md"), "w", encoding="utf-8") as f:
        f.write(transcript)
    try:
        summary = ask_model([
            {"role": "system", "content": "You write short, accurate memory notes in plain English."},
            {"role": "user", "content": (
                f"Here is a conversation between {USER_NAME} and Ellie. Write 3 to 6 short bullet points: "
                "what was discussed, anything decided, and anything unfinished. "
                "Only include things that were actually said.\n\n" + transcript)},
        ], temperature=0.3)
        with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
            f.write("Last chat: " + stamp + "\n\n" + summary)
    except Exception:
        pass


# ---------- Terminal chat ----------
if __name__ == "__main__":
    from ellie_voice import speak

    print("Using model:", MODEL)
    messages = start_messages()
    chat_log = []
    print("Ellie is ready. Type bye to stop.\n")
    while True:
        user_text = input("You: ").strip()
        if not user_text:
            continue
        messages.append({"role": "user", "content": user_text})
        try:
            reply = ask_model(messages)
        except (requests.exceptions.RequestException, KeyError):
            print("Can't reach Ollama. Is it running?")
            break
        print("\nEllie: " + reply + "\n")
        speak(reply)
        messages.append({"role": "assistant", "content": reply})
        chat_log += [f"**{SPEAKER}:** " + user_text, "**Ellie:** " + reply]
        if user_text.lower() in ("bye", "goodbye"):
            break
    save_chat(chat_log)
