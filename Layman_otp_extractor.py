import imaplib
import email
import re
import time
from email.utils import parsedate_to_datetime
from bs4 import BeautifulSoup
import pyperclip
import threading
import tkinter as tk
from tkinter import messagebox

# --- Config ---
IMAP_SERVER = "imap.gmail.com"
CHECK_INTERVAL = 1  # seconds
KEYWORDS = ["otp", "code", "pin", "password", "verification"]

# --- Functions ---
def get_unread(mail):
    mail.select("inbox")
    status, messages = mail.search(None, "(UNSEEN)")
    return messages[0].split()

def extract_text(msg):
    plain_text = ""
    html_text = ""
    
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            payload = part.get_payload(decode=True)
            if not payload:
                continue
            decoded = payload.decode(errors="ignore")
            if ctype == "text/plain":
                plain_text += decoded
            elif ctype == "text/html":
                html_text += BeautifulSoup(decoded, "html.parser").get_text(" ", strip=True)
    else:
        plain_text = msg.get_payload(decode=True).decode(errors="ignore")
    
    return plain_text if plain_text.strip() else html_text

def find_otp(text):
    # 1️⃣ Look for OTP/code/pin near keywords
    for keyword in KEYWORDS:
        pattern = rf"{keyword}.{{0,30}}(\d{{4,8}})|(\d{{4,8}}).{{0,30}}{keyword}"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            otp = match.group(1) or match.group(2)
            print(f"✅ OTP candidate accepted: {otp} (near '{keyword}')")
            return otp

    # 2️⃣ Fallback: any standalone 6-digit number
    fallback_regex = r"\b\d{6}\b"
    match = re.search(fallback_regex, text)
    if match:
        otp = match.group()
        print(f"⚡ Fallback OTP candidate: {otp}")
        return otp

    return None

def watch_inbox(email_address, app_password):
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(email_address, app_password)

    while True:
        unseen = get_unread(mail)
        if not unseen:
            time.sleep(CHECK_INTERVAL)
            continue

        # Fetch all unseen emails with date
        emails_with_date = []
        for num in unseen:
            _, data = mail.fetch(num, "(RFC822)")
            msg = email.message_from_bytes(data[0][1])
            date_header = msg.get("Date")
            try:
                date_obj = parsedate_to_datetime(date_header)
            except:
                date_obj = None
            emails_with_date.append((date_obj, msg))

        # Sort by newest first
        emails_with_date.sort(key=lambda x: x[0] or 0, reverse=True)

        # Check only the latest email
        latest_msg = emails_with_date[0][1]
        text = extract_text(latest_msg)
        otp = find_otp(text)
        if otp:
            pyperclip.copy("")   # clear clipboard first
            pyperclip.copy(otp)  # copy fresh OTP
            messagebox.showinfo("OTP Received", f"Your OTP is: {otp}\nCopied to clipboard!")
            root.quit()
            return

        time.sleep(CHECK_INTERVAL)

def start_watcher():
    email_address = email_entry.get().strip()
    app_password = password_entry.get().strip()
    if not email_address or not app_password:
        messagebox.showerror("Error", "Please enter both email and app password")
        return
    start_button.config(state="disabled")
    threading.Thread(target=watch_inbox, args=(email_address, app_password), daemon=True).start()

# --- GUI ---
root = tk.Tk()
root.title("OTP Watcher (Mac Version)")

tk.Label(root, text="Email:").grid(row=0, column=0, padx=10, pady=5)
email_entry = tk.Entry(root, width=30)
email_entry.grid(row=0, column=1, padx=10, pady=5)

tk.Label(root, text="App Password:").grid(row=1, column=0, padx=10, pady=5)
password_entry = tk.Entry(root, width=30, show="*")
password_entry.grid(row=1, column=1, padx=10, pady=5)

start_button = tk.Button(root, text="Start Watching", command=start_watcher)
start_button.grid(row=2, column=0, columnspan=2, pady=10)

root.mainloop()
