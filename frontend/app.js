const $ = (s, r = document) => r.querySelector(s);
let current = null;

async function api(path, opts = {}) {
  const r = await fetch('/api' + path, opts);
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw d.detail || d;
  return d;
}
const post = (path, body) => api(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
function say(text, err) { $('#msg').innerHTML = `<p class="${err ? 'err' : ''}"></p>`; $('#msg p').textContent = text; }
const errText = e => e && e.code ? `${e.code}: ${e.message}` : JSON.stringify(e);
const fmt = d => d ? new Date(d + 'Z').toLocaleString() : '';
const tone = s => /CLOSED|DELIVERED|QC_PASSED|VERIFIED/.test(s) ? 'ok' : /HOLD/.test(s) ? 'bad' : /QUOTE|FAST|REOPEN|REPLACEMENT/.test(s) ? 'warn' : '';
const chip = s => `<span class="chip ${tone(s)}">${s.replace(/_/g, ' ')}</span>`;

// ---- tabs
document.querySelectorAll('nav button').forEach(b => b.onclick = () => {
  document.querySelectorAll('nav button').forEach(x => x.classList.toggle('on', x === b));
  document.querySelectorAll('.tab').forEach(t => t.hidden = t.id !== b.dataset.tab);
  if (b.dataset.tab === 'list') loadList(); if (b.dataset.tab === 'dev') loadDevices();
});

// ---- list + detail
async function loadList() {
  const rows = await api('/complaints');
  $('#tbl tbody').innerHTML = rows.map(c => `<tr tabindex="0" data-id="${c.id}" class="${current === c.id ? 'sel' : ''}">
    <td>${c.id}</td><td>${esc(c.customer_name)}</td><td>${esc(c.imei)}</td><td>${chip(c.status)}</td><td>${c.priority || ''}</td></tr>`).join('');
  document.querySelectorAll('#tbl tbody tr').forEach(tr => {
    tr.onclick = () => openDetail(+tr.dataset.id);
    tr.onkeydown = e => { if (e.key === 'Enter') openDetail(+tr.dataset.id); };
  });
}
const esc = s => String(s ?? '').replace(/[&<>"]/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[m]));

// next-step buttons per status: [label, endpoint, fixed values, fields]
const P = ['Critical', 'High', 'Medium', 'Low'];
const ACTIONS = {
  FIRST_LEVEL_HELP: [['Problem solved', 'guidance', { solved: true }], ['Not solved: triage', 'triage', {}, [['issue_code', 'text', 'Issue code'], ['priority', P, 'Priority']]]],
  FAST_TRACK: [['Approve replacement', 'replacement', {}, [['new_imei', 'text', 'New IMEI']]]],
  TRIAGED: [['Phone received', 'receive', {}, [['customer_damage', 'checkbox', 'Customer-caused damage found']]]],
  DIAGNOSING: [['Repairable', 'diagnose', { repairable: true }], ['Not repairable', 'diagnose', { repairable: false }]],
  REOPENED: [['Repairable', 'diagnose', { repairable: true }], ['Not repairable', 'diagnose', { repairable: false }]],
  QUOTE_PENDING: [['Send quote', 'quote', {}, [['amount', 'number', 'Parts + labour']]]],
  QUOTE_SENT: [['Customer approves', 'quote-decision', { approved: true }], ['Customer declines', 'quote-decision', { approved: false }]],
  REPAIRING: [['QC passed', 'repair', { qc_passed: true }], ['QC failed', 'repair', { qc_passed: false }]],
  REPLACEMENT_PENDING: [['Approve replacement', 'replacement', {}, [['new_imei', 'text', 'New IMEI']]]],
  QC_PASSED: [['Dispatch to dealer', 'dispatch', {}, [['tracking_no', 'text', 'Courier tracking no.']]]],
  REPLACEMENT_APPROVED: [['Dispatch to dealer', 'dispatch', {}, [['tracking_no', 'text', 'Courier tracking no.']]]],
  DISPATCHED: [['Hand over to customer', 'handover', {}]],
  DELIVERED: [['Customer satisfied', 'feedback', { satisfied: true }], ['Not satisfied: reopen', 'feedback', { satisfied: false }]],
};

async function openDetail(id) {
  current = id; const c = await api('/complaints/' + id);
  const acts = ACTIONS[c.status] || [];
  $('#detail').innerHTML = `<h2>Complaint #${c.id} ${chip(c.status)}</h2>
    <p>${esc(c.customer_name)}, ${esc(c.phone)}<br>${esc(c.model || '')} <small>${esc(c.imei)}</small></p>
    <p>${esc(c.issue)}</p>
    <p><small>Warranty: ${c.warranty_status || 'n/a'} ${c.priority ? ' | Priority ' + c.priority : ''} ${c.sla_due ? ' | SLA ' + fmt(c.sla_due) : ''}
    ${c.quote_amount ? ' | Quote ' + c.quote_amount : ''} ${c.tracking_no ? ' | Tracking ' + esc(c.tracking_no) : ''}</small></p>
    <div class="actions">${acts.map((a, i) => `<button class="act ${i ? 'alt' : ''}" data-i="${i}">${a[0]}</button>`).join('') || '<small>No further steps.</small>'}</div>
    <div id="sub"></div>
    <h3>History</h3><ol class="hist">${c.history.map(h => `<li>${chip(h.status)} <small>${fmt(h.at)}</small><br>${esc(h.note)}</li>`).join('')}</ol>`;
  document.querySelectorAll('.act').forEach(b => b.onclick = () => runAction(c, acts[+b.dataset.i]));
  loadList();
}

function runAction(c, [label, path, fixed, fields]) {
  const send = async body => {
    try { await post(`/complaints/${c.id}/${path}`, body); say(label + ': done'); openDetail(c.id); }
    catch (e) { say(errText(e), true); }
  };
  if (!fields) return send(fixed);
  $('#sub').innerHTML = `<form class="sub">${fields.map(([n, t, l]) => Array.isArray(t)
    ? `<label>${l}<select name="${n}">${t.map(o => `<option>${o}</option>`).join('')}</select></label>`
    : t === 'checkbox' ? `<label class="chk"><input type="checkbox" name="${n}"> ${l}</label>`
    : `<label>${l}<input name="${n}" type="${t}" required></label>`).join('')}<button class="act">${label}</button></form>`;
  $('#sub form').onsubmit = e => {
    e.preventDefault(); const body = { ...fixed };
    fields.forEach(([n, t]) => { const el = e.target[n]; body[n] = t === 'checkbox' ? el.checked : t === 'number' ? +el.value : el.value; });
    send(body);
  };
}

// ---- forms
const formData = (f, bools) => { const o = Object.fromEntries(new FormData(f)); bools.forEach(b => o[b] = f[b].checked); return o; };
$('#f-new').onsubmit = async e => {
  e.preventDefault();
  try {
    const c = await post('/complaints', formData(e.target, ['dead_on_arrival', 'customer_caused']));
    say(c.error_code ? `Complaint #${c.id} is on hold (${c.error_code}).` : `Complaint #${c.id} registered.`);
    e.target.reset(); document.querySelector('[data-tab=list]').click(); openDetail(c.id);
  } catch (err) { say(errText(err), true); }
};
$('#f-bulk').onsubmit = async e => {
  e.preventDefault();
  try {
    const r = await api('/complaints/bulk', { method: 'POST', body: new FormData(e.target) });
    say(`Batch ${r.batch_id}: ${r.accepted} of ${r.rows.length} rows accepted.`);
    $('#bulk-res').innerHTML = '<tr><th>Row</th><th>Result</th><th>Detail</th></tr>' + r.rows.map(x =>
      `<tr><td>${x.row}</td><td>${x.ok ? 'Accepted #' + x.id : 'Rejected ' + (x.code || '')}</td><td>${esc(x.message || x.status || '')}</td></tr>`).join('');
  } catch (err) { say(errText(err), true); }
};
$('#f-dev').onsubmit = async e => {
  e.preventDefault();
  try { await post('/devices', { ...formData(e.target, ['blacklisted']), warranty_months: +e.target.warranty_months.value });
    say('Device added.'); e.target.reset(); loadDevices(); } catch (err) { say(errText(err), true); }
};
async function loadDevices() {
  const d = await api('/devices');
  $('#dev-tbl').innerHTML = '<tr><th>IMEI</th><th>Serial</th><th>Model</th><th>Sold</th><th>Warranty</th><th>Blacklisted</th></tr>' +
    d.map(x => `<tr><td>${x.imei}</td><td>${esc(x.serial)}</td><td>${esc(x.model)}</td><td>${x.sale_date}</td><td>${x.warranty_months} mo</td><td>${x.blacklisted ? 'Yes' : 'No'}</td></tr>`).join('');
}
loadList();
