# Ellie - desktop window. Chat, voice, and a password-locked Private Journal.
# Double-click the "Ellie" shortcut on the Desktop, or run this file.
# Closing the window locks the journal and saves the normal chat with a short summary.

import os
import threading
import tkinter as tk
import traceback
from datetime import datetime
from tkinter import font as tkfont
from tkinter import messagebox, simpledialog, ttk

import EllieChat as ellie
from ellie_journal import Journal, REMEMBER_MESSAGES
from ellie_voice import speak

HERE = os.path.dirname(os.path.abspath(__file__))
messages = ellie.start_messages()
chat_log = []
journal = Journal()
current = {"entry": None}       # the journal entry that is open, if any

JOURNAL_PROMPT = f"""
You are Ellie, keeping {ellie.USER_NAME} company while they write in their private journal.
Listen first. Reflect back what you hear, ask one gentle question at a time, and help them
put their thoughts in order. Keep replies short. Plain, modern English. No emojis.
"""

# ---------- Look: clean and light ----------
BG = "#eef1f7"
PANEL = "#ffffff"
LINE = "#d5dbe8"
INK = "#1f2937"
MUTED = "#6b7280"
ACCENT = "#4f6df5"      # Ellie blue
ACCENT_DARK = "#3b55d1"
YOU = "#0f766e"         # your messages
PRIVATE = "#7c3aed"     # journal is open

root = tk.Tk()
root.title("Ellie")
root.geometry("880x660")
root.minsize(640, 460)
root.configure(bg=BG)

_families = set(tkfont.families())
SANS = next((f for f in ("Segoe UI", "Calibri", "Arial") if f in _families), "TkDefaultFont")
TITLE = (SANS, 18, "bold")
HEAD = (SANS, 11, "bold")
BODY = (SANS, 11)
UI = (SANS, 10)
SMALL = (SANS, 9)

style = ttk.Style()
style.theme_use("clam")
style.configure("Vertical.TScrollbar", background=LINE, troughcolor=PANEL, bordercolor=PANEL,
                arrowcolor=MUTED, lightcolor=LINE, darkcolor=LINE, gripcount=0)


def report_error(exc, val, tb):
    """Errors are written to ellie_error.log and shown, instead of failing silently."""
    try:
        with open(os.path.join(HERE, "ellie_error.log"), "a", encoding="utf-8") as f:
            f.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n"
                    + "".join(traceback.format_exception(exc, val, tb)) + "\n")
    except OSError:
        pass
    messagebox.showerror("Ellie", "Something went wrong:\n" + str(val)
                         + "\n\nDetails were saved to ellie_error.log.", parent=root)


root.report_callback_exception = report_error


def button(parent, text, command=None, primary=False):
    return tk.Button(parent, text=text, command=command, font=UI, relief="flat", bd=0, padx=14, pady=5,
                     cursor="hand2", bg=ACCENT if primary else PANEL, fg="white" if primary else INK,
                     activebackground=ACCENT_DARK if primary else LINE,
                     activeforeground="white" if primary else INK, disabledforeground="#b0b6c3",
                     highlightthickness=1, highlightbackground=ACCENT if primary else LINE)


# ---------- Header ----------
header = tk.Frame(root, bg=BG)
header.pack(fill="x", padx=18, pady=(14, 8))
tk.Label(header, text="Ellie", bg=BG, fg=ACCENT, font=TITLE).pack(side="left")
status = tk.Label(header, text="", bg=BG, fg=MUTED, font=SMALL)
status.pack(side="left", padx=(14, 0), pady=(6, 0))

# ---------- Bottom bar (packed before the page so a small window shrinks the page, not the controls) ----------
bottom = tk.Frame(root, bg=BG)
bottom.pack(side="bottom", fill="x", padx=18, pady=(8, 14))
typing_row = tk.Frame(bottom, bg=BG)
typing_row.pack(fill="x")
send_button = button(typing_row, "Send", primary=True)
send_button.pack(side="right", padx=(8, 0), fill="y")
entry_box = tk.Frame(typing_row, bg=PANEL, highlightthickness=1, highlightbackground=LINE,
                     highlightcolor=ACCENT)
entry_box.pack(side="left", fill="x", expand=True)
entry = tk.Entry(entry_box, bg=PANEL, fg=INK, insertbackground=ACCENT, relief="flat", font=BODY)
entry.pack(fill="x", ipady=7, padx=10)
entry.focus()

