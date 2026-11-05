// Complaints list page
const open = id => { location.href = 'complaint.html?id=' + encodeURIComponent(id); };

(async function loadList() {
  try {
    const rows = await api('/complaints');
    $('#tbl tbody').innerHTML = rows.length ? rows.map(c => `<tr tabindex="0" data-id="${c.id}">
      <td><a href="complaint.html?id=${c.id}">${c.id}</a></td><td>${esc(c.customer_name)}</td><td>${esc(c.imei)}</td>
      <td>${chip(c.status)}</td><td>${esc(c.priority || '')}</td><td>${esc(c.batch_id || '')}</td></tr>`).join('')
      : '<tr><td colspan="6" class="empty">No complaints yet. Use "New complaint" or "Bulk upload".</td></tr>';
    document.querySelectorAll('#tbl tbody tr[data-id]').forEach(tr => {
      tr.onclick = e => { if (e.target.tagName !== 'A') open(tr.dataset.id); };
      tr.onkeydown = e => { if (e.key === 'Enter') open(tr.dataset.id); };
    });
  } catch (e) { sayErr(e); }
})();