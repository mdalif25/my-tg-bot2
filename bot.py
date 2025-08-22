import os, io, asyncio, random, string, time, re, textwrap
from typing import List, Dict, Any, Optional, Tuple

import aiohttp
from bs4 import BeautifulSoup
from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton,
    InputFile
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

# =============== CONFIG & STATE ===============

BOT_TOKEN = os.getenv("BOT_TOKEN", "PUT_YOUR_TOKEN_HERE")
# Comma-separated Telegram user IDs who are admins
ADMIN_IDS = list(map(int, filter(None, os.getenv("ADMIN_IDS", "").split(","))))  # e.g. "123,456"

LOADING_GIF = "https://media.giphy.com/media/xTk9ZvMnbIiIew7IpW/giphy.gif"
MAILTM_API = "https://api.mail.tm"

# state stores
user_sessions: Dict[int, str] = {}     # temp mail JWT per user
user_proxies: Dict[int, List[str]] = {}  # proxies per user ["ip:port:user:pass", ...]
proxy_dead_cache: Dict[int, set] = {}     # per-user dead set
scan_jobs: Dict[int, Dict[str, Any]] = {} # active scan jobs per user

# per-user “modes” for freeform inputs (add proxy, remove proxy, single scan url, etc.)
MODE_NONE = "none"
MODE_PROXY_ADD = "proxy_add"
MODE_PROXY_REMOVE = "proxy_remove"
MODE_SH_SINGLE_URL = "sh_single_url"
MODE_AWAIT_TXT = "await_txt"
MODE_PROXY_CHECK_INLINE = "proxy_check_inline"   # optional

# =============== HELPERS ===============

def is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS

def normalize_url(u: str) -> str:
    u = (u or "").strip()
    if not u:
        return u
    if not u.startswith(("http://", "https://")):
        u = "http://" + u
    return u

def chunk_lines(s: str) -> List[str]:
    raw = [ln.strip() for ln in s.replace("\r", "\n").split("\n")]
    return [ln for ln in raw if ln]

def now_ms() -> int:
    return int(time.time() * 1000)

def make_secret_code() -> str:
    return "#" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

def human_bool(v: bool) -> str:
    return "True 😢" if v else "False 🔥"

def clamp(n: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, n))

# =============== TEMP MAIL (mail.tm) ===============

async def tm_create_account_and_token() -> Tuple[str, str]:
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
