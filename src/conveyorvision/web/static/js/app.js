/**
 * ConveyorVision — Single Page Application Frontend Client
 * Xử lý: WebSocket kết nối trực tiếp, cập nhật HUD, bảng nhật ký sự kiện tại chỗ,
 * bộ tổng hợp âm thanh còi báo lỗi (Web Audio API), hỗ trợ đa dạng vật thể và điều hướng 6 màn hình.
 */

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

class ConveyorVisionApp {
  constructor() {
    this.currentScreen = "overview";
    this.ws = null;
    this.wsConnected = false;
    this.audioContext = null;
    this.soundEnabled = true;
    this.settings = {
      defaultConf: 0.45,
      defaultTracker: "bytetrack.yaml",
      soundAlarm: true,
      loopVideo: true
    };

    // Lưu vết các track hiển thị trên bảng nhật ký: trackId -> { element, statusBadge, typeElem, confElem, timeElem }
    this.eventRows = new Map();

    this.init();
  }

  init() {
    this.loadSettings();
    this.loadSettingsFromServer();
    this.loadModelsList();
    this.bindNavigation();
    this.bindControls();
    this.bindModals();
    this.initClock();
    this.initWebSocket();
    this.loadOverviewData();
  }

  // ============================================================================
  // CÀI ĐẶT & LƯU TRỮ CỤC BỘ & MÁY CHỦ
  // ============================================================================
  loadSettings() {
    try {
      const saved = localStorage.getItem("conveyorvision_settings");
      if (saved) {
        this.settings = Object.assign(this.settings, JSON.parse(saved));
      }
      this.soundEnabled = this.settings.soundAlarm !== false;
      const soundCheck = document.getElementById("sound-alarm-toggle");
      if (soundCheck) soundCheck.checked = this.soundEnabled;
    } catch (e) {
      console.warn("Không thể tải cài đặt cục bộ:", e);
    }
  }

  saveSettings() {
    try {
      localStorage.setItem("conveyorvision_settings", JSON.stringify(this.settings));
    } catch (e) {
      console.warn("Không thể lưu cài đặt cục bộ:", e);
    }
  }

  async loadSettingsFromServer() {
    try {
      const res = await fetch("/api/settings");
      if (res.ok) {
        const data = await res.json();
        const trackerSel = document.getElementById("setting-tracker");
        const lostBuf = document.getElementById("setting-lost-buffer");
        const minVotes = document.getElementById("setting-min-votes");
        const autoCsv = document.getElementById("setting-auto-csv");
        const soundAlarm = document.getElementById("setting-sound-alarm");

        if (trackerSel && data.tracker) trackerSel.value = data.tracker;
        if (lostBuf && data.lost_track_buffer !== undefined) lostBuf.value = data.lost_track_buffer;
        if (minVotes && data.min_observation_votes !== undefined) minVotes.value = data.min_observation_votes;
        if (autoCsv && data.auto_save_csv !== undefined) autoCsv.checked = !!data.auto_save_csv;
        if (soundAlarm && data.sound_alarm !== undefined) {
          soundAlarm.checked = !!data.sound_alarm;
          this.soundEnabled = !!data.sound_alarm;
          const liveSound = document.getElementById("sound-alarm-toggle");
          if (liveSound) liveSound.checked = this.soundEnabled;
        }
      }
    } catch (e) {
      console.warn("Lỗi nạp cài đặt từ server:", e);
    }
  }

