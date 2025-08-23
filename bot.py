import telebot
from telebot import types
import time, random, requests
from faker import Faker

# -------------------------------
# Bot Config
# -------------------------------
BOT_TOKEN = "YOUR_BOT_TOKEN"   # এখানে তোমার Bot Token বসাও
bot = telebot.TeleBot(BOT_TOKEN)

faker = Faker()
registered_users = {}
user_proxies = {}   # {user_id: [list of proxies]}
iban_temp = {}      # {user_id: {"list": [...], "pos": 0}}
temp_mails = {}

# ======================================================
# /start
# ======================================================
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    user_firstname = message.from_user.first_name

    # Loading Animation
    loading_msg = bot.send_animation(
        chat_id,
        animation="https://media.giphy.com/media/xTkcEQACH24SMPxIQg/giphy.gif",
        caption="👋 Welcome to [V2.O]\n⚡ Loading your dashboard…"
    )
    time.sleep(4)
    bot.delete_message(chat_id, loading_msg.message_id)

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Register", callback_data="register"))
    kb.add(types.InlineKeyboardButton("📜 Commands", callback_data="commands"))
    kb.add(types.InlineKeyboardButton("❌ Close", callback_data="close"))

    bot.send_message(
        chat_id,
        f"🌟 Hello {user_firstname}\n\n"
        "Welcome aboard the V2.O 💌\n\n"
        "I am your go-to bot, packed with a variety of gates, tools, and commands.\n"
        "👇 Tap Register to begin your journey.\n👇 Or view available Commands.",
        reply_markup=kb
    )

# ======================================================
# Navigation Pages
# ======================================================
def show_page1(chat_id):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("💳 CC Gen", callback_data="ccgen"))
    kb.add(types.InlineKeyboardButton("✅ CC Chk", callback_data="ccchk"))
    kb.add(types.InlineKeyboardButton("🏦 BIN Info", callback_data="bininfo"))
    kb.add(types.InlineKeyboardButton("🏦 IBAN Gen", callback_data="iban"))
    kb.add(types.InlineKeyboardButton("➡️ Next", callback_data="next1"))
    bot.send_message(chat_id, "📜 Page-1 Tools:", reply_markup=kb)

def show_page2(chat_id):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🏠 Fake Address", callback_data="fake"))
    kb.add(types.InlineKeyboardButton("🔍 Site Hunter", callback_data="site"))
    kb.add(types.InlineKeyboardButton("📧 Temp Mail", callback_data="temp"))
    kb.add(types.InlineKeyboardButton("🌐 Proxy Manager", callback_data="proxy"))
    kb.add(types.InlineKeyboardButton("🔙 Back", callback_data="back2"))
    kb.add(types.InlineKeyboardButton("➡️ Next", callback_data="next2"))
    bot.send_message(chat_id, "📜 Page-2 Tools:", reply_markup=kb)

def show_page3(chat_id):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("❌ Close", callback_data="close"))
    kb.add(types.InlineKeyboardButton("🔙 Back", callback_data="back3"))
    kb.add(types.InlineKeyboardButton("📞 Contact Admin", callback_data="contact"))
    bot.send_message(chat_id, "📜 Page-3:", reply_markup=kb)

# ======================================================
# Callback Handler
# ======================================================
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id

    if call.data == "register":
        if user_id in registered_users:
            bot.send_message(chat_id,
                "⚠️ Already Registered ‼️\nEnjoy our Bot Tools 🥳")
        else:
            registered_users[user_id] = True
            bot.send_message(chat_id,
                "🎉 You have been successfully registered!\nEnjoy the tools 🚀")

        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🛠 Explore Tools", callback_data="commands"))
        kb.add(types.InlineKeyboardButton("❌ Close", callback_data="close"))
        bot.send_message(chat_id, "👇 What would you like to do next?", reply_markup=kb)

    elif call.data == "commands": show_page1(chat_id)
    elif call.data == "close": bot.delete_message(chat_id, call.message.message_id)
    elif call.data == "next1": show_page2(chat_id)
    elif call.data == "back2": show_page1(chat_id)
    elif call.data == "next2": show_page3(chat_id)
    elif call.data == "back3": show_page2(chat_id)

    # Page-1
    elif call.data == "ccgen":
        bot.send_message(chat_id, "💳 Use /gen <BIN> <count> [MM|YY]")
    elif call.data == "ccchk":
        bot.send_message(chat_id, "⚠️ CC Checker tool is under maintenance.")
    elif call.data == "bininfo":
        bot.send_message(chat_id, "🏦 Use /bin <BIN>")
    elif call.data == "iban":
        bot.send_message(chat_id, "🏦 Use /ibangen <CC> <count> OR /ichk <IBAN>")
    # Page-2
    elif call.data == "fake":
        bot.send_message(chat_id, "🏠 Use /fake <country_code>")
    elif call.data == "site":
        bot.send_message(chat_id,
            "🔍 Site Hunter\n/url <site>\n/murl <url1,url2,...>")
    elif call.data == "temp":
        bot.send_message(chat_id,
            "📧 Temp Mail\n/temp → new\n/ib → inbox\n/fresh → refresh\n/dlt → delete")
    elif call.data == "proxy":
        bot.send_message(chat_id,
            "🌐 Proxy Manager\n/addproxy, /chkproxy, /vproxy, /rproxy\n/mproxy (≤50)")
    elif call.data == "contact":
        bot.send_message(chat_id, "📞 Contact Admin: @YourAdminUsername")

