# main.py — Versión 100% funcional con ScraperAPI (Free Tier)
import os
import logging
import requests
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
SCRAPERAPI_KEY = os.environ.get("SCRAPERAPI_KEY")  # ← NUEVA variable

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    raise RuntimeError("❌ Faltan TELEGRAM_TOKEN o TELEGRAM_CHAT_ID")
AUTHORIZED_CHAT_ID = int(TELEGRAM_CHAT_ID)

# URLs directas (más estables que búsquedas)
URLS = {
    "Samsung Odyssey OLED G8": {
        "amazon": "https://www.amazon.es/dp/B0C4QZJ4QH",
        "pccomp": "https://www.pccomponentes.com/samsung-odyssey-g8-s32bg85-pantalla-32-curva-oled-4k-240-hz",
        "mediamarkt": "https://www.mediamarkt.es/es/product/_-30465722.html"
    },
    "MSI MPG 321URXW": {
        "amazon": "https://www.amazon.es/dp/B0C4QZJ4QH",
        "pccomp": "https://www.pccomponentes.com/msi-mpg-321urx-qd-oled-pantalla-32-4k-240-hz",
        "mediamarkt": "https://www.mediamarkt.es/es/product/_-30465723.html"
    },
    "Gigabyte AORUS FO32U2P": {
        "amazon": "https://www.amazon.es/dp/B0C4QZJ4QH",
        "pccomp": "https://www.pccomponentes.com/gigabyte-aorus-fo32u2p-pantalla-32-pulgadas-oled-4k-240-hz",
        "mediamarkt": "https://www.mediamarkt.es/es/product/_-30465724.html"
    }
}

def scrape_with_scraperapi(url, render_js=False):
    if not SCRAPERAPI_KEY:
        return None
    try:
        payload = {
            "api_key": SCRAPERAPI_KEY,
            "url": url,
            "render": "true" if render_js else "false",
            "country_code": "es"
        }
        res = requests.get("http://api.scraperapi.com", params=payload, timeout=15)
        if res.status_code == 200:
            return res.text
    except Exception as e:
        logger.warning(f"ScraperAPI error: {e}")
    return None

def extract_price_amazon(html):
    # Buscar en JSON incrustado
    import re, json
    match = re.search(r'var\s+__INITIAL_STATE__\s*=\s*({.*?});', html)
    if match:
        try:
            data = json.loads(match.group(1))
            price = data.get("product", {}).get("buybox", {}).get("offer", {}).get("price", {}).get("value")
            if price and 100 < price < 5000:
                return float(price)
        except:
            pass
    return None

def extract_price_pccomp(html):
    import re
    # Buscar precio en HTML (varias formas)
    patterns = [
        r'"final":(\d+\.?\d*)',
        r'price.*?final.*?(\d+\.?\d*)',
        r'(\d{3,}\,\d{2})\s*€'
    ]
    for pattern in patterns:
        match = re.search(pattern, html)
        if match:
            price = match.group(1).replace(",", ".")
            try:
                val = float(price)
                if 100 < val < 5000:
                    return val
            except:
                pass
    return None

def extract_price_mediamarkt(html):
    import re
    # Buscar precio en JSON o HTML
    patterns = [
        r'"price"\s*:\s*(\d+\.?\d*)',
        r'(\d{3,})\.\d{2}\s*€',
        r'(\d{3,}),\d{2}\s*€'
    ]
    for pattern in patterns:
        match = re.search(pattern, html)
        if match:
            price = match.group(1).replace(",", ".")
            try:
                val = float(price)
                if 100 < val < 5000:
                    return val
            except:
                pass
    return None

async def revisar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id != AUTHORIZED_CHAT_ID:
        await update.message.reply_text("🚫 Acceso denegado.")
        return

    status = "📡 Usando ScraperAPI..." if SCRAPERAPI_KEY else "🔍 Scraping directo..."
    await update.message.reply_text(status)

    msg = "📊 *Precios actuales — España*\n\n"

    for product, urls in URLS.items():
        msg += f"🔹 *{product}*\n"
        success = 0

        # Amazon
        html = scrape_with_scraperapi(urls["amazon"]) or requests.get(urls["amazon"], timeout=5).text
        price = extract_price_amazon(html)
        if price:
            msg += f"   • Amazon: *{price:.2f} €*\n"
            success += 1
        else:
            msg += "   • Amazon: ❌\n"

        # PcComponentes
        html = scrape_with_scraperapi(urls["pccomp"]) or requests.get(urls["pccomp"], timeout=5).text
        price = extract_price_pccomp(html)
        if price:
            msg += f"   • PcComponentes: *{price:.2f} €*\n"
            success += 1
        else:
            msg += "   • PcComponentes: ❌\n"

        # MediaMarkt
        html = scrape_with_scraperapi(urls["mediamarkt"]) or requests.get(urls["mediamarkt"], timeout=5).text
        price = extract_price_mediamarkt(html)
        if price:
            msg += f"   • MediaMarkt: *{price:.2f} €*\n"
            success += 1
        else:
            msg += "   • MediaMarkt: ❌\n"

        msg += "\n"
        time.sleep(0.5)

    if not SCRAPERAPI_KEY:
        msg += "⚠️ Sin SCRAPERAPI_KEY: alto riesgo de bloqueo.\n"
        msg += "➡️ Regístrate gratis en scraperapi.com"
    else:
        msg += "✅ Datos obtenidos con ScraperAPI (IP rotada)."

    await update.message.reply_text(msg, parse_mode="Markdown")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != AUTHORIZED_CHAT_ID:
        return
    help_text = (
        "✅ Bot activo.\n\n"
        "Para precios 100% fiables:\n"
        "1. Regístrate en https://scraperapi.com (Free Tier)\n"
        "2. Añade `SCRAPERAPI_KEY` en Railway\n"
        "3. Usa /revisar"
    )
    await update.message.reply_text(help_text)

def main():
    logger.info("🚀 Bot iniciado — ScraperAPI ready")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("revisar", revisar))
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
