// ============================================================
//  Soil Testing Web Server — ESP32 (Arduino Framework)
//  Sensors: pH, NPK (N/P/K), Moisture, EC  (simulated)
//  Web UI  : Capture / Reset / Send  (5-sample workflow)
// ============================================================

#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>   // Install: ArduinoJson by Benoit Blanchon

// ─── USER CONFIG ────────────────────────────────────────────
const char* WIFI_SSID     = "YOUR_SSID";
const char* WIFI_PASSWORD = "YOUR_PASSWORD";
const char* BACKEND_URL   = "http://192.168.1.100:8000/ingest";  // change IP
// ────────────────────────────────────────────────────────────

#define MAX_SAMPLES 5

WebServer server(80);

// ── Sample storage ──────────────────────────────────────────
struct SoilSample {
  float ph;
  float n;
  float p;
  float k;
  float moisture;
  float ec;
};

SoilSample samples[MAX_SAMPLES];
int sampleCount = 0;

// ============================================================
//  SENSOR FUNCTIONS  (replace with real driver calls)
// ============================================================

/** Returns a simulated soil reading. Replace body with real sensor reads. */
SoilSample readSensors() {
  SoilSample s;
  // pH  : 4.0 – 8.5
  s.ph       = 4.0f  + (random(0, 4500) / 1000.0f);
  // NPK : 0 – 200 mg/kg
  s.n        = random(10, 200) + random(0, 100) / 100.0f;
  s.p        = random(5,  150) + random(0, 100) / 100.0f;
  s.k        = random(20, 250) + random(0, 100) / 100.0f;
  // Moisture : 10 – 80 %
  s.moisture = 10.0f + (random(0, 7000) / 100.0f);
  // EC  : 0.1 – 3.5 dS/m
  s.ec       = 0.1f  + (random(0, 3400) / 1000.0f);
  return s;
}

// ============================================================
//  SAMPLE MANAGEMENT
// ============================================================

bool captureSample() {
  if (sampleCount >= MAX_SAMPLES) return false;
  samples[sampleCount++] = readSensors();
  return true;
}

void resetSamples() {
  sampleCount = 0;
}

// ============================================================
//  JSON BUILDER
// ============================================================

String buildJSON(const String& farmerId,
                 const String& landId,
                 const String& cropName) {
  // Capacity: 6 fields × 5 samples + top-level keys
  StaticJsonDocument<1024> doc;

  doc["farmer_id"]    = farmerId;
  doc["land_id"]      = landId;
  doc["current_crop"] = cropName;

  JsonArray arr = doc.createNestedArray("samples");
  for (int i = 0; i < sampleCount; i++) {
    JsonObject o = arr.createNestedObject();
    o["ph"]       = serialized(String(samples[i].ph,       2));
    o["n"]        = serialized(String(samples[i].n,        2));
    o["p"]        = serialized(String(samples[i].p,        2));
    o["k"]        = serialized(String(samples[i].k,        2));
    o["moisture"] = serialized(String(samples[i].moisture, 2));
    o["ec"]       = serialized(String(samples[i].ec,       3));
  }

  String out;
  serializeJson(doc, out);
  return out;
}

// ============================================================
//  BACKEND COMMUNICATION
// ============================================================

/** Returns HTTP status code, or negative on connection error. */
int sendData(const String& payload) {
  HTTPClient http;
  http.begin(BACKEND_URL);
  http.addHeader("Content-Type", "application/json");
  int code = http.POST(payload);
  http.end();
  return code;
}

// ============================================================
//  HTML UI  (embedded as raw string)
// ============================================================

