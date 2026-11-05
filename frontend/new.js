// New complaint page
$('#f-new').onsubmit = async e => {
  e.preventDefault();
  try {
    const c = await post('/complaints', formData(e.target, ['dead_on_arrival', 'customer_caused']));
    let text = c.error_code ? `Complaint #${c.id} is on hold (${c.error_code}).` : `Complaint #${c.id} registered.`;
    let bad = false;
    const files = $('#new-files').files;
    if (files.length) {
      try { await uploadFiles(c.id, files); }
      catch (up) { text += ' File upload failed: ' + errText(up); bad = true; }
    }
    flash(text, bad);
    location.href = 'complaint.html?id=' + c.id;       // go to this complaint's own page
  } catch (err) { sayErr(err); }
};