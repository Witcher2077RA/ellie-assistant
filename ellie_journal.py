# Ellie's Private Journal: one encrypted, password-protected file.
# Without the password nothing in it can be read, by Ellie or by anyone who opens the file.
# The password is never saved. There is NO recovery: forget it and the journal is gone.
#
# Encryption: the password is stretched with PBKDF2-HMAC-SHA256 (600,000 rounds, random salt)
# into a key for Fernet (AES-128-CBC + HMAC-SHA256) from the "cryptography" package.
#
# Inside, the journal holds a list of entries. Each entry has a title and its conversation with Ellie.

import base64
import hashlib
import json
import os
import uuid
from datetime import datetime

from cryptography.fernet import Fernet, InvalidToken

from EllieChat import DATA_FOLDER

JOURNAL_FILE = os.path.join(DATA_FOLDER, "journal.enc")
REMEMBER_MESSAGES = 20      # how many recent messages of an entry Ellie sees when you continue it


def _key(password, salt):
    raw = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 600000)
    return base64.urlsafe_b64encode(raw)


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class Journal:
    def __init__(self):
        self._fernet = None
        self._salt = None
        self.data = None

    def exists(self):
        return os.path.exists(JOURNAL_FILE)

    def is_open(self):
        return self._fernet is not None

    def unlock(self, password):
        """Opens the journal, or creates it the first time. Returns False if the password is wrong."""
        if self.exists():
            with open(JOURNAL_FILE, "rb") as f:
                blob = f.read()
            salt, token = blob[:16], base64.urlsafe_b64encode(blob[16:])
            fernet = Fernet(_key(password, salt))
            try:
                data = json.loads(fernet.decrypt(token).decode("utf-8"))
            except (InvalidToken, ValueError):
                return False
        else:
            salt = os.urandom(16)
            fernet = Fernet(_key(password, salt))
            data = {"entries": []}
        self._fernet, self._salt, self.data = fernet, salt, data
        self.data.setdefault("entries", [])
        self.save()
        return True

    def save(self):
        if not self.is_open():
            return
        token = self._fernet.encrypt(json.dumps(self.data).encode("utf-8"))
        temp = JOURNAL_FILE + ".tmp"
        with open(temp, "wb") as f:
            f.write(self._salt + base64.urlsafe_b64decode(token))
        os.replace(temp, JOURNAL_FILE)      # write-then-swap, so a crash never leaves half a file

    def lock(self):
        self._fernet = self._salt = self.data = None

    # ---------- Entries ----------
    def entries(self):
        return self.data["entries"] if self.is_open() else []

    def new_entry(self, title):
        entry = {"id": uuid.uuid4().hex, "title": title, "messages": [], "updated": _now()}
        self.data["entries"].append(entry)
        self.save()
        return entry

    def touch(self, entry):
        """Call after changing an entry: stamps the time and saves."""
        entry["updated"] = _now()
        self.save()

    def delete_entry(self, entry):
        self.data["entries"] = [e for e in self.data["entries"] if e["id"] != entry["id"]]
        self.save()