controls = tk.Frame(bottom, bg=BG)
controls.pack(fill="x", pady=(8, 0))
journal_button = button(controls, "🔒  Private Journal")
journal_button.pack(side="left")
voice_on = tk.BooleanVar(value=True)
tk.Checkbutton(controls, text="Voice", variable=voice_on, bg=BG, fg=INK, selectcolor=PANEL,
               activebackground=BG, font=UI, cursor="hand2").pack(side="left", padx=(12, 0))

# ---------- Journal entries (left) and the conversation (right) ----------
body = tk.Frame(root, bg=BG)
body.pack(side="top", fill="both", expand=True, padx=18)

sidebar = tk.Frame(body, bg=BG, width=190)
sidebar.pack(side="left", fill="y", padx=(0, 12))
tk.Label(sidebar, text="Journal entries", bg=BG, fg=INK, font=HEAD).pack(anchor="w")
sidebar_hint = tk.Label(sidebar, bg=BG, fg=MUTED, font=SMALL, justify="left", wraplength=180)
sidebar_hint.pack(anchor="w", pady=(0, 6))
sidebar_buttons = tk.Frame(sidebar, bg=BG)
sidebar_buttons.pack(side="bottom", fill="x")
entries_box = tk.Listbox(sidebar, bg=PANEL, fg=INK, selectbackground=ACCENT, selectforeground="white",
                         relief="flat", highlightthickness=1, highlightbackground=LINE, font=UI,
                         activestyle="none", exportselection=False, width=24, height=3)
entries_box.pack(fill="both", expand=True)

