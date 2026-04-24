/**
 * auth.js — Login & Sign Up logic
 */
'use strict';

// Theme apply
(function() {
  const t = localStorage.getItem('theme') || 'dark';
  document.documentElement.setAttribute('data-theme', t);
})();

const loginForm  = document.getElementById('loginForm');
const signupForm = document.getElementById('signupForm');

// Password toggle helper
['togglePw1','togglePw2'].forEach(id => {
  const btn = document.getElementById(id);
  if (!btn) return;
  const inp = btn.previousElementSibling || btn.closest('.input-wrap').querySelector('input');
  btn.addEventListener('click', () => {
    inp.type = inp.type === 'password' ? 'text' : 'password';
    btn.textContent = inp.type === 'password' ? '👁' : '🙈';
  });
});

if (loginForm) {
  loginForm.addEventListener('submit', async e => {
    e.preventDefault();
    const btn = document.getElementById('loginBtn');
    const errEl = document.getElementById('loginError');
    errEl.textContent = '';

    const email    = document.getElementById('loginEmail').value.trim();
    const password = document.getElementById('loginPassword').value;

    setLoading(btn, true);
    try {
      const res = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json();
      if (data.success) {
        window.location.href = data.role === 'admin' ? '/admin' : '/';
      } else {
        errEl.textContent = data.error || 'Login failed';
      }
    } catch {
      errEl.textContent = 'Network error. Please try again.';
    } finally {
      setLoading(btn, false);
    }
  });
}

if (signupForm) {
  signupForm.addEventListener('submit', async e => {
    e.preventDefault();
    const btn = document.getElementById('signupBtn');
    const errEl = document.getElementById('signupError');
    errEl.textContent = '';

    const name     = document.getElementById('signupName').value.trim();
    const email    = document.getElementById('signupEmail').value.trim();
    const password = document.getElementById('signupPassword').value;

    if (!name || name.length < 2) {
      errEl.textContent = 'Please enter your full name (min 2 chars)';
      return;
    }
    if (password.length < 6) {
      errEl.textContent = 'Password must be at least 6 characters';
      return;
    }

    setLoading(btn, true);
    try {
      const res = await fetch('/api/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, password }),
      });
      const data = await res.json();
      if (data.success) {
        window.location.href = '/';
      } else {
        errEl.textContent = data.error || 'Sign up failed';
      }
    } catch {
      errEl.textContent = 'Network error. Please try again.';
    } finally {
      setLoading(btn, false);
    }
  });
}

function setLoading(btn, loading) {
  const text = btn.querySelector('.btn-text');
  const spin = btn.querySelector('.btn-spinner');
  btn.disabled = loading;
  if (text) text.style.display = loading ? 'none' : 'inline';
  if (spin) spin.style.display = loading ? 'inline' : 'none';
}
