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
CHAT_ID = int(os.environ.get("TELEGRAM_CHAT_ID"))  # Importante: convertir a int

archivo_historial = "precios.json"

# ------------------ Historial ------------------
def cargar_historial():
    try:
        with open(archivo_historial, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def guardar_historial(historial):
    with open(archivo_historial, "w") as f:
        json.dump(historial, f, indent=2)

# ------------------ Scraping de precios ------------------
def limpiar_precio(texto):
    if not texto:
        return None
    texto = texto.replace("€", "").replace(".", "").replace(",", ".").strip()
    try:
        return float(texto)
    except:
        return None

def obtener_precio(url, tienda):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=12)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        if tienda == "pc":
            # Buscar en PCComponentes
            tag = soup.select_one("span.product-sales-price, span.precio")
            if tag:
                return limpiar_precio(tag.get_text())
            return None

        elif tienda == "amazon":
            # Primero intentar con .a-offscreen
            tag = soup.select_one("span.a-offscreen")
            if tag:
                precio = limpiar_precio(tag.get_text())
                if precio:
                    return precio

            # Alternativa: combinar parte entera y decimal
            whole = soup.select_one(".a-price-whole")
            fraction = soup.select_one(".a-price-fraction")
            if whole:
                texto = whole.get_text().strip().replace(",", "")
                if fraction:
                    texto += "." + fraction.get_text().strip()
                else:
                    texto += ".00"
                return limpiar_precio(texto)
            return None

    except Exception as e:
        print(f"[{tienda.upper()}] Error scraping {url}: {e}")
        return None

# ------------------ Función de revisión ------------------
async def revisar(context: ContextTypes.DEFAULT_TYPE):
    historial = cargar_historial()
    mensajes = []

    for p in productos:
        linea = f"📦 *{p['nombre']}*\n"
        for tienda, url in [("PCComponentes", p["url_pccomponentes"]), ("Amazon", p["url_amazon"])]:
            precio = obtener_precio(url, "pc" if tienda == "PCComponentes" else "amazon")
            clave = f"{p['nombre']}_{tienda.lower()}"

            if precio is None:
                linea += f"- {tienda}: ❌ no disponible\n"
            else:
                historial[clave] = precio
                if precio <= p["precio_minimo"]:
                    linea += f"- {tienda}: 🔥 *{precio:.2f}€* (mínimo {p['precio_minimo']}€)\n"
                else:
                    linea += f"- {tienda}: {precio:.2f}€\n"
        mensajes.append(linea)

    guardar_historial(historial)

    texto = "📋 *Precios actuales:*\n\n" + "\n".join(mensajes)
    try:
        await context.bot.send_message(chat_id=CHAT_ID, text=texto, parse_mode="Markdown")
    except Exception as e:
        print(f"Error al enviar mensaje: {e}")

# ------------------ Comando /revisa ------------------
async def comando_revisa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⌛ Obteniendo precios...")
    await revisar(context)
    await update.message.reply_text("✅ Revisión completada.")

# ------------------ Función principal ------------------
def main():
    if not TOKEN or not CHAT_ID:
        print("❌ Faltan variables de entorno: TELEGRAM_TOKEN o TELEGRAM_CHAT_ID")
        return

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("revisa", comando_revisa))

    # Programar revisiones diarias
    job_queue = app.job_queue
    job_queue.run_daily(revisar, time(hour=11, tzinfo=None))
    job_queue.run_daily(revisar, time(hour=23, tzinfo=None))

    print("✅ Bot iniciado. Revisiones: 11:00 y 23:00. Comando: /revisa")
    app.run_polling()

if __name__ == "__main__":
    main()

