function connectWebSocket() {
    // Only connect if the user is authenticated (we can check a global flag or attribute set by Django)
    const wsScheme = window.location.protocol === "https:" ? "wss://" : "ws://";
    const notificationSocket = new WebSocket(wsScheme + window.location.host + '/ws/notifications/');

    notificationSocket.onopen = function(e) {
        console.log("Global Live Connection Established: Listening for notifications!");
    };

    notificationSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        alert(data.message);
    };

    notificationSocket.onerror = function(e) {
        console.error("WebSocket Connection Error.");
    };

    notificationSocket.onclose = function(e) {
        console.log("WebSocket disconnected. Reconnecting in 3 seconds...");
        setTimeout(connectWebSocket, 3000);
    };
}

connectWebSocket();