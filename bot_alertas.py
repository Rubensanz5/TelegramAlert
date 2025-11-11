import os
import requests
from bs4 import BeautifulSoup
import json
import random
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from datetime import time

productos = [
    {
        "nombre": "Samsung Odyssey OLED G8",
        "url_pccomponentes": "https://www.pccomponentes.com/monitor-samsung-odyssey-oled-g8-ls32fg816suxen-32-qd-oled-ultrahd-4k-240hz-003ms-hdr400-freesync-premium-pro",
        "url_amazon": "https://www.amazon.es/SAMSUNG-LS32DG802SUXEN-FreeSync-Antirreflejos-Plateado/dp/B0DFVCV1XL/ref=sr_1_1_mod_primary_new?__mk_es_ES=%C3%85M%C3%85%C5%BD%C3%95%C3%91&sbo=RZvfv%2F%2FHxDF%2BO5021pAnSA%3D%3D&sr=8-1",
        "precio_minimo": 994.32
    },
    {
        "nombre": "MSI MPG 321URXW",
        "url_pccomponentes": "https://www.pccomponentes.com/monitor-msi-mpg-321urxw-qd-oled-315-qd-oled-ultrahdt-4k-240hz-003ms-hdr-400-adaptive-sync-usb-c",
        "url_amazon": "https://www.amazon.es/MSI-321URXW-QD-OLED-Monitor-cu%C3%A1nticos/dp/B0BSN2BXC5/ref=sr_1_1",
        "precio_minimo": 849.00
    },
    {
        "nombre": "Gigabyte AORUS FO32U2P",
        "url_pccomponentes": "https://www.pccomponentes.com/monitor-gigabyte-aorus-fo32u2p-315-qd-oled-ultrahd-4k-240hz-freesync-premium",
        "url_amazon": "https://www.amazon.es/Gigabyte-Monitor-Juegos-AORUS-FO32U2P/dp/B0CYQG1LZX/ref=sr_1_1",
        "precio_minimo": 799.00
    }
]

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

archivo_historial = "precios.json"
MIN_DELAY = 3
MAX_DELAY = 7

def cargar_historial():
    try:
        with open(archivo_historial, "r") as f:
            return json.load(f)
    except:
        return {}

def guardar_historial(historial):
    with open(archivo_historial, "w") as f:
        json.dump(historial, f, indent=2)

def obtener_precio(url, tienda):
    headers = {"User-Agent": "Mozilla/5.0", "Accept-Language": "es-ES,es;q=0.9"}
    try:
        page = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(page.text, "html.parser")
        if tienda == "pc":
            tag = soup.find("span", class_="product-sales-price")
        else:
            tag = soup.find("span", class_="a-price-whole")
        if tag:
            return float(tag.text.replace(".", "").replace("€", "").replace(",", "."))
    except:
        return None

async def revisar(context: ContextTypes.DEFAULT_TYPE):
    historial = cargar_historial()
    for p in productos:
        for tienda, url in [("pc", p["url_pccomponentes"]), ("amazon", p["url_amazon"])]:
            precio = obtener_precio(url, tienda)
            if not precio:
                continue
            clave = f"{p['nombre']}_{tienda}"
            if clave in historial and historial[clave] != precio:
                await context.bot.send_message(CHAT_ID, f"🔔 {p['nombre']} cambio de precio ({tienda}): {historial[clave]}€ → {precio}€")
            if precio <= p["precio_minimo"]:
                await context.bot.send_message(CHAT_ID, f"🔥 BAJADA! {p['nombre']} en {tienda}: {precio}€ (mínimo {p['precio_minimo']}€)")
            historial[clave] = precio
    guardar_historial(historial)

async def comando_revisa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⌛ Revisando precios...")
    await revisar(context)
    await update.message.reply_text("✅ Revisión manual completada.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("revisa", comando_revisa))
    app.job_queue.run_daily(revisar, time(hour=11))
    app.job_queue.run_daily(revisar, time(hour=23))
    print("✅ Bot activo con revisiones automáticas 11:00 y 23:00")
    app.run_polling()

if __name__ == "__main__":
    main()
