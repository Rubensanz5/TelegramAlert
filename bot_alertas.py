import os
import requests
from bs4 import BeautifulSoup
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from datetime import time

# Lista de productos
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
        "url_amazon": "https://www.amazon.es/Gigabyte-Monitor-Juegos-AORUS-FO32U2P/dp/B0CYQG1LZX/ref=sr_1_1?__mk_es_ES=%C3%85M%C3%85%C5%BD%C3%95%C3%91&sr=8-1",
        "precio_minimo": 799.00
    }
]

# Variables de entorno
TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Archivo para historial de precios
archivo_historial = "precios.json"

# ------------------ Funciones de historial ------------------
def cargar_historial():
    try:
        with open(archivo_historial, "r") as f:
            return json.load(f)
    except:
        return {}

def guardar_historial(historial):
    with open(archivo_historial, "w") as f:
        json.dump(historial, f, indent=2)

# ------------------ Función para obtener precio ------------------
def obtener_precio(url, tienda):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/118.0.5993.90 Safari/537.36",
        "Accept-Language": "es-ES,es;q=0.9"
    }
    try:
        page = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(page.text, "html.parser")

        if tienda == "pc":
            tag = soup.find("span", class_="product-sales-price") or \
                  soup.find("span", class_="precio")
            if tag:
                texto = tag.text.strip().replace(".", "").replace("€", "").replace(",", ".")
                return float(texto)

        elif tienda == "amazon":
            tag = soup.find("span", class_="a-offscreen")
            if tag:
                texto = tag.text.strip().replace("€", "").replace(".", "").replace(",", ".")
                return float(texto)

    except Exception as e:
        print(f"Error al obtener precio de {tienda} ({url}): {e}")

    return None

# ------------------ Función principal de revisión ------------------
async def revisar(context: ContextTypes.DEFAULT_TYPE):
    historial = cargar_historial()
    mensajes = []

    for p in productos:
        linea = f"📦 *{p['nombre']}*\n"
        for tienda, url in [("PCComponentes", p["url_pccomponentes"]), ("Amazon", p["url_amazon"])]:
            precio = obtener_precio(url, tienda.lower())
            clave = f"{p['nombre']}_{tienda.lower()}"

            if precio is None:
                linea += f"- {tienda}: ❌ no disponible\n"
            else:
                historial[clave] = precio
                if precio <= p["precio_minimo"]:
                    linea += f"- {tienda}: 🔥 *{precio}€* (mínimo {p['precio_minimo']}€)\n"
                else:
                    linea += f"- {tienda}: {precio}€\n"
        mensajes.append(linea)

    guardar_historial(historial)

    texto = "📋 *Precios actuales:*\n\n" + "\n".join(mensajes)
    await context.bot.send_message(chat_id=CHAT_ID, text=texto, parse_mode="Markdown")

# ------------------ Comando /revisa ------------------
async def comando_revisa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⌛ Obteniendo precios de los productos...")
    await revisar(context)
    await update.message.reply_text("✅ Revisión completada.")

# ------------------ Función principal del bot ------------------
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("revisa", comando_revisa))

    # JobQueue para revisiones automáticas
    jq = app.job_queue
    jq.run_daily(revisar, time(hour=11))
    jq.run_daily(revisar, time(hour=23))

    print("✅ Bot activo: revisiones automáticas 11:00 y 23:00, comando /revisa disponible")
    app.run_polling()

if __name__ == "__main__":
    main()
