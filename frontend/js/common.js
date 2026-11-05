// Shared helpers loaded by every page.
const $ = (s, r = document) => r.querySelector(s);

// ---- header + navigation (same on every page)
const PAGES = [
  ['list', 'index.html', 'Complaints'],
  ['new', 'new.html', 'New complaint'],
  ['bulk', 'bulk.html', 'Bulk upload'],
  ['dev', 'devices.html', 'Manufacturing DB'],
];
(function renderHeader() {
  const h = $('#top'); if (!h) return;
  const cur = document.body.dataset.page;
  h.innerHTML = '<h1>Phone complaints</h1><nav aria-label="Main">' + PAGES.map(([k, url, label]) =>
    `<a href="${url}" class="${k === cur ? 'on' : ''}"${k === cur ? ' aria-current="page"' : ''}>${label}</a>`).join('') + '</nav>';
})();

// ---- API
async function api(path, opts = {}) {
  const r = await fetch('/api' + path, opts);
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw d.detail || d;
  return d;
}
const post = (path, body) => api(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

// ---- messages
const errText = e => e && e.code ? `${e.code}: ${e.message}` : JSON.stringify(e);
function say(text, err, openId) {
  const box = $('#msg'); if (!box) return;
  box.innerHTML = `<p class="${err ? 'err' : ''}"><span></span></p>`; $('#msg span').textContent = text;
  if (openId) {
    const a = document.createElement('a'); a.className = 'act alt'; a.style.marginLeft = '1rem';
    a.textContent = 'Open complaint #' + openId; a.href = 'complaint.html?id=' + encodeURIComponent(openId);
    $('#msg p').appendChild(a);
  }
}
const sayErr = e => say(errText(e), true, e && e.existing_id);

// A message to show on the NEXT page (used after a redirect).
function flash(text, err) { try { sessionStorage.setItem('flash', JSON.stringify({ text, err: !!err })); } catch (e) { /* storage blocked */ } }
(function showFlash() {
  try {
    const raw = sessionStorage.getItem('flash'); if (!raw) return;
    sessionStorage.removeItem('flash');
    const f = JSON.parse(raw); say(f.text, f.err);
  } catch (e) { /* ignore */ }
})();

// ---- formatting
const esc = s => String(s ?? '').replace(/[&<>"]/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[m]));
const fmt = d => d ? new Date(d + 'Z').toLocaleString() : '';
const tone = s => /CLOSED|DELIVERED|QC_PASSED|VERIFIED/.test(s) ? 'ok' : /HOLD/.test(s) ? 'bad' : /QUOTE|FAST|REOPEN|REPLACEMENT/.test(s) ? 'warn' : '';
const chip = s => `<span class="chip ${tone(s)}">${s.replace(/_/g, ' ')}</span>`;
const formData = (f, bools) => { const o = Object.fromEntries(new FormData(f)); bools.forEach(b => o[b] = f[b].checked); return o; };

// ---- files
async function uploadFiles(id, files) {
  for (const f of files) {
    const fd = new FormData(); fd.append('file', f);
    await api(`/complaints/${id}/files`, { method: 'POST', body: fd });
  }
}

// ---- Generate a valid IMEI (15 digits with a correct Luhn check digit)
function generateImei() {
  const d = '35' + Array.from({ length: 12 }, () => Math.floor(Math.random() * 10)).join('');
  let sum = 0;
  for (let i = 0; i < 14; i++) {
    let n = +d[13 - i];
    if (i % 2 === 0) { n *= 2; if (n > 9) n -= 9; }
    sum += n;
  }
  return d + ((10 - (sum % 10)) % 10);
}