const char HTML_PAGE[] PROGMEM = R"rawhtml(
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>SoilSense — Field Station</title>
<style>
  /* ── Palette & fonts ───────────────────────────── */
  @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@700;800&display=swap');

  :root{
    --bg:     #0d1117;
    --panel:  #161b22;
    --border: #30363d;
    --green:  #3fb950;
    --green2: #238636;
    --amber:  #d29922;
    --red:    #f85149;
    --text:   #e6edf3;
    --muted:  #8b949e;
    --radius: 10px;
  }

  *{box-sizing:border-box;margin:0;padding:0}
  body{
    background:var(--bg);
    color:var(--text);
    font-family:'Space Mono',monospace;
    min-height:100vh;
    display:flex;
    flex-direction:column;
    align-items:center;
    padding:32px 16px 64px;
  }

  /* ── Header ────────────────────────────────────── */
  header{text-align:center;margin-bottom:36px}
  header h1{
    font-family:'Syne',sans-serif;
    font-size:clamp(1.8rem,5vw,2.8rem);
    font-weight:800;
    letter-spacing:-1px;
    background:linear-gradient(135deg,#3fb950 30%,#58a6ff);
    -webkit-background-clip:text;
    -webkit-text-fill-color:transparent;
    background-clip:text;
  }
  header p{color:var(--muted);font-size:.78rem;margin-top:4px;letter-spacing:.5px}

  /* ── Card ──────────────────────────────────────── */
  .card{
    background:var(--panel);
    border:1px solid var(--border);
    border-radius:var(--radius);
    padding:24px;
    width:100%;
    max-width:540px;
    margin-bottom:16px;
  }
  .card h2{
    font-family:'Syne',sans-serif;
    font-size:.95rem;
    letter-spacing:2px;
    text-transform:uppercase;
    color:var(--muted);
    margin-bottom:16px;
    border-bottom:1px solid var(--border);
    padding-bottom:10px;
  }

  /* ── Form fields ───────────────────────────────── */
  .field{margin-bottom:14px}
  label{display:block;font-size:.72rem;color:var(--muted);margin-bottom:5px;letter-spacing:.8px;text-transform:uppercase}
  input[type=text]{
    width:100%;
    background:#0d1117;
    border:1px solid var(--border);
    border-radius:6px;
    color:var(--text);
    font-family:'Space Mono',monospace;
    font-size:.88rem;
    padding:9px 12px;
    outline:none;
    transition:border-color .2s;
  }
  input[type=text]:focus{border-color:#58a6ff}

  /* ── Sample counter ────────────────────────────── */
  .counter-row{
    display:flex;
    align-items:center;
    gap:12px;
    margin-bottom:4px;
  }
  .counter-num{
    font-family:'Syne',sans-serif;
    font-size:2.6rem;
    font-weight:800;
    color:var(--green);
    line-height:1;
  }
  .counter-label{color:var(--muted);font-size:.78rem;line-height:1.4}
  .pip-row{display:flex;gap:6px;margin-top:8px}
  .pip{
    width:36px;height:8px;
    border-radius:4px;
    background:var(--border);
    transition:background .3s;
  }
  .pip.filled{background:var(--green)}

  /* ── Buttons ───────────────────────────────────── */
  .btn-row{display:flex;gap:10px;flex-wrap:wrap;margin-top:8px}
  button{
    flex:1;min-width:130px;
    padding:11px 16px;
    border:none;
    border-radius:6px;
    font-family:'Space Mono',monospace;
    font-size:.78rem;
    font-weight:700;
    letter-spacing:.5px;
    cursor:pointer;
    transition:opacity .15s,transform .1s;
  }
  button:active{transform:scale(.97)}
  button:disabled{opacity:.35;cursor:not-allowed}

  #btnCapture{background:var(--green2);color:#fff}
  #btnCapture:hover:not(:disabled){opacity:.85}
  #btnReset{background:#21262d;color:var(--text);border:1px solid var(--border)}
  #btnReset:hover:not(:disabled){border-color:var(--amber);color:var(--amber)}
  #btnSend{background:#1f6feb;color:#fff}
  #btnSend:hover:not(:disabled){opacity:.85}

  /* ── Toast notification ────────────────────────── */
  #toast{
    position:fixed;bottom:28px;left:50%;transform:translateX(-50%) translateY(80px);
    background:#161b22;border:1px solid var(--border);
    border-radius:8px;padding:12px 22px;
    font-size:.82rem;letter-spacing:.4px;
    transition:transform .35s cubic-bezier(.34,1.56,.64,1),opacity .35s;
    opacity:0;z-index:999;white-space:nowrap;
  }
  #toast.show{transform:translateX(-50%) translateY(0);opacity:1}
  #toast.ok  {border-color:var(--green);color:var(--green)}
  #toast.err {border-color:var(--red);color:var(--red)}
  #toast.warn{border-color:var(--amber);color:var(--amber)}

  /* ── Sample table ──────────────────────────────── */
  #sampleTable{width:100%;border-collapse:collapse;font-size:.72rem;margin-top:8px}
  #sampleTable th{
    color:var(--muted);font-weight:400;text-align:left;
    padding:4px 8px;border-bottom:1px solid var(--border);letter-spacing:.6px
  }
  #sampleTable td{padding:5px 8px;border-bottom:1px solid #21262d;color:var(--text)}
  #sampleTable tr:last-child td{border-bottom:none}
  #noSamples{color:var(--muted);font-size:.78rem;text-align:center;padding:16px 0}
</style>
</head>
<body>

<header>
  <h1>⬡ SoilSense</h1>
  <p>FIELD DATA COLLECTION STATION</p>
</header>

<!-- ── Operator Info ── -->
<div class="card">
  <h2>Operator Info</h2>
  <div class="field">
    <label>Farmer ID *</label>
    <input type="text" id="farmerId" placeholder="e.g. F001" maxlength="40"/>
  </div>
  <div class="field">
    <label>Land ID *</label>
    <input type="text" id="landId" placeholder="e.g. L001" maxlength="40"/>
  </div>
  <div class="field">
    <label>Crop Name (optional)</label>
    <input type="text" id="cropName" placeholder="e.g. rice" maxlength="60"/>
  </div>
