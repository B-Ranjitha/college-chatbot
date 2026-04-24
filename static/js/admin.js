/**
 * admin.js — Admin Dashboard Logic
 * FAQs CRUD, chat logs, analytics
 */
'use strict';

// Theme
(function() {
  document.documentElement.setAttribute('data-theme', localStorage.getItem('theme') || 'dark');
})();

const toast = document.getElementById('toast');
let toastTimer;
function showToast(msg) {
  toast.textContent = msg;
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 3000);
}

// ─────────────── TAB NAVIGATION ───────────────
let currentTab = 'overview';
document.querySelectorAll('.admin-nav-item').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.admin-nav-item').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.admin-tab').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    currentTab = btn.dataset.tab;
    document.getElementById(`tab-${currentTab}`).classList.add('active');
    if (currentTab === 'overview') loadOverview();
    else if (currentTab === 'faqs') loadFaqs();
    else if (currentTab === 'chats') loadChats();
    else if (currentTab === 'analytics') loadAnalytics();
  });
});

// ─────────────── OVERVIEW ───────────────
async function loadOverview() {
  try {
    const r = await fetch('/api/admin/analytics');
    const d = await r.json();
    renderStats(d.summary);
    renderTopQueries(d.top_queries);
  } catch (e) {
    showToast('❌ Failed to load overview');
  }
}

function renderStats(s) {
  const grid = document.getElementById('statsGrid');
  grid.innerHTML = `
    <div class="stat-card">
      <div class="stat-icon">💬</div>
      <div class="stat-value">${s.total_chats.toLocaleString()}</div>
      <div class="stat-label">Total Queries</div>
    </div>
    <div class="stat-card">
      <div class="stat-icon">👤</div>
      <div class="stat-value">${s.total_users.toLocaleString()}</div>
      <div class="stat-label">Registered Users</div>
    </div>
    <div class="stat-card">
      <div class="stat-icon">❓</div>
      <div class="stat-value">${s.total_faqs}</div>
      <div class="stat-label">FAQs in DB</div>
    </div>
    <div class="stat-card">
      <div class="stat-icon">👍</div>
      <div class="stat-value">${s.positive_feedback}</div>
      <div class="stat-label">Positive Feedback</div>
    </div>
  `;
}

function renderTopQueries(queries) {
  const list = document.getElementById('topQueriesList');
  if (!queries.length) { list.innerHTML = '<p style="color:var(--text-muted);font-size:13px">No queries yet.</p>'; return; }
  list.innerHTML = queries.map(q => `
    <div class="query-item">
      <span class="query-text">${escapeHtml(q.query)}</span>
      <span class="query-cat">${q.category || 'general'}</span>
      <span class="query-count">×${q.count}</span>
    </div>
  `).join('');
}

document.getElementById('buildEmbeddingsBtn').addEventListener('click', async () => {
  showToast('🧠 Building embeddings...');
  try {
    const r = await fetch('/api/admin/build-embeddings', { method: 'POST' });
    const d = await r.json();
    showToast(`✅ Built ${d.built} embeddings`);
  } catch { showToast('❌ Failed to build embeddings'); }
});

// ─────────────── FAQs ───────────────
let allFaqs = [];

async function loadFaqs() {
  try {
    const r = await fetch('/api/admin/faqs');
    const d = await r.json();
    allFaqs = d.faqs;
    renderFaqs(allFaqs);
  } catch { showToast('❌ Failed to load FAQs'); }
}

function renderFaqs(faqs) {
  const list = document.getElementById('faqList');
  if (!faqs.length) { list.innerHTML = '<p style="color:var(--text-muted);font-size:13px;padding:20px">No FAQs found.</p>'; return; }
  list.innerHTML = faqs.map(f => `
    <div class="faq-item" data-id="${f.id}">
      <div class="faq-item-header">
        <div>
          <span class="faq-cat-badge">${f.category}</span>
          <p class="faq-question" style="margin-top:6px">${escapeHtml(f.question)}</p>
        </div>
        <div class="faq-actions">
          <button class="faq-edit-btn" onclick="openEditModal(${f.id})">✏️ Edit</button>
          <button class="faq-del-btn" onclick="deleteFaq(${f.id})">🗑 Del</button>
        </div>
      </div>
      <p class="faq-answer">${escapeHtml(f.answer.substring(0, 150))}${f.answer.length > 150 ? '…' : ''}</p>
    </div>
  `).join('');
}

// Search & filter
document.getElementById('faqSearch').addEventListener('input', filterFaqs);
document.getElementById('faqCategoryFilter').addEventListener('change', filterFaqs);

function filterFaqs() {
  const q = document.getElementById('faqSearch').value.toLowerCase();
  const cat = document.getElementById('faqCategoryFilter').value;
  const filtered = allFaqs.filter(f => {
    const matchCat = !cat || f.category === cat;
    const matchQ = !q || f.question.toLowerCase().includes(q) || f.answer.toLowerCase().includes(q);
    return matchCat && matchQ;
  });
  renderFaqs(filtered);
}