  async saveSettingsToServer() {
    try {
      const tracker = document.getElementById("setting-tracker")?.value || "bytetrack.yaml";
      const lost_track_buffer = parseInt(document.getElementById("setting-lost-buffer")?.value) || 30;
      const min_observation_votes = parseInt(document.getElementById("setting-min-votes")?.value) || 3;
      const auto_save_csv = !!document.getElementById("setting-auto-csv")?.checked;
      const sound_alarm = !!document.getElementById("setting-sound-alarm")?.checked;

      this.soundEnabled = sound_alarm;
      this.settings.soundAlarm = sound_alarm;
      this.saveSettings();

      const liveSound = document.getElementById("sound-alarm-toggle");
      if (liveSound) liveSound.checked = sound_alarm;

      const res = await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tracker, lost_track_buffer, min_observation_votes, auto_save_csv, sound_alarm })
      });

      if (res.ok) {
        const statusSpan = document.getElementById("settings-save-status");
        if (statusSpan) {
          statusSpan.style.display = "inline";
          setTimeout(() => { statusSpan.style.display = "none"; }, 2500);
        }
      } else {
        alert("Không thể lưu cấu hình lên máy chủ.");
      }
    } catch (e) {
      alert(`Lỗi lưu cấu hình: ${e.message}`);
    }
  }

  async loadModelsList() {
    try {
      const res = await fetch("/api/models");
      if (!res.ok) return;
      const models = await res.json();
      const select = document.getElementById("model-select");
      if (!select || !models.length) return;

      select.innerHTML = models.map((m) => {
        const val = m.path || (m.name.startsWith("yolo") ? m.name : `models/${m.name}`);
        const selected = m.is_active ? "selected" : "";
        return `<option value="${escapeHtml(val)}" ${selected}>${escapeHtml(m.name)} (${escapeHtml(m.size_mb)} MB)</option>`;
      }).join("");
    } catch (e) {
      console.warn("Lỗi nạp danh sách model:", e);
    }
  }

  // ============================================================================
  // ĐỒNG HỒ TRỰC TIẾP
  // ============================================================================
  initClock() {
    const clockElem = document.getElementById("live-clock");
    const updateTime = () => {
      const now = new Date();
      const pad = (n) => String(n).padStart(2, "0");
      const timeStr = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
      const dateStr = `${pad(now.getDate())}/${pad(now.getMonth() + 1)}/${now.getFullYear()}`;
      if (clockElem) {
        clockElem.textContent = `${timeStr} — ${dateStr}`;
      }
    };
    updateTime();
    setInterval(updateTime, 1000);
  }

  // ============================================================================
  // ĐIỀU HƯỚNG MÀN HÌNH (ROUTING)
  // ============================================================================
  bindNavigation() {
    const navItems = document.querySelectorAll(".nav-item");
    navItems.forEach((item) => {
      item.addEventListener("click", () => {
        const targetScreen = item.getAttribute("data-screen");
        this.switchScreen(targetScreen);
      });
    });

    const quickStartBtn = document.getElementById("btn-quick-start");
    if (quickStartBtn) {
      quickStartBtn.addEventListener("click", () => {
        this.switchScreen("live");
      });
    }
  }

  switchScreen(screenName) {
    if (!screenName) return;
    this.currentScreen = screenName;

    document.querySelectorAll(".nav-item").forEach((item) => {
      if (item.getAttribute("data-screen") === screenName) {
        item.classList.add("active");
      } else {
        item.classList.remove("active");
      }
    });

    document.querySelectorAll(".screen-view").forEach((view) => {
      if (view.id === `screen-${screenName}`) {
        view.classList.add("active");
      } else {
        view.classList.remove("active");
      }
    });

    if (screenName === "overview") this.loadOverviewData();
    if (screenName === "history") this.loadHistoryData();
    if (screenName === "evaluation") this.loadEvaluationData();
    if (screenName === "dataset") this.loadDatasetData();
    if (screenName === "settings") this.loadSettingsFromServer();
  }

  // ============================================================================
  // WEBSOCKET & SỰ KIỆN THỜI GIAN THỰC
  // ============================================================================
  initWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/events`;

    const connect = () => {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.wsConnected = true;
        console.log("WebSocket connected:", wsUrl);
      };

      this.ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          this.handleServerEvent(msg);
        } catch (e) {
          console.warn("Lỗi phân tích WebSocket JSON:", e);
        }
      };

      this.ws.onclose = () => {
        this.wsConnected = false;
        console.warn("WebSocket ngắt kết nối. Đang thử kết nối lại sau 2.5s...");
        setTimeout(connect, 2500);
      };

      this.ws.onerror = (err) => {
        console.error("Lỗi WebSocket:", err);
      };
    };

    connect();
  }

  handleServerEvent(msg) {
    const { type, payload } = msg;

    if (type === "init_status" || type === "status_changed") {
      this.updateSystemStatusUI(payload);
    } else if (type === "stats_update") {
      this.updateLiveStats(payload);
    } else if (type === "track_event") {
      this.handleTrackEvent(payload);
    } else if (type === "defect_alert") {
      this.triggerDefectAlert(payload);
    } else if (type === "session_finished") {
      this.handleSessionFinished(payload);
    }
  }

  updateSystemStatusUI(status) {
    const statusPill = document.getElementById("system-status-pill");
    const statusText = document.getElementById("system-status-text");
    const btnStart = document.getElementById("btn-start-inspection");
    const btnPause = document.getElementById("btn-pause-inspection");
    const btnStop = document.getElementById("btn-stop-inspection");

    const state = status.state || "STOPPED";

    if (statusPill && statusText) {
      statusPill.className = "status-pill";
      if (state === "RUNNING") {
        statusPill.classList.add("running");
        statusText.textContent = "Đang kiểm định";
      } else if (state === "PAUSED") {
        statusPill.classList.add("paused");
        statusText.textContent = "Tạm dừng";
      } else if (state === "ERROR") {
        statusPill.classList.add("error");
        statusText.textContent = status.error_message ? `Lỗi: ${status.error_message.substring(0, 30)}` : "Có lỗi xảy ra";
      } else {
        statusPill.classList.add("idle");
        statusText.textContent = "Sẵn sàng";
      }
    }

    if (btnStart) btnStart.disabled = (state === "RUNNING");
    if (btnPause) {
      btnPause.disabled = (state === "STOPPED" || state === "ERROR");
      btnPause.textContent = state === "PAUSED" ? "▶ Tiếp tục" : "⏸ Tạm dừng";
    }
    if (btnStop) btnStop.disabled = (state === "STOPPED" || state === "ERROR");

    if (status.model) {
      const modelTag = document.getElementById("active-model-tag");
      if (modelTag) modelTag.textContent = status.model;
    }
  }

  updateLiveStats(stats) {
    const elemFps = document.getElementById("live-fps-val");
    const elemPass = document.getElementById("live-pass-val");
    const elemDefect = document.getElementById("live-defect-val");
    const elemOther = document.getElementById("live-other-val");
    const elemInspecting = document.getElementById("live-inspecting-val");
    const elemRate = document.getElementById("live-rate-val");

    if (elemFps) elemFps.textContent = stats.fps ?? 0.0;
    if (elemPass) elemPass.textContent = stats.total_pass ?? 0;
    if (elemDefect) elemDefect.textContent = stats.total_defect ?? 0;
    if (elemOther) elemOther.textContent = stats.total_other ?? 0;
    if (elemInspecting) elemInspecting.textContent = stats.inspecting_count ?? 0;
    if (elemRate) elemRate.textContent = `${stats.defect_rate ?? 0.0}%`;

    const hudFps = document.getElementById("hud-fps");
    const hudBelt = document.getElementById("hud-belt");
    const hudPass = document.getElementById("hud-pass");
    const hudDefect = document.getElementById("hud-defect");
    const hudOther = document.getElementById("hud-other");

    if (hudFps) hudFps.textContent = `FPS: ${stats.fps ?? 0.0}`;
    if (hudBelt) hudBelt.textContent = `Đang quét: ${stats.inspecting_count ?? 0}`;
    if (hudPass) hudPass.textContent = `PASS: ${stats.total_pass ?? 0}`;
    if (hudDefect) hudDefect.textContent = `DEFECT: ${stats.total_defect ?? 0}`;
    if (hudOther) hudOther.textContent = `DỊ VẬT: ${stats.total_other ?? 0}`;

    const banner = document.getElementById("video-rejection-banner");
    if (banner) {
      if (stats.alert_active) {
        banner.classList.add("active");
        if (stats.alert_message) {
          banner.textContent = `⚠️ ${stats.alert_message} (MÔ PHỎNG) ⚠️`;
        }
      } else {
        banner.classList.remove("active");
      }
    }
  }

  handleTrackEvent(item) {
    const tbody = document.getElementById("live-events-tbody");
    if (!tbody) return;

    const trackId = item.track_id;
    const isCorrection = item.is_update || item.event === "DEFECT_CORRECTION";

    // Cập nhật tại chỗ nếu track đã tồn tại
    if (this.eventRows.has(trackId)) {
      const rowData = this.eventRows.get(trackId);
      const row = rowData.element;

      if (item.status === "DEFECT") {
        rowData.statusBadge.className = "badge-status defect";
        rowData.statusBadge.innerHTML = `DEFECT <span class="badge-updated">Hiệu chỉnh</span>`;
        rowData.typeElem.textContent = escapeHtml(item.class_name || "Chai lỗi");
        rowData.typeElem.style.color = "var(--color-defect)";
        rowData.confElem.textContent = item.conf ? Number(item.conf).toFixed(2) : "--";
        rowData.timeElem.textContent = item.timestamp || "--";

        row.classList.add("row-updated-highlight");
        setTimeout(() => row.classList.remove("row-updated-highlight"), 1200);

        if (this.soundEnabled) this.playAlertSound();
      } else if (item.status === "PASS") {
        rowData.statusBadge.className = "badge-status pass";
        rowData.statusBadge.textContent = "PASS";
        rowData.typeElem.textContent = escapeHtml(item.class_name || "Chai đạt");
        rowData.typeElem.style.color = "var(--color-pass)";
        rowData.confElem.textContent = item.conf ? Number(item.conf).toFixed(2) : "--";
      } else if (item.status === "OTHER" || item.category === "OTHER") {
        rowData.statusBadge.className = "badge-status other";
        rowData.statusBadge.textContent = "DỊ VẬT";
        rowData.typeElem.textContent = escapeHtml(item.class_name || "Vật thể khác");
        rowData.typeElem.style.color = "#c084fc";
        rowData.confElem.textContent = item.conf ? Number(item.conf).toFixed(2) : "--";
        row.classList.add("row-updated-highlight");
        setTimeout(() => row.classList.remove("row-updated-highlight"), 1200);
      }
    } else {
      // Tạo dòng mới
      const row = document.createElement("tr");

      let badgeClass = "inspecting";
      let statusText = "Đang kiểm tra";
      let typeColor = "var(--color-warning)";

      if (item.status === "DEFECT") {
        badgeClass = "defect";
        statusText = "DEFECT";
        typeColor = "var(--color-defect)";
        if (isCorrection) statusText += ` <span class="badge-updated">Hiệu chỉnh</span>`;
      } else if (item.status === "PASS") {
        badgeClass = "pass";
        statusText = "PASS";
        typeColor = "var(--color-pass)";
      } else if (item.status === "OTHER" || item.category === "OTHER") {
        badgeClass = "other";
        statusText = "DỊ VẬT";
        typeColor = "#c084fc";
      }

      const confStr = item.conf ? Number(item.conf).toFixed(2) : "--";

      row.innerHTML = `
        <td style="font-family: var(--font-mono); font-weight: 600;">#${escapeHtml(trackId)}</td>
        <td class="cell-time" style="font-size: 0.8rem; color: var(--text-secondary);">${escapeHtml(item.timestamp || "--")}</td>
        <td class="cell-type" style="font-weight: 500; color: ${typeColor};">${escapeHtml(item.class_name || "--")}</td>
        <td class="cell-conf" style="font-family: var(--font-mono);">${escapeHtml(confStr)}</td>
        <td class="cell-status">
          <span class="badge-status ${badgeClass}">${statusText}</span>
        </td>
      `;

      if (tbody.children.length > 50) {
        tbody.removeChild(tbody.lastChild);
      }
      tbody.insertBefore(row, tbody.firstChild);

      this.eventRows.set(trackId, {
        element: row,
        statusBadge: row.querySelector(".cell-status span"),
        typeElem: row.querySelector(".cell-type"),
        confElem: row.querySelector(".cell-conf"),
        timeElem: row.querySelector(".cell-time")
      });
    }
  }

  triggerDefectAlert(payload) {
    const banner = document.getElementById("video-rejection-banner");
    if (banner) {
      banner.classList.add("active");
      if (payload && payload.message) {
        banner.textContent = `⚠️ ${payload.message} (MÔ PHỎNG) ⚠️`;
      }
      setTimeout(() => banner.classList.remove("active"), 1500);
    }
    if (this.soundEnabled) {
      this.playAlertSound();
    }
  }

  handleSessionFinished(summary) {
    this.updateSystemStatusUI({ state: "STOPPED" });
    alert(`🎉 Phiên kiểm định hoàn tất!\n- Tổng kiểm tra: ${summary.total_items}\n- PASS: ${summary.total_pass}\n- DEFECT: ${summary.total_defect}\n- DỊ VẬT: ${summary.total_other ?? 0}\n- Tỷ lệ lỗi: ${summary.defect_rate}%`);
    this.loadOverviewData();
  }

  // ============================================================================
  // CÒI BÁO PHẾ PHẨM (WEB AUDIO API SYNTHESIZER)
  // ============================================================================
  playAlertSound() {
    try {
      if (!this.audioContext) {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        this.audioContext = new AudioCtx();
      }
      if (this.audioContext.state === "suspended") {
        this.audioContext.resume();
      }

      const osc = this.audioContext.createOscillator();
      const gain = this.audioContext.createGain();

      osc.type = "sawtooth";
      osc.frequency.setValueAtTime(880, this.audioContext.currentTime);
      osc.frequency.exponentialRampToValueAtTime(440, this.audioContext.currentTime + 0.18);

      gain.gain.setValueAtTime(0.2, this.audioContext.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + 0.2);

      osc.connect(gain);
      gain.connect(this.audioContext.destination);

      osc.start();
      osc.stop(this.audioContext.currentTime + 0.22);
    } catch (e) {
      console.warn("Không thể phát âm thanh cảnh báo:", e);
    }
  }

  // ============================================================================
  // ĐIỀU KHIỂN NÚT BẤM MÀN HÌNH LIVE INSPECTION
  // ============================================================================
  bindControls() {
    const btnStart = document.getElementById("btn-start-inspection");
    const btnPause = document.getElementById("btn-pause-inspection");
    const btnStop = document.getElementById("btn-stop-inspection");
    const btnSnapshot = document.getElementById("btn-snapshot");
    const btnFullscreen = document.getElementById("btn-fullscreen");
    const soundToggle = document.getElementById("sound-alarm-toggle");
    const btnSaveSettings = document.getElementById("btn-save-settings");

    const confSlider = document.getElementById("conf-slider");
    const confDisplay = document.getElementById("conf-display-val");
    if (confSlider && confDisplay) {
      confSlider.addEventListener("input", (e) => {
        confDisplay.textContent = Number(e.target.value).toFixed(2);
      });
    }

    if (soundToggle) {
      soundToggle.addEventListener("change", (e) => {
        this.soundEnabled = e.target.checked;
        this.settings.soundAlarm = this.soundEnabled;
        this.saveSettings();
      });
    }

    const modeSelect = document.getElementById("mode-select");
    const modeBadge = document.getElementById("active-mode-badge");
    if (modeSelect && modeBadge) {
      modeSelect.addEventListener("change", (e) => {
        if (e.target.value === "bottle_and_other") {
          modeBadge.textContent = "🍶 Chai & Dị vật khác";
        } else {
          modeBadge.textContent = "🔍 QC Chai Đạt / Lỗi";
        }
      });
    }

    const imgszSelect = document.getElementById("imgsz-select");
    const resBadge = document.getElementById("active-resolution-badge");
    if (imgszSelect && resBadge) {
      imgszSelect.addEventListener("change", (e) => {
        resBadge.textContent = e.target.value === "480" ? "⚡ 480px Fast" : "🎯 640px Chuẩn";
      });
    }

    if (btnStart) {
      btnStart.addEventListener("click", () => this.startInspection());
    }

    if (btnPause) {
      btnPause.addEventListener("click", () => this.togglePauseInspection());
    }

    if (btnStop) {
      btnStop.addEventListener("click", () => this.stopInspection());
    }

    if (btnSnapshot) {
      btnSnapshot.addEventListener("click", () => this.takeSnapshot());
    }

    if (btnSaveSettings) {
      btnSaveSettings.addEventListener("click", () => this.saveSettingsToServer());
    }

    if (btnFullscreen) {
      btnFullscreen.addEventListener("click", () => {
        const container = document.getElementById("video-viewport-container");
        if (container) {
          if (!document.fullscreenElement) {
            container.requestFullscreen().catch((err) => alert(`Lỗi toàn màn hình: ${err.message}`));
          } else {
            document.exitFullscreen();
          }
        }
      });
    }

    // Xử lý upload video
    const uploadInput = document.getElementById("video-file-upload");
    if (uploadInput) {
      uploadInput.addEventListener("change", async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append("file", file);

        try {
          const res = await fetch("/api/upload_video", { method: "POST", body: formData });
          const data = await res.json();
          if (data.success) {
            const sourceSelect = document.getElementById("source-select");
            const opt = document.createElement("option");
            opt.value = data.source;
            opt.textContent = `📁 ${data.filename}`;
            opt.selected = true;
            sourceSelect.appendChild(opt);
            alert(`Đã tải lên thành công: ${data.filename}`);
          } else {
            alert(`Tải file thất bại: ${data.detail || "Lỗi không xác định"}`);
          }
        } catch (err) {
          alert(`Lỗi khi tải file video: ${err.message}`);
        }
      });
    }
  }

  async startInspection() {
    const source = document.getElementById("source-select")?.value || "raw_videos/conveyor_demo.mp4";
    const model = document.getElementById("model-select")?.value || "models/conveyor_yolo26_30ep_best.pt";
    const mode = document.getElementById("mode-select")?.value || "bottle_and_other";
    const imgsz = parseInt(document.getElementById("imgsz-select")?.value) || 480;
    const conf = parseFloat(document.getElementById("conf-slider")?.value) || 0.45;
    const tracker = document.getElementById("tracker-select")?.value || "bytetrack.yaml";

    const tbody = document.getElementById("live-events-tbody");
    if (tbody) tbody.innerHTML = "";
    this.eventRows.clear();

    try {
      const res = await fetch("/api/start_inspection", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source, model, mode, imgsz, conf, tracker, loop: true })
      });
      const data = await res.json();
      if (!res.ok) {
        alert(`Không thể bắt đầu: ${data.detail || "Lỗi không xác định"}`);
        return;
      }

      const videoImg = document.getElementById("video-stream-feed");
      if (videoImg) {
        videoImg.src = `/api/video_feed?t=${Date.now()}`;
      }
    } catch (err) {
      alert(`Lỗi kết nối tới máy chủ: ${err.message}`);
    }
  }

  async togglePauseInspection() {
    const btnPause = document.getElementById("btn-pause-inspection");
    const isPaused = btnPause.textContent.includes("Tiếp tục");
    const endpoint = isPaused ? "/api/resume_inspection" : "/api/pause_inspection";

    try {
      const res = await fetch(endpoint, { method: "POST" });
      const data = await res.json();
      if (!res.ok) alert(`Thao tác thất bại: ${data.detail}`);
    } catch (err) {
      alert(`Lỗi: ${err.message}`);
    }
  }

  async stopInspection() {
    if (!confirm("Bạn có chắc muốn kết thúc phiên kiểm định hiện tại?")) return;
    try {
      const res = await fetch("/api/stop_inspection", { method: "POST" });
      const data = await res.json();
      if (!res.ok) alert(`Lỗi: ${data.detail}`);
    } catch (err) {
      alert(`Lỗi: ${err.message}`);
    }
  }

  async takeSnapshot() {
    try {
      const res = await fetch("/api/snapshot", { method: "POST" });
      const data = await res.json();
      if (res.ok && data.success) {
        alert(`📸 Đã lưu ảnh hiện trường tại:\n${data.path}`);
      } else {
        alert(`Không thể chụp ảnh: ${data.detail || "Chưa có khung hình"}`);
      }
    } catch (err) {
      alert(`Lỗi: ${err.message}`);
    }
  }

  // ============================================================================
  // MÀN HÌNH 1: TỔNG QUAN (OVERVIEW)
  // ============================================================================
  async loadOverviewData() {
    try {
      const [statusRes, historyRes] = await Promise.all([
        fetch("/api/status"),
        fetch("/api/history")
      ]);

      const status = await statusRes.json();
      const sessions = await historyRes.json();

      this.updateSystemStatusUI(status);

      let totalInspectedAll = 0;
      let totalPassAll = 0;
      let totalDefectAll = 0;

      sessions.forEach((s) => {
        totalInspectedAll += s.total_items || 0;
        totalPassAll += s.total_pass || 0;
        totalDefectAll += s.total_defect || 0;
      });

      const avgDefectRate = totalInspectedAll > 0
        ? ((totalDefectAll / totalInspectedAll) * 100).toFixed(1)
        : "0.0";

      const ovTotal = document.getElementById("ov-total-inspected");
      const ovPass = document.getElementById("ov-total-pass");
      const ovDefect = document.getElementById("ov-total-defect");
      const ovRate = document.getElementById("ov-defect-rate");
      const ovSessions = document.getElementById("ov-total-sessions");

      if (ovTotal) ovTotal.textContent = totalInspectedAll.toLocaleString();
      if (ovPass) ovPass.textContent = totalPassAll.toLocaleString();
      if (ovDefect) ovDefect.textContent = totalDefectAll.toLocaleString();
      if (ovRate) ovRate.textContent = `${avgDefectRate}%`;
      if (ovSessions) ovSessions.textContent = sessions.length;

      const tbody = document.getElementById("overview-recent-sessions-tbody");
      if (tbody) {
        if (sessions.length === 0) {
          tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">Chưa có phiên kiểm định nào được ghi nhận.</td></tr>`;
        } else {
          tbody.innerHTML = sessions.slice(0, 5).map((s) => `
            <tr>
              <td style="font-family: var(--font-mono); font-weight: 600;">${escapeHtml(s.session_id)}</td>
              <td style="color: var(--text-secondary);">${escapeHtml(s.start_time)}</td>
              <td>${escapeHtml(s.source)}</td>
              <td style="font-weight: 700;">${escapeHtml(s.total_items)}</td>
              <td><span class="badge-status pass">${escapeHtml(s.total_pass)} PASS</span></td>
              <td><span class="badge-status defect">${escapeHtml(s.total_defect)} DEFECT</span></td>
            </tr>
          `).join("");
        }
      }
    } catch (e) {
      console.warn("Lỗi nạp dữ liệu tổng quan:", e);
    }
  }

  // ============================================================================
  // MÀN HÌNH 3: LỊCH SỬ KIỂM ĐỊNH (HISTORY)
  // ============================================================================
  async loadHistoryData() {
    try {
      const res = await fetch("/api/history");
      const sessions = await res.json();
      const tbody = document.getElementById("history-sessions-tbody");
      if (!tbody) return;

      if (sessions.length === 0) {
        tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--text-muted); padding: 2rem;">Chưa có lịch sử phiên kiểm định. Hãy khởi chạy phiên đầu tiên tại mục "Kiểm định trực tiếp".</td></tr>`;
        return;
      }

      tbody.innerHTML = sessions.map((s) => `
        <tr>
          <td style="font-family: var(--font-mono); font-weight: 600;">${escapeHtml(s.session_id)}</td>
          <td>${escapeHtml(s.start_time)}</td>
          <td>${s.duration_sec ? `${escapeHtml(s.duration_sec)}s` : "--"}</td>
          <td>${escapeHtml(s.source)}</td>
          <td style="font-weight: 700;">${escapeHtml(s.total_items)}</td>
          <td><span class="badge-status pass">${escapeHtml(s.total_pass)}</span></td>
          <td><span class="badge-status defect">${escapeHtml(s.total_defect)}</span></td>
          <td style="font-weight: 600; color: ${s.defect_rate > 15 ? 'var(--color-defect)' : 'var(--text-primary)'};">${escapeHtml(s.defect_rate)}%</td>
          <td>
            <div style="display: flex; gap: 0.35rem;">
              <button class="btn btn-secondary" style="padding: 0.25rem 0.55rem; font-size: 0.78rem;" onclick="app.viewSessionDetail('${escapeHtml(s.session_id)}')">Chi tiết</button>
              <a href="/api/download_report/${encodeURIComponent(s.session_id)}" class="btn btn-primary" style="padding: 0.25rem 0.55rem; font-size: 0.78rem;" download>Tải CSV</a>
              <button class="btn btn-danger" style="padding: 0.25rem 0.45rem; font-size: 0.78rem;" onclick="app.deleteSession('${escapeHtml(s.session_id)}')">✕</button>
            </div>
          </td>
        </tr>
      `).join("");
    } catch (e) {
      console.warn("Lỗi nạp lịch sử:", e);
    }
  }

  async viewSessionDetail(sessionId) {
    try {
      const res = await fetch(`/api/history/${encodeURIComponent(sessionId)}`);
      const session = await res.json();
      if (!res.ok) return alert("Không tìm thấy thông tin phiên.");

      const title = document.getElementById("session-detail-title");
      const body = document.getElementById("session-detail-body");
      if (title) title.textContent = `Chi tiết phiên: ${session.session_id}`;

      const tracks = session.tracks || [];
      let tracksHtml = "";
      if (tracks.length === 0) {
        tracksHtml = `<p style="color: var(--text-muted); margin-top: 1rem;">Không có bản ghi từng chai hoặc chưa chốt sản phẩm nào.</p>`;
      } else {
        tracksHtml = `
          <div class="data-table-container" style="margin-top: 1rem; max-height: 380px;">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Mã Track</th>
                  <th>Phân loại</th>
                  <th>Độ tin cậy</th>
                  <th>Số frame quan sát</th>
                  <th>Thời gian xuất hiện</th>
                  <th>Trạng thái</th>
                </tr>
              </thead>
              <tbody>
                ${tracks.map((t) => `
                  <tr>
                    <td style="font-family: var(--font-mono); font-weight: 600;">#${escapeHtml(t.track_id)}</td>
                    <td style="font-weight: 500; color: ${t.state === 'DEFECT' ? 'var(--color-defect)' : (t.state === 'OTHER' ? '#c084fc' : 'var(--color-pass)')};">${escapeHtml(t.class_name)}</td>
                    <td style="font-family: var(--font-mono);">${escapeHtml(t.max_conf)}</td>
                    <td>${escapeHtml(t.obs_votes)} frames</td>
                    <td>${escapeHtml(t.first_ts)}s → ${escapeHtml(t.last_ts)}s</td>
                    <td>
                      <span class="badge-status ${escapeHtml(t.state.toLowerCase())}">${escapeHtml(t.state)}</span>
                      ${t.was_corrected ? '<span class="badge-updated">Hiệu chỉnh</span>' : ''}
                    </td>
                  </tr>
                `).join("")}
              </tbody>
            </table>
          </div>
        `;
      }

      if (body) {
        body.innerHTML = `
          <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.75rem; margin-bottom: 1rem;">
            <div class="mini-kpi-card"><div class="label">Tổng kiểm tra</div><div class="val">${escapeHtml(session.total_items)}</div></div>
            <div class="mini-kpi-card pass"><div class="label">Đạt chuẩn</div><div class="val">${escapeHtml(session.total_pass)}</div></div>
            <div class="mini-kpi-card defect"><div class="label">Phế phẩm</div><div class="val">${escapeHtml(session.total_defect)}</div></div>
            <div class="mini-kpi-card rate"><div class="label">Tỷ lệ lỗi</div><div class="val">${escapeHtml(session.defect_rate)}%</div></div>
          </div>
          <p><strong>Nguồn kiểm định:</strong> ${escapeHtml(session.source)} | <strong>Model:</strong> ${escapeHtml(session.model_name)}</p>
          <p><strong>Bắt đầu:</strong> ${escapeHtml(session.start_time)} | <strong>Kết thúc:</strong> ${escapeHtml(session.end_time || '--')} (${escapeHtml(session.duration_sec)}s)</p>
          ${tracksHtml}
        `;
      }

      this.openModal("session-detail-modal");
    } catch (e) {
      alert(`Lỗi xem chi tiết: ${e.message}`);
    }
  }

  async deleteSession(sessionId) {
    if (!confirm(`Bạn có chắc muốn xóa lịch sử phiên ${sessionId}?`)) return;
    try {
      const res = await fetch(`/api/history/${encodeURIComponent(sessionId)}`, { method: "DELETE" });
      if (res.ok) {
        this.loadHistoryData();
      } else {
        alert("Không thể xóa phiên.");
      }
    } catch (e) {
      alert(`Lỗi: ${e.message}`);
    }
  }

  // ============================================================================
  // MÀN HÌNH 4: ĐÁNH GIÁ MÔ HÌNH (EVALUATION)
  // ============================================================================
  async loadEvaluationData() {
    try {
      const res = await fetch("/api/evaluation");
      const data = await res.json();

      const tbody = document.getElementById("eval-metrics-tbody");
      if (tbody && data.test_metrics) {
        const ov = data.test_metrics.overall;
        let html = `
          <tr style="background-color: rgba(2, 132, 199, 0.08); font-weight: 700;">
            <td>Tất cả (Overall)</td>
            <td>${escapeHtml(data.test_metrics.num_images)}</td>
            <td>${escapeHtml(data.test_metrics.num_boxes)}</td>
            <td style="color: var(--color-primary-light);">${escapeHtml(ov.precision)}%</td>
            <td style="color: var(--color-primary-light);">${escapeHtml(ov.recall)}%</td>
            <td style="color: var(--color-pass);">${escapeHtml(ov.map50)}%</td>
            <td style="color: var(--color-pass);">${escapeHtml(ov.map50_95)}%</td>
          </tr>
        `;

        data.test_metrics.classes.forEach((c) => {
          const isDefect = c.name.includes("defect");
          html += `
            <tr>
              <td style="font-weight: 600; color: ${isDefect ? 'var(--color-defect)' : 'var(--color-pass)'};">${escapeHtml(c.name)}</td>
              <td>${escapeHtml(c.images)}</td>
              <td>${escapeHtml(c.boxes)}</td>
              <td>${escapeHtml(c.precision)}%</td>
              <td>${escapeHtml(c.recall)}%</td>
              <td style="font-weight: 700;">${escapeHtml(c.map50)}%</td>
              <td>${escapeHtml(c.map50_95)}%</td>
            </tr>
          `;
        });
        tbody.innerHTML = html;
      }

      const speed = data.speed_benchmark;
      const speedContainer = document.getElementById("eval-speed-details");
      if (speedContainer && speed) {
        speedContainer.innerHTML = `
          <p><strong>Thiết bị đo lường:</strong> ${escapeHtml(speed.device)}</p>
          <p><strong>Thời gian tiền xử lý:</strong> ${escapeHtml(speed.preprocess_ms)} ms/ảnh | <strong>Suy luận (Inference):</strong> ${escapeHtml(speed.inference_ms)} ms/ảnh | <strong>Hậu xử lý:</strong> ${escapeHtml(speed.postprocess_ms)} ms/ảnh</p>
          <p><strong>Tốc độ thực tế đạt được:</strong> <span style="font-size: 1.15rem; font-weight: 700; color: var(--color-pass);">${escapeHtml(speed.fps_cpu)} FPS (CPU)</span> — Dự kiến: <span style="font-weight: 600; color: var(--color-primary-light);">${escapeHtml(speed.fps_gpu_projected)}</span></p>
        `;
      }

      this.initChartTabs(data.charts);
    } catch (e) {
      console.warn("Lỗi nạp số liệu đánh giá:", e);
    }
  }

  initChartTabs(charts) {
    const nav = document.getElementById("chart-tabs-nav");
    const container = document.getElementById("chart-display-container");
    if (!nav || !container || !charts) return;

    nav.innerHTML = charts.map((ch, idx) => `
      <button class="chart-tab-btn ${idx === 0 ? 'active' : ''}" data-chart-id="${escapeHtml(ch.id)}">
        ${escapeHtml(ch.title.split("(")[0])}
      </button>
    `).join("");

    const displayChart = (chart) => {
      container.innerHTML = `
        <div style="margin-bottom: 0.75rem; text-align: left; width: 100%;">
          <h4 style="font-size: 1rem; color: var(--text-primary);">${escapeHtml(chart.title)}</h4>
          <p style="font-size: 0.82rem; color: var(--text-secondary); margin-top: 0.2rem;">${escapeHtml(chart.description)}</p>
        </div>
        <img src="${escapeHtml(chart.image_url)}" alt="${escapeHtml(chart.title)}" class="chart-img-preview" onclick="app.openImageZoom('${escapeHtml(chart.image_url)}', '${escapeHtml(chart.title)}')" />
        <div style="margin-top: 0.5rem; font-size: 0.75rem; color: var(--text-muted);">💡 Nhấp vào ảnh để phóng to toàn màn hình</div>
      `;
    };

    displayChart(charts[0]);

    nav.querySelectorAll(".chart-tab-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        nav.querySelectorAll(".chart-tab-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        const chartId = btn.getAttribute("data-chart-id");
        const chart = charts.find((c) => c.id === chartId);
        if (chart) displayChart(chart);
      });
    });
  }

  // ============================================================================
  // MÀN HÌNH 5: DỮ LIỆU & MÔ HÌNH (DATASET & MODELS)
  // ============================================================================
  async loadDatasetData() {
    try {
      const [dsRes, modelsRes] = await Promise.all([
        fetch("/api/dataset_info"),
        fetch("/api/models")
      ]);

      const ds = await dsRes.json();
      const models = await modelsRes.json();

      const dsSplits = document.getElementById("dataset-splits-container");
      if (dsSplits && ds.splits) {
        dsSplits.innerHTML = `
          <div class="mini-kpi-card"><div class="label">Tập Huấn luyện (Train)</div><div class="val">${escapeHtml(ds.splits.train.count)} <span style="font-size: 0.9rem; color: var(--text-secondary);">(${escapeHtml(ds.splits.train.pct)}%)</span></div></div>
          <div class="mini-kpi-card"><div class="label">Tập Kiểm định (Val)</div><div class="val">${escapeHtml(ds.splits.val.count)} <span style="font-size: 0.9rem; color: var(--text-secondary);">(${escapeHtml(ds.splits.val.pct)}%)</span></div></div>
          <div class="mini-kpi-card"><div class="label">Tập Kiểm thử (Test)</div><div class="val">${escapeHtml(ds.splits.test.count)} <span style="font-size: 0.9rem; color: var(--text-secondary);">(${escapeHtml(ds.splits.test.pct)}%)</span></div></div>
          <div class="mini-kpi-card rate"><div class="label">Tổng số ảnh chuẩn hóa</div><div class="val">${escapeHtml(ds.total_images)}</div></div>
        `;
      }

      const tbody = document.getElementById("models-list-tbody");
      if (tbody) {
        tbody.innerHTML = models.map((m) => `
          <tr style="${m.is_active ? 'background-color: rgba(16, 185, 129, 0.06);' : ''}">
            <td style="font-weight: 600; font-family: var(--font-mono);">${escapeHtml(m.name)}</td>
            <td>${escapeHtml(m.size_mb)} MB</td>
            <td>${escapeHtml(m.modified)}</td>
            <td>
              ${m.is_active
                ? '<span class="badge-status pass">Đang hoạt động (Active)</span>'
                : '<span class="badge-status" style="background: rgba(148, 163, 184, 0.1); color: var(--text-secondary);">Dự phòng / Backup</span>'}
            </td>
            <td style="font-size: 0.82rem; color: var(--text-secondary);">${escapeHtml(m.description)}</td>
          </tr>
        `).join("");
      }
    } catch (e) {
      console.warn("Lỗi nạp dữ liệu dataset:", e);
    }
  }

  // ============================================================================
  // CÁC HỘP THOẠI (MODALS) & ZOOM ẢNH
  // ============================================================================
  bindModals() {
    const btnHelp = document.getElementById("btn-help-modal");
    if (btnHelp) {
      btnHelp.addEventListener("click", () => this.openModal("help-modal"));
    }

    document.querySelectorAll(".modal-close-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const modal = btn.closest(".modal-backdrop");
        if (modal) modal.classList.remove("open");
      });
    });

    document.querySelectorAll(".modal-backdrop").forEach((backdrop) => {
      backdrop.addEventListener("click", (e) => {
        if (e.target === backdrop) backdrop.classList.remove("open");
      });
    });
  }

  openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.add("open");
  }

  openImageZoom(imgUrl, title) {
    const modal = document.getElementById("image-zoom-modal");
    const zoomImg = document.getElementById("image-zoom-img");
    const zoomTitle = document.getElementById("image-zoom-title");
    if (modal && zoomImg) {
      zoomImg.src = imgUrl;
      if (zoomTitle) zoomTitle.textContent = title || "Xem chi tiết biểu đồ";
      modal.classList.add("open");
    }
  }
}

// Khởi tạo ứng dụng khi DOM sẵn sàng
document.addEventListener("DOMContentLoaded", () => {
  window.app = new ConveyorVisionApp();
});