</div>

<!-- ── Sample Counter ── -->
<div class="card">
  <h2>Samples</h2>
  <div class="counter-row">
    <div class="counter-num" id="countNum">0</div>
    <div class="counter-label">of 5 samples<br>collected</div>
  </div>
  <div class="pip-row" id="pips">
    <div class="pip" id="p0"></div>
    <div class="pip" id="p1"></div>
    <div class="pip" id="p2"></div>
    <div class="pip" id="p3"></div>
    <div class="pip" id="p4"></div>
  </div>
</div>

<!-- ── Samples Preview ── -->
<div class="card">
  <h2>Captured Readings</h2>
  <div id="tableWrap">
    <p id="noSamples">No samples yet — press Capture Sample to begin.</p>
    <table id="sampleTable" style="display:none">
      <thead>
        <tr>
          <th>#</th><th>pH</th><th>N</th><th>P</th>
          <th>K</th><th>Moist%</th><th>EC</th>
        </tr>
      </thead>
      <tbody id="tbody"></tbody>
    </table>
  </div>
</div>

<!-- ── Action Buttons ── -->
<div class="card">
  <h2>Actions</h2>
  <div class="btn-row">
    <button id="btnCapture" onclick="captureClicked()">▶ Capture Sample</button>
    <button id="btnReset"   onclick="resetClicked()">↺ Reset Samples</button>
    <button id="btnSend"    onclick="sendClicked()" disabled>⬆ Send Data</button>
  </div>
</div>

<div id="toast"></div>

<script>
let sampleCount = 0;

function showToast(msg, type='ok', dur=3200){
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'show ' + type;
  clearTimeout(t._tid);
  t._tid = setTimeout(()=>{ t.className=''; }, dur);
}

function updateUI(count){
  sampleCount = count;
  document.getElementById('countNum').textContent = count;
  for(let i=0;i<5;i++){
    document.getElementById('p'+i).className = 'pip' + (i < count ? ' filled' : '');
  }
  document.getElementById('btnCapture').disabled = (count >= 5);
  document.getElementById('btnSend').disabled    = (count !== 5);
}

async function captureClicked(){
  if(sampleCount >= 5){ showToast('Maximum 5 samples reached.','warn'); return; }
  const btn = document.getElementById('btnCapture');
  btn.disabled = true;
  btn.textContent = '⏳ Reading…';
  try{
    const r = await fetch('/capture', {method:'POST'});
    const d = await r.json();
    if(d.status === 'ok'){
      appendRow(d.index, d.sample);
      document.getElementById('noSamples').style.display='none';
      document.getElementById('sampleTable').style.display='table';
      updateUI(d.count);
      showToast(`Sample ${d.count} captured ✓`, 'ok');
    } else {
      showToast(d.message || 'Capture failed','err');
      btn.disabled = false;
    }
  } catch(e){
    showToast('Network error: ' + e.message,'err');
    btn.disabled = false;
  }
  btn.textContent = '▶ Capture Sample';
  if(sampleCount < 5) btn.disabled = false;
}

async function resetClicked(){
  if(!confirm('Clear all ' + sampleCount + ' sample(s)?')) return;
  const r = await fetch('/reset', {method:'POST'});
  const d = await r.json();
  if(d.status === 'ok'){
    document.getElementById('tbody').innerHTML = '';
    document.getElementById('noSamples').style.display='block';
    document.getElementById('sampleTable').style.display='none';
    updateUI(0);
    showToast('Samples cleared.','warn');
  }
}

async function sendClicked(){
  const farmerId = document.getElementById('farmerId').value.trim();
  const landId   = document.getElementById('landId').value.trim();
  if(!farmerId){ showToast('Farmer ID is required.','err'); return; }
  if(!landId)  { showToast('Land ID is required.','err');   return; }
  if(sampleCount !== 5){ showToast('Need exactly 5 samples.','warn'); return; }

  const btn = document.getElementById('btnSend');
  btn.disabled = true;
  btn.textContent = '⏳ Sending…';

  const crop = document.getElementById('cropName').value.trim();
  const params = new URLSearchParams({farmer_id:farmerId, land_id:landId, crop_name:crop});
  try{
    const r = await fetch('/send?' + params.toString(), {method:'POST'});
    const d = await r.json();
    if(d.status === 'ok'){
      showToast('Data sent successfully ✓  (HTTP ' + d.http_code + ')','ok',4000);
    } else {
      showToast('Send failed: ' + (d.message||d.http_code),'err',5000);
    }
  } catch(e){
    showToast('Network error: ' + e.message,'err');
  }
  btn.textContent = '⬆ Send Data';
  if(sampleCount === 5) btn.disabled = false;
}