// Modal
const modal = document.getElementById('faqModal');
document.getElementById('addFaqBtn').addEventListener('click', () => openAddModal());
document.getElementById('modalClose').addEventListener('click', closeModal);
document.getElementById('modalCancel').addEventListener('click', closeModal);

function openAddModal() {
  document.getElementById('modalTitle').textContent = 'Add FAQ';
  document.getElementById('faqId').value = '';
  document.getElementById('faqCategory').value = 'admissions';
  document.getElementById('faqQuestion').value = '';
  document.getElementById('faqAnswer').value = '';
  modal.style.display = 'flex';
}

function openEditModal(id) {
  const faq = allFaqs.find(f => f.id === id);
  if (!faq) return;
  document.getElementById('modalTitle').textContent = 'Edit FAQ';
  document.getElementById('faqId').value = faq.id;
  document.getElementById('faqCategory').value = faq.category;
  document.getElementById('faqQuestion').value = faq.question;
  document.getElementById('faqAnswer').value = faq.answer;
  modal.style.display = 'flex';
}

function closeModal() { modal.style.display = 'none'; }

document.getElementById('faqForm').addEventListener('submit', async e => {
  e.preventDefault();
  const id = document.getElementById('faqId').value;
  const payload = {
    category: document.getElementById('faqCategory').value,
    question: document.getElementById('faqQuestion').value.trim(),
    answer:   document.getElementById('faqAnswer').value.trim(),
  };
  if (!payload.question || !payload.answer) { showToast('⚠️ Fill all fields'); return; }

  try {
    const url = id ? `/api/admin/faqs/${id}` : '/api/admin/faqs';
    const method = id ? 'PUT' : 'POST';
    const r = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    const d = await r.json();
    if (d.success) {
      showToast(id ? '✅ FAQ updated' : '✅ FAQ added');
      closeModal();
      loadFaqs();
    }
  } catch { showToast('❌ Save failed'); }
});

async function deleteFaq(id) {
  if (!confirm('Delete this FAQ?')) return;
  try {
    await fetch(`/api/admin/faqs/${id}`, { method: 'DELETE' });
    showToast('🗑 FAQ deleted');
    loadFaqs();
  } catch { showToast('❌ Delete failed'); }
}

// ─────────────── CHATS ───────────────
async function loadChats() {
  try {
    const r = await fetch('/api/admin/chats');
    const d = await r.json();
    const list = document.getElementById('chatLogList');
    if (!d.chats.length) { list.innerHTML = '<p style="color:var(--text-muted);font-size:13px;padding:20px">No chats yet.</p>'; return; }
    list.innerHTML = d.chats.map(c => `
      <div class="chat-log-item">
        <span class="chat-log-role ${c.role}">${c.role === 'user' ? '👤 User' : '🤖 Bot'}</span>
        <span class="chat-log-engine">${c.engine_used || 'rule'}</span>
        ${escapeHtml(c.message.substring(0, 120))}${c.message.length > 120 ? '…' : ''}
        <span class="chat-log-time">${c.created_at ? c.created_at.substring(0,16) : ''}</span>
      </div>
    `).join('');
  } catch { showToast('❌ Failed to load chats'); }
}

// ─────────────── ANALYTICS ───────────────
async function loadAnalytics() {
  try {
    const r = await fetch('/api/admin/analytics');
    const d = await r.json();
    const s = d.summary;
    const total = s.positive_feedback + s.negative_feedback;
    const pos_pct = total ? Math.round(s.positive_feedback / total * 100) : 0;

    document.getElementById('analyticsContent').innerHTML = `
      <div class="stats-grid" style="margin-bottom:24px">
        <div class="stat-card">
          <div class="stat-icon">📊</div>
          <div class="stat-value">${pos_pct}%</div>
          <div class="stat-label">Positive Feedback Rate</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">👍</div>
          <div class="stat-value">${s.positive_feedback}</div>
          <div class="stat-label">Helpful Responses</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">👎</div>
          <div class="stat-value">${s.negative_feedback}</div>
          <div class="stat-label">Needs Improvement</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">💬</div>
          <div class="stat-value">${s.total_chats}</div>
          <div class="stat-label">Total Interactions</div>
        </div>
      </div>
      <h3 style="font-family:'Syne',sans-serif;margin-bottom:12px">🔥 Top Asked Queries</h3>
      <div class="queries-list">
        ${d.top_queries.map((q, i) => `
          <div class="query-item">
            <span style="color:var(--text-muted);font-size:12px;min-width:20px">#${i+1}</span>
            <span class="query-text">${escapeHtml(q.query)}</span>
            <span class="query-cat">${q.category || 'general'}</span>
            <span class="query-count">×${q.count}</span>
          </div>
        `).join('') || '<p style="color:var(--text-muted)">No data yet.</p>'}
      </div>
    `;
  } catch { showToast('❌ Failed to load analytics'); }
}

// ─────────────── INIT ───────────────
loadOverview();

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
