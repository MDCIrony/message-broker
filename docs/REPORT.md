# Documentación Técnica: Funcionamiento Interno del Broker de Mensajes

Este documento detalla el funcionamiento interno de la aplicación y el flujo secuencial de procesamiento y distribución de los mensajes en el sistema.

---

## 1. Funcionamiento del Broker

El servidor del broker actúa como un intermediario o concentrador de comunicaciones (*hub*). Su diseño se basa en un desacoplamiento temporal y espacial entre los clientes productores y los consumidores.

### Características Clave de la Implementación

1. **Gestión In-Memory de Suscripciones**: 
   - El servicio `BrokerService` mantiene mapas que relacionan tópicos con colecciones activas de sockets de clientes de forma dinámica.
2. **Persistencia Transaccional (SQLite)**: 
   - Cada mensaje recibido y autorizado se guarda en una base de datos SQLite de manera asíncrona mediante consultas SQL puras (no-ORM) antes de su distribución.
3. **Control de Acceso Fino (ACL y Seguridad)**:
   - Implementa el patrón Strategy para la validación de seguridad a través de la interfaz `BaseSecurityValidator`. La implementación concreta `ACLSecurityValidator` valida la autenticidad de los tokens y autoriza las acciones (`publish` o `subscribe`) según el tópico en base a una Lista de Control de Acceso (ACL).
4. **Sistema de Logs Centralizado (Patrón Strategy)**:
   - Los eventos críticos (conexiones, publicaciones, despachos) se reportan a un `CentralizedLogger` global que delega a múltiples estrategias registradas (`ConsoleLogStrategy` y `WebSocketLogStrategy`). Esto permite incorporar nuevos colectores de logs (ej. bases de datos de auditoría, archivos planos o servicios cloud) sin modificar la lógica del broker.
5. **Agnosticismo de Tópicos**: 
   - El broker no requiere pre-configurar qué tópicos existen. Cualquier canal solicitado por productores autorizados es creado dinámicamente.

---

## 2. Flujo de Mensajes y Secuencia de Procesamiento

El ciclo de vida de un mensaje consta de las siguientes fases secuenciales desde su envío hasta su recepción por los consumidores suscritos:

```
[Cliente/Productor] (REST/WS)
     │
     ▼ (1. Envía mensaje + Token Credencial)
[FastAPI Router / Handshake WS]
     │
     ├─► (2. Valida Autenticación y ACL en security.py)
     │   │
     │   └───► [Denegado] ──► Retorna 403 Forbidden / Cierra Socket
     │
     ▼ [Aprobado] (3. Invoca MessageService.publish)
[MessageService]
     ├───► [MessageRepository] ──► (4. SQL INSERT) ──► [SQLite DB]
     │
     ▼ (5. Invoca BrokerService.broadcast_to_topic)
[BrokerService]
     ├───► Obtiene subscriptores activos autorizados del tópico
     ├───► (6. Despacha mensajes concurrentemente con asyncio.gather)
     │     └───► [Consumidor Suscrito] ──► Recibe payload en vivo
     │
     ▼ (7. Reporta resultado al CentralizedLogger)
[CentralizedLogger]
     ├───► ConsoleLogStrategy ──► Imprime log en consola
     └───► WebSocketLogStrategy ──► Distribuye log al Dashboard de Monitoreo
```

### Detalle de las Etapas:

1. **Publicación**: El productor envía un mensaje (por HTTP POST o WebSocket). Debe incluir su cabecera `X-Broker-Token` o query parameter `token`.
2. **Autenticación y ACL**: El broker consulta a `ACLSecurityValidator`. Si el token no es válido o no tiene permiso de escritura (`publish`) en dicho tópico, se aborta la petición con `403 Forbidden`.
3. **Persistencia**: Si se autoriza, el `MessageService` delega en `MessageRepository` para registrar de forma no bloqueante el mensaje en la tabla SQLite.
4. **Despacho / Broadcast**: Se invoca a `BrokerService.broadcast_to_topic()`. El broker recupera los sockets activos y realiza envíos concurrentes seguros.
5. **Auditoría / Logueo**: El broker reporta el éxito o fallo al `CentralizedLogger`, que propaga la bitácora hacia la consola del servidor y la UI del Dashboard.
