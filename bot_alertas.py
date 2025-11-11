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
        "url_amazon": "https://www.amazon.es/SAMSUNG-LS32DG802SUXEN-FreeSync-Antirreflejos-Plateado/dp/B0DFVCV1XL",
        "precio_minimo": 994.32
    },
    {
        "nombre": "MSI MPG 321URXW",
        "url_pccomponentes": "https://www.pccomponentes.com/monitor-msi-mpg-321urxw-qd-oled-315-qd-oled-ultrahd-4k-240hz-003ms-hdr-400-adaptive-sync-usb-c",
        "url_amazon": "https://www.amazon.es/MSI-321URXW-QD-OLED-Monitor-cu%C3%A1nticos/dp/B0BSN2BXC5",
        "precio_minimo": 849.00
    },
    {
        "nombre": "Gigabyte AORUS FO32U2P",
        "url_pccomponentes": "https://www.pccomponentes.com/monitor-gigabyte-aorus-fo32u2p-315-qd-oled-ultrahd-4k-240hz-freesync-premium",
        "url_amazon": "https://www.amazon.es/Gigabyte-Monitor-Juegos-AORUS-FO32U2P/dp/B0CYQG1LZX",
        "precio_minimo": 799.00
    }
]

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = int(os.environ.get("TELEGRAM_CHAT_ID"))
archivo_historial = "precios.json"

def cargar_historial():
    try:
        with open(archivo_historial, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def guardar_historial(historial):
    with open(archivo_historial, "w") as f:
        json.dump(historial, f, indent=2)

# ------------------ Scraping ------------------
def limpiar_precio(texto):
    if not texto:
        return None
    texto = texto.replace("€", "").replace(".", "").replace(",", ".").strip()
    try:
        return float(texto)
    except:
        return None

def obtener_precio_pccomponentes(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url.strip(), headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        tag = soup.select_one("span.product-sales-price, span.precio")
        if tag:
            return limpiar_precio(tag.get_text())
        return None
    except Exception as e:
        print(f"[PCC] Error: {e}")
        return None

def obtener_precio_amazon(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }
        response = requests.get(url.strip(), headers=headers, timeout=12)
        soup = BeautifulSoup(response.text, 'html.parser')

        # 🔴 Si no hay stock, Amazon lo dice explícitamente
        if "No featured offers available" in response.text:
            return None

        # 🔴 Verifica si hay botón de compra (solo si hay stock)
        if not soup.select_one("#add-to-cart-button, #buy-now-button"):
            return None

        # ✅ Extraer precio principal
        price_whole = soup.select_one('.a-price-whole')
        price_fraction = soup.select_one('.a-price-fraction')
        if price_whole:
            whole = price_whole.get_text().strip().replace('.', '').replace(',', '')
            fraction = price_fraction.get_text().strip() if price_fraction else "00"
            try:
                precio = float(f"{whole}.{fraction}")
                if 50 <= precio <= 2000:  # Validación de rango razonable
                    return precio
            except:
                pass

        # Alternativa: .a-price .a-offscreen
        price_span = soup.select_one('.a-price .a-offscreen')
        if price_span:
            precio = limpiar_precio(price_span.get_text())
            if precio and 50 <= precio <= 2000:
                return precio

        return None

    except Exception as e:
        print(f"[Amazon] Error en {url}: {e}")
        return None

def obtener_precio(url, tienda):
    if tienda == "pc":
        return obtener_precio_pccomponentes(url)
    elif tienda == "amazon":
        return obtener_precio_amazon(url)
    return None

# ------------------ Revisión ------------------
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
    await context.bot.send_message(chat_id=CHAT_ID, text=texto, parse_mode="Markdown")

async def comando_revisa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⌛ Obteniendo precios...")
    await revisar(context)
    await update.message.reply_text("✅ Revisión completada.")

# ------------------ Main ------------------
def main():
    if not TOKEN or not CHAT_ID:
        print("❌ Faltan variables: TELEGRAM_TOKEN o TELEGRAM_CHAT_ID")
        return

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("revisa", comando_revisa))

    job_queue = app.job_queue
    job_queue.run_daily(revisar, time(hour=11))
    job_queue.run_daily(revisar, time(hour=23))

    print("✅ Bot activo")
    app.run_polling()

if __name__ == "__main__":
    main()
