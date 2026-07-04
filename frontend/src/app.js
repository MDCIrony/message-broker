const HOST = window.location.hostname || 'localhost',
      API_URL = `http://${HOST}:8000/api`,
      WS_URL = `ws://${HOST}:8000/ws`,
      ADMIN_TOKEN = 'admin-token-999';

const clientId = `admin_dashboard_${Math.random().toString(36).substring(2, 8)}`;
let socket = null;

// DOM Elements
const statusBadge = document.getElementById('broker-status'),
      statActiveClients = document.getElementById('stat-active-clients'),
      statActiveTopics = document.getElementById('stat-active-topics'),
      statTotalMessages = document.getElementById('stat-total-messages'),
      activeProducersTbody = document.getElementById('active-producers-tbody'),
      activeConsumersTbody = document.getElementById('active-consumers-tbody'),
      countProducers = document.getElementById('count-producers'),
      countConsumers = document.getElementById('count-consumers'),
      adminTopicsList = document.getElementById('admin-topics-list'),
      adminPublisherForm = document.getElementById('admin-publisher-form'),
      adminTopicInput = document.getElementById('admin-topic'),
      adminPayloadInput = document.getElementById('admin-payload'),
      messagesReceivedFeed = document.getElementById('messages-received-feed'),
      brokerEventsLog = document.getElementById('broker-events-log');

// Setup WebSocket connection as Admin
function connectWebSocket() {
    socket = new WebSocket(`${WS_URL}/${clientId}?token=${ADMIN_TOKEN}`);
    
    socket.onopen = () => {
        statusBadge.className = 'status-badge connected';
        statusBadge.querySelector('.status-text').textContent = `Admin conectado (${clientId})`;
        
        // Register to receive all broker logs
        socket.send(JSON.stringify({ action: 'register_logs' }));
    };
    
    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.error) {
            handleServerError(data.error);
        } else if (data.event_type) {
            handleBrokerLog(data);
            
            // If it's a message event, dynamically append it to the message feed
            if (data.event_type === 'MESSAGE_RECEIVED') {
                appendLiveMessage(data.topic, data.message);
            }
        }
    };
    
    socket.onclose = () => {
        statusBadge.className = 'status-badge disconnected';
        statusBadge.querySelector('.status-text').textContent = 'Desconectado';
        setTimeout(connectWebSocket, 3000);
    };
}

// Fetch general broker status
async function pollBrokerStatus() {
    try {
        const response = await fetch(`${API_URL}/admin/status`, {
            headers: { 'X-Broker-Token': ADMIN_TOKEN }
        });
        if (!response.ok) throw new Error(`HTTP Error ${response.status}`);
        
        const status = await response.json();
        updateDashboardMetrics(status);
        updateActiveClientsTable(status.active_clients);
    } catch (err) {
        console.error("Failed to poll status", err);
    }
}

// Fetch historical messages to initialize the feed
async function loadMessageHistory() {
    try {
        const response = await fetch(`${API_URL}/messages?limit=50`, {
            headers: { 'X-Broker-Token': ADMIN_TOKEN }
        });
        if (!response.ok) throw new Error(`HTTP Error ${response.status}`);
        
        const messages = await response.json();
        statTotalMessages.textContent = messages.length;
        
        if (messages.length > 0) {
            messagesReceivedFeed.innerHTML = '';
            // Messages are returned DESC, so we reverse to render them chronologically
            messages.slice().reverse().forEach(msg => {
                appendLiveMessage(msg.topic, msg.payload, msg.created_at);
            });
        }
    } catch (err) {
        console.error("Failed to load message history", err);
    }
}

// Update upper cards / stats
function updateDashboardMetrics(status) {
    statActiveClients.textContent = status.active_clients_count;
    statActiveTopics.textContent = status.topics.length;
    updateTopicsList(status.topics);
}

// Render registered topics list chips
function updateTopicsList(topics) {
    if (!topics || topics.length === 0) {
        adminTopicsList.innerHTML = '<span class="empty-state-text">No hay tópicos registrados</span>';
        return;
    }
    adminTopicsList.innerHTML = '';
    topics.forEach(topic => {
        const chip = document.createElement('span');
        chip.className = 'topic-chip';
        chip.textContent = topic;
        // UX micro-interaction: populate publisher field on click
        chip.onclick = () => {
            adminTopicInput.value = topic;
        };
        adminTopicsList.appendChild(chip);
    });
}

