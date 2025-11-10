import requests
from bs4 import BeautifulSoup
import json
import random
from datetime import datetime, time as dtime
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ------------------------------
# CONFIGURACIÓN DE PRODUCTOS
# ------------------------------
productos = [
    {
        "nombre": "Samsung Odyssey OLED G8",
        "url_pccomponentes": "https://www.pccomponentes.com/monitor-samsung-odyssey-oled-g8-ls32fg816suxen-32-qd-oled-ultrahd-4k-240hz-003ms-hdr400-freesync-premium-pro",
        "url_amazon": "https://www.amazon.es/SAMSUNG-LS32DG802SUXEN-FreeSync-Antirreflejos-Plateado/dp/B0DFVCV1XL/ref=sr_1_1_mod_primary_new?__mk_es_ES=%C3%85M%C3%85%C5%BD%C3%95%C3%91&sbo=RZvfv%2F%2FHxDF%2BO5021pAnSA%3D%3D&sr=8-1",
        "precio_minimo": 994.32
    },
    {
        "nombre": "MSI MPG 321URXW",
        "url_pccomponentes": "https://www.pccomponentes.com/monitor-msi-mpg-321urxw-qd-oled-315-qd-oled-ultrahd-4k-240hz-003ms-hdr-400-adaptive-sync-usb-c",
        "url_amazon": "https://www.amazon.es/MSI-321URXW-QD-OLED-Monitor-cu%C3%A1nticos/dp/B0BSN2BXC5/ref=sr_1_1?__mk_es_ES=%C3%85M%C3%85%C5%BD%C3%95%C3%91&sr=8-1",
        "precio_minimo": 849.00
    },
    {
        "nombre": "Gigabyte AORUS FO32U2P",
        "url_pccomponentes": "https://www.pccomponentes.com/monitor-gigabyte-aorus-fo32u2p-315-qd-oled-ultrahd-4k-240hz-freesync-premium",
        "url_amazon": "https://www.amazon.es/Gigabyte-Monitor-Juegos-AORUS-FO32U2P/dp/B0CYQG1LZX/ref=sr_1_1?__mk_es_ES=%C3%85M%C3%85%C5%BD%C3%95%C3%91&sr=8-1y",
        "precio_minimo": 799.00
    }
]

TOKEN = "7963591728:AAFVwQiaM5-QMgoeA01SABGDSMlo-rNoTeI"
CHAT_ID = "7963591728"
archivo_historial = "precios.json"
MIN_DELAY = 3
MAX_DELAY = 7

# ------------------------------
# FUNCIONES DEL BOT
# ------------------------------
def cargar_historial():
    try:
        with open(archivo_historial, "r") as f:
            return json.load(f)
    except:
        return {}

def guardar_historial(historial):
    with open(archivo_historial, "w") as f:
        json.dump(historial, f, indent=2)

def enviar_telegram(mensaje, context):
    context.bot.send_message(chat_id=CHAT_ID, text=mensaje)

def obtener_precio(url, tienda):
    headers_pc = {"User-Agent": "Mozilla/5.0"}
    headers_amazon = {"User-Agent": "Mozilla/5.0","Accept-Language": "es-ES,es;q=0.9"}
    for _ in range(3):
        try:
            if tienda == "pccomponentes":
                page = requests.get(url, headers=headers_pc, timeout=10)
                soup = BeautifulSoup(page.content, "html.parser")
                precio_tag = soup.find("span", class_="product-sales-price")
            else:
                page = requests.get(url, headers=headers_amazon, timeout=10)
                soup = BeautifulSoup(page.content, "html.parser")
                precio_tag = soup.find("span", class_="a-price-whole")
            if precio_tag:
                precio_str = precio_tag.text.strip().replace(".", "").replace(",", ".").replace("€","")
                return float(precio_str)
        except:
            continue
    return None

def revisar_precios(context):
    historial = cargar_historial()
    for p in productos:
        for tienda, url in [("pccomponentes", p["url_pccomponentes"]), ("amazon", p["url_amazon"])]:
            precio = obtener_precio(url, tienda)
            if precio is None:
                continue
            key = f"{p['nombre']}_{tienda}"
            if key in historial and historial[key] != precio:
                enviar_telegram(f"🔔 {p['nombre']} cambio de precio en {tienda}: {historial[key]}€ → {precio}€", context)
            if precio <= p["precio_minimo"]:
                enviar_telegram(f"🎯 {p['nombre']} bajó de su precio mínimo en {tienda}: {precio}€", context)
            historial[key] = precio
            import time; time.sleep(random.randint(MIN_DELAY, MAX_DELAY))
    guardar_historial(historial)

# ------------------------------
# COMANDO /revisa
# ------------------------------
async def comando_revisa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔎 Revisando precios manualmente...")
    revisar_precios(context)
    await update.message.reply_text("✅ Revisión manual completada.")

# ------------------------------
# TAREA AUTOMÁTICA
# ------------------------------
async def tarea_automatica(app):
    while True:
        ahora = datetime.now()
        # Ejecuta a las 11 AM o 11 PM
        if ahora.hour == 11 or ahora.hour == 23:
            revisar_precios(app)
            # Espera 60 segundos para no ejecutar dos veces en el mismo minuto
            await asyncio.sleep(60)
        else:
            await asyncio.sleep(30)  # Revisa la hora cada 30 segundos

# ------------------------------
# INICIAR BOT
# ------------------------------
async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("revisa", comando_revisa))
    
    # Ejecutar tarea automática en segundo plano
    app.create_task(tarea_automatica(app))
    
    print("Bot iniciado. Comando /revisa disponible y revisiones automáticas 11AM/11PM activas.")
    await app.run_polling()

# Ejecutar asyncio
import asyncio
asyncio.run(main())