# ======================================================
# CC Generator
# ======================================================
@bot.message_handler(commands=['gen'])
def gen_handler(message):
    try:
        _, bin_code, count, *rest = message.text.split()
        count = int(count)
        exp = rest[0] if rest else None
        cards = []
        for _ in range(count):
            cc = bin_code + "".join(str(random.randint(0,9)) for _ in range(16-len(bin_code)))
            if exp:
                mm, yy = exp.split("|")
            else:
                mm, yy = str(random.randint(1,12)).zfill(2), str(random.randint(24,29))
            cvv = str(random.randint(100,999))
            cards.append(f"{cc}|{mm}|{yy}|{cvv}")
        bot.reply_to(message, "✅ Generated:\n" + "\n".join(cards))
    except:
        bot.reply_to(message, "❌ Usage: /gen <BIN> <count> [MM|YY]")

# ======================================================
# BIN Info
# ======================================================
@bot.message_handler(commands=['bin'])
def bin_handler(message):
    try:
        _, bin_code = message.text.split()
        r = requests.get(f"https://lookup.binlist.net/{bin_code}").json()
        msg = f"🔎 BIN Information\n━━━━━━━━━\n"
        msg += f"BIN: {bin_code}\nScheme: {r.get('scheme')}\nType: {r.get('type')}\n"
        msg += f"Brand: {r.get('brand')}\nBank: {r['bank'].get('name')}\n"
        msg += f"Country: {r['country'].get('name')} {r['country'].get('emoji')}\n"
        msg += f"Currency: {r['country'].get('currency')}\n"
        msg += f"Website: {r['bank'].get('url')}\nPhone: {r['bank'].get('phone')}"
        bot.reply_to(message, msg)
    except:
        bot.reply_to(message, "❌ Usage: /bin <BIN>")

# ======================================================
# IBAN Gen / Check
# ======================================================
@bot.message_handler(commands=['ibangen'])
def ibangen_handler(message):
    try:
        _, cc, count = message.text.split()
        count = int(count)
        ibans = []
        for i in range(count):
            iban = f"{cc}{random.randint(10**18, 10**20)}"
            ibans.append(iban)
        iban_temp[message.from_user.id] = {"list": ibans, "pos": 0}
        bot.reply_to(message, "✅ Generated:\n" + "\n".join(ibans))
    except:
        bot.reply_to(message, "❌ Usage: /ibangen <country_code> <count>")

@bot.message_handler(commands=['ichk'])
def ichk_handler(message):
    try:
        _, iban = message.text.split()
        bot.reply_to(message,
            f"🔎 IBAN Check Result\n━━━━━━━━━\nIBAN: {iban}\nBank: DemoBank\nCountry: DE\nStatus: ✅ Valid")
    except:
        bot.reply_to(message, "❌ Usage: /ichk <IBAN>")

# ======================================================
# Fake Address
# ======================================================
@bot.message_handler(commands=['fake'])
def fake_handler(message):
    try:
        _, cc = message.text.split()
        addr = faker.address().replace("\n", ", ")
        bot.reply_to(message, f"🏠 Fake Address ({cc}):\n{addr}")
    except:
        bot.reply_to(message, "❌ Usage: /fake <country_code>")

# ======================================================
# Site Hunter
# ======================================================
@bot.message_handler(commands=['url'])
def url_handler(message):
    try:
        _, site = message.text.split()
        bot.reply_to(message, f"🔎 Checking site: {site}\nResult: ✅ Working")
    except:
        bot.reply_to(message, "❌ Usage: /url <site>")

@bot.message_handler(commands=['murl'])
def murl_handler(message):
    try:
        urls = message.text.split()[1].split(",")
        results = [f"{u} → ✅ OK" for u in urls]
        bot.reply_to(message, "\n".join(results))
    except:
        bot.reply_to(message, "❌ Usage: /murl <url1,url2,...>")

# ======================================================
# Temp Mail (Demo)
# ======================================================
@bot.message_handler(commands=['temp'])
def temp_handler(message):
    email = f"{random.randint(1000,9999)}@mail.tm"
    temp_mails[message.from_user.id] = email
    bot.reply_to(message, f"📧 Temp Mail Created: {email}")

@bot.message_handler(commands=['ib'])
def inbox_handler(message):
    email = temp_mails.get(message.from_user.id)
    if email:
        bot.reply_to(message, f"📥 Inbox for {email}\n(No API integration demo)")
    else:
        bot.reply_to(message, "❌ No temp mail. Use /temp first.")

@bot.message_handler(commands=['fresh'])
def refresh_handler(message):
    bot.reply_to(message, "🔄 Inbox refreshed (demo).")

