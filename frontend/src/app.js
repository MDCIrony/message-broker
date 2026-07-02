const HOST = window.location.hostname || 'localhost', API_URL = `http://${HOST}:8000/api`, WS_URL = `ws://${HOST}:8000/ws`;
const clientId = `client_${Math.random().toString(36).substring(2, 8)}`, activeSubscriptions = new Set();
let socket = null;

const statusBadge = document.getElementById('broker-status'),
      brokerEventsLog = document.getElementById('broker-events-log'),
      producerForm = document.getElementById('producer-form'),
      producerTopic = document.getElementById('producer-topic'),
      producerPayload = document.getElementById('producer-payload'),
      producerHistoryLog = document.getElementById('producer-history-log'),
      subscriptionForm = document.getElementById('subscription-form'),
      consumerTopic = document.getElementById('consumer-topic'),
      subscriptionsList = document.getElementById('subscriptions-list'),
      consumerReceivedLog = document.getElementById('consumer-received-log'),
      tokenSelector = document.getElementById('token-selector');

function connect() {
    const token = tokenSelector.value;
    socket = new WebSocket(`${WS_URL}/${clientId}?token=${token}`);
    socket.onopen = () => {
        statusBadge.className = 'status-badge connected';
        statusBadge.querySelector('.status-text').textContent = `Conectado (${clientId})`;
        socket.send(JSON.stringify({ action: 'register_logs' }));
    };
    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.error) handleSystemError(data.error);
        else if (data.event_type) handleBrokerEvent(data);
        else if (data.topic && data.payload) handleConsumerMessage(data);
    };
    socket.onclose = () => {
        statusBadge.className = 'status-badge disconnected';
        statusBadge.querySelector('.status-text').textContent = 'Desconectado';
        setTimeout(connect, 3000);
    };
}

function handleSystemError(err) {
    if (brokerEventsLog.querySelector('.empty-state')) brokerEventsLog.innerHTML = '';
    const div = document.createElement('div');
    div.className = 'log-line'; div.style.borderLeftColor = 'var(--danger)'; div.style.color = '#f87171';
    div.innerHTML = `<span class="log-time">[${new Date().toLocaleTimeString()}]</span> <span class="log-type">ERROR:</span> ${err}`;
    brokerEventsLog.appendChild(div); brokerEventsLog.scrollTop = brokerEventsLog.scrollHeight;
}

tokenSelector.addEventListener('change', () => {
    activeSubscriptions.clear(); renderSubscriptionChips();
    if (socket) socket.close();
});

function handleBrokerEvent(event) {
    if (brokerEventsLog.querySelector('.empty-state')) brokerEventsLog.innerHTML = '';
    const time = new Date(event.timestamp).toLocaleTimeString();
    const div = document.createElement('div');
    div.className = `log-line log-${event.event_type}`;
    div.innerHTML = `<span class="log-time">[${time}]</span><span class="log-type">${event.event_type}:</span> Client: ${event.client_id} ${event.topic ? `| Topic: <b>${event.topic}</b>` : ''} ${event.message ? `| Payload: <i>${event.message}</i>` : ''}`;
    brokerEventsLog.appendChild(div); brokerEventsLog.scrollTop = brokerEventsLog.scrollHeight;
}

function handleConsumerMessage(msg) {
    if (consumerReceivedLog.querySelector('.empty-state')) consumerReceivedLog.innerHTML = '';
    const div = document.createElement('div');
    div.className = 'log-line log-received-msg';
    div.innerHTML = `<span class="log-time">[${new Date().toLocaleTimeString()}]</span><span class="topic-badge">${msg.topic}</span>: ${msg.payload}`;
    consumerReceivedLog.appendChild(div); consumerReceivedLog.scrollTop = consumerReceivedLog.scrollHeight;
}

async function publishMessage(topic, payload) {
    try {
        const token = tokenSelector.value;
        const response = await fetch(`${API_URL}/publish`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-Broker-Token': token },
            body: JSON.stringify({ topic, payload })
        });
        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || `HTTP Error ${response.status}`);
        }
        const data = await response.json();
        if (producerHistoryLog.querySelector('.empty-state')) producerHistoryLog.innerHTML = '';
        const div = document.createElement('div');
        div.className = 'log-line log-sent-msg';
        div.innerHTML = `<span class="log-time">[${new Date().toLocaleTimeString()}]</span><span class="topic-badge">${data.topic}</span>: ${data.payload}`;
        producerHistoryLog.appendChild(div); producerHistoryLog.scrollTop = producerHistoryLog.scrollHeight;
    } catch (err) {
        console.error("Publish failed", err); alert(`Error al publicar mensaje: ${err.message}`);
    }
}

subscriptionForm.addEventListener('submit', () => {
    const topic = consumerTopic.value.trim();
    if (topic && !activeSubscriptions.has(topic)) {
        socket.send(JSON.stringify({ action: 'subscribe', topic }));
        activeSubscriptions.add(topic); renderSubscriptionChips(); consumerTopic.value = '';
    }
});

function unsubscribe(topic) {
    socket.send(JSON.stringify({ action: 'unsubscribe', topic }));
    activeSubscriptions.delete(topic); renderSubscriptionChips();
}

function renderSubscriptionChips() {
    if (activeSubscriptions.size === 0) return subscriptionsList.innerHTML = '<span class="empty-state-text">Ninguna suscripción activa</span>';
    subscriptionsList.innerHTML = '';
    activeSubscriptions.forEach(t => {
        const chip = document.createElement('span'); chip.className = 'chip';
        chip.innerHTML = `${t} <span class="chip-close" onclick="unsubscribe('${t}')">&times;</span>`;
        subscriptionsList.appendChild(chip);
    });
}

producerForm.addEventListener('submit', () => {
    const topic = producerTopic.value.trim(), payload = producerPayload.value.trim();
    if (topic && payload) { publishMessage(topic, payload); producerPayload.value = ''; }
});

connect();
