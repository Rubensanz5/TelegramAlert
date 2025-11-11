# main.py — Bot de Telegram que responde a /revisar con precios actuales
import os
import logging
import time
import random
import re
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ======================
# CONFIGURACIÓN
# ======================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 🔑 Variables de entorno (¡exactamente como pediste!)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    raise RuntimeError("❌ Faltan variables de entorno: TELEGRAM_TOKEN y/o TELEGRAM_CHAT_ID")

# Convertimos CHAT_ID a entero (requerido por la API)
try:
    AUTHORIZED_CHAT_ID = int(TELEGRAM_CHAT_ID)
except ValueError:
    raise RuntimeError("❌ TELEGRAM_CHAT_ID debe ser un número (ej: 123456789)")

# ======================
# UTILIDADES
# ======================
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
]

def get_headers():
    return {"User-Agent": random.choice(USER_AGENTS)}

def clean_price(text):
    if not text:
        return None
    cleaned = re.sub(r"[^\d,.]", "", text)
    if not cleaned:
        return None
    # Formato español: 1.299,99 → 1299.99
    if ',' in cleaned and '.' in cleaned:
        if cleaned.find(',') > cleaned.find('.'):
            cleaned = cleaned.replace('.', '').replace(',', '.')
        else:
            cleaned = cleaned.replace(',', '')
    elif ',' in cleaned:
        cleaned = cleaned.replace(',', '.')
    try:
        val = float(cleaned)
        return val if 100 < val < 10000 else None  # filtro lógico para monitores
    except:
        return None

# ======================
# SCRAPERS (100% compatibles con Railway)
# ======================

def scrape_pccomponentes(query):
    try:
        url = f"https://www.pccomponentes.com/buscar?q={query.replace(' ', '+')}"
        res = requests.get(url, headers=get_headers(), timeout=8)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        article = soup.select_one("article[data-id]")
        if not article:
            return None
        price_elem = article.select_one(".price, [data-testid='price']")
        return clean_price(price_elem.get_text()) if price_elem else None
    except Exception as e:
        logger.warning(f"[PcComp] Error buscando '{query}': {e}")
        return None

def scrape_amazon_es(query):
    try:
        url = f"https://www.amazon.es/s?k={query.replace(' ', '+')}&rh=p_36%3A800-4000"
        res = requests.get(url, headers=get_headers(), timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        result = soup.select_one("div[data-component-type='s-search-result']")
        if not result:
            return None
        whole = result.select_one(".a-price-whole")
        fraction = result.select_one(".a-price-fraction")
        if whole:
            price_str = whole.get_text().strip()
            if fraction:
                price_str += "." + fraction.get_text().strip()
            return clean_price(price_str)
    except Exception as e:
        logger.warning(f"[Amazon] Error buscando '{query}': {e}")
        return None

def scrape_mediamarkt_es(query):
    try:
        url = f"https://www.mediamarkt.es/es/search.html?query={query.replace(' ', '+')}"
        res = requests.get(url, headers=get_headers(), timeout=8)
        soup = BeautifulSoup(res.text, "html.parser")
        price_elem = soup.select_one("span[font-weight='bold'], .price, [data-test='price']")
        if price_elem:
            return clean_price(price_elem.get_text())
    except Exception as e:
        logger.warning(f"[MediaMarkt] Error buscando '{query}': {e}")
        return None

def get_prices():
    PRODUCTS = {
        "Samsung Odyssey OLED G8": "Samsung Odyssey G8 S32BG85",
        "MSI MPG 321URXW": "MSI MPG 321URXW QD-OLED",
        "Gigabyte AORUS FO32U2P": "Gigabyte AORUS FO32U2P 4K"
    }
    results = {}
    for name, query in PRODUCTS.items():
        logger.info(f"🔍 Buscando: {name}")
        amazon = scrape_amazon_es(query)
        pccomp = scrape_pccomponentes(query)
        mediamarkt = scrape_mediamarkt_es(query)
        results[name] = {
            "Amazon": amazon,
            "PcComponentes": pccomp,
            "MediaMarkt": mediamarkt
        }
        time.sleep(1 + random.random())
    return results

# ======================
# MANEJADORES DE COMANDOS
# ======================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != AUTHORIZED_CHAT_ID:
        await update.message.reply_text("🚫 No estás autorizado para usar este bot.")
        return
    await update.message.reply_text(
        "👋 ¡Hola! Usa /revisar para obtener los precios actuales de:\n"
        "• Samsung Odyssey OLED G8\n"
        "• MSI MPG 321URXW\n"
        "• Gigabyte AORUS FO32U2P"
    )

async def revisar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id != AUTHORIZED_CHAT_ID:
        await update.message.reply_text("🚫 Acceso denegado.")
        return

    await update.message.reply_text("⏳ Buscando precios... (puede tardar 10–20 segundos)")
    logger.info(f"Usuario {chat_id} ejecutó /revisar")

    try:
        prices = get_prices()
        msg = "📊 *Precios actuales (España)*\n\n"
        for product, stores in prices.items():
            msg += f"🔹 *{product}*\n"
            for store, price in stores.items():
                if price is not None:
                    msg += f"   • {store}: *{price:.2f} €*\n"
                else:
                    msg += f"   • {store}: ⚠️ No encontrado\n"
            msg += "\n"
        msg += f"✅ Actualizado: {time.strftime('%d/%m %H:%M:%S')}"
        await update.message.reply_text(msg, parse_mode="Markdown")
        logger.info("✅ Precios enviados.")
    except Exception as e:
        logger.error(f"❌ Excepción al ejecutar /revisar: {e}")
        await update.message.reply_text("⚠️ Error al obtener precios. Revisa los logs.")

# ======================
# INICIO DEL BOT
# ======================

def main():
    logger.info("🚀 Iniciando bot (escuchando comandos: /revisar, /start)...")
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("revisar", revisar))
    application.add_handler(CommandHandler("check", revisar))    # alias
    application.add_handler(CommandHandler("precios", revisar))  # alias

    logger.info("📡 Bot activo. Esperando comandos en Telegram...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