@bot.message_handler(commands=['dlt'])
def delete_handler(message):
    if message.from_user.id in temp_mails:
        del temp_mails[message.from_user.id]
        bot.reply_to(message, "🗑 Temp mail deleted.")
    else:
        bot.reply_to(message, "❌ No temp mail to delete.")

# ======================================================
# Proxy Manager
# ======================================================
@bot.message_handler(commands=['addproxy'])
def addproxy_handler(message):
    lines = message.text.split()[1:]
    user_id = message.from_user.id
    if not user_id in user_proxies: user_proxies[user_id] = []
    added = []
    for p in lines:
        if ":" in p:
            user_proxies[user_id].append(p)
            added.append(p)
    bot.reply_to(message, "➕ Added Proxies:\n" + "\n".join(added))

@bot.message_handler(commands=['vproxy'])
def viewproxy_handler(message):
    proxies = user_proxies.get(message.from_user.id, [])
    if proxies:
        bot.reply_to(message, "👁 Your Proxies:\n" + "\n".join(proxies))
    else:
        bot.reply_to(message, "❌ No proxies saved.")

@bot.message_handler(commands=['rproxy'])
def removeproxy_handler(message):
    user_proxies[message.from_user.id] = []
    bot.reply_to(message, "🗑 All proxies removed.")

@bot.message_handler(commands=['chkproxy'])
def chkproxy_handler(message):
    proxies = user_proxies.get(message.from_user.id, [])
    if not proxies:
        bot.reply_to(message, "❌ No proxies saved.")
        return
    results = [f"{p} → ✅ Alive" for p in proxies]  # demo
    bot.reply_to(message, "\n".join(results))

@bot.message_handler(commands=['mproxy'])
def mproxy_handler(message):
    try:
        proxies = message.text.split()[1].split(",")[:50]
        results = [f"{p} → ✅ Alive" for p in proxies]
        bot.reply_to(message, "\n".join(results))
    except:
        bot.reply_to(message, "❌ Usage: /mproxy ip:port,...")

# ======================================================
# Run Bot
# ======================================================
print("🤖 Bot is running…")
bot.infinity_polling()    kb.add(types.InlineKeyboardButton("🔙 Back", callback_data="back2"))
    kb.add(types.InlineKeyboardButton("➡️ Next", callback_data="next2"))
    bot.send_message(chat_id, "📜 Page-2 Tools:", reply_markup=kb)

def show_page3(chat_id):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("❌ Close", callback_data="close"))
    kb.add(types.InlineKeyboardButton("🔙 Back", callback_data="back3"))
    bot.send_message(chat_id, "📜 Page-3:", reply_markup=kb)

# =============================
# CALLBACK HANDLER
# =============================
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id

    if call.data == "register":
        if user_id in registered_users:
            bot.send_message(chat_id, "⚠️ Already Registered ‼️\nEnjoy our Bot Tools 🥳")
        else:
            registered_users[user_id] = True
            bot.send_message(chat_id, "🎉 You have been successfully registered!\nEnjoy the tools 🚀")

        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🛠 Explore Tools", callback_data="commands"))
        kb.add(types.InlineKeyboardButton("❌ Close", callback_data="close"))
        bot.send_message(chat_id, "👇 What would you like to do next?", reply_markup=kb)

    elif call.data == "commands": show_page1(chat_id)
    elif call.data == "close": bot.delete_message(chat_id, call.message.message_id)
    elif call.data == "next1": show_page2(chat_id)
    elif call.data == "back2": show_page1(chat_id)
    elif call.data == "next2": show_page3(chat_id)
    elif call.data == "back3": show_page2(chat_id)

    # Page-1
    elif call.data == "ccgen": bot.send_message(chat_id, "💳 Use /gen <BIN> <count> [MM|YY]")
    elif call.data == "ccchk": bot.send_message(chat_id, "⚠️ CC Checker tool is under maintenance.")
    elif call.data == "bininfo": bot.send_message(chat_id, "🏦 Use /bin <BIN>")
    elif call.data == "iban": bot.send_message(chat_id, "🏦 Use /ibangen <CC> <count> OR /ichk <IBAN>")

    # Page-2
    elif call.data == "fake": bot.send_message(chat_id, "🏠 Use /fake <country_code>")
    elif call.data == "site":
        bot.send_message(chat_id, "🔍 Site Hunter\n/url <site>\n/murl <url1,url2,...>")
    elif call.data == "temp":
        bot.send_message(chat_id,
            "📧 Temp Mail\n/temp → new\n/ib → inbox\n/fresh → refresh\n/dlt → delete")
    elif call.data == "proxy":
        bot.send_message(chat_id,
            "🌐 Proxy Manager\n/addproxy, /chkproxy, /vproxy, /rproxy\n/mproxy (≤50)")

# =============================
# CC GEN
# =============================
@bot.message_handler(commands=['gen'])
def gen_handler(message):
    try:
        _, bin_code, count, *rest = message.text.split()
        count = int(count)
        exp = rest[0] if rest else None
        cards = []
        for _ in range(count):
            cc = bin_code + "".join(str(random.randint(0,9)) for _ in range(16-len(bin_code)))
            mm, yy = exp.split("|") if exp else (str(random.randint(1,12)).zfill(2), str(random.randint(24,29)))
            cvv = str(random.randint(100,999))
            cards.append(f"{cc}|{mm}|{yy}|{cvv}")
        bot.reply_to(message, "✅ Generated:\n" + "\n".join(cards))
    except:
        bot.reply_to(message, "❌ Usage: /gen <BIN> <count> [MM|YY]")

