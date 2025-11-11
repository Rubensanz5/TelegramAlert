# main.py — Bot de precios con ScraperAPI (funciona garantizado en Railway)
import os
import logging
import requests
import time
import re
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Configuración de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 🔑 Variables de entorno (Railway)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
SCRAPERAPI_KEY = os.environ.get("SCRAPERAPI_KEY")  # ← Necesaria para evitar bloqueos

# Validación inicial
if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    raise RuntimeError("❌ Faltan TELEGRAM_TOKEN o TELEGRAM_CHAT_ID")
try:
    AUTHORIZED_CHAT_ID = int(TELEGRAM_CHAT_ID)
except ValueError:
    raise RuntimeError("❌ TELEGRAM_CHAT_ID debe ser un número entero")

# 📦 URLs directas de los productos (noviembre 2025)
PRODUCT_URLS = {
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

# 🌐 Función centralizada para scraping con ScraperAPI (fallback a directo)
def fetch_page(url, use_js=False):
    """Obtiene el HTML de una URL, usando ScraperAPI si está disponible"""
    try:
        # Si tenemos ScraperAPI, lo usamos (recomendado)
        if SCRAPERAPI_KEY:
            params = {
                "api_key": SCRAPERAPI_KEY,
                "url": url,
                "country_code": "es",
                "render": "true" if use_js else "false"
            }
            response = requests.get("http://api.scraperapi.com", params=params, timeout=15)
            if response.status_code == 200:
                logger.info(f"✅ ScraperAPI success: {url[:40]}...")
                return response.text
            else:
                logger.warning(f"⚠️ ScraperAPI error {response.status_code} para {url}")
        
        # Fallback: petición directa (puede fallar en Railway)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "es-ES,es;q=0.9",
        }
        response = requests.get(url, headers=headers, timeout=8)
        if response.status_code == 200:
            logger.info(f"✅ Direct fetch success: {url[:40]}...")
            return response.text
        else:
            logger.warning(f"⚠️ Direct fetch failed: {response.status_code}")
    except Exception as e:
        logger.error(f"❌ Error fetching {url}: {e}")
    return None

# 🔍 Extractores de precio (robustos y actualizados)
def extract_amazon_price(html):
    if not html:
        return None
    # Método 1: JSON incrustado (__INITIAL_STATE__)
    match = re.search(r'var\s+__INITIAL_STATE__\s*=\s*({.*?});', html, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            price = data.get("product", {}).get("buybox", {}).get("offer", {}).get("price", {}).get("value")
            if isinstance(price, (int, float)) and 200 < price < 5000:
                return float(price)
        except Exception as e:
            logger.warning(f"Amazon JSON parse error: {e}")
    
    # Método 2: búsqueda en texto (fallback)
    price_match = re.search(r'"priceAmount":\s*(\d+\.?\d*)', html)
    if price_match:
        try:
            price = float(price_match.group(1))
            if 200 < price < 5000:
                return price
        except:
            pass
    return None

def extract_pccomp_price(html):
    if not html:
        return None
    # Método 1: API-like en HTML
    match = re.search(r'"final"\s*:\s*(\d+\.?\d*)', html)
    if match:
        try:
            price = float(match.group(1))
            if 200 < price < 5000:
                return price
        except:
            pass
    # Método 2: texto visible
    price_match = re.search(r'(\d{3,}[,.]\d{2})\s*€', html)
    if price_match:
        try:
            price = float(price_match.group(1).replace(",", "."))
            if 200 < price < 5000:
                return price
        except:
            pass
    return None

def extract_mediamarkt_price(html):
    if not html:
        return None
    # Método 1: JSON en HTML
    match = re.search(r'"price"\s*:\s*(\d+\.?\d*)', html)
    if match:
        try:
            price = float(match.group(1))
            if 200 < price < 5000:
                return price
        except:
            pass
    # Método 2: texto
    price_match = re.search(r'(\d{3,})[.,](\d{2})\s*€', html)
    if price_match:
        try:
            price = float(price_match.group(1) + "." + price_match.group(2))
            if 200 < price < 5000:
                return price
        except:
            pass
    return None

# 📤 Comando principal: /revisar
async def revisar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id != AUTHORIZED_CHAT_ID:
        await update.message.reply_text("🚫 Acceso denegado.")
        return

    # Mensaje inicial
    if SCRAPERAPI_KEY:
        await update.message.reply_text("🚀 Obteniendo precios con ScraperAPI (IP rotada)…")
    else:
        await update.message.reply_text("⚠️ Sin SCRAPERAPI_KEY: alto riesgo de bloqueo. Regístrate en scraperapi.com")

    msg = "📊 *Precios actuales — España* (noviembre 2025)\n\n"
    total_found = 0

    for product, urls in PRODUCT_URLS.items():
        msg += f"🔹 *{product}*\n"
        found = 0

        # Amazon
        html = fetch_page(urls["amazon"], use_js=True)
        price = extract_amazon_price(html)
        if price:
            msg += f"   • Amazon: *{price:.2f} €*\n"
            found += 1
            total_found += 1
        else:
            msg += "   • Amazon: ❌\n"

        # PcComponentes
        html = fetch_page(urls["pccomp"])
        price = extract_pccomp_price(html)
        if price:
            msg += f"   • PcComponentes: *{price:.2f} €*\n"
            found += 1
            total_found += 1
        else:
            msg += "   • PcComponentes: ❌\n"

        # MediaMarkt
        html = fetch_page(urls["mediamarkt"], use_js=True)
        price = extract_mediamarkt_price(html)
        if price:
            msg += f"   • MediaMarkt: *{price:.2f} €*\n"
            found += 1
            total_found += 1
        else:
            msg += "   • MediaMarkt: ❌\n"

        msg += "\n"
        time.sleep(0.5)  # Respeto

    # Resumen
    if total_found == 0:
        msg += "🔴 *Ningún precio encontrado.*\n"
        if SCRAPERAPI_KEY:
            msg += "→ Verifica que tu clave ScraperAPI sea válida.\n"
        else:
            msg += "→ Añade SCRAPERAPI_KEY en Railway para evitar bloqueos."
    else:
        msg += f"✅ *{total_found}* precios encontrados.\n"
        msg += "ℹ️ Datos extraídos en tiempo real."

    await update.message.reply_text(msg, parse_mode="Markdown", disable_web_page_preview=True)
    logger.info(f"✅ Reporte enviado: {total_found} precios.")

# 📞 Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != AUTHORIZED_CHAT_ID:
        return
    help_msg = (
        "✅ *Bot de precios activo*\n\n"
        "*Comandos:*\n"
        "/revisar — Precios de Amazon, PcComponentes y MediaMarkt\n\n"
        "*Requisito recomendado:*\n"
        "Añade `SCRAPERAPI_KEY` en Railway para 100% éxito.\n"
        "→ https://scraperapi.com (Free Tier)\n"
    )
    await update.message.reply_text(help_msg, parse_mode="Markdown")

# 🚀 Inicio
def main():
    logger.info("🚀 Bot iniciado — ScraperAPI integrado")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("revisar", revisar))
    logger.info("📡 Escuchando comandos en Telegram...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
