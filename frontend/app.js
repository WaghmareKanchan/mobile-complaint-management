const $ = (s, r = document) => r.querySelector(s);
let current = null;

async function api(path, opts = {}) {
  const r = await fetch('/api' + path, opts);
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw d.detail || d;
  return d;
}
const post = (path, body) => api(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
function say(text, err, openId) {
  $('#msg').innerHTML = `<p class="${err ? 'err' : ''}"><span></span></p>`; $('#msg span').textContent = text;
  if (openId) { const b = document.createElement('button'); b.className = 'act alt'; b.style.marginLeft = '1rem';
    b.textContent = 'Open complaint #' + openId; b.onclick = () => { document.querySelector('[data-tab=list]').click(); openDetail(openId); };
    $('#msg p').appendChild(b); }
}
const sayErr = e => say(errText(e), true, e && e.existing_id);
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
const REPL = [['new_imei', 'text', 'New IMEI'], ['new_serial', 'text', 'New serial'], ['collect_old', 'checkbox', 'Old phone collected']];
const FB = [['rating', 'number', 'Rating 1-5 (optional)'], ['comment', 'text', 'Comment (optional)']];
const ACTIONS = {
  FIRST_LEVEL_HELP: [['Problem solved', 'guidance', { solved: true }], ['Not solved: triage', 'triage', {}, [['issue_code', 'text', 'Issue code'], ['priority', P, 'Priority']]]],
  FAST_TRACK: [['Approve replacement', 'replacement', {}, REPL]],
  TRIAGED: [['Phone received', 'receive', {}, [['customer_damage', 'checkbox', 'Customer-caused damage found'], ['condition_notes', 'text', 'Condition notes (optional)']]]],
  DIAGNOSING: [['Repairable', 'diagnose', { repairable: true }], ['Not repairable', 'diagnose', { repairable: false }]],
  REOPENED: [['Repairable', 'diagnose', { repairable: true }], ['Not repairable', 'diagnose', { repairable: false }]],
  QUOTE_PENDING: [['Send quote', 'quote', {}, [['amount', 'number', 'Parts + labour']]]],
  QUOTE_SENT: [['Customer approves', 'quote-decision', { approved: true }], ['Customer declines', 'quote-decision', { approved: false }]],
  REPAIRING: [['QC passed', 'repair', { qc_passed: true }], ['QC failed', 'repair', { qc_passed: false }]],
  REPLACEMENT_PENDING: [['Approve replacement', 'replacement', {}, REPL]],
  QC_PASSED: [['Dispatch to dealer', 'dispatch', {}, [['tracking_no', 'text', 'Courier tracking no.']]]],
  REPLACEMENT_APPROVED: [['Dispatch to dealer', 'dispatch', {}, [['tracking_no', 'text', 'Courier tracking no.']]]],
  DISPATCHED: [['Hand over to customer', 'handover', {}, [['otp', 'text', 'Customer OTP']]]],
  DELIVERED: [['Customer satisfied', 'feedback', { satisfied: true }, FB], ['Not satisfied: reopen', 'feedback', { satisfied: false }, FB]],
};

async function openDetail(id) {
  current = id; const c = await api('/complaints/' + id);
  const acts = ACTIONS[c.status] || [];
  $('#detail').innerHTML = `<h2>Complaint #${c.id} ${chip(c.status)}</h2>
    <p>${esc(c.customer_name)}, ${esc(c.phone)}<br>${esc(c.model || '')} <small>${esc(c.imei)}</small></p>
    <p>${esc(c.issue)}</p>
    <div class="facts">${[['Warranty', c.warranty_status], ['Issue code', c.issue_code], ['Priority', c.priority], ['SLA due', c.sla_due && fmt(c.sla_due)],
      ['Pickup', c.pickup_type], ['Job card no.', c.job_card_no], ['Condition notes', c.condition_notes], ['Quote amount', c.quote_amount],
      ['New IMEI', c.new_imei], ['Old phone collected', c.new_imei ? (c.old_phone_collected ? 'Yes' : 'No') : null], ['Courier tracking no.', c.tracking_no],
      ['Handover OTP (demo)', c.status === 'DISPATCHED' ? c.handover_otp : null], ['Rating', c.feedback_rating], ['Feedback', c.feedback_text]]
      .filter(([, v]) => v !== null && v !== undefined && v !== '').map(([k, v]) => `<div><small>${k}</small><b>${esc(v)}</b></div>`).join('')}</div>
    <div class="actions">${acts.map((a, i) => `<button class="act ${i ? 'alt' : ''}" data-i="${i}">${a[0]}</button>`).join('') || '<small>No further steps.</small>'}</div>
    <div id="sub"></div>
    <h3>Photos / videos</h3>
    <div class="files">${c.files.map(f => f.kind === 'photo'
      ? `<a href="/api/complaints/${c.id}/files/${f.id}" target="_blank"><img src="/api/complaints/${c.id}/files/${f.id}" alt="${esc(f.original_name)}" title="${esc(f.stage)}"></a>`
      : `<video controls preload="metadata" src="/api/complaints/${c.id}/files/${f.id}" title="${esc(f.stage)}"></video>`).join('') || '<small>No files yet.</small>'}</div>
    <form id="f-up" class="sub"><input type="file" id="up-file" multiple required accept="image/jpeg,image/png,image/webp,video/mp4,video/webm,video/quicktime"><button class="act alt">Upload</button></form>
    <h3>History</h3><ol class="hist">${c.history.map(h => `<li>${chip(h.status)} <small>${fmt(h.at)}</small><br>${esc(h.note)}</li>`).join('')}</ol>`;
  document.querySelectorAll('.actions .act').forEach(b => b.onclick = () => runAction(c, acts[+b.dataset.i]));
  $('#f-up').onsubmit = async e => {
    e.preventDefault();
    try { await uploadFiles(c.id, $('#up-file').files); say('File uploaded.'); openDetail(c.id); } catch (err) { sayErr(err); }
  };
  loadList();
}

function runAction(c, [label, path, fixed, fields]) {
  const send = async body => {
    try { await post(`/complaints/${c.id}/${path}`, body); say(label + ': done'); openDetail(c.id); }
    catch (e) { sayErr(e); }
  };
  if (!fields) return send(fixed);
  $('#sub').innerHTML = `<form class="sub">${fields.map(([n, t, l]) => Array.isArray(t)
    ? `<label>${l}<select name="${n}">${t.map(o => `<option>${o}</option>`).join('')}</select></label>`
    : t === 'checkbox' ? `<label class="chk"><input type="checkbox" name="${n}"> ${l}</label>`
    : `<label>${l}<input name="${n}" type="${t}" ${/optional/.test(l) ? '' : 'required'}></label>`).join('')}<button class="act">${label}</button></form>`;
  
  const ni = $('#sub input[name="new_imei"]');
  if (ni) {
    const g = document.createElement('button'); g.type = 'button'; g.className = 'act alt'; g.textContent = 'Generate IMEI';
    g.onclick = () => { ni.value = generateImei(); }; ni.insertAdjacentElement('afterend', g);
  }

    $('#sub form').onsubmit = e => {
    e.preventDefault(); const body = { ...fixed };
    fields.forEach(([n, t]) => { const el = e.target[n]; body[n] = t === 'checkbox' ? el.checked : t === 'number' ? (el.value === '' ? null : +el.value) : (el.value || null); });
    send(body);
  };
}

// ---- forms
async function uploadFiles(id, files) {
  for (const f of files) {
    const fd = new FormData(); fd.append('file', f);
    await api(`/complaints/${id}/files`, { method: 'POST', body: fd });
  }
}
const formData = (f, bools) => { const o = Object.fromEntries(new FormData(f)); bools.forEach(b => o[b] = f[b].checked); return o; };
$('#f-new').onsubmit = async e => {
  e.preventDefault();
  try {
    const c = await post('/complaints', formData(e.target, ['dead_on_arrival', 'customer_caused']));
    say(c.error_code ? `Complaint #${c.id} is on hold (${c.error_code}).` : `Complaint #${c.id} registered.`);
    const files = $('#new-files').files;
    if (files.length) { try { await uploadFiles(c.id, files); } catch (up) { sayErr(up); } }
    e.target.reset(); document.querySelector('[data-tab=list]').click(); openDetail(c.id);
  } catch (err) { sayErr(err); }
};
$('#f-bulk').onsubmit = async e => {
  e.preventDefault();
  try {
    const r = await api('/complaints/bulk', { method: 'POST', body: new FormData(e.target) });
    say(`Batch ${r.batch_id}: ${r.accepted} of ${r.rows.length} rows accepted.`); lastBulk = r;
    $('#err-report').hidden = r.rows.every(x => x.ok);
    $('#bulk-res').innerHTML = '<tr><th>Row</th><th>Result</th><th>Detail</th></tr>' + r.rows.map(x =>
      `<tr><td>${x.row}</td><td>${x.ok ? 'Accepted #' + x.id : 'Rejected ' + (x.code || '')}</td><td>${esc(x.message || x.status || '')}</td></tr>`).join('');
  } catch (err) { sayErr(err); }
};
let lastBulk = null;
$('#err-report').onclick = () => {
  const rej = lastBulk.rows.filter(x => !x.ok);
  const csv = 'row,imei,error_code,message\n' + rej.map(x => [x.row, x.imei || '', x.code || '', '"' + (x.message || x.status || '').replace(/"/g, '""') + '"'].join(',')).join('\n');
  const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
  a.download = 'error_report_' + lastBulk.batch_id + '.csv'; a.click();
};
$('#f-dev').onsubmit = async e => {
  e.preventDefault();
  try { await post('/devices', { ...formData(e.target, ['blacklisted']), warranty_months: +e.target.warranty_months.value });
    say('Device added.'); e.target.reset(); loadDevices(); } catch (err) { sayErr(err); }
};
async function loadDevices() {
  const d = await api('/devices');
  $('#dev-tbl').innerHTML = '<tr><th>IMEI</th><th>Serial</th><th>Model</th><th>Sold</th><th>Warranty</th><th>Blacklisted</th></tr>' +
    d.map(x => `<tr><td>${x.imei}</td><td>${esc(x.serial)}</td><td>${esc(x.model)}</td><td>${x.sale_date}</td><td>${x.warranty_months} mo</td><td>${x.blacklisted ? 'Yes' : 'No'}</td></tr>`).join('');
}
// ---- Generate a valid IMEI (15 digits with a correct check digit)
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
const gen = $('#gen-imei');
if (gen) gen.onclick = () => { $('#dev-imei').value = generateImei(); };

loadList();