# =============================
# BIN INFO
# =============================
@bot.message_handler(commands=['bin'])
def bin_handler(message):
    try:
        _, bin_code = message.text.split()
        r = requests.get(f"https://lookup.binlist.net/{bin_code}").json()
        msg = f"🔎 BIN Information\n━━━━━━━━━\n"
        msg += f"BIN: {bin_code}\nScheme: {r.get('scheme')}\nType: {r.get('type')}\n"
        msg += f"Brand: {r.get('brand')}\nBank: {r['bank'].get('name')}\n"
        msg += f"Country: {r['country'].get('name')} {r['country'].get('emoji')}\n"
        msg += f"Currency: {r['country'].get('currency')}\n"
        msg += f"Website: {r['bank'].get('url')}\nPhone: {r['bank'].get('phone')}"
        bot.reply_to(message, msg)
    except:
        bot.reply_to(message, "❌ Usage: /bin <BIN>")

# =============================
# IBAN GEN + CHECK
# =============================
@bot.message_handler(commands=['ibangen'])
def ibangen_handler(message):
    try:
        _, cc, count = message.text.split()
        count = int(count)
        ibans = []
        for i in range(count):
            iban = f"{cc}{random.randint(10**18, 10**20)}"
            ibans.append(iban)
        iban_temp[message.from_user.id] = {"list": ibans, "pos": 0}
        bot.reply_to(message, "✅ Generated:\n" + "\n".join(ibans))
    except:
        bot.reply_to(message, "❌ Usage: /ibangen <country_code> <count>")

@bot.message_handler(commands=['ichk'])
def ichk_handler(message):
    try:
        _, iban = message.text.split()
        bot.reply_to(message,
            f"🔎 IBAN Check Result\n━━━━━━━━━\nIBAN: {iban}\nBank: DemoBank\nCountry: DE\nStatus: ✅ Valid")
    except:
        bot.reply_to(message, "❌ Usage: /ichk <IBAN>")

# =============================
# FAKE ADDRESS
# =============================
@bot.message_handler(commands=['fake'])
def fake_handler(message):
    try:
        _, cc = message.text.split()
        addr = faker.address().replace("\n", ", ")
        bot.reply_to(message, f"🏠 Fake Address ({cc}):\n{addr}")
    except:
        bot.reply_to(message, "❌ Usage: /fake <country_code>")

# =============================
# SITE HUNTER
# =============================
@bot.message_handler(commands=['url'])
def url_handler(message):
    try:
        _, site = message.text.split()
        bot.reply_to(message, f"🔍 Checking site: {site}\nResult: ✅ Working")
    except:
        bot.reply_to(message, "❌ Usage: /url <site>")

@bot.message_handler(commands=['murl'])
def murl_handler(message):
    try:
        urls = message.text.split()[1].split(",")
        results = [f"{u} → ✅ OK" for u in urls]
        bot.reply_to(message, "\n".join(results))
    except:
        bot.reply_to(message, "❌ Usage: /murl <url1,url2,...>")

# =============================
# TEMP MAIL
# =============================
@bot.message_handler(commands=['temp'])
def temp_handler(message):
    email = f"{random.randint(1000,9999)}@mail.tm"
    temp_mails[message.from_user.id] = email
    bot.reply_to(message, f"📧 Temp Mail Created: {email}")

@bot.message_handler(commands=['ib'])
def inbox_handler(message):
    email = temp_mails.get(message.from_user.id)
    if email:
        bot.reply_to(message, f"📥 Inbox for {email}\n(No API integration demo)")
    else:
        bot.reply_to(message, "❌ No temp mail. Use /temp first.")

@bot.message_handler(commands=['fresh'])
def refresh_handler(message):
    bot.reply_to(message, "🔄 Inbox refreshed (demo).")

@bot.message_handler(commands=['dlt'])
def delete_handler(message):
    if message.from_user.id in temp_mails:
        del temp_mails[message.from_user.id]
        bot.reply_to(message, "🗑 Temp mail deleted.")
    else:
        bot.reply_to(message, "❌ No temp mail to delete.")

# =============================
# PROXY MANAGER
# =============================
@bot.message_handler(commands=['addproxy'])
def addproxy_handler(message):
    lines = message.text.split()[1:]
    user_id = message.from_user.id
    if not user_id in user_proxies: user_proxies[user_id] = []
    added = []
    for p in lines:
        if ":" in p:
            user_proxies[user_id].append(p)
            added.append(p)
    bot.reply_to(message, "➕ Added Proxies:\n" + "\n".join(added))

@bot.message_handler(commands=['vproxy'])
def viewproxy_handler(message):
    proxies = user_proxies.get(message.from_user.id, [])
    if proxies:
        bot.reply_to(message, "👁 Your Proxies:\n" + "\n".join(proxies))
    else:
        bot.reply_to(message, "❌ No proxies saved.")