page = tk.Frame(body, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
page.pack(side="left", fill="both", expand=True)
scroll = ttk.Scrollbar(page, orient="vertical")
scroll.pack(side="right", fill="y")
log = tk.Text(page, wrap="word", bg=PANEL, fg=INK, font=BODY, relief="flat", padx=16, pady=12,
              spacing1=2, spacing3=8, yscrollcommand=scroll.set, width=1, height=1)
log.pack(side="left", fill="both", expand=True)
scroll.configure(command=log.yview)
log.tag_config("you", foreground=YOU, font=(SANS, 10, "bold"))
log.tag_config("ellie", foreground=ACCENT, font=(SANS, 10, "bold"))
log.configure(state="disabled")


def add(who, text, tag):
    log.configure(state="normal")
    log.insert("end", who + "\n", tag)
    log.insert("end", text.strip() + "\n\n")
    log.configure(state="disabled")
    log.see("end")


def clear_screen():
    log.configure(state="normal")
    log.delete("1.0", "end")
    log.configure(state="disabled")


# ---------- Status ----------
sidebar_actions = []


def update_status():
    is_open = journal.is_open()
    if is_open:
        name = current["entry"]["title"] if current["entry"] else "no entry chosen"
        status.configure(text="Private Journal open  ·  " + name + "  ·  encrypted, voice off", fg=PRIVATE)
    else:
        status.configure(text="Chat  ·  model " + ellie.MODEL, fg=MUTED)
    journal_button.configure(text="🔓  Lock journal" if is_open else "🔒  Private Journal",
                             fg=PRIVATE if is_open else INK)
    sidebar_hint.configure(text="Click an entry to open it." if is_open
                           else "Locked. Open the Private Journal to see your entries.")
    for b in sidebar_actions:
        b.configure(state="normal" if is_open else "disabled")


# ---------- Journal entries ----------
def refresh_entries():
    entries_box.delete(0, "end")
    for e in journal.entries():
        entries_box.insert("end", "  " + e["title"])
    if current["entry"] in journal.entries():
        i = journal.entries().index(current["entry"])
        entries_box.selection_set(i)
        entries_box.see(i)


def open_entry(e):
    current["entry"] = e
    clear_screen()
    for m in e["messages"]:
        mine = m["role"] == "user"
        add("You" if mine else "Ellie", m["content"], "you" if mine else "ellie")
    if not e["messages"]:
        add("Ellie", "A fresh page. What's on your mind?", "ellie")
    refresh_entries()
    update_status()


def on_pick(event=None):
    picked = entries_box.curselection()
    if picked and journal.is_open():
        open_entry(journal.entries()[picked[0]])


def default_title():
    return datetime.now().strftime("%B %d, %Y")


def new_entry():
    title = simpledialog.askstring("New entry", "Title:", initialvalue=default_title(), parent=root)
    if title is not None:
        open_entry(journal.new_entry(title.strip() or default_title()))


def rename_entry():
    e = current["entry"]
    if e:
        title = simpledialog.askstring("Rename entry", "New title:", initialvalue=e["title"], parent=root)
        if title and title.strip():
            e["title"] = title.strip()
            journal.touch(e)
            refresh_entries()
            update_status()


def delete_entry():
    e = current["entry"]
    if e and messagebox.askyesno("Delete entry", 'Delete "' + e["title"] + '" for good?\n'
                                 "This cannot be undone.", default="no", parent=root):
        journal.delete_entry(e)
        current["entry"] = None
        entries = journal.entries()
        open_entry(entries[-1] if entries else journal.new_entry(default_title()))


entries_box.bind("<<ListboxSelect>>", on_pick)
for label, action in (("+  New entry", new_entry), ("Rename", rename_entry), ("Delete", delete_entry)):
    b = button(sidebar_buttons, label, action)
    b.pack(fill="x", pady=(6, 0))
    sidebar_actions.append(b)


# ---------- Locking and unlocking ----------
def lock_journal():
    """Saves and locks the journal, then wipes it from the screen and memory."""
    if not journal.is_open():
        return
    journal.save()
    journal.lock()
    current["entry"] = None
    entries_box.delete(0, "end")
    clear_screen()
    update_status()
    add("Ellie", "Your journal is locked. Back to normal chat.", "ellie")


def toggle_journal():
    if journal.is_open():
        lock_journal()
        return
    first_time = not journal.exists()
    prompt = ("Create a password for your Private Journal.\nIt can't be recovered, so keep it safe:"
              if first_time else "Journal password:")
    password = simpledialog.askstring("Private Journal", prompt, show="*", parent=root)
    if not password:
        return
    if first_time:
        again = simpledialog.askstring("Private Journal", "Type it once more to confirm:", show="*", parent=root)
        if again != password:
            messagebox.showwarning("Private Journal", "The passwords didn't match. Nothing was created.",
                                   parent=root)
            return
    if not journal.unlock(password):
        messagebox.showwarning("Private Journal", "Wrong password. The journal stays locked.", parent=root)
        return
    entries = journal.entries()
    latest = max(entries, key=lambda e: e["updated"]) if entries else journal.new_entry(default_title())
    open_entry(latest)


journal_button.configure(command=toggle_journal)


# ---------- Talking to Ellie ----------
def finish(user_text, reply, thread, e):
    """Runs on the window thread once Ellie answers."""
    if e is not None:
        if journal.is_open() and e in journal.entries():
            e["messages"] += [{"role": "user", "content": user_text}, {"role": "assistant", "content": reply}]
            journal.touch(e)
        show = journal.is_open() and current["entry"] is e
    else:
        thread.append({"role": "assistant", "content": reply})
        chat_log.extend([f"**{ellie.SPEAKER}:** " + user_text, "**Ellie:** " + reply])
        show = True
    if show:
        add("Ellie", reply, "ellie")
    entry.configure(state="normal")
    entry.focus()


def failed(thread, e):
    if e is None:
        thread.pop()
    add("Ellie", "(I can't reach Ollama. Is it running?)", "ellie")
    entry.configure(state="normal")


def think(user_text, thread, e):
    try:
        reply = ellie.ask_model(thread)
    except Exception:
        root.after(0, failed, thread, e)
        return
    root.after(0, finish, user_text, reply, thread, e)
    if voice_on.get() and e is None:        # the journal is never read aloud
        speak(reply)


def send(event=None):
    if str(entry.cget("state")) == "disabled":
        return
    text = entry.get().strip()
    if not text:
        return
    entry.delete(0, "end")
    entry.configure(state="disabled")
    e = None
    if journal.is_open():
        if current["entry"] is None:
            open_entry(journal.new_entry(default_title()))
        e = current["entry"]
        thread = ([{"role": "system", "content": JOURNAL_PROMPT}]
                  + e["messages"][-REMEMBER_MESSAGES:] + [{"role": "user", "content": text}])
    else:
        thread = messages
        thread.append({"role": "user", "content": text})
    add("You", text, "you")
    threading.Thread(target=think, args=(text, thread, e), daemon=True).start()


def on_close():
    root.title("Ellie - saving...")
    root.update()
    lock_journal()
    ellie.save_chat(chat_log)
    root.destroy()


send_button.configure(command=send)
entry.bind("<Return>", send)
root.protocol("WM_DELETE_WINDOW", on_close)
update_status()
add("Ellie", f"Hi{' ' + ellie.YOUR_NAME if ellie.YOUR_NAME else ''}! I'm running locally on {ellie.MODEL}. What can I help with?", "ellie")
root.mainloop()