// Rebuild active WebSockets client tables (Producers vs Consumers)
function updateActiveClientsTable(clients) {
    const producers = clients.filter(c => c.role === 'producer');
    const consumers = clients.filter(c => c.role === 'consumer' || c.role === 'admin' || c.is_log_subscriber);

    // Update table header badges
    countProducers.textContent = producers.length;
    countConsumers.textContent = consumers.length;

    // 1. Populate Producers
    if (producers.length === 0) {
        activeProducersTbody.innerHTML = `
            <tr>
                <td colspan="3" class="table-empty">Ningún productor conectado</td>
            </tr>`;
    } else {
        activeProducersTbody.innerHTML = '';
        producers.forEach(p => {
            const tr = document.createElement('tr');
            const time = new Date(p.connected_at).toLocaleTimeString();
            tr.innerHTML = `
                <td><strong>${p.client_id}</strong></td>
                <td><code>${p.ip}</code></td>
                <td style="color: var(--color-text-muted); font-size: 0.8rem;">${time}</td>
            `;
            activeProducersTbody.appendChild(tr);
        });
    }

    // 2. Populate Consumers
    if (consumers.length === 0) {
        activeConsumersTbody.innerHTML = `
            <tr>
                <td colspan="4" class="table-empty">Ningún consumidor conectado</td>
            </tr>`;
    } else {
        activeConsumersTbody.innerHTML = '';
        consumers.forEach(c => {
            const tr = document.createElement('tr');
            const time = new Date(c.connected_at).toLocaleTimeString();
            
            let subsHTML = '';
            if (c.is_log_subscriber) {
                subsHTML = '<span class="role-badge role-admin" style="font-size: 0.7rem;">Bitácora de Logs</span>';
            } else if (c.subscriptions && c.subscriptions.length > 0) {
                subsHTML = c.subscriptions.map(s => `<span class="table-chip">${s}</span>`).join('');
            } else {
                subsHTML = '<span class="table-empty" style="font-size: 0.8rem; padding: 0;">Ninguna</span>';
            }

            tr.innerHTML = `
                <td><strong>${c.client_id}</strong></td>
                <td><code>${c.ip}</code></td>
                <td>${subsHTML}</td>
                <td style="color: var(--color-text-muted); font-size: 0.8rem;">${time}</td>
            `;
            activeConsumersTbody.appendChild(tr);
        });
    }
}

// Publish message from Admin tool
async function publishMessage(topic, payload) {
    try {
        const response = await fetch(`${API_URL}/publish`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-Broker-Token': ADMIN_TOKEN },
            body: JSON.stringify({ topic, payload })
        });
        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || `Error HTTP ${response.status}`);
        }
        
        // Force quick updates after publishing
        pollBrokerStatus();
    } catch (err) {
        alert(`Error al publicar: ${err.message}`);
    }
}

// Append new message to UI feed
function appendLiveMessage(topic, payload, timestamp = null) {
    if (messagesReceivedFeed.querySelector('.empty-state')) {
        messagesReceivedFeed.innerHTML = '';
    }
    
    const timeStr = timestamp ? new Date(timestamp).toLocaleTimeString() : new Date().toLocaleTimeString();
    const div = document.createElement('div');
    div.className = 'msg-feed-line';
    
    div.innerHTML = `
        <div class="msg-feed-header">
            <span class="msg-feed-topic">${topic}</span>
            <span class="msg-feed-time">${timeStr}</span>
        </div>
        <div class="msg-feed-payload">${payload}</div>
    `;
    
    messagesReceivedFeed.appendChild(div);
    messagesReceivedFeed.scrollTop = messagesReceivedFeed.scrollHeight;
}

// Append server log to UI feed
function handleBrokerLog(log) {
    if (brokerEventsLog.querySelector('.empty-state')) {
        brokerEventsLog.innerHTML = '';
    }
    
    const time = log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : new Date().toLocaleTimeString();
    const div = document.createElement('div');
    div.className = `log-line log-${log.event_type}`;
    
    div.innerHTML = `
        <span class="log-time">[${time}]</span>
        <span class="log-type">${log.event_type}:</span> 
        Client: ${log.client_id} 
        ${log.topic ? `| Topic: <b>${log.topic}</b>` : ''} 
        ${log.message ? `| Payload: <i>${log.message}</i>` : ''}
    `;
    
    brokerEventsLog.appendChild(div);
    brokerEventsLog.scrollTop = brokerEventsLog.scrollHeight;
}

// Append error to log feed
function handleServerError(err) {
    if (brokerEventsLog.querySelector('.empty-state')) {
        brokerEventsLog.innerHTML = '';
    }
    
    const div = document.createElement('div');
    div.className = 'log-line';
    div.style.borderLeftColor = 'var(--danger)';
    div.style.color = '#f87171';
    div.innerHTML = `<span class="log-time">[${new Date().toLocaleTimeString()}]</span> <span class="log-type">ERROR:</span> ${err}`;
    
    brokerEventsLog.appendChild(div);
    brokerEventsLog.scrollTop = brokerEventsLog.scrollHeight;
}

// Event Listeners
adminPublisherForm.addEventListener('submit', () => {
    const topic = adminTopicInput.value.trim();
    const payload = adminPayloadInput.value.trim();
    
    if (topic && payload) {
        publishMessage(topic, payload);
        adminPayloadInput.value = '';
    }
});

// Initialization
connectWebSocket();
loadMessageHistory();
pollBrokerStatus();

// Polling interval for status updates
setInterval(pollBrokerStatus, 2000);
