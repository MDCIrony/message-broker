import asyncio
import sys
import os
import json
import urllib.request
import urllib.error
from datetime import datetime

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
        sys.exit(1)

# Variables globales para almacenar el estado
broker_status = {}
recent_logs = []
MAX_LOG_LINES = 10


def fetch_status(host, port, token):
    """Realiza una petición HTTP GET sincrónica al endpoint de administración."""
    url = f"http://{host}:{port}/api/admin/status"
    req = urllib.request.Request(url)
    req.add_header("X-Broker-Token", token)
    try:
        with urllib.request.urlopen(req, timeout=2) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 403:
            return {"error": "Acceso denegado: Token de admin inválido"}
        return {"error": f"Error HTTP {e.code}: {e.reason}"}
    except Exception as e:
        return {"error": f"No se pudo conectar al Broker: {e}"}


def draw_dashboard(host, port):
    """Limpia la terminal y redibuja la consola de administración en texto ASCII."""
    # Código ANSI para limpiar la pantalla y mover el cursor arriba
    sys.stdout.write("\033[H\033[2J")
    sys.stdout.flush()

    print("=" * 80)
    print(f"        MONITOR ADMINISTRATIVO DEL MESSAGE BROKER (TIEMPO SEMI-REAL)")
    print("=" * 80)
    print(f" Servidor Broker: {host}:{port} | Hora Local: {datetime.now().strftime('%T')}")
    print("-" * 80)

    if "error" in broker_status:
        print(f"\033[91m[ERROR]\033[0m {broker_status['error']}")
        print("=" * 80)
        return

    # Estadísticas generales
    active_count = broker_status.get("active_clients_count", 0)
    topics = broker_status.get("topics", [])
    topics_str = ", ".join(topics) if topics else "(ninguno)"

    print(f"ESTADÍSTICAS DEL SISTEMA:")
    print(f"  - Clientes WebSockets Conectados: \033[92m{active_count}\033[0m")
    print(f"  - Tópicos Activos (con historial): {topics_str}")
    print("-" * 80)

    # Listado de clientes
    print(f"{'ID CLIENTE':<30} {'ROL':<10} {'DIRECCIÓN IP':<20} {'SUSCRIPCIONES'}")
    print("-" * 80)

    active_clients = broker_status.get("active_clients", [])
    if not active_clients:
        print("  (No hay clientes WebSockets activos conectados)")
    else:
        for client in active_clients:
            client_id = client.get("client_id", "desconocido")
            role = client.get("role", "desconocido")
            ip = client.get("ip", "desconocido")
            subs = client.get("subscriptions", [])
            is_log = client.get("is_log_subscriber", False)

            # Formatear la lista de suscripciones
            subs_str = ", ".join(subs) if subs else "(ninguna)"
            if is_log:
                subs_str = "\033[96m(Logs de Servidor)\033[0m"

            # Colorear según el rol
            role_color = "\033[0m"
            if role == "admin":
                role_color = "\033[95m" # Magenta
            elif role == "producer":
                role_color = "\033[93m" # Amarillo
            elif role == "consumer":
                role_color = "\033[92m" # Verde

            print(f"{client_id:<30} {role_color}{role:<10}\033[0m {ip:<20} {subs_str}")

    print("-" * 80)

    # Bitácora de logs en vivo
    print(f"BITÁCORA DE LOGS EN TIEMPO REAL (Últimos {MAX_LOG_LINES} eventos):")
    print("-" * 80)
    if not recent_logs:
        print("  Esperando eventos...")
    else:
        for log in recent_logs:
            time_str = datetime.fromisoformat(log["timestamp"]).strftime("%T") if "timestamp" in log else datetime.now().strftime("%T")
            msg_str = f"Client: {log.get('client_id')} " \
                      f"{'| Topic: ' + log.get('topic') if log.get('topic') else ''} " \
                      f"{'| Msg: ' + log.get('message') if log.get('message') else ''}"

            # Colorear tipo de log
            event_type = log.get("event_type", "EVENT")
            event_color = "\033[94m" # Azul por defecto
            if "DISCONNECTED" in event_type or "FAILED" in event_type:
                event_color = "\033[91m" # Rojo
            elif "CONNECTED" in event_type:
                event_color = "\033[92m" # Verde
            elif "RECEIVED" in event_type:
                event_color = "\033[93m" # Amarillo

            print(f"  [{time_str}] {event_color}[{event_type:<20}]\033[0m {msg_str}")

    print("=" * 80)
    print(" Presiona Ctrl+C para salir.")


async def status_polling_loop(host, port, token):
    """Tarea para consultar periódicamente el estado HTTP."""
    global broker_status
    loop = asyncio.get_running_loop()
    while True:
        # Ejecutar fetch_status en un hilo secundario para no bloquear el bucle de eventos
        broker_status = await loop.run_in_executor(None, fetch_status, host, port, token)
        draw_dashboard(host, port)
        await asyncio.sleep(2)


async def ws_logs_loop(host, port, token):
    """Tarea para escuchar logs del servidor vía WebSocket."""
    global recent_logs
    clientId = f"admin_monitor_{datetime.now().strftime('%M%S')}"
    uri = f"ws://{host}:{port}/ws/{clientId}?token={token}"

    while True:
        try:
            async with websockets.connect(uri) as websocket:
                # Solicitar recibir los logs del broker
                await websocket.send(json.dumps({"action": "register_logs"}))

                async for message in websocket:
                    data = json.loads(message)

                    # Si es un log del servidor (tiene event_type), lo encolamos
                    if "event_type" in data:
                        recent_logs.append(data)
                        if len(recent_logs) > MAX_LOG_LINES:
                            recent_logs.pop(0)
                        draw_dashboard(host, port)
        except Exception as e:
            # Reintentar conexión si se cae
            await asyncio.sleep(3)


async def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    port = sys.argv[2] if len(sys.argv) > 2 else "8000"
    token = sys.argv[3] if len(sys.argv) > 3 else "admin-token-999"

    # Iniciar las tareas concurrentemente
    await asyncio.gather(
        status_polling_loop(host, port, token),
        ws_logs_loop(host, port, token)
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Restaurar cursor y limpiar pantalla al salir
        sys.stdout.write("\033[H\033[2J")
        print("Monitor administrativo finalizado.")
        sys.exit(0)
