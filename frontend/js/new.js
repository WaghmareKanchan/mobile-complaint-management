// New complaint page
$('#f-new').onsubmit = async e => {
  e.preventDefault();
  try {
    const f = e.target;
    const body = {
      customer_name: f.customer_name.value.trim(),
      phone: f.phone.value.trim(),
      imei: f.imei.value.trim(),
      serial: f.serial.value.trim(),
      issue: f.issue.value.trim(),
    };
    console.log('sending', body);
    const c = await post('/complaints', body);
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