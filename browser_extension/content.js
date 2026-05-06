/* global chrome */
(function () {
  'use strict';

  if (window.__rtmFabInjected) return;
  window.__rtmFabInjected = true;

  let autoAlign = false;
  let lensRunning = false;

  // ── Toast ─────────────────────────────────────────────────────────
  function showToast(msg, type = 'info') {
    let toast = document.getElementById('rtm-toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'rtm-toast';
      toast.className = 'rtm-toast';
      document.body.appendChild(toast);
    }
    toast.className = 'rtm-toast rtm-toast-' + type;
    toast.textContent = msg;
    requestAnimationFrame(() => toast.classList.add('show'));
    setTimeout(() => toast.classList.remove('show'), 2500);
  }

  // ── Send to background → Native Host ─────────────────────────────
  function send(msg) {
    chrome.runtime.sendMessage(msg, (resp) => {
      if (chrome.runtime.lastError) {
        const err = chrome.runtime.lastError.message || '';
        if (err.includes('Extension context invalidated')) {
          // Extension was reloaded; old content script is orphaned.
          // Silently remove the stale FAB so the user isn't spammed with toasts.
          const stale = document.getElementById('rtm-fab-container');
          if (stale) {
            stale.remove();
            window.__rtmFabInjected = false;
          }
          return;
        }
        showToast('RealTimeMix not connected', 'error');
      } else if (resp && resp.status === 'error') {
        showToast(resp.message || 'Error', 'error');
      }
    });
  }

  // ── Find nearest media element ───────────────────────────────────
  function findMediaElement(el) {
    while (el && el !== document.body) {
      if (el.tagName === 'IMG' || el.tagName === 'VIDEO') {
        return el;
      }
      el = el.parentElement;
    }
    return null;
  }

  // ── Get element rect relative to top-level window screen ─────────
  function getScreenRect(el) {
    let rect = el.getBoundingClientRect();
    let win = window;
    let iframeDepth = 0;

    // Walk up through nested iframes and accumulate each iframe's offset
    while (win !== win.top) {
      try {
        const frameEl = win.frameElement;
        if (frameEl) {
          const fr = frameEl.getBoundingClientRect();
          rect = {
            left: rect.left + fr.left,
            top: rect.top + fr.top,
            width: rect.width,
            height: rect.height
          };
          iframeDepth++;
        }
        win = win.parent;
      } catch (err) {
        // Cross-origin iframe: can't access frameElement or parent document.
        // We'll send what we have; the offset will be incomplete.
        break;
      }
    }
    return { rect, iframeDepth, win };
  }

  // ── Ctrl+Shift+LMB ───────────────────────────────────────────────
  document.addEventListener('mousedown', (e) => {
    if (!(e.ctrlKey && e.shiftKey && e.button === 0)) return;
    if (!autoAlign) {
      showToast('Auto-align is off. Enable it in the floating panel.', 'info');
      return;
    }
    e.preventDefault();
    e.stopPropagation();

    const media = findMediaElement(e.target);
    if (!media) {
      showToast('Please click an image or video element', 'error');
      return;
    }

    const { rect, iframeDepth, win } = getScreenRect(media);
    const dpr = win.devicePixelRatio || 1;

    // e.screenY - e.clientY gives the viewport top edge in CSS screen px,
    // bypassing the need to know browser UI height. Same for X.
    const viewportLeft = e.screenX - e.clientX;
    const viewportTop  = e.screenY - e.clientY;
    const x = Math.round((viewportLeft + rect.left) * dpr);
    const y = Math.round((viewportTop  + rect.top)  * dpr);
    const w = Math.round(rect.width  * dpr);
    const h = Math.round(rect.height * dpr);

    console.log('[RTM align debug]', JSON.stringify({
      screenX: e.screenX, screenY: e.screenY,
      clientX: e.clientX, clientY: e.clientY,
      viewportLeft, viewportTop,
      rectLeft: rect.left, rectTop: rect.top,
      rectW: rect.width, rectH: rect.height,
      dpr, x, y, w, h,
    }));

    send({
      cmd: 'align',
      rect: { x, y, width: w, height: h },
      type: media.tagName.toLowerCase(),
      debug: {
        iframeDepth,
        screenLeft: win.screenLeft,
        screenTop: win.screenTop,
        cssRect: { left: rect.left, top: rect.top, width: rect.width, height: rect.height },
        dpr,
        url: win.location.href
      }
    });
    showToast('Aligning lens…', 'success');
  }, true);

  // ── FAB ──────────────────────────────────────────────────────────
  function createFab() {
    const container = document.createElement('div');
    container.id = 'rtm-fab-container';

    const panel = document.createElement('div');
    panel.id = 'rtm-fab-panel';
    panel.className = 'rtm-collapsed';

    // Title
    const title = document.createElement('div');
    title.className = 'rtm-title';
    title.textContent = '🔒 RealTimeMix';
    panel.appendChild(title);

    // Seed box
    const seedBox = document.createElement('textarea');
    seedBox.className = 'rtm-seed-box';
    seedBox.placeholder = 'Paste seed here…';
    panel.appendChild(seedBox);

    // Apply seed button
    const btnApply = document.createElement('button');
    btnApply.className = 'rtm-btn rtm-btn-primary';
    btnApply.textContent = 'Apply Seed';
    btnApply.onclick = () => {
      const seed = seedBox.value.trim();
      if (!seed) {
        showToast('Seed is empty', 'error');
        return;
      }
      send({ cmd: 'set_seed', seed });
      showToast('Seed sent', 'success');
    };
    panel.appendChild(btnApply);

    // Auto-align toggle
    const toggleRow = document.createElement('div');
    toggleRow.className = 'rtm-row';
    const toggleWrap = document.createElement('label');
    toggleWrap.className = 'rtm-toggle-wrap';
    const toggleSwitch = document.createElement('input');
    toggleSwitch.type = 'checkbox';
    toggleSwitch.className = 'rtm-switch';
    toggleSwitch.checked = autoAlign;
    toggleSwitch.onchange = () => {
      autoAlign = toggleSwitch.checked;
      send({ cmd: 'toggle_auto_align', enabled: autoAlign });
    };
    const toggleLabel = document.createElement('span');
    toggleLabel.textContent = 'Auto Align';
    toggleWrap.appendChild(toggleSwitch);
    toggleWrap.appendChild(toggleLabel);
    toggleRow.appendChild(toggleWrap);
    panel.appendChild(toggleRow);

    // Lens start/stop button
    const btnLens = document.createElement('button');
    btnLens.className = 'rtm-btn rtm-btn-primary';
    btnLens.textContent = '▶ Start Lens';
    btnLens.onclick = () => {
      if (lensRunning) {
        send({ cmd: 'stop_lens' });
      } else {
        send({ cmd: 'start_lens' });
      }
    };
    panel.appendChild(btnLens);

    // Toggle button (floating circle)
    const toggleBtn = document.createElement('button');
    toggleBtn.id = 'rtm-fab-toggle';
    toggleBtn.textContent = '🔒';
    toggleBtn.onclick = () => {
      panel.classList.toggle('rtm-collapsed');
    };

    container.appendChild(panel);
    container.appendChild(toggleBtn);
    document.body.appendChild(container);

    // Update UI helper
    function updateUI() {
      btnLens.textContent = lensRunning ? '⏹ Stop Lens' : '▶ Start Lens';
      btnLens.className = lensRunning
        ? 'rtm-btn rtm-btn-danger'
        : 'rtm-btn rtm-btn-primary';
      toggleSwitch.checked = autoAlign;
    }

    // Listen for host state updates
    chrome.runtime.onMessage.addListener((msg) => {
      if (msg.from === 'host') {
        const d = msg.data || {};
        if (d.lens_running !== undefined) lensRunning = d.lens_running;
        if (d.auto_align !== undefined) {
          autoAlign = d.auto_align;
        }
        updateUI();
        if (d.message && d.status === 'error') {
          showToast(d.message, 'error');
        }
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', createFab);
  } else {
    createFab();
  }
})();
