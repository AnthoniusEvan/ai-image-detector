document.querySelectorAll(".drop-zone-input").forEach(inputElement => {
    const dropZoneElement = inputElement.closest(".drop-zone");

    dropZoneElement.addEventListener("click", e => {
        inputElement.click();
    })

    inputElement.addEventListener("change", e => {
        if (inputElement.files.length > 0){
            updateThumbnail(dropZoneElement, inputElement.files[0]);
        }
    })

    dropZoneElement.addEventListener("dragover", e => {
        e.preventDefault();
        dropZoneElement.classList.add("drop-zone-over");
    })

    dropZoneElement.addEventListener("dragleave", e => {
            e.preventDefault();
            dropZoneElement.classList.remove("drop-zone-over");
    });

    dropZoneElement.addEventListener("dragend", e => {
            e.preventDefault();
            dropZoneElement.classList.remove("drop-zone-over");
    });
    
    dropZoneElement.addEventListener("drop", e => {
        e.preventDefault();

        if (e.dataTransfer.files.length) {
            inputElement.files = e.dataTransfer.files;
            updateThumbnail(dropZoneElement, e.dataTransfer.files[0]);
        }

        dropZoneElement.classList.remove("drop-zone-over");
    });
});

/**
 * @param {HTMLElement} dropZoneElement 
 * @param {File} file 
 */
function updateThumbnail(dropZoneElement, file) {
    let thumbnailElement = dropZoneElement.querySelector(".drop-zone-thumb");
    const dropZonePrompt = dropZoneElement.querySelector(".drop-zone-prompt");

    if (file.type.startsWith("image/")){
        if (dropZonePrompt) dropZonePrompt.classList.add("hidden");

        if (!thumbnailElement){
            thumbnailElement = document.createElement("div");
            thumbnailElement.classList.add("drop-zone-thumb");
            dropZoneElement.appendChild(thumbnailElement);
        }

        thumbnailElement.dataset.label = file.name;

        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = () => {
            thumbnailElement.style.backgroundImage = `url('${reader.result}')`;
        }
    }
    else{
        dropZonePrompt.classList.remove("hidden");
        dropZonePrompt.textContent = "Please select an image."

        if (thumbnailElement) thumbnailElement.style.backgroundImage = null;
    }
    
}

(function () {
  const banner = document.getElementById('conn-banner');

  const State = {
    UNKNOWN: 'unknown',
    CONNECTED: 'connected',
    OFFLINE: 'offline',
    SERVER_DOWN: 'server_down',
    RECONNECTING: 'reconnecting',
  };

  let state = State.UNKNOWN;

  function paint(nextState, text) {
    if (!banner) return;
    banner.textContent = text;

    if (nextState === State.CONNECTED) {
      banner.style.background = '#e8f5e9';
      banner.style.color = '#1b5e20';
    } else if (nextState === State.RECONNECTING) {
      banner.style.background = '#fff8e1';
      banner.style.color = '#8d6e63';
    } else if (nextState === State.OFFLINE || nextState === State.SERVER_DOWN) {
      banner.style.background = '#ffebee';
      banner.style.color = '#b71c1c';
    } else {
      banner.style.background = '#fffbdd';
      banner.style.color = '#735c0f';
    }
    state = nextState;
  }

  async function ping() {
    if (state === State.UNKNOWN || state === State.OFFLINE || state === State.SERVER_DOWN) {
      paint(State.RECONNECTING, 'Reconnecting…');
    }

    const controller = new AbortController();
    const to = setTimeout(() => controller.abort(), 3000);

    try {
      const res = await fetch('/health', { signal: controller.signal, cache: 'no-store' });
      if (res.ok) {
        paint(State.CONNECTED, 'Connected');
      } else {
        paint(State.SERVER_DOWN, 'Server unreachable');
      }
    } catch {
      paint(State.SERVER_DOWN, 'Server unreachable');
    } finally {
      clearTimeout(to);
    }
  }

  paint(State.UNKNOWN, 'Connecting…');
  ping();
  setInterval(ping, 5000);

  window.addEventListener('offline', () => {
    paint(State.OFFLINE, 'Offline (waiting for network)…');
  });

  window.addEventListener('online', () => {
    paint(State.RECONNECTING, 'Reconnecting…');
    ping();
  });

  const form = document.querySelector('form[action="/detect"]');
  if (form) {
    form.addEventListener('submit', () => {
      if (state !== State.CONNECTED) {
        alert('Unable to connect to server');
      }
    });
  }
})();