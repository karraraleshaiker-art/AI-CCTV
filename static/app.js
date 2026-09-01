const canvas = document.querySelector("#zoneCanvas");
const stream = document.querySelector("#stream");
const editButton = document.querySelector("#editZone");
const clearButton = document.querySelector("#clearZone");
const saveButton = document.querySelector("#saveZone");
const fps = document.querySelector("#fps");
const frames = document.querySelector("#frames");
const people = document.querySelector("#people");
const alerts = document.querySelector("#alerts");
const tracks = document.querySelector("#tracks");
const error = document.querySelector("#error");
const cameraMeta = document.querySelector("#cameraMeta");

const ctx = canvas.getContext("2d");
let editing = false;
let zone = [];

function resizeCanvas() {
  const rect = canvas.getBoundingClientRect();
  canvas.width = Math.max(1, Math.floor(rect.width * window.devicePixelRatio));
  canvas.height = Math.max(1, Math.floor(rect.height * window.devicePixelRatio));
  ctx.setTransform(window.devicePixelRatio, 0, 0, window.devicePixelRatio, 0, 0);
  drawZone();
}

function drawZone() {
  const rect = canvas.getBoundingClientRect();
  ctx.clearRect(0, 0, rect.width, rect.height);
  if (zone.length === 0) return;

  ctx.lineWidth = 2;
  ctx.strokeStyle = "#f3c94f";
  ctx.fillStyle = "rgba(243, 201, 79, 0.14)";
  ctx.beginPath();
  zone.forEach(([x, y], index) => {
    const px = x * rect.width;
    const py = y * rect.height;
    if (index === 0) ctx.moveTo(px, py);
    else ctx.lineTo(px, py);
  });
  if (zone.length >= 3) ctx.closePath();
  ctx.fill();
  ctx.stroke();

  for (const [x, y] of zone) {
    ctx.beginPath();
    ctx.arc(x * rect.width, y * rect.height, 5, 0, Math.PI * 2);
    ctx.fillStyle = "#f3c94f";
    ctx.fill();
  }
}

canvas.addEventListener("click", (event) => {
  if (!editing) return;
  const rect = canvas.getBoundingClientRect();
  zone.push([
    Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width)),
    Math.min(1, Math.max(0, (event.clientY - rect.top) / rect.height)),
  ]);
  drawZone();
});

editButton.addEventListener("click", () => {
  editing = !editing;
  editButton.classList.toggle("active", editing);
  canvas.classList.toggle("editing", editing);
});

clearButton.addEventListener("click", () => {
  if (!editing) return;
  zone = [];
  drawZone();
});

saveButton.addEventListener("click", async () => {
  if (zone.length < 3) return;
  const response = await fetch("/api/zone", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ points: zone }),
  });
  if (response.ok) {
    const data = await response.json();
    zone = data.zone;
    editing = false;
    editButton.classList.remove("active");
    canvas.classList.remove("editing");
    drawZone();
  }
});

alerts.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-ack-alert]");
  if (!button) return;
  const alertId = button.dataset.ackAlert;
  const response = await fetch(`/api/alerts/${encodeURIComponent(alertId)}/ack`, { method: "POST" });
  if (response.ok) refreshStatus();
});

async function refreshStatus() {
  const response = await fetch("/api/status");
  const data = await response.json();
  fps.textContent = data.fps;
  frames.textContent = data.frame_count;
  people.textContent = data.tracks.length;
  const frameStatus = data.frame_count === 0 ? data.status : "Live processing";
  cameraMeta.textContent = `${frameStatus} | ${data.config.camera_source} | ${data.config.model_name} | ${data.config.frame_width}w @ ${data.config.stream_fps} fps target`;
  if (!editing) {
    zone = data.zone;
    drawZone();
  }

  if (data.error) {
    error.hidden = false;
    error.textContent = data.error;
  } else {
    error.hidden = true;
    error.textContent = "";
  }

  tracks.innerHTML = "";
  for (const track of data.tracks) {
    const item = document.createElement("li");
    const title = document.createElement("strong");
    const meta = document.createElement("span");
    title.textContent = `Person #${track.id}`;
    meta.textContent = track.inside_zone
      ? `Inside place | phone frames ${track.phone_frames}`
      : `Outside place | outside frames ${track.outside_zone_frames}`;
    item.classList.toggle("outside", !track.inside_zone);
    item.append(title, meta);
    tracks.append(item);
  }
  if (data.tracks.length === 0) {
    const item = document.createElement("li");
    item.className = "empty";
    item.textContent = "No people detected";
    tracks.append(item);
  }

  alerts.innerHTML = "";
  for (const alert of data.alerts) {
    const item = document.createElement("li");
    const title = document.createElement("strong");
    const meta = document.createElement("span");
    const row = document.createElement("div");
    title.textContent = alert.message;
    meta.textContent = `${alert.kind} | ${alert.iso_time}${alert.acknowledged ? " | acknowledged" : ""}`;
    item.append(title, meta);
    if (alert.evidence_url) {
      const link = document.createElement("a");
      link.href = alert.evidence_url;
      link.target = "_blank";
      link.rel = "noreferrer";
      link.textContent = "Evidence";
      row.append(link);
    }
    if (!alert.acknowledged) {
      const button = document.createElement("button");
      button.type = "button";
      button.dataset.ackAlert = alert.id;
      button.textContent = "Acknowledge";
      row.append(button);
    }
    if (row.children.length) {
      row.className = "alert-actions";
      item.append(row);
    }
    item.classList.toggle("acknowledged", alert.acknowledged);
    alerts.append(item);
  }
  if (data.alerts.length === 0) {
    const item = document.createElement("li");
    item.className = "empty";
    item.textContent = "No alerts";
    alerts.append(item);
  }
}

window.addEventListener("resize", resizeCanvas);
stream.addEventListener("load", resizeCanvas);
resizeCanvas();
refreshStatus();
setInterval(refreshStatus, 1000);