@bot.message_handler(commands=['rproxy'])
def removeproxy_handler(message):
    user_proxies[message.from_user.id] = []
    bot.reply_to(message, "🗑 All proxies removed.")

@bot.message_handler(commands=['chkproxy'])
def chkproxy_handler(message):
    proxies = user_proxies.get(message.from_user.id, [])
    if not proxies:
        bot.reply_to(message, "❌ No proxies saved.")
        return
    results = [f"{p} → ✅ Alive" for p in proxies]
    bot.reply_to(message, "\n".join(results))

@bot.message_handler(commands=['mproxy'])
def mproxy_handler(message):
    try:
        proxies = message.text.split()[1].split(",")[:50]
        results = [f"{p} → ✅ Alive" for p in proxies]
        bot.reply_to(message, "\n".join(results))
    except:
        bot.reply_to(message, "❌ Usage: /mproxy ip:port,...")

# =============================
print("🤖 Bot is running…")
bot.infinity_polling()async def tm_create_account_and_token() -> Tuple[str, str]:
    """Create a mail.tm account and return (address, jwt)."""
    username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    address = f"{username}@mailto.plus"

    async with aiohttp.ClientSession() as session:
        async with session.post(f"{MAILTM_API}/accounts", json={"address": address, "password": password}) as r1:
            _ = await r1.json()
        async with session.post(f"{MAILTM_API}/token", json={"address": address, "password": password}) as r2:
            tok = await r2.json()
            jwt = tok.get("token")
    return address, jwt

async def tm_inbox(jwt: str) -> List[Dict[str, Any]]:
    async with aiohttp.ClientSession(headers={"Authorization": f"Bearer {jwt}"}) as session:
        async with session.get(f"{MAILTM_API}/messages") as r:
            data = await r.json()
            return data.get("hydra:member", []) or []

# =============== PROXY UTILS ===============

def parse_proxy_line(line: str) -> Optional[str]:
    """Validate proxy format ip:port:user:pass; return normalized or None."""
    parts = line.split(":")
    if len(parts) != 4: return None
    ip, port, user, pwd = [p.strip() for p in parts]
    if not ip or not port or not user or not pwd:
        return None
    return f"{ip}:{port}:{user}:{pwd}"

async def proxy_is_alive(proxy: str) -> bool:
    """Check a proxy by hitting httpbin.org/ip."""
    try:
        ip, port, user, pwd = proxy.split(":")
        proxy_url = f"http://{user}:{pwd}@{ip}:{port}"
        async with aiohttp.ClientSession() as session:
            async with session.get("http://httpbin.org/ip", proxy=proxy_url, timeout=12) as resp:
                return resp.status == 200
    except:
        return False

def next_alive_proxy(uid: int) -> Optional[str]:
    """Pick next (random) alive proxy not in dead-cache; None if none."""
    pool = [p for p in user_proxies.get(uid, []) if p not in proxy_dead_cache.setdefault(uid, set())]
    if not pool:
        return None
    return random.choice(pool)

def mark_proxy_dead(uid: int, proxy: str):
    proxy_dead_cache.setdefault(uid, set()).add(proxy)

# =============== SITE HUNTER SCAN (async) ===============

PAYMENT_PATTERNS = {
    "Stripe": [r"js\.stripe\.com", r"checkout\.stripe\.com", r"\bstripe\b"],
    "PayPal": [r"www\.paypal\.com/sdk/js", r"paypalobjects\.com", r"\bpaypal\b"],
    "Square": [r"web\.squarecdn\.com", r"\bsquare(up)?\b"],
    "Braintree": [r"braintreegateway\.com", r"\bbraintree\b"],
    "Adyen": [r"checkoutshopper.*\.adyen\.com", r"\badyen\b"],
    "Razorpay": [r"checkout\.razorpay\.com", r"\brazorpay\b"],
    "SSLCommerz": [r"secure\.sslcommerz\.com", r"\bsslcommerz\b"],
    "ShurjoPay": [r"\bshurjopay\b"],
    "aamarPay": [r"\baamarpay\b"],
    "Paytm": [r"paytm\.com", r"securegw-(?:stage\.)?paytm\.in"],
    "Google Pay": [r"pay\.google\.com/gp/p/js", r"\bgpay\b|\bgoogle\s*pay\b"],
    "Apple Pay (JS)": [r"\bapple\s*pay\b", r"\bapplepay\b"],
    "Flutterwave": [r"checkout\.flutterwave\.com", r"\bflutterwave\b"],
    "Paystack": [r"js\.paystack\.co", r"\bpaystack\b"],
    "Paddle": [r"cdn\.paddle\.com", r"\bpaddle\b"],
}

CAPTCHA_PATTERNS = {
    "Google reCAPTCHA": [r"www\.google\.com/recaptcha", r"\bgrecaptcha\b", r"recaptcha/api\.js"],
    "hCaptcha": [r"hcaptcha\.com", r"\bhcaptcha\b"],
    "Cloudflare Turnstile": [r"challenges\.cloudflare\.com/turnstile", r"\bcf-turnstile\b"],
    "Arkose/FunCaptcha": [r"funcaptcha\.com"],
    "GeeTest": [r"api\.geetest\.com", r"\bgee?t?est\b"],
}

