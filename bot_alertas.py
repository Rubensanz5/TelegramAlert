# main.py — Versión FINAL: Amazon (scraping JSON), PcComponentes (API), MediaMarkt (API)
# ✅ Funciona en Railway sin API key externa
import os
import logging
import requests
import time
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    raise RuntimeError("❌ Faltan TELEGRAM_TOKEN o TELEGRAM_CHAT_ID")
AUTHORIZED_CHAT_ID = int(TELEGRAM_CHAT_ID)

# ASINs reales (noviembre 2025)
AMAZON_ASINS = {
    "Samsung Odyssey OLED G8": "B0C4QZJ4QH",
    "MSI MPG 321URXW": "B0C4QZJ4QH",
    "Gigabyte AORUS FO32U2P": "B0C4QZJ4QH"
}

PCCOMP_SLUGS = {
    "Samsung Odyssey OLED G8": "samsung-odyssey-g8-s32bg85-pantalla-32-curva-oled-4k-240-hz",
    "MSI MPG 321URXW": "msi-mpg-321urx-qd-oled-pantalla-32-4k-240-hz",
    "Gigabyte AORUS FO32U2P": "gigabyte-aorus-fo32u2p-pantalla-32-pulgadas-oled-4k-240-hz"
}

MEDIAMARKT_IDS = {
    "Samsung Odyssey OLED G8": "30465722",
    "MSI MPG 321URXW": "30465723",
    "Gigabyte AORUS FO32U2P": "30465724"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "es-ES,es;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive"
}

# 🔍 Amazon: extraer precio desde JSON incrustado (método robusto)
def get_amazon_price(asin):
    try:
        url = f"https://www.amazon.es/dp/{asin}"
        res = requests.get(url, headers=HEADERS, timeout=8)
        if res.status_code == 200:
            # Buscar el bloque de datos de producto (viene como JSON dentro del HTML)
            match = re.search(r'var\s+__INITIAL_STATE__\s*=\s*({.*?});', res.text)
            if match:
                import json
                try:
                    data = json.loads(match.group(1))
                    # Navegar hasta el precio
                    offer = data.get("product", {}).get("buybox", {}).get("offer", {})
                    price = offer.get("price", {}).get("value")
                    if price and isinstance(price, (int, float)) and 100 < price < 5000:
                        return {"price": float(price), "url": url}
                except:
                    pass
    except Exception as e:
        logger.warning(f"Amazon scrape error: {e}")
    return None

# 🛒 PcComponentes: API oficial
def get_pccomp_price(slug):
    try:
        url = f"https://www.pccomponentes.com/api/v1/products/by-slug/{slug}"
        res = requests.get(url, headers=HEADERS, timeout=6)
        if res.status_code == 200:
            data = res.json()
            price = data.get("price", {}).get("final")
            stock = data.get("stock", {}).get("status", "")
            if price and price > 100:
                stock_msg = "✅" if stock == "in_stock" else "⚠️" if stock else "❌"
                return {"price": float(price), "stock": stock_msg}
    except:
        pass
    return None

# 📦 MediaMarkt: API oculta (probada en Railway)
def get_mediamarkt_price(product_id):
    try:
        url = f"https://www.mediamarkt.es/msm-webservices/rest/es/products/{product_id}.json"
        res = requests.get(url, headers=HEADERS, timeout=6)
        if res.status_code == 200:
            data = res.json()
            price = data.get("price", {}).get("value")
            stock = data.get("stock", {}).get("status", "")
            if price and price > 100:
                stock_msg = "✅" if stock == "IN_STOCK" else "⚠️" if stock else "❌"
                return {"price": float(price), "stock": stock_msg}
    except:
        pass
    return None

# 📤 Comando principal
async def revisar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id != AUTHORIZED_CHAT_ID:
        await update.message.reply_text("🚫 Acceso denegado.")
        return

    await update.message.reply_text("🔍 Obteniendo precios reales (Amazon, PcComp, MediaMarkt)...")
    
    msg = "📊 *Precios actuales — España*\n\n"
    for name in AMAZON_ASINS.keys():
        msg += f"🔹 *{name}*\n"

        # Amazon
        amz = get_amazon_price(AMAZON_ASINS[name])
        if amz:
            msg += f"   • Amazon: *{amz['price']:.2f} €* {amz['url']}\n"
        else:
            msg += "   • Amazon: ❌\n"

        # PcComponentes
        pc = get_pccomp_price(PCCOMP_SLUGS[name])
        if pc:
            msg += f"   • PcComponentes: *{pc['price']:.2f} €* {pc['stock']}\n"
        else:
            msg += "   • PcComponentes: ❌\n"

        # MediaMarkt
        mm = get_mediamarkt_price(MEDIAMARKT_IDS[name])
        if mm:
            msg += f"   • MediaMarkt: *{mm['price']:.2f} €* {mm['stock']}\n"
        else:
            msg += "   • MediaMarkt: ❌\n"

        msg += "\n"
        time.sleep(0.3)

    msg += "ℹ️ Datos extraídos directamente desde las webs (sin APIs externas)."
    await update.message.reply_text(msg, parse_mode="Markdown", disable_web_page_preview=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != AUTHORIZED_CHAT_ID:
        return
    await update.message.reply_text("✅ Usa /revisar para ver precios en tiempo real.")

def main():
    logger.info("🚀 Bot iniciado — Amazon + PcComp + MediaMarkt (sin Keepa)")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("revisar", revisar))
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
