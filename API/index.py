from fastapi import FastAPI, Request
import telebot
import json
import os

BOT_TOKEN = os.getenv("8956064048:AAFq02ocgGuWsOAxB67jtuh7WxznaarGGgc")
GROUP_ID = -1004413547137

bot = telebot.TeleBot(BOT_TOKEN)
app = FastAPI() # Vercel isi ko dhoond raha tha

def is_admin(chat_id, user_id):
    try:
        s = bot.get_chat_member(chat_id, user_id).status
        return s in ['administrator','creator']
    except:
        return False

def mention(user):
    return f"@{user.username}" if user.username else f"[{user.first_name}](tg://user?id={user.id})"

def load(f, d):
    try: return json.load(open(f))
    except: return d

def save(f, d):
    try: json.dump(d, open(f,'w'))
    except: pass

# /bye
@bot.message_handler(commands=['bye'])
def bye_handler(message):
    if message.chat.id!= GROUP_ID: return
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, f"{mention(message.from_user)} tu admin nahi hai ❌", parse_mode="Markdown")
        return
    if not message.reply_to_message: return
    if is_admin(message.chat.id, message.reply_to_message.from_user.id): return
    bot.ban_chat_member(message.chat.id, message.reply_to_message.from_user.id)
    bot.send_message(message.chat.id, f"Bye Bye {mention(message.reply_to_message.from_user)} 👋 {mention(message.from_user)} ne ban kiya!", parse_mode="Markdown")

# /pin
@bot.message_handler(commands=['pin'])
def pin_handler(message):
    if message.chat.id!= GROUP_ID or not is_admin(message.chat.id, message.from_user.id): return
    if message.reply_to_message:
        bot.pin_chat_message(message.chat.id, message.reply_to_message.message_id)
        bot.send_message(message.chat.id, f"Done {mention(message.from_user)} 📌", parse_mode="Markdown")

# /give
@bot.message_handler(commands=['give'])
def give_handler(message):
    if message.chat.id!= GROUP_ID or not is_admin(message.chat.id, message.from_user.id): return
    if message.reply_to_message:
        bot.promote_chat_member(message.chat.id, message.reply_to_message.from_user.id, can_delete_messages=True, can_restrict_members=True, can_pin_messages=True)
        bot.send_message(message.chat.id, f"👑 {mention(message.reply_to_message.from_user)} ab admin hai! {mention(message.from_user)} ne banaya", parse_mode="Markdown")

# /restrict
@bot.message_handler(commands=['restrict'])
def restrict_handler(message):
    if message.chat.id!= GROUP_ID or not is_admin(message.chat.id, message.from_user.id): return
    words = load("/tmp/words.json", [])
    text_to_ban = ""
    if message.reply_to_message and len(message.text.split()) == 1:
        text_to_ban = message.reply_to_message.text.lower()
    else:
        parts = message.text.split(maxsplit=1)
        if len(parts) > 1: text_to_ban = parts[1].lower()

    if text_to_ban and text_to_ban not in words:
        words.append(text_to_ban)
        save("/tmp/words.json", words)
        bot.send_message(message.chat.id, f"{mention(message.from_user)} ne ban kiya word -> `{text_to_ban}` 🚫", parse_mode="Markdown")

# /alert + 📢 @all
@bot.message_handler(commands=['alert'])
@bot.message_handler(func=lambda m: m.text and m.text.startswith(("📢","🚨","@all")))
def alert_handler(message):
    if message.chat.id!= GROUP_ID or not is_admin(message.chat.id, message.from_user.id): return
    clean = message.text
    for x in ["/alert","📢","🚨","@all","@ALL"]: clean = clean.replace(x,"")
    msg = clean.strip() or "Attention Everyone!"

    tag_text = ""
    try:
        # Vercel pe saare members ko tag karna possible nahi, admin ko hi kar sakte hai (Telegram limit)
        for a in bot.get_chat_administrators(message.chat.id):
            tag_text += f"{mention(a.user)} "
    except: pass

    bot.send_message(message.chat.id, f"🚨 ALERT from {mention(message.from_user)} 🚨\n\n{msg}\n\n{tag_text}", parse_mode="Markdown")

# Filter + Warn
@bot.message_handler(func=lambda m: True)
def filter_all(message):
    if message.chat.id!= GROUP_ID or message.text.startswith("/"): return
    if is_admin(message.chat.id, message.from_user.id): return

    words = load("/tmp/words.json", [])
    warns = load("/tmp/warns.json", {})

    for w in words:
        if w in message.text.lower():
            try: bot.delete_message(message.chat.id, message.message_id)
            except: pass
            uid = str(message.from_user.id)
            warns[uid] = warns.get(uid, 0) + 1
            save("/tmp/warns.json", warns)
            if warns[uid] >= 4:
                bot.ban_chat_member(message.chat.id, message.from_user.id)
                bot.send_message(message.chat.id, f"{mention(message.from_user)} 4/4 warns -> Ban ☠️", parse_mode="Markdown")
                warns[uid]=0
                save("/tmp/warns.json", warns)
            else:
                bot.send_message(message.chat.id, f"Oye {mention(message.from_user)} mana hai `{w}` Warn {warns[uid]}/4 😠", parse_mode="Markdown")
            break

# --- Vercel Webhook Part ---
@app.get("/")
def home():
    return {"status": "Bot Live"}

@app.post("/")
async def webhook(request: Request):
    data = await request.json()
    update = telebot.types.Update.de_json(data)
    bot.process_new_updates([update])
    return {"ok": True}