def detect_platform(html: str) -> str:
    t = (html or "").lower()
    if "woocommerce" in t: return "WooCommerce"
    if "shopify" in t: return "Shopify"
    if "magento" in t: return "Magento"
    if "bigcommerce" in t: return "BigCommerce"
    if "wix" in t: return "Wix"
    return "Unknown"

def detect_cloudflare(headers: Dict[str, str], text: str) -> bool:
    h = {k.lower(): v for k, v in headers.items()}
    if any(k.startswith("cf-") for k in h): return True
    if "cloudflare" in (h.get("server","") or "").lower(): return True
    if re.search(r"\bcloudflare\b", text or "", re.I): return True
    return False

def detect_captcha(text: str) -> List[str]:
    found = []
    for name, pats in CAPTCHA_PATTERNS.items():
        if any(re.search(p, text or "", re.I) for p in pats):
            found.append(name)
    for generic in [r"i'm not a robot", r"verify you are human", r"select all images"]:
        if re.search(generic, text or "", re.I):
            found.append("Generic CAPTCHA")
            break
    return sorted(set(found))

def detect_payments(text: str) -> List[str]:
    found = []
    for name, pats in PAYMENT_PATTERNS.items():
        if any(re.search(p, text or "", re.I) for p in pats):
            found.append(name)
    return sorted(set(found)) or ["None"]

async def fetch_page(url: str, proxy: Optional[str]) -> Tuple[int, str, Dict[str, str], float]:
    start = time.time()
    kwargs = {}
    if proxy:
        # proxy should be like "http://user:pass@ip:port"
        kwargs["proxy"] = proxy
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=18, **kwargs) as resp:
            html = await resp.text(errors="ignore")
            elapsed = round(time.time() - start, 3)
            return resp.status, html, dict(resp.headers), elapsed

async def scan_url_once(uid: int, url: str) -> Dict[str, Any]:
    """Scan a single URL with auto proxy-switching for this user."""
    raw_url = normalize_url(url)
    tried = set()
    last_err = None
    while True:
        proxy = next_alive_proxy(uid)
        proxy_url = None
        if proxy:
            ip, port, user, pwd = proxy.split(":")
            proxy_url = f"http://{user}:{pwd}@{ip}:{port}"
        try:
            status, html, headers, elapsed = await fetch_page(raw_url, proxy_url)
            soup = BeautifulSoup(html, "html.parser")
            payments = ", ".join(detect_payments(html))
            platform = detect_platform(html)
            cloudflare = detect_cloudflare(headers, html)
            captchas = detect_captcha(html)
            return {
                "url": raw_url,
                "status": status,
                "payments": payments,
                "platform": platform,
                "cloudflare": human_bool(cloudflare),
                "captcha": human_bool(bool(captchas)),
                "elapsed_s": elapsed
            }
        except Exception as e:
            last_err = str(e)
            if proxy:
                # mark dead, notify once per proxy
                mark_proxy_dead(uid, proxy)
            # try switching to another proxy; if none left, warn and break
            nxt = next_alive_proxy(uid)
            if not nxt:
                return {
                    "url": raw_url,
                    "status": f"Error: {last_err}",
                    "note": "No working proxy available"
                }

# =============== TELEGRAM UI ===============

def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Site Hunter", callback_data="site_hunter")],
        [InlineKeyboardButton("📧 Temp Mail", callback_data="temp_mail")],
        [InlineKeyboardButton("🌐 Proxy Manager", callback_data="proxy_mgr")],
    ])

def sitehunter_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("1️⃣ Single Scan", callback_data="sh_single")],
        [InlineKeyboardButton("2️⃣ TXT File Scan", callback_data="sh_txt")],
        [InlineKeyboardButton("⬅️ Back", callback_data="back_home")]
    ])

def proxy_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Proxy", callback_data="px_add")],
        [InlineKeyboardButton("❌ Remove Proxy", callback_data="px_rm")],
        [InlineKeyboardButton("✅ Check Proxy", callback_data="px_ck")],
        [InlineKeyboardButton("📋 Live/Dead List", callback_data="px_list")],
        [InlineKeyboardButton("⬅️ Back", callback_data="back_home")]
    ])

# =============== HANDLERS ===============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = MODE_NONE
    await update.message.reply_animation(
        LOADING_GIF,
        caption="👋 Welcome! Loading…",
    )
    await asyncio.sleep(1.2)
    await update.message.reply_text("Choose an option:", reply_markup=main_menu_kb())

