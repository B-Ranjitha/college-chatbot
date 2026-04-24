/**
 * main.js — BBC College AI Chatbot Frontend
 * Features: streaming, voice I/O, markdown, feedback, dark/light, suggestions
 */

'use strict';

// ─────────────── STATE ───────────────
const state = {
  isTyping: false,
  isListening: false,
  user: null,
  charLimit: 1000,
};

// ─────────────── DOM REFS ───────────────
const $ = id => document.getElementById(id);
const chatMessages  = $('chatMessages');
const chatInput     = $('chatInput');
const sendBtn       = $('sendBtn');
const typingInd     = $('typingIndicator');
const welcomeScreen = $('welcomeScreen');
const charCount     = $('charCount');
const toast         = $('toast');
const sidebar       = $('sidebar');
const overlay       = $('overlay');
const micBtn        = $('micBtn');

// ─────────────── INIT ───────────────
(async function init() {
  applyTheme();
  loadUser();
  loadHistory();
  bindEvents();
  marked.setOptions({ breaks: true, gfm: true });
})();

async function loadUser() {
  try {
    const r = await fetch('/api/me');
    const d = await r.json();
    state.user = d;
  } catch {}
}

async function loadHistory() {
  try {
    const r = await fetch('/api/chat/history');
    const d = await r.json();
    if (d.history && d.history.length > 0) {
      hideWelcome();
      d.history.forEach(msg => {
        if (msg.role === 'user') appendUserMsg(msg.message, formatTime(msg.created_at));
        else appendBotMsg(msg.message, msg.engine_used || 'rule', [], msg.id);
      });
      scrollToBottom();
    }
  } catch {}
}

// ─────────────── EVENTS ───────────────
function bindEvents() {
  sendBtn.addEventListener('click', handleSend);

  chatInput.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  });

  chatInput.addEventListener('input', () => {
    autoResize(chatInput);
    const len = chatInput.value.length;
    charCount.textContent = `${len} / ${state.charLimit}`;
    sendBtn.disabled = len === 0 || state.isTyping;
  });

  $('newChatBtn').addEventListener('click', async () => {
    await fetch('/api/chat/clear', { method: 'POST' });
    chatMessages.innerHTML = '';
    showWelcome();
    closeSidebar();
    showToast('✨ New conversation started');
  });

  $('clearChatBtn').addEventListener('click', async () => {
    if (!confirm('Clear this conversation?')) return;
    await fetch('/api/chat/clear', { method: 'POST' });
    chatMessages.innerHTML = '';
    showWelcome();
    showToast('🗑 Chat cleared');
  });

  $('themeToggle').addEventListener('click', () => {
    const theme = document.documentElement.getAttribute('data-theme');
    const next = theme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
    showToast(`${next === 'dark' ? '🌙' : '☀️'} Switched to ${next} mode`);
  });

  $('exportBtn').addEventListener('click', () => {
    window.open('/api/chat/export', '_blank');
  });

  const logoutBtn = $('logoutBtn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', async () => {
      await fetch('/api/logout', { method: 'POST' });
      location.reload();
    });
  }

  $('sidebarOpen').addEventListener('click', openSidebar);
  $('sidebarClose').addEventListener('click', closeSidebar);
  overlay.addEventListener('click', closeSidebar);

  // Quick cards
  document.querySelectorAll('.quick-card, .sidebar-item[data-query]').forEach(el => {
    el.addEventListener('click', () => {
      const q = el.dataset.query;
      if (q) {
        chatInput.value = q;
        chatInput.dispatchEvent(new Event('input'));
        handleSend();
        closeSidebar();
      }
    });
  });

  // Voice
  micBtn.addEventListener('click', toggleVoice);
}

// ─────────────── SEND ───────────────
async function handleSend() {
  const msg = chatInput.value.trim();
  if (!msg || state.isTyping) return;

  hideWelcome();
  chatInput.value = '';
  chatInput.style.height = 'auto';
  sendBtn.disabled = true;
  charCount.textContent = `0 / ${state.charLimit}`;

  appendUserMsg(msg, nowTime());
  showTyping();
  state.isTyping = true;

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg }),
    });
    const data = await res.json();
    hideTyping();

    if (data.error) {
      appendBotMsg('⚠️ ' + data.error, 'error', []);
    } else {
      appendBotMsg(data.answer, data.engine, data.suggestions || [], data.msg_id);
      if (data.answer) speakResponse(data.answer);
    }
  } catch (err) {
    hideTyping();
    appendBotMsg('⚠️ Network error. Please check your connection and try again.', 'error', []);
  } finally {
    state.isTyping = false;
    sendBtn.disabled = chatInput.value.length === 0;
    scrollToBottom();
  }
}

