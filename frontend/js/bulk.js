// Bulk upload page
let lastBulk = null;

$('#f-bulk').onsubmit = async e => {
  e.preventDefault();
  try {
    const r = await api('/complaints/bulk', { method: 'POST', body: new FormData(e.target) });
    say(`Batch ${r.batch_id}: ${r.accepted} of ${r.rows.length} rows accepted.`); lastBulk = r;
    $('#err-report').hidden = r.rows.every(x => x.ok);
    $('#bulk-res').innerHTML = '<tr><th>Row</th><th>Result</th><th>Detail</th></tr>' + r.rows.map(x =>
      `<tr><td>${x.row}</td><td>${x.ok ? `Accepted <a href="complaint.html?id=${x.id}">#${x.id}</a>` : 'Rejected ' + esc(x.code || '')}</td><td>${esc(x.message || x.status || '')}</td></tr>`).join('');
  } catch (err) { sayErr(err); }
};

$('#err-report').onclick = () => {
  const rej = lastBulk.rows.filter(x => !x.ok);
  const csv = 'row,imei,error_code,message\n' + rej.map(x => [x.row, x.imei || '', x.code || '', '"' + (x.message || x.status || '').replace(/"/g, '""') + '"'].join(',')).join('\n');
  const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
  a.download = 'error_report_' + lastBulk.batch_id + '.csv'; a.click();
};