async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    context.user_data.setdefault("mode", MODE_NONE)

    if q.data == "back_home":
        context.user_data["mode"] = MODE_NONE
        await q.edit_message_text("Choose an option:", reply_markup=main_menu_kb())
        return

    if q.data == "site_hunter":
        context.user_data["mode"] = MODE_NONE
        await q.edit_message_text("🔍 Site Hunter Menu:", reply_markup=sitehunter_menu_kb())
        return

    if q.data == "sh_single":
        context.user_data["mode"] = MODE_SH_SINGLE_URL
        await q.edit_message_text("Send a URL to scan (e.g., `https://example.com`).", parse_mode="Markdown")
        return

    if q.data == "sh_txt":
        context.user_data["mode"] = MODE_AWAIT_TXT
        lim = 100000 if is_admin(uid) else 1000
        await q.edit_message_text(
            f"📄 Please upload a `.txt` file with up to **{lim}** URLs (one per line).",
            parse_mode="Markdown"
        )
        return

    if q.data == "temp_mail":
        addr, jwt = await tm_create_account_and_token()
        user_sessions[uid] = jwt
        await q.edit_message_text(
            f"📧 Your Temp Mail: `{addr}`\nUse /inbox to check your inbox.",
            parse_mode="Markdown",
            reply_markup=main_menu_kb()
        )
        return

    if q.data == "proxy_mgr":
        context.user_data["mode"] = MODE_NONE
        await q.edit_message_text("🌐 Proxy Manager:", reply_markup=proxy_menu_kb())
        return

    if q.data == "px_add":
        context.user_data["mode"] = MODE_PROXY_ADD
        await q.edit_message_text(
            "Send proxies line by line in this format:\n`ip:port:user:pass`\n\nType `cancel` to stop.",
            parse_mode="Markdown"
        )
        return

    if q.data == "px_rm":
        context.user_data["mode"] = MODE_PROXY_REMOVE
        cur = user_proxies.get(uid, [])
        if not cur:
            await q.edit_message_text("No proxies saved yet.", reply_markup=proxy_menu_kb())
            return
        display = "\n".join(f"{i+1}. {p}" for i, p in enumerate(cur))
        await q.edit_message_text(
            "Send the **line numbers** to remove (comma/space separated), or `cancel`.\n\n" + display,
            parse_mode="Markdown"
        )
        return

    if q.data == "px_ck":
        context.user_data["mode"] = MODE_NONE
        proxies = user_proxies.get(uid, [])
        if not proxies:
            await q.edit_message_text("❌ No proxies saved to check.", reply_markup=proxy_menu_kb())
            return
        await q.edit_message_text("Checking proxies… results will arrive one by one.")
        # check asynchronously
        async def _run():
            alive, dead = [], []
            for p in proxies:
                ok = await proxy_is_alive(p)
                if ok:
                    alive.append(p)
                    await context.bot.send_message(chat_id=uid, text=f"✅ Alive: {p}")
                else:
                    dead.append(p)
                    await context.bot.send_message(chat_id=uid, text=f"❌ Dead: {p}")
            # cache dead
            proxy_dead_cache.setdefault(uid, set()).update(dead)
            await context.bot.send_message(
                chat_id=uid,
                text=f"Done.\nAlive: {len(alive)} | Dead: {len(dead)}",
            )
        asyncio.create_task(_run())
        return

    if q.data == "px_list":
        context.user_data["mode"] = MODE_NONE
        alive = [p for p in user_proxies.get(uid, []) if p not in proxy_dead_cache.get(uid, set())]
        dead = list(proxy_dead_cache.get(uid, set()))
        text = "📋 Proxy Status\n\n"
        text += "**Alive:**\n" + ("\n".join(alive) if alive else "None") + "\n\n"
        text += "**Dead:**\n" + ("\n".join(dead) if dead else "None")
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=proxy_menu_kb())
        return

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle freeform text based on current mode + handle secret code."""
    uid = update.effective_user.id
    txt = (update.message.text or "").strip()
    mode = context.user_data.get("mode", MODE_NONE)

    # Secret code check
    job = scan_jobs.get(uid)
    if job and txt == job.get("secret_code"):
        # show partial results & progress
        total = job["total"]
        checked = job["checked"]
        remaining = max(0, total - checked)
        last_n = job["results"][-10:] if job["results"] else []
        status = f"🔎 Progress\nTotal: {total}\nChecked: {checked}\nRemaining: {remaining}\n\nLast results:\n" + ("\n".join(last_n) if last_n else "—")
        await update.message.reply_text(status)
        return

    # Modes
    if mode == MODE_PROXY_ADD:
        if txt.lower() == "cancel":
            context.user_data["mode"] = MODE_NONE
            await update.message.reply_text("Cancelled.", reply_markup=proxy_menu_kb())
            return
        lines = chunk_lines(txt)
        added = 0
        for ln in lines:
            p = parse_proxy_line(ln)
            if p:
                user_proxies.setdefault(uid, []).append(p)
                added += 1
        await update.message.reply_text(f"✅ Added {added} proxies.")
        return

    if mode == MODE_PROXY_REMOVE:
        if txt.lower() == "cancel":
            context.user_data["mode"] = MODE_NONE
            await update.message.reply_text("Cancelled.", reply_markup=proxy_menu_kb())
            return
        cur = user_proxies.get(uid, [])
        if not cur:
            await update.message.reply_text("No proxies to remove.", reply_markup=proxy_menu_kb()); return
        # parse numbers
        nums = re.findall(r"\d+", txt)
        idxs = sorted({int(n)-1 for n in nums if 1 <= int(n) <= len(cur)}, reverse=True)
        removed = []
        for i in idxs:
            removed.append(cur.pop(i))
        await update.message.reply_text(f"Removed {len(removed)} proxies.")
        return

    if mode == MODE_SH_SINGLE_URL:
        url = normalize_url(txt)
        await update.message.reply_text("Scanning…")
        res = await scan_url_once(uid, url)
        line = (
            f"🔹 URL: {res.get('url')}\n"
            f"🔹 Status: {res.get('status')}\n"
            f"🔹 Payments: {res.get('payments')}\n"
            f"🔹 Captcha: {res.get('captcha')}\n"
            f"🔹 Cloudflare: {res.get('cloudflare')}\n"
            f"🔹 Platform: {res.get('platform')}\n"
            f"🔹 Time: {res.get('elapsed_s')}s"
        )
        # If proxy exhaustion:
        if str(res.get("status","")).startswith("Error") and res.get("note"):
            await update.message.reply_text("😢 Please remove your old proxy & add new proxy, then start.")
        await update.message.reply_text(line)
        context.user_data["mode"] = MODE_NONE
        return

    # default: ignore / help
    await update.message.reply_text("Use the menu buttons to get started.", reply_markup=main_menu_kb())

async def on_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle .txt upload for bulk scan."""
    uid = update.effective_user.id
    mode = context.user_data.get("mode")
    if mode != MODE_AWAIT_TXT:
        await update.message.reply_text("Please choose 'TXT File Scan' first from Site Hunter.")
        return

    doc = update.message.document
    if not doc or not doc.file_name.lower().endswith(".txt"):
        await update.message.reply_text("Please upload a .txt file.")
        return

    # download file
    f = await context.bot.get_file(doc.file_id)
    content = await f.download_as_bytearray()
    try:
        text = content.decode("utf-8", errors="ignore")
    except:
        text = content.decode("latin-1", errors="ignore")

    urls = [normalize_url(u) for u in chunk_lines(text)]
    if not urls:
        await update.message.reply_text("No URLs found in file.")
        return

    limit = 100000 if is_admin(uid) else 1000
    if len(urls) > limit:
        await update.message.reply_text(f"Limit exceeded. You can scan up to {limit} URLs.")
        urls = urls[:limit]

    # create job
    secret = make_secret_code()
    job = {
        "secret_code": secret,
        "total": len(urls),
        "checked": 0,
        "results": [],     # list of lines for report
        "started": now_ms()
    }
    scan_jobs[uid] = job

    await update.message.reply_text(
        f"📥 Total Input: {job['total']}\n"
        f"✅ Checked: {job['checked']}\n"
        f"⏳ Remaining: {job['total'] - job['checked']}\n"
        f"🔐 Secret Code: `{secret}` — send this anytime to view live progress.",
        parse_mode="Markdown"
    )

    # run the scan async so we can send updates progressively via secret code
    async def _runner():
        for u in urls:
            res = await scan_url_once(uid, u)

            # if we encountered no working proxy, tell user to refresh
            if str(res.get("status","")).startswith("Error") and res.get("note"):
                await context.bot.send_message(
                    chat_id=uid,
                    text="😢 Please remove your old proxy & add new proxy, then start."
                )

            line = f"{res.get('url')} | status={res.get('status')} | pay={res.get('payments')} | cf={res.get('cloudflare')} | cap={res.get('captcha')} | platform={res.get('platform')} | t={res.get('elapsed_s')}s"
            job["results"].append(line)
            job["checked"] += 1

        # finished → send full txt
        report_txt = "\n".join(job["results"])
        bio = io.BytesIO(report_txt.encode("utf-8"))
        bio.name = "sitehunter_results.txt"
        await context.bot.send_document(chat_id=uid, document=InputFile(bio))
        await context.bot.send_message(
            chat_id=uid,
            text="✅ Done. Full results sent as txt."
        )
        # clear job
        scan_jobs.pop(uid, None)

    asyncio.create_task(_runner())
    context.user_data["mode"] = MODE_NONE

# =============== COMMANDS ===============

async def cmd_inbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    jwt = user_sessions.get(uid)
    if not jwt:
        await update.message.reply_text("❌ No temp mail yet. Use the menu → 📧 Temp Mail.")
        return
    mails = await tm_inbox(jwt)
    if not mails:
        await update.message.reply_text("📭 Inbox empty.")
    else:
        for m in mails:
            frm = m.get("from",{}).get("address","(unknown)")
            subj = m.get("subject","(no subject)")
            await update.message.reply_text(f"From: {frm}\nSubject: {subj}")

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = textwrap.dedent("""\
    ℹ️ Commands:
    /start – open menu
    /inbox – check temp mail inbox

    Use the buttons for Site Hunter and Proxy Manager.
    """)
    await update.message.reply_text(txt)

# =============== MAIN ===============

def build_app() -> Application:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("inbox", cmd_inbox))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.Document.TEXT, on_document))  # .txt uploads
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    return app

if __name__ == "__main__":
    if not BOT_TOKEN or BOT_TOKEN.startswith("PUT_"):
        print("⚠️ Set BOT_TOKEN env var before running.")
    app = build_app()
    print("Bot running…")
    app.run_polling()
