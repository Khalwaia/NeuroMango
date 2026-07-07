let player;
let isPlayerReady = false;
let currentSongId = null;

// Initialize YouTube IFrame API
function onYouTubeIframeAPIReady() {
    player = new YT.Player('youtube-player', {
        height: '100',
        width: '100',
        videoId: '',
        playerVars: {
            'playsinline': 1,
            'autoplay': 1,
            'controls': 0
        },
        events: {
            'onReady': onPlayerReady,
            'onStateChange': onPlayerStateChange,
            'onError': onPlayerError
        }
    });
}

function onPlayerReady(event) {
    isPlayerReady = true;
    console.log("YouTube Player Ready");
    connectWebSocket(); // Connect only after player is ready
}

function onPlayerStateChange(event) {
    // 0 = ended
    if (event.data === YT.PlayerState.ENDED) {
        console.log("Song ended, requesting next...");
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: "song_ended" }));
        }
    }
}

function onPlayerError(event) {
    console.error("YouTube Player Error:", event.data);
    // If error, just skip to next
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "song_ended" }));
    }
}

let ws;
function connectWebSocket() {
    let wsUrl;
    if (window.location.protocol === 'file:') {
        wsUrl = 'ws://127.0.0.1:8766/ws';
    } else {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        wsUrl = `${wsProtocol}//${window.location.host}/ws`;
    }
    
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log("Connected to NeuroMango Server");
        // Ask for current state immediately
        ws.send(JSON.stringify({ type: "get_queue" }));
    };

    ws.onmessage = (event) => {
        if (typeof event.data === "string") {
            try {
                const msg = JSON.parse(event.data);
                if (msg.type === "queue_update") {
                    updateWidgetUI(msg.data);
                    handlePlayback(msg.data.current_song);
                }
            } catch (e) {
                // Ignore non-json or other messages
            }
        }
    };

    ws.onclose = () => {
        console.log("Disconnected. Reconnecting in 3s...");
        setTimeout(connectWebSocket, 3000);
    };
}

function updateWidgetUI(data) {
    const container = document.getElementById("widget-container");
    
    if (!data.current_song && data.queue.length === 0) {
        container.classList.add("hidden");
        return;
    }
    
    container.classList.remove("hidden");

    // Update Current Song
    if (data.current_song) {
        document.getElementById("current-title").innerText = data.current_song.title;
        document.getElementById("current-thumb").src = data.current_song.thumbnail;
        document.getElementById("current-requester").innerText = data.current_song.requested_by;
    } else {
        document.getElementById("current-title").innerText = "Ожидание трека...";
        document.getElementById("current-thumb").src = "";
    }

    // Update Queue List (show max 3 next)
    const queueList = document.getElementById("queue-list");
    queueList.innerHTML = "";
    
    const maxItems = Math.min(data.queue.length, 3);
    for (let i = 0; i < maxItems; i++) {
        const item = data.queue[i];
        const el = document.createElement("div");
        el.className = "queue-item";
        el.innerHTML = `
            <img src="${item.thumbnail}" alt="">
            <div class="queue-item-title">${item.title}</div>
        `;
        queueList.appendChild(el);
    }
    
    if (data.queue.length > 3) {
        const extra = document.createElement("div");
        extra.className = "queue-item";
        extra.style.color = "#888";
        extra.innerHTML = `<div>и ещё ${data.queue.length - 3}...</div>`;
        queueList.appendChild(extra);
    }
}

function handlePlayback(song) {
    if (!isPlayerReady) return;
    
    if (song) {
        if (song.id !== currentSongId) {
            currentSongId = song.id;
            console.log("Playing:", song.title);
            // Some browsers require interaction to unmute/autoplay, 
            // but in OBS Browser Source, autoplay is allowed by default if configured in OBS.
            player.loadVideoById(song.id);
            // OBS tip: Check "Route audio to OBS" in browser source properties!
        }
    } else {
        currentSongId = null;
        player.stopVideo();
    }
}
