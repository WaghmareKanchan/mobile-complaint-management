// Single complaint page: complaint.html?id=7
const id = Number(new URLSearchParams(location.search).get('id'));

// next-step buttons per status: [label, endpoint, fixed values, fields]
const P = ['Critical', 'High', 'Medium', 'Low'];
const REPL = [['new_imei', 'imei', 'New IMEI'], ['new_serial', 'text', 'New serial'], ['collect_old', 'checkbox', 'Old phone collected']];
const FB = [['rating', 'number', 'Rating 1-5 (optional)'], ['comment', 'text', 'Comment (optional)']];
// statuses where "Go back one step" is offered (the server checks again)
const BACK_STATUSES = ['TRIAGED', 'DIAGNOSING', 'QUOTE_PENDING', 'QUOTE_SENT', 'REPAIRING', 'QC_PASSED',
  'REPLACEMENT_PENDING', 'REPLACEMENT_APPROVED', 'DISPATCHED', 'DELIVERED'];
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

async function load() {
  const box = $('#detail');
  if (!id) { box.innerHTML = '<p class="empty">No complaint selected. <a href="index.html">Go to the complaints list</a>.</p>'; return; }
  let c;
  try { c = await api('/complaints/' + id); }
  catch (e) { sayErr(e); box.innerHTML = '<p class="empty">This complaint could not be loaded. <a href="index.html">Back to the list</a>.</p>'; return; }
  document.title = `Complaint #${c.id} · Phone complaints`;
  const acts = ACTIONS[c.status] || [];
  box.innerHTML = `<h2>Complaint #${c.id} ${chip(c.status)}</h2>
    <p>${esc(c.customer_name)}, ${esc(c.phone)}<br>${esc(c.model || '')} <small>${esc(c.imei)}</small></p>
    <p>${esc(c.issue)}</p>
    <div class="facts">${[['Warranty', c.warranty_status], ['Issue code', c.issue_code], ['Priority', c.priority], ['SLA due', c.sla_due && fmt(c.sla_due)],
      ['Batch ID', c.batch_id], ['Pickup', c.pickup_type], ['Job card no.', c.job_card_no], ['Condition notes', c.condition_notes], ['Quote amount', c.quote_amount],
      ['New IMEI', c.new_imei], ['Old phone collected', c.new_imei ? (c.old_phone_collected ? 'Yes' : 'No') : null], ['Courier tracking no.', c.tracking_no],
      ['Handover OTP (demo)', c.status === 'DISPATCHED' ? c.handover_otp : null], ['Rating', c.feedback_rating], ['Feedback', c.feedback_text]]
      .filter(([, v]) => v !== null && v !== undefined && v !== '').map(([k, v]) => `<div><small>${k}</small><b>${esc(v)}</b></div>`).join('')}</div>
    <div class="actions">${acts.map((a, i) => `<button class="act ${i ? 'alt' : ''}" data-i="${i}">${a[0]}</button>`).join('') || '<small>No further steps.</small>'}</div>
    <div id="sub"></div>
    ${BACK_STATUSES.includes(c.status) ? '<div class="undo"><button type="button" id="btn-back" class="act alt">&larr; Go back one step</button> <small>Entered something wrong? Undo the last step and enter it again.</small></div>' : ''}
    <h3>Photos / videos</h3>
    <div class="files">${c.files.map(f => f.kind === 'photo'
      ? `<a href="/api/complaints/${c.id}/files/${f.id}" target="_blank"><img src="/api/complaints/${c.id}/files/${f.id}" alt="${esc(f.original_name)}" title="${esc(f.stage)}"></a>`
      : `<video controls preload="metadata" src="/api/complaints/${c.id}/files/${f.id}" title="${esc(f.stage)}"></video>`).join('') || '<small>No files yet.</small>'}</div>
    <form id="f-up" class="sub"><input type="file" id="up-file" multiple required accept="image/jpeg,image/png,image/webp,video/mp4,video/webm,video/quicktime"><button class="act alt">Upload</button></form>
    <h3>History</h3><ol class="hist">${c.history.map(h => `<li>${chip(h.status)} <small>${fmt(h.at)}</small><br>${esc(h.note)}</li>`).join('')}</ol>`;
  document.querySelectorAll('.actions .act').forEach(b => b.onclick = () => runAction(c, acts[+b.dataset.i]));

  const backBtn = $('#btn-back');
  if (backBtn) backBtn.onclick = async () => {
    const warn = c.status === 'REPLACEMENT_APPROVED' ? ' The new phone will also be removed from the Manufacturing DB.' : '';
    if (!confirm('Go back one step? The last step will be undone and what you entered in it will be cleared.' + warn)) return;
    try {
      const r = await post(`/complaints/${c.id}/back`, {});
      say('Went back to ' + r.status.replace(/_/g, ' ') + '. You can enter that step again.'); load();
    } catch (e) { sayErr(e); }
  };
  $('#f-up').onsubmit = async e => {
    e.preventDefault();
    try { await uploadFiles(c.id, $('#up-file').files); say('File uploaded.'); load(); } catch (err) { sayErr(err); }
  };
}

function runAction(c, [label, path, fixed, fields]) {
  const send = async body => {
    try { await post(`/complaints/${c.id}/${path}`, body); say(label + ': done'); load(); }
    catch (e) { sayErr(e); }
  };
  if (!fields) return send(fixed);
  $('#sub').innerHTML = `<form class="sub">${fields.map(([n, t, l]) => Array.isArray(t)
    ? `<label>${l}<select name="${n}">${t.map(o => `<option>${o}</option>`).join('')}</select></label>`
    : t === 'checkbox' ? `<label class="chk"><input type="checkbox" name="${n}"> ${l}</label>`
    : t === 'imei' ? `<label>${l}<span style="display:flex;gap:.5rem"><input name="${n}" required maxlength="15" style="flex:1"><button type="button" class="act alt" data-gen="${n}">Generate IMEI</button></span></label>`
    : `<label>${l}<input name="${n}" type="${t}" ${/optional/.test(l) ? '' : 'required'}></label>`).join('')}<button class="act">${label}</button></form>`;
  document.querySelectorAll('#sub [data-gen]').forEach(b => b.onclick = () => { $('#sub input[name="' + b.dataset.gen + '"]').value = generateImei(); });
  $('#sub form').onsubmit = e => {
    e.preventDefault(); const body = { ...fixed };
    fields.forEach(([n, t]) => { const el = e.target[n]; body[n] = t === 'checkbox' ? el.checked : t === 'number' ? (el.value === '' ? null : +el.value) : (el.value || null); });
    send(body);
  };
}

load();