function appendRow(idx, s){
  const tb = document.getElementById('tbody');
  const tr = document.createElement('tr');
  tr.innerHTML =
    `<td>${idx+1}</td>` +
    `<td>${s.ph}</td><td>${s.n}</td><td>${s.p}</td>` +
    `<td>${s.k}</td><td>${s.moisture}</td><td>${s.ec}</td>`;
  tb.appendChild(tr);
}

// Initialise count from server on page load
fetch('/count').then(r=>r.json()).then(d=>updateUI(d.count));
</script>
</body>
</html>
)rawhtml";

// ============================================================
//  HTTP ROUTE HANDLERS
// ============================================================

/** GET / — serve the HTML page */
void handleRoot() {
  server.send_P(200, "text/html", HTML_PAGE);
}

/** GET /count — return current sample count as JSON */
void handleCount() {
  server.send(200, "application/json",
              "{\"count\":" + String(sampleCount) + "}");
}

/** POST /capture — read sensors, store one sample */
void handleCapture() {
  if (sampleCount >= MAX_SAMPLES) {
    server.send(200, "application/json",
                "{\"status\":\"error\",\"message\":\"Maximum 5 samples reached\"}");
    return;
  }

  SoilSample s = readSensors();
  samples[sampleCount] = s;

  // Build response JSON manually (no heap alloc needed for small payload)
  String body = "{\"status\":\"ok\","
                "\"index\":"   + String(sampleCount)   + ","
                "\"count\":"   + String(sampleCount + 1) + ","
                "\"sample\":{"
                "\"ph\":"       + String(s.ph,       2) + ","
                "\"n\":"        + String(s.n,        2) + ","
                "\"p\":"        + String(s.p,        2) + ","
                "\"k\":"        + String(s.k,        2) + ","
                "\"moisture\":" + String(s.moisture, 2) + ","
                "\"ec\":"       + String(s.ec,       3) +
                "}}";

  sampleCount++;
  server.send(200, "application/json", body);
}

/** POST /reset — clear all samples */
void handleReset() {
  resetSamples();
  server.send(200, "application/json", "{\"status\":\"ok\"}");
}

/** POST /send?farmer_id=&land_id=&crop_name= — forward to backend */
void handleSend() {
  if (sampleCount != MAX_SAMPLES) {
    server.send(200, "application/json",
                "{\"status\":\"error\",\"message\":\"Need exactly 5 samples\"}");
    return;
  }

  String farmerId = server.hasArg("farmer_id") ? server.arg("farmer_id") : "";
  String landId   = server.hasArg("land_id")   ? server.arg("land_id")   : "";
  String cropName = server.hasArg("crop_name") ? server.arg("crop_name") : "";

  if (farmerId.isEmpty() || landId.isEmpty()) {
    server.send(200, "application/json",
                "{\"status\":\"error\",\"message\":\"farmer_id and land_id required\"}");
    return;
  }

  String payload = buildJSON(farmerId, landId, cropName);
  int httpCode   = sendData(payload);

  if (httpCode > 0) {
    server.send(200, "application/json",
                "{\"status\":\"ok\",\"http_code\":" + String(httpCode) + "}");
  } else {
    server.send(200, "application/json",
                "{\"status\":\"error\",\"message\":\"Backend unreachable\","
                "\"http_code\":" + String(httpCode) + "}");
  }
}

/** 404 fallback */
void handleNotFound() {
  server.send(404, "text/plain", "Not found");
}

// ============================================================
//  SETUP & LOOP
// ============================================================

void setup() {
  Serial.begin(115200);
  randomSeed(analogRead(0));   // seed random with floating ADC noise

  // ── WiFi ──
  Serial.printf("\nConnecting to %s", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print('.');
  }
  Serial.printf("\nWiFi connected — IP: %s\n", WiFi.localIP().toString().c_str());

  // ── Routes ──
  server.on("/",       HTTP_GET,  handleRoot);
  server.on("/count",  HTTP_GET,  handleCount);
  server.on("/capture",HTTP_POST, handleCapture);
  server.on("/reset",  HTTP_POST, handleReset);
  server.on("/send",   HTTP_POST, handleSend);
  server.onNotFound(handleNotFound);

  server.begin();
  Serial.println("HTTP server started on port 80");
  Serial.printf("Open http://%s in your browser\n", WiFi.localIP().toString().c_str());
}

void loop() {
  // Reconnect WiFi if dropped
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi lost — reconnecting…");
    WiFi.reconnect();
    unsigned long t = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - t < 15000) delay(500);
    if (WiFi.status() == WL_CONNECTED)
      Serial.printf("Reconnected — IP: %s\n", WiFi.localIP().toString().c_str());
  }

  server.handleClient();
}