// ─────────────── MESSAGE RENDERING ───────────────
function appendUserMsg(text, time) {
  const tmpl = document.getElementById('userMsgTemplate');
  const el = tmpl.content.cloneNode(true).querySelector('.message');
  el.querySelector('.msg-bubble').textContent = text;
  el.querySelector('.msg-time').textContent = time;
  chatMessages.appendChild(el);
  scrollToBottom();
}

function appendBotMsg(text, engine, suggestions, msgId) {
  const tmpl = document.getElementById('botMsgTemplate');
  const el = tmpl.content.cloneNode(true).querySelector('.message');

  const bubble = el.querySelector('.msg-bubble');
  bubble.innerHTML = marked.parse(text || '');

  el.querySelector('.msg-time').textContent = nowTime();

  const badge = el.querySelector('.engine-badge');
  const engineLabels = { rule: '⚡ Quick', semantic: '🧠 Smart', llm: '🤖 AI', fallback: '📋 FAQ', error: '⚠️' };
  badge.textContent = engineLabels[engine] || '⚡';

  // Feedback buttons
  const thumbUp = el.querySelector('.thumb-up');
  const thumbDown = el.querySelector('.thumb-down');
  if (msgId) {
    thumbUp.addEventListener('click', () => sendFeedback(msgId, 1, thumbUp, thumbDown));
    thumbDown.addEventListener('click', () => sendFeedback(msgId, 0, thumbDown, thumbUp));
  }

  // Copy button
  el.querySelector('.copy-btn').addEventListener('click', () => {
    navigator.clipboard.writeText(text).then(() => showToast('📋 Copied!'));
  });

  // Suggestions
  const sugRow = el.querySelector('.suggestions-row');
  if (suggestions && suggestions.length > 0) {
    suggestions.forEach(s => {
      const chip = document.createElement('button');
      chip.className = 'suggestion-chip';
      chip.textContent = s;
      chip.addEventListener('click', () => {
        chatInput.value = s;
        chatInput.dispatchEvent(new Event('input'));
        handleSend();
      });
      sugRow.appendChild(chip);
    });
  }

  chatMessages.appendChild(el);
  scrollToBottom();
}

async function sendFeedback(msgId, rating, activeBtn, otherBtn) {
  try {
    await fetch('/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: msgId, rating }),
    });
    activeBtn.classList.add('active');
    otherBtn.classList.remove('active');
    showToast(rating === 1 ? '👍 Thanks for the feedback!' : '👎 Feedback noted, we\'ll improve!');
  } catch {}
}

// ─────────────── VOICE ───────────────
let recognition = null;

function toggleVoice() {
  if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
    showToast('🎙 Voice not supported in this browser');
    return;
  }

  if (state.isListening) {
    recognition?.stop();
    return;
  }

  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SpeechRec();
  recognition.lang = 'en-IN';
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;

  recognition.onstart = () => {
    state.isListening = true;
    micBtn.classList.add('listening');
    showToast('🎙 Listening... Speak now');
  };

  recognition.onresult = e => {
    const transcript = e.results[0][0].transcript;
    chatInput.value = transcript;
    chatInput.dispatchEvent(new Event('input'));
    handleSend();
  };

  recognition.onerror = e => {
    showToast('🎙 Voice error: ' + e.error);
  };

  recognition.onend = () => {
    state.isListening = false;
    micBtn.classList.remove('listening');
  };

  recognition.start();
}

const synth = window.speechSynthesis;
function speakResponse(text) {
  if (!synth) return;
  // Only speak short responses
  const clean = text.replace(/[#*`[\]()]/g, '').substring(0, 200);
  const utt = new SpeechSynthesisUtterance(clean);
  utt.lang = 'en-IN';
  utt.rate = 1.05;
  utt.pitch = 1;
  synth.cancel();
  synth.speak(utt);
}

// ─────────────── TYPING INDICATOR ───────────────
function showTyping() { typingInd.style.display = 'flex'; scrollToBottom(); }
function hideTyping()  { typingInd.style.display = 'none'; }

// ─────────────── WELCOME SCREEN ───────────────
function hideWelcome() {
  if (welcomeScreen) welcomeScreen.style.display = 'none';
}
function showWelcome() {
  if (welcomeScreen) welcomeScreen.style.display = 'flex';
}

// ─────────────── SIDEBAR ───────────────
function openSidebar()  { sidebar.classList.add('open'); overlay.classList.add('active'); }
function closeSidebar() { sidebar.classList.remove('open'); overlay.classList.remove('active'); }

// ─────────────── THEME ───────────────
function applyTheme() {
  const saved = localStorage.getItem('theme') || 'dark';
  document.documentElement.setAttribute('data-theme', saved);
}

// ─────────────── TOAST ───────────────
let toastTimer;
function showToast(msg) {
  toast.textContent = msg;
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 3000);
}

// ─────────────── UTILS ───────────────
function scrollToBottom() {
  requestAnimationFrame(() => {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  });
}

function nowTime() {
  return new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
}

function formatTime(iso) {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
  } catch { return ''; }
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 140) + 'px';
}
