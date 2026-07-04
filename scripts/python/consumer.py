import asyncio
import sys
import uuid
import json
import os

# Asegurar que websockets esté instalado
try:
    import websockets
except ImportError:
    print("[INFO] El paquete 'websockets' es necesario. Intentando instalar...")
    import subprocess
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "websockets"])
        import websockets
        print("[INFO] Paquete 'websockets' instalado con éxito.\n")
    except Exception as e:
        print(f"[ERROR] No se pudo instalar 'websockets': {e}")
        print("Por favor instala 'websockets' manualmente con: pip install websockets")
        sys.exit(1)


async def receive_messages(websocket):
    """Tarea para recibir y mostrar mensajes del broker continuamente."""
    try:
        async for message in websocket:
            data = json.loads(message)
            if "error" in data:
                print(f"\n\033[91m[ERROR BROKER]\033[0m {data['error']}\n> ", end="", flush=True)
            elif "event_type" in data:
                # Evento administrativo de bitácora
                print(f"\n\033[94m[EVENTO BROKER]\033[0m {data['event_type']} - Client: {data.get('client_id')} "
                      f"{'| Topic: ' + data.get('topic') if data.get('topic') else ''} "
                      f"{'| Msg: ' + data.get('message') if data.get('message') else ''}\n> ", end="", flush=True)
            elif "topic" in data and "payload" in data:
                # Mensaje de tópico suscrito recibido en vivo
                print(f"\n\033[92m[MENSAJE RECIBIDO]\033[0m \033[1m[{data['topic']}]\033[0m {data['payload']}\n> ", end="", flush=True)
            else:
                print(f"\n[WS RECIBIDO] {data}\n> ", end="", flush=True)
    except websockets.exceptions.ConnectionClosed:
        print("\n\033[93m[INFO] Conexión cerrada por el servidor.\033[0m")
    except Exception as e:
        print(f"\n[ERROR] Error leyendo del WebSocket: {e}\n> ", end="", flush=True)


async def interactive_console(websocket):
    """Tarea para leer comandos de stdin y enviarlos al WebSocket."""
    loop = asyncio.get_running_loop()
    print("==================================================")
    print(" Consumidor Interactivo iniciado.")
    print("==================================================")
    print("Comandos disponibles:")
    print("  sub <topic>   -> Suscribirse a un tópico")
    print("  unsub <topic> -> Cancelar suscripción a un tópico")
    print("  exit          -> Salir del programa")
    print("--------------------------------------------------")

    while True:
        # Imprimir prompt
        sys.stdout.write("> ")
        sys.stdout.flush()

        # Leer línea asíncronamente
        line = await loop.run_in_executor(None, sys.stdin.readline)
        if not line:
            break

        parts = line.strip().split(maxsplit=1)
        if not parts:
            continue

        cmd = parts[0].lower()
        if cmd == "exit":
            print("Cerrando conexión...")
            break
        elif cmd == "sub":
            if len(parts) < 2:
                print("Uso: sub <nombre_de_topico>")
                continue
            topic = parts[1]
            await websocket.send(json.dumps({"action": "subscribe", "topic": topic}))
            print(f"Suscripción solicitada para: {topic}")
        elif cmd == "unsub":
            if len(parts) < 2:
                print("Uso: unsub <nombre_de_topico>")
                continue
            topic = parts[1]
            await websocket.send(json.dumps({"action": "unsubscribe", "topic": topic}))
            print(f"Desuscripción solicitada para: {topic}")
        else:
            print(f"Comando desconocido: '{cmd}'. Usa 'sub <topic>', 'unsub <topic>' o 'exit'")


async def main():
    # Parámetros: puerto, nombre_consumidor, token
    port = sys.argv[1] if len(sys.argv) > 1 else "8000"
    client_name = sys.argv[2] if len(sys.argv) > 2 else "consumidor_cli"
    token = sys.argv[3] if len(sys.argv) > 3 else "consumer-token-xyz"

    # Generar identificador con UUID para cumplir la regla 3
    client_uuid = str(uuid.uuid4())[:8]
    full_client_id = f"{client_name}_{client_uuid}"

    uri = f"ws://localhost:{port}/ws/{full_client_id}?token={token}"
    print(f"Conectándose a: {uri} ...")

    try:
        async with websockets.connect(uri) as websocket:
            print(f"Conectado exitosamente como: {full_client_id}\n")
            # Ejecutar de manera concurrente recibir mensajes y consola interactiva
            await asyncio.gather(
                receive_messages(websocket),
                interactive_console(websocket)
            )
    except Exception as e:
        print(f"\n[ERROR] No se pudo conectar al broker: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nSaliendo...")
        sys.exit(0)
