// Manufacturing DB page
async function loadDevices() {
  try {
    const d = await api('/devices');
    $('#dev-tbl').innerHTML = '<tr><th>IMEI</th><th>Serial</th><th>Model</th><th>Sold</th><th>Warranty</th></tr>' +
      d.map(x => `<tr><td>${esc(x.imei)}</td><td>${esc(x.serial)}</td><td>${esc(x.model)}</td><td>${esc(x.sale_date)}</td><td>${x.warranty_months} mo</td></tr>`).join('');
  } catch (e) { sayErr(e); }
}

$('#gen-imei').onclick = () => { $('#dev-imei').value = generateImei(); };

$('#f-dev').onsubmit = async e => {
  e.preventDefault();
  const f = e.target;
  const body = {
    imei: f.imei.value.trim(),
    serial: f.serial.value.trim(),
    model: f.model.value.trim(),
    sale_date: f.sale_date.value,
    warranty_months: +f.warranty_months.value,
  };
  console.log('sending', body);
  try {
    await post('/devices', body);
    say('Device added.'); f.reset(); loadDevices();
  } catch (err) { sayErr(err); }
};

loadDevices();