// VisionAid - Vishwakarma Awards 2026-27 Stage 2 design-specification deck.
// Follows the official Stage 2 template's slide order and look (white slides, navy titles, light cards,
// Vishwakarma Awards + Maker Bhavan logos). Every number is labelled Target / Calculated / Simulated / Cited.
// Run: node ppt/build_deck.js   (pptxgenjs installed in tools/node)
const path = require('path');
const fs = require('fs');
const ROOT = path.resolve(__dirname, '..');
const pptxgen = require(path.join(ROOT, 'tools/node/node_modules/pptxgenjs'));
const A = (f) => path.join(__dirname, 'assets', f);

const NAVY = '25325F', LIME = '8CC63F', SLATE = '5B6BA8', INK = '1F2937', MUTED = '5F6B7A';
const CARD = 'F3F5FA', CARDLINE = 'DFE4EE', GREEN = 'EEF6E4', GREENLINE = 'C9E3A8', RED = 'B3261E', WHITE = 'FFFFFF';
const FONT = 'Calibri';

const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE';                       // 13.333 x 7.5 in, same 16:9 ratio as the template
pres.title = 'VisionAid - Stage 2 Design Specification';
pres.author = 'Team SVNIT';
pres.company = 'Team SVNIT';
pres.theme = { headFontFace: FONT, bodyFontFace: FONT };

function pngSize(file) {
  const b = fs.readFileSync(file);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
}

pres.defineSlideMaster({
  title: 'CONTENT',
  background: { color: WHITE },
  objects: [
    { image: { path: A('logo_vishwakarma.png'), x: 0.35, y: 6.95, w: 1.42, h: 0.44 } },
    { image: { path: A('logo_makerbhavan.png'), x: 12.12, y: 6.93, w: 0.98, h: 0.44 } },
    { placeholder: { options: { name: 'title', type: 'title', x: 0.45, y: 0.28, w: 10.6, h: 0.62, fontFace: FONT,
      fontSize: 28, bold: true, color: NAVY, valign: 'middle', align: 'left', margin: 0 }, text: '' } },
  ],
  slideNumber: { x: 12.45, y: 0.35, w: 0.5, h: 0.3, fontFace: FONT, fontSize: 10, color: MUTED, align: 'right' },
});

let slideNo = 0;
function content(title, tag) {
  const s = pres.addSlide({ masterName: 'CONTENT' });
  slideNo += 1;
  s.addText(title, { placeholder: 'title' });
  if (tag) {
    s.addText(tag, { x: 10.6, y: 0.38, w: 1.75, h: 0.3, fontFace: FONT, fontSize: 9, bold: true, color: '3F6E12',
      fill: { color: GREEN }, line: { color: GREENLINE, width: 0.75 }, align: 'center', valign: 'middle',
      shape: pres.ShapeType.roundRect, rectRadius: 0.08, margin: 0, isTextBox: true });
  }
  return s;
}

function img(s, file, x, y, w, h, opts = {}) {
  const { w: iw, h: ih } = pngSize(A(file));
  const r = Math.min(w / iw, h / ih);
  const dw = iw * r, dh = ih * r;
  s.addImage({ path: A(file), x: x + (w - dw) / 2, y: y + (h - dh) / 2, w: dw, h: dh, ...opts });
  return { x: x + (w - dw) / 2, y: y + (h - dh) / 2, w: dw, h: dh };
}

function caption(s, text, x, y, w) {
  s.addText(text, { x, y, w, h: 0.28, fontFace: FONT, fontSize: 10, italic: true, color: MUTED, align: 'center',
    margin: 0, isTextBox: true });
}

function card(s, x, y, w, h, head, lines, opt = {}) {
  s.addShape(pres.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.06, fill: { color: opt.fill || CARD },
    line: { color: opt.line || CARDLINE, width: 0.75 } });
  const runs = [];
  if (head) runs.push({ text: head, options: { bold: true, color: opt.headColor || NAVY, fontSize: opt.headSize || 15,
    breakLine: true, paraSpaceAfter: 4 } });
  lines.forEach((l, i) => {
    const o = { fontSize: opt.size || 13, color: INK, breakLine: i < lines.length - 1, paraSpaceAfter: 3 };
    if (opt.bullets !== false) o.bullet = { indent: 12 };
    if (Array.isArray(l)) {           // [boldLabel, rest]
      runs.push({ text: l[0], options: { ...o, bold: true, breakLine: false } });
      runs.push({ text: l[1], options: { ...o, bullet: undefined } });
    } else runs.push({ text: l, options: o });
  });
  s.addText(runs, { x: x + 0.15, y: y + 0.1, w: w - 0.3, h: h - 0.2, fontFace: FONT, valign: 'top', margin: 0,
    isTextBox: true });
}

function note(s, label, text, y = 6.35) {
  s.addShape(pres.ShapeType.roundRect, { x: 0.45, y, w: 12.43, h: 0.46, rectRadius: 0.05, fill: { color: GREEN },
    line: { color: GREENLINE, width: 0.75 } });
  s.addText([{ text: label + ' ', options: { bold: true, color: '3F6E12' } }, { text, options: { color: INK } }],
    { x: 0.6, y, w: 12.15, h: 0.46, fontFace: FONT, fontSize: 12, valign: 'middle', margin: 0, isTextBox: true });
}

function table(s, rows, x, y, w, colW, opt = {}) {
  const fs_ = opt.size || 11;
  const data = rows.map((r, i) => r.map((c) => ({
    text: String(c),
    options: i === 0
      ? { bold: true, color: WHITE, fill: { color: NAVY }, fontSize: fs_ }
      : { color: INK, fill: { color: i % 2 ? WHITE : CARD }, fontSize: fs_ },
  })));
  s.addTable(data, { x, y, w, colW, fontFace: FONT, border: { type: 'solid', pt: 0.5, color: CARDLINE },
    margin: [3, 5, 3, 5], valign: 'middle', autoPage: false, rowH: opt.rowH });
}

function stat(s, x, y, w, big, small, src) {
  s.addShape(pres.ShapeType.roundRect, { x, y, w, h: 1.25, rectRadius: 0.06, fill: { color: CARD },
    line: { color: CARDLINE, width: 0.75 } });
  s.addText(big, { x, y: y + 0.08, w, h: 0.62, fontFace: FONT, fontSize: 30, bold: true, color: NAVY, align: 'center',
    margin: 0, isTextBox: true });
  s.addText(small, { x: x + 0.1, y: y + 0.68, w: w - 0.2, h: 0.32, fontFace: FONT, fontSize: 11, bold: true,
    color: INK, align: 'center', margin: 0, isTextBox: true });
  s.addText(src, { x: x + 0.1, y: y + 0.97, w: w - 0.2, h: 0.24, fontFace: FONT, fontSize: 9, italic: true,
    color: MUTED, align: 'center', margin: 0, isTextBox: true });
}

function box(s, x, y, w, h, text, fill, color = WHITE, size = 12, bold = true) {
  s.addShape(pres.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.06, fill: { color: fill },
    line: { color: fill, width: 0.75 } });
  s.addText(text, { x: x + 0.05, y, w: w - 0.1, h, fontFace: FONT, fontSize: size, bold, color, align: 'center',
    valign: 'middle', margin: 0, isTextBox: true });
}

function arrow(s, x1, y1, x2, y2, color = SLATE) {
  s.addShape(pres.ShapeType.line, { x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1) || 0.001,
    h: Math.abs(y2 - y1) || 0.001, flipH: x2 < x1, flipV: y2 < y1,
    line: { color, width: 1.75, endArrowType: 'triangle' } });
}

// ======================================================================================= 1. title
{
  const s = pres.addSlide();
  slideNo += 1;
  s.background = { color: WHITE };
  s.addImage({ path: A('logo_vishwakarma.png'), x: 0.45, y: 0.35, w: 2.3, h: 0.71 });
  s.addImage({ path: A('logo_makerbhavan.png'), x: 11.4, y: 0.35, w: 1.5, h: 0.67 });
  s.addText('VISHWAKARMA AWARDS 2026-27  ·  STAGE 2 DESIGN SPECIFICATION', { x: 0.6, y: 1.45, w: 7.4, h: 0.4,
    fontFace: FONT, fontSize: 13, bold: true, color: SLATE, charSpacing: 1, margin: 0, isTextBox: true });
  s.addText('Vishwakarma Application ID: [add before submission]', { x: 0.6, y: 1.9, w: 7.4, h: 0.45,
    fontFace: FONT, fontSize: 16, bold: true, color: RED, margin: 0, isTextBox: true });
  s.addText('VisionAid', { x: 0.6, y: 2.45, w: 7.4, h: 1.0, fontFace: FONT, fontSize: 54, bold: true, color: NAVY,
    margin: 0, isTextBox: true });
  s.addText('A chest-worn, fully offline navigation aid that adds head-level-obstacle and drop-off warnings to the white cane - with an FPGA "safety island" whose alerts keep working even if the AI computer fails.',
    { x: 0.6, y: 3.45, w: 7.2, h: 1.0, fontFace: FONT, fontSize: 16, color: INK, margin: 0, isTextBox: true });
  const meta = [
    ['Team ID: ', '[add before submission]'],
    ['Track: ', 'Assistive Solutions & Inclusive Living'],
    ['Team SVNIT: ', 'Jayant Kumawat (lead), Sneha Ahir, Aman Gupta - SVNIT Surat'],
    ['Mentor institute: ', 'IIT Indore'],
    ['Design files: ', 'github.com/silentaf/viswa_id1'],
  ];
  s.addText(meta.map((m, i) => [{ text: m[0], options: { bold: true, color: NAVY } },
    { text: m[1], options: { color: m[1].startsWith('[') ? RED : INK, breakLine: i < meta.length - 1 } }]).flat(),
    { x: 0.6, y: 4.6, w: 7.3, h: 1.8, fontFace: FONT, fontSize: 14, paraSpaceAfter: 4, margin: 0, isTextBox: true });
  img(s, 'pod_assembled_iso.png', 8.3, 1.5, 4.6, 5.1);
  caption(s, 'CAD v1 of the chest pod (FreeCAD) - design stage, not yet fabricated', 8.3, 6.7, 4.6);
}

// ======================================================================================= 2. problem
{
  const s = content('Problem Context');
  stat(s, 0.45, 1.15, 2.95, '43.3 M', 'people blind worldwide (2020)', 'Cited: Bourne et al., Lancet GH 2021');
  stat(s, 3.6, 1.15, 2.95, '295 M', 'moderate / severe vision impairment', 'Cited: Bourne et al., Lancet GH 2021');
  stat(s, 6.75, 1.15, 2.95, '1.99 %', 'blindness among Indians aged 50+', 'Cited: NBVIS India 2015-19');
  stat(s, 9.9, 1.15, 2.98, '₹3,500', 'SmartCane - closest Indian aid', 'Cited: IIT Delhi / Assistech');
  card(s, 0.45, 2.6, 6.1, 3.55, 'Problem statement', [
    'The white cane only senses what it touches at ground level, about one cane-length ahead.',
    'Head-level obstacles (branches, poles, signs, truck bodies) and drop-offs (open drains, kerbs, steps) are what it misses. In a survey of 307 blind / legally blind travellers, 13 % hit their head at least once a month and 7 % fell at least once a month; 23 % of head-level accidents needed medical care, and cane vs guide-dog users did not differ (cited: Manduchi & Kurniawan, 2011; US-based sample).',
    'Reading a label or sign still needs a sighted helper or a hand-held phone.',
    ['Target beneficiary: ', 'blind and low-vision cane users who walk independently on Indian streets and campuses.'],
  ], { size: 14 });
  s.addText('Public search disclosure - what exists', { x: 6.75, y: 2.6, w: 6.1, h: 0.35, fontFace: FONT, fontSize: 15,
    bold: true, color: NAVY, margin: 0, isTextBox: true });
  table(s, [
    ['Product', 'Price (cited)', 'Gap'],
    ['SmartCane (IIT Delhi)', '≈ ₹3,500 (2016)', 'Above-knee only; no drop-offs, no naming / reading'],
    ['OrCam MyEye 3 Pro', '≈ US$4,250', 'Reading aid, not mobility; expensive'],
    ['Envision Glasses', 'US$1,899-3,499', 'Reading / description; expensive'],
    ['Phone apps (Lookout, MANI)', 'free', 'Need a hand + pointed phone; no continuous warning'],
  ], 6.75, 3.02, 6.13, [1.85, 1.35, 2.93], { size: 11 });
  note(s, 'Core innovation:', 'head-level + drop-off warnings for the cane user, with an alert path bounded in hardware (FPGA) and an on-device AI layer that names hazards and reads text - fully offline.');
}

// ======================================================================================= 3. before
{
  const s = content('User Journey - Before (cane only)');
  const steps = [['Walks with cane', 'cane sweeps the ground ~1 m ahead'], ['Head-level obstacle', 'not touched by the cane'],
    ['Collision', 'head / face injury risk'], ['Open drain or step down', 'found only when the cane drops in'],
    ['Needs to read a label', 'asks a stranger / holds a phone']];
  steps.forEach((st, i) => {
    const x = 0.45 + i * 2.52;
    box(s, x, 1.3, 2.25, 0.62, st[0], i === 2 ? RED : NAVY, WHITE, 13);
    s.addText(st[1], { x, y: 1.97, w: 2.25, h: 0.55, fontFace: FONT, fontSize: 11, color: MUTED, align: 'center',
      margin: 0, isTextBox: true });
    if (i < 4) arrow(s, x + 2.27, 1.61, x + 2.5, 1.61);
  });
  card(s, 0.45, 2.85, 6.1, 3.3, 'Current pain points', [
    'Warning comes from contact: the cane reports an obstacle only when it touches it.',
    'Nothing above the cane: overhanging objects are invisible to it.',
    'Drop-offs are found by falling-in of the cane tip - the user is already at the edge.',
    'Reading and identifying objects depend on another person.',
  ], { size: 15 });
  card(s, 6.75, 2.85, 6.13, 3.3, 'Quantified inefficiency (calculated, not measured)', [
    ['Warning time for ground obstacles: ', '~1 m cane reach ÷ 1.2 m/s walking speed ≈ 0.8 s.'],
    ['Warning time for head-level obstacles: ', '0 s - the cane never touches them.'],
    ['Warning before a drop-off: ', 'only as far as the cane tip; no advance cue.'],
    ['Text: ', 'every label / sign needs a helper; no independent reading.'],
  ], { fill: GREEN, line: GREENLINE, size: 15 });
  note(s, 'Assumptions:', '1.2 m/s typical adult walking speed and ~1 m cane reach are design assumptions; Stage 3 user interviews and trials will replace them with measured values.');
}

// ======================================================================================= 4. after
{
  const s = content('User Journey - After (cane + VisionAid)');
  const steps = [['Walks with cane + pod', 'pod scans 0.3-3 m, waist to head'], ['Obstacle in 3 m', 'FPGA classifies distance zone'],
    ['L / R vibration', 'pulse rate = distance; side = direction'], ['Floor drops ahead', 'LiDAR: drop-off alarm + buzzer'],
    ['Presses READ', 'Pi reads text aloud (offline)']];
  steps.forEach((st, i) => {
    const x = 0.45 + i * 2.52;
    box(s, x, 1.3, 2.25, 0.62, st[0], i === 2 ? '3F6E12' : NAVY, WHITE, 13);
    s.addText(st[1], { x, y: 1.97, w: 2.25, h: 0.55, fontFace: FONT, fontSize: 11, color: MUTED, align: 'center',
      margin: 0, isTextBox: true });
    if (i < 4) arrow(s, x + 2.27, 1.61, x + 2.5, 1.61);
  });
  card(s, 0.45, 2.85, 6.1, 3.3, 'How the user benefits', [
    'Warned before contact - including head-level obstacles the cane cannot reach.',
    'Left / right motors on the chest straps say which side the hazard is on.',
    'Drop-off warning ahead of the edge, not at it.',
    'Hands stay free; speech through a bone-conduction headset keeps the ears open to traffic.',
    'Alerts never depend on the AI computer (FPGA safety island).',
  ], { size: 15 });
  card(s, 6.75, 2.85, 6.13, 3.3, 'Quantified efficiency (labels say where each number comes from)', [
    ['Warning time, 3 m range at 1.2 m/s: ', '≈ 2.5 s (calculated, target range)'],
    ['Echo edge → motor on: ', 'max 214 ns over 4 events (simulated; target ≤ 1 ms)'],
    ['Update per direction: ', '99 ms (by design, simulated)'],
    ['Drop-off warned: ', '1.86 m before the step (calculated from CAD angles); alert 22 ms after (simulated)'],
    ['Image → speech audio ready: ', '211 ms (measured on laptop, not Pi 5; excludes capture + playback)'],
  ], { fill: GREEN, line: GREENLINE, size: 15 });
  note(s, 'Honesty rule:', 'no hardware built yet - simulated = our Verilog testbench; measured = our Pi software run on the dev laptop; Pi 5 and field numbers come in Stage 3.');
}

// ======================================================================================= 5. architecture
{
  const s = content('System Architecture - Block Diagram');
  // sensors
  const sens = ['3 × RCWL-1601 ultrasonic\n(left, right, head-level)', 'TF-Luna LiDAR\n(floor, −35°)', '3 buttons\n(READ / MODE / QUIET)'];
  sens.forEach((t, i) => box(s, 0.45, 1.25 + i * 1.0, 2.6, 0.8, t, SLATE, WHITE, 11));
  box(s, 4.0, 1.25, 3.4, 2.8, 'FPGA SAFETY ISLAND\nSipeed Tang Nano 9K (27 MHz)\n\necho timing · distance zones\nLiDAR drop-off · PWM patterns\nwatchdog · fault detection', NAVY, WHITE, 12);
  sens.forEach((t, i) => arrow(s, 3.07, 1.65 + i * 1.0, 3.98, 1.65 + i * 1.0));
  const outs = ['Left / right coin motors\n(chest straps, wired)', 'Buzzer\n("check device", drop-off)'];
  outs.forEach((t, i) => { box(s, 8.35, 1.45 + i * 1.3, 2.6, 0.85, t, '3F6E12', WHITE, 11); arrow(s, 7.42, 1.87 + i * 1.3, 8.33, 1.87 + i * 1.3); });
  box(s, 4.0, 4.75, 3.4, 1.3, 'AI PATH - Raspberry Pi 5\nYOLO-nano object names · OCR\ntext-to-speech (EN / HI)', '36456F', WHITE, 12);
  box(s, 0.45, 4.95, 2.6, 0.9, 'Camera Module 3\n(autofocus)', SLATE, WHITE, 11);
  arrow(s, 3.07, 5.4, 3.98, 5.4);
  box(s, 8.35, 4.95, 2.6, 0.9, 'Bluetooth bone-conduction\nheadset (speech)', '3F6E12', WHITE, 11);
  arrow(s, 7.42, 5.4, 8.33, 5.4);
  arrow(s, 5.45, 4.07, 5.45, 4.73); arrow(s, 5.95, 4.73, 5.95, 4.07);
  s.addText('UART 115200 status / config\n+ heartbeat + fault line', { x: 6.05, y: 4.12, w: 2.2, h: 0.55, fontFace: FONT,
    fontSize: 10, color: MUTED, margin: 0, isTextBox: true });
  box(s, 11.2, 1.25, 1.68, 4.8, 'POWER\n\nBIS-certified\nUSB-C power bank\n→ Pi 5\n→ 500 mA PTC\n→ carrier 5 V\n→ AMS1117 3.3 V', 'E8ECF4', NAVY, 11);
  note(s, 'Safety rule:', 'the FPGA drives the motors itself; the Pi can only add information and tune thresholds within clamped limits (it cannot switch alerts off). If the Pi\'s heartbeat stops, alerts continue and an "AI offline" chirp sounds.', 6.3);
}

// ======================================================================================= 6. specs + hardware
{
  const s = content('Target Specifications & Hardware Selection');
  table(s, [
    ['Parameter', 'Target', 'Evidence so far', 'Selected hardware / protocol'],
    ['Obstacle range (waist-head)', '0.3-3.0 m', 'sensor class; housings +25° / ±15° (CAD)', '3 × RCWL-1601, 3.3 V, sequenced'],
    ['Alert latency (echo → motor)', '≤ 1 ms', 'Simulated: max 214 ns (4 events)', 'Tang Nano 9K GW1NR-9 FPGA, 27 MHz'],
    ['Update period / direction', '≤ 100 ms', '99 ms by design (simulated)', '3 × 33 ms slots (no crosstalk)'],
    ['Distance resolution', '≤ ±5 cm to 2 m', 'Timer logic simulated: 1500 → 1499 mm (sensor error: Stage 3)', '1 µs echo timer (0.17 mm/count)'],
    ['Drop-off warning', '≥ 1.0 m ahead', 'Calculated 1.86 m (−35° from 1.3 m); alert 22 ms (sim.)', 'Benewake TF-Luna + IMU tilt correction'],
    ['Object name / OCR', '≤ 1 s / ≤ 3 s', 'Laptop: detect 28 ms, e2e 211 ms, OCR 1.2-1.4 s', 'Raspberry Pi 5 4 GB + Camera Module 3'],
    ['Pi fails → alert path', 'unaffected, cue ≤ 1 s', 'Simulated: AI-offline at 666 ms', 'FPGA heartbeat watchdog (GPIO17)'],
    ['Runtime', '≥ 4 h', 'Calc. (cited Pi 5 W): 4.3 h if AI busy ~50 % (assumed); 3.1 h if always on', '10,000 mAh BIS power bank, USB-C'],
    ['Pod mass', '≤ 250 g', 'Estimate: likely over (plastic ≈156 g solid)', 'PETG, 2.5 mm wall; lightening in v2'],
  ], 0.45, 1.15, 12.43, [2.75, 1.75, 3.6, 4.33], { size: 12, rowH: 0.43 });
  note(s, 'Architecture rationale:', 'Pi 5 (4 × Cortex-A76, 2.4 GHz) instead of the Stage 1 PYNQ-Z2 (2 × Cortex-A9, 650 MHz) for detection + OCR; FPGA kept for the parallel, cycle-exact, fault-isolated alert path; wired haptics so no radio sits in the safety path.', 5.95);
}

// ======================================================================================= 7. CAD
{
  const s = content('CAD Design & Mechanical Specs', 'FREECAD · PARAMETRIC');
  img(s, 'pod_exploded_iso.png', 0.45, 1.1, 5.2, 4.5);
  caption(s, 'Exploded: shell | Pi 5 | 20 mm standoffs | carrier PCB + Tang Nano | lid + housings | sensors', 0.45, 5.6, 5.2);
  img(s, 'pod_back_mount.png', 5.8, 1.1, 2.55, 2.4);
  caption(s, 'Back: GoPro-style mount, vents', 5.8, 3.5, 2.55);
  img(s, 'pod_front.png', 5.8, 3.85, 2.55, 1.75);
  caption(s, 'Front: sensor housings', 5.8, 5.6, 2.55);
  card(s, 8.55, 1.1, 4.33, 4.78, 'Mechanical specification', [
    ['Envelope: ', '112 × 84 × 48 mm shell + front housings'],
    ['Model: ', '19-parameter spreadsheet drives the model; shell sketch fully constrained'],
    ['Housings: ', 'head sensor +25°, side sensors ±15° yaw, LiDAR −35°'],
    ['Mount: ', 'GoPro-style 2-finger (3 mm, M5) on a chest harness'],
    ['Cooling: ', 'side + top/bottom vents for the Pi 5 active cooler'],
    ['Interference check: ', '0 mm³ vs Pi, carrier, Tang Nano, sensors'],
  ], { size: 12 });
  note(s, 'Design iteration:', 'adding the Tang Nano 3D model showed a 182 mm³ clash with the lid (171 mm³ of it the HDMI connector) - shell depth raised 44 → 48 mm in one parameter; clash now 0 mm³.', 6.1);
}

// ======================================================================================= 8. FEA
{
  const s = content('Material Selection & FEA (chest mount)', 'SIMULATED');
  img(s, 'fea_convergence.png', 0.45, 1.05, 7.6, 2.85);
  img(s, 'fea_contour_v1_sharp_side20N.png', 0.45, 3.95, 3.7, 2.3);
  caption(s, 'v1 sharp roots - 20 N side', 0.45, 6.05, 3.7);
  img(s, 'fea_contour_v2_fillet1p5_side20N.png', 4.35, 3.95, 3.7, 2.3);
  caption(s, 'v2 1.5 mm fillets - 20 N side', 4.35, 6.05, 3.7);
  table(s, [
    ['Material', 'Tg / softening', 'Choice'],
    ['PLA', '≈ 60 °C', 'No - softens in a car / summer sun'],
    ['PETG', '≈ 80 °C', 'Yes - tough, easy to print'],
    ['ASA', '≈ 100 °C, UV-stable', 'Stage 3 option outdoors'],
  ], 8.25, 1.05, 4.63, [0.9, 1.45, 2.28], { size: 11 });
  card(s, 8.25, 2.75, 4.63, 3.45, 'FreeCAD FEM + Gmsh + CalculiX', [
    ['Load A: ', '50 N down (0.3 kg × ~17 g bump); B: 20 N sideways'],
    ['PETG: ', 'E 2.0 GPa, ν 0.38, yield ≈ 50 MPa; required FoS ≥ 3'],
    ['Result: ', 'v2 worst FoS 8.7 (every run ≥ 8.6); max deflection 0.064 mm'],
    ['v1: ', 'root stress kept rising with mesh refinement → sharp-corner singularity'],
    ['v2: ', '1.5 mm root fillets → converged (≤ 3 % spread, 3 meshes); now in the CAD'],
  ], { size: 12 });
  note(s, 'Limitations:', 'linear isotropic model (printed parts are anisotropic); finest v2 mesh failed to solve, so v2 uses 3 mesh levels; a printed-mount pull test is planned for Stage 3.', 6.4);
}

// ======================================================================================= 9. electronics
{
  const s = content('Electronics - Schematic & Carrier PCB', 'KICAD 9');
  img(s, 'schematic.png', 0.45, 1.05, 7.4, 5.2);
  caption(s, 'Carrier-board schematic (A3): power, Pi header, FPGA, sensors, haptics, buttons, test points', 0.45, 6.05, 7.4);
  img(s, 'pcb_3d_iso.png', 8.0, 1.05, 4.88, 2.75);
  card(s, 8.0, 3.9, 4.88, 2.35, 'Power distribution & checks', [
    'Power bank → Pi 5 → header 5 V → 500 mA PTC → +5 V',
    '+5 V → AMS1117 → +3V3 (sensors, motors, IMU)',
    '+5 V → SS14 → Tang Nano (blocks USB back-feed)',
    ['Verified: ', 'ERC 0 · DRC 0 · unrouted 0 · parity 0'],
  ], { size: 12 });
  note(s, 'PCB:', '85 × 56 mm, 2 layers, Pi 5 outline + mounting holes, 20 mm standoffs + 40-way ribbon; 3.3 V-bank FPGA pins only; MOSFET motor drivers with flyback diodes; Gerbers generated.', 6.4);
}

// ======================================================================================= 10. BOM
{
  const s = content('Bill of Materials & Sourcing');
  table(s, [
    ['Component', 'Part / specification', 'Qty', 'Source · origin · lead', '₹ (basis)'],
    ['AI computer', 'Raspberry Pi 5 4 GB + active cooler', '1', 'KSP Electronics · imported · out of stock', '15,050 (quote + est.)'],
    ['FPGA', 'Sipeed Tang Nano 9K', '1', 'Probots · imported · out of stock', '2,999 (quote)'],
    ['Camera', 'Pi Camera Module 3 + cable', '1', 'Thingbits · imported · in stock', '3,358 (quote + est.)'],
    ['LiDAR', 'Benewake TF-Luna', '1', 'Probots · imported · out of stock', '2,118 (quote)'],
    ['Ultrasonic + IMU', 'RCWL-1601 × 4, MPU-6050', '5', 'Robu · local · 2-4 d', '800 (est.)'],
    ['Feedback', 'Coin motors × 2, BT bone-conduction headset', '3', 'Robu / Amazon.in · 2-5 d', '2,120 (est.)'],
    ['Power', '10,000 mAh BIS power bank', '1', 'local · 1-3 d', '1,200 (est.)'],
    ['Carrier PCB', '2-layer fab ×5 + SMD parts + connectors + ribbon', '1', 'LionCircuits (domestic) · 5-7 d', '3,250 (est.)'],
    ['Mechanical', 'PETG, standoffs, inserts, harness, buttons', '1', 'Robu / Amazon.in · 2-5 d', '2,350 (est.)'],
    ['microSD', '64 GB A2', '1', 'local · 1-3 d', '700 (est.)'],
    ['TOTAL', '', '', 'Grant ₹30,000', '33,945'],
  ], 0.45, 1.1, 8.3, [1.35, 2.75, 0.45, 2.45, 1.3], { size: 11, rowH: 0.38 });
  card(s, 8.95, 1.1, 3.93, 2.55, 'Budget - honest status', [
    'Everything except the Pi 5 board: ₹19,445.',
    'Pi 5 4 GB on 9 Oct: ₹12,600-14,500, out of stock → ₹2,045-3,945 over the grant.',
    ['Rule: ', 'Pi 5 must be ≤ ₹10,555 to fit; else re-quote or cover the gap from team funds.'],
  ], { size: 12, fill: GREEN, line: GREENLINE });
  card(s, 8.95, 3.8, 3.93, 2.35, 'Battery life (calculated, cited Pi 5 W)', [
    'Pi 5: ≈ 3.0 W idle, ≈ 8.8 W full load (published); rest 1.34 W (est.)',
    ['AI always on: ', '10.1 W → 3.1 h'],
    ['Event-triggered, ~50 % (assumed): ', '7.2 W → 4.3 h'],
    ['AI idle: ', '4.3 W → 7.2 h'],
  ], { size: 12 });
  note(s, 'Procurement status:', 'nothing ordered in Stage 2. Quotes are live listings checked 9 Oct 2026; Pi 5, Tang Nano 9K and TF-Luna were out of stock that day - re-quote and order early. Itemised BOM: design/bom/VisionAid_BOM_Power.xlsx.', 6.35);
}

// ======================================================================================= 11. FPGA evidence
{
  const s = content('FPGA Safety Island - Verification & Implementation', 'SIM + REAL P&R');
  img(s, 'waveform_latency_zoom.png', 0.45, 1.05, 7.5, 4.75);
  caption(s, 'Plotted event: 136 ns from echo edge to motor ON (motor rises on the same clock as the zone change). The testbench monitor samples 2 clocks later, so its 214 ns is a conservative upper bound.', 0.45, 5.75, 7.5);
  table(s, [
    ['Testbench check (Icarus Verilog)', 'Result'],
    ['Distance 1500 / 2500 mm', '1499 / 2499 mm'],
    ['Echo edge → motor ON', '136 ns wave; ≤ 214 ns bound'],
    ['Frames to Pi (Verilog / Py)', '192 / 192 decoded, 0 bad'],
    ['LiDAR drop-off', 'alert 22.3 ms after change'],
    ['Pi heartbeat lost', 'AI-offline 666 ms; alerts on'],
    ['Sensor unplugged', 'fault flag + FAULT_N low'],
    ['Overall', 'ALL TESTS PASSED'],
  ], 8.15, 1.05, 4.73, [2.45, 2.28], { size: 11, rowH: 0.3 });
  table(s, [
    ['27 MHz', 'GW1NR-9 nextpnr', 'Zynq-7020 Vivado'],
    ['LUTs', '1,512 / 8,640 (17 %)', '653 / 53,200 (1.2 %)'],
    ['Flip-flops', '568 / 6,480 (8 %)', '580 / 106,400 (0.55 %)'],
    ['ALU / DSP', '914 ALU (14 %)', '1 DSP (0.45 %)'],
    ['Block RAM', '0 / 26', '0 / 140'],
    ['I/O', '26 / 276', 'n/a (OOC run)'],
    ['Timing', 'Fmax 67.9 MHz, met', 'WNS +30.2 ns, met'],
  ], 8.15, 3.75, 4.73, [1.05, 1.85, 1.83], { size: 10, rowH: 0.28 });
  caption(s, 'Routed results (GW1NR-9 bitstream built; Vivado out-of-context). No hardware yet.', 8.15, 6.0, 4.73);
  note(s, 'Cross-verified:', 'the Verilog FPGA accepted a command built by our Python Pi code, and the Python decoder read every byte the FPGA sent - both sides of the link agree.', 6.4);
}

// ======================================================================================= AI path proof of concept
{
  const s = content('AI Path (Raspberry Pi software) - Proof of Concept', 'MEASURED · LAPTOP');
  img(s, 'ai_path_results.png', 0.45, 1.05, 12.43, 3.6);
  card(s, 0.45, 4.75, 6.1, 1.5, 'What runs (same code for the Pi 5)', [
    'YOLOv5n (ONNX) → hazard + side; RapidOCR; Piper TTS English + Hindi; alert manager; IMU floor baseline',
    'Event-triggered: AI runs only when the FPGA sees an obstacle < 3 m',
  ], { size: 12 });
  card(s, 6.75, 4.75, 6.13, 1.5, 'Full-loop replay (FPGA sim bytes → speech)', [
    '"Step down ahead. Stop."  ·  "Check device: head sensor."',
    '"person, left, 1.6 metres" - WAV files in design/pi/results/replay',
  ], { size: 12, fill: GREEN, line: GREENLINE });
  note(s, 'Honest scope:', 'speeds measured on an i7 laptop (4 threads), NOT on a Pi 5; 211 ms excludes camera capture and audio playback. Accuracy is hardware-independent (COCO: 200 images vs human labels; OCR: 64 synthetic labels). Pi 5 timing in Stage 3.', 6.38);
}

// ======================================================================================= pothole fine-tune
{
  const s = content('Model Training - Pothole Detector (fine-tuned)', 'TRAINED · HELD-OUT TEST');
  img(s, 'pothole_test_pred.png', 0.45, 1.05, 5.0, 4.98);
  caption(s, 'Our model on 16 held-out test images (boxes = its predictions, number = confidence)', 0.45, 6.06, 5.0);
  table(s, [
    ['Held-out test split (100 images, 269 potholes)', 'Result'],
    ['Precision', '0.64'],
    ['Recall', '0.30'],
    ['mAP50 / mAP50-95', '0.37 / 0.15'],
    ['Speed, laptop CPU, 4 threads (not Pi 5)', '26 ms / image'],
    ['Before fine-tuning (COCO model)', 'no pothole class at all'],
  ], 5.75, 1.05, 7.13, [4.83, 2.3], { size: 12, rowH: 0.36 });
  card(s, 5.75, 3.35, 3.47, 2.8, 'How it was trained', [
    'YOLO11n, COCO-pretrained start, 100 epochs, RTX 5060 GPU, 7.7 min',
    'Public dataset, CC BY 4.0: 100 train / 100 valid / 100 test images',
    'Checked: no train-test image overlap (name + pixel hash, incl. flips)',
  ], { size: 12 });
  card(s, 9.41, 3.35, 3.47, 2.8, 'Honest limits', [
    'Finds ~3 in 10 potholes; ~2 in 3 detections are real',
    'Small set of mostly non-Indian road photos, taken from vehicle / hand height',
    'Stage 3: Indian, chest-height data from our own camera',
  ], { size: 12, headColor: RED });
  note(s, 'Why it matters:', 'the whole training pipeline (data checks → fine-tune → held-out test → ONNX for the Pi) works end to end; files in design/pi/training.', 6.38);
}

// ======================================================================================= sensor analysis
{
  const s = content('Sensor Coverage & Drop-off Analysis', 'CALCULATED + SIMULATED');
  img(s, 'sensor_geometry.png', 0.45, 1.05, 12.43, 3.75);
  card(s, 0.45, 4.9, 4.0, 1.35, 'Drop-off: target met', [
    'LiDAR at −35° from 1.3 m sees a 15 cm step 1.86 m ahead (≈ 1.5 s at walking speed)',
  ], { size: 12, bullets: false, fill: GREEN, line: GREENLINE });
  card(s, 4.65, 4.9, 4.0, 1.35, 'Found: walking sway', [
    '±3° chest sway → 25 false alarms in 20 s; IMU-corrected baseline → 0 (now in the Pi code)',
  ], { size: 12, bullets: false, headColor: RED });
  card(s, 8.85, 4.9, 4.03, 1.35, 'Found: waist-height gap', [
    'Under 1 m ahead, 0.3-1.0 m height is not covered → tilt forward sensors −10° in CAD v2',
  ], { size: 12, bullets: false, headColor: RED });
  note(s, 'Assumptions:', '1.3 m pod height, 15° ultrasonic half-beam (datasheet class), ±3° sway at 1.8 Hz, 1 cm LiDAR noise - design/analysis/sensor_geometry.py.', 6.38);
}

// ======================================================================================= 12. maker journey
{
  const s = content('Your Maker Journey - Evidence');
  const ph = (x, y, w, h, t) => {
    s.addShape(pres.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.06, fill: { color: 'FBEDEC' },
      line: { color: RED, width: 1, dashType: 'dash' } });
    s.addText(t, { x: x + 0.15, y, w: w - 0.3, h, fontFace: FONT, fontSize: 13, bold: true, color: RED, align: 'center',
      valign: 'middle', margin: 0, isTextBox: true });
  };
  ph(0.45, 1.1, 3.0, 2.3, 'PHOTO TO ADD:\nteam member doing CAD / KiCad with SVNIT ID badge visible');
  ph(0.45, 3.55, 3.0, 2.3, 'PHOTO TO ADD:\njoint review with faculty guide / IIT Indore mentor');
  img(s, 'freecad_tree.png', 3.65, 1.1, 4.5, 3.0);
  caption(s, 'FreeCAD feature tree - FingerRootFillet R 1.5 mm', 3.65, 4.1, 4.5);
  img(s, 'drc_erc_strips.png', 8.35, 1.1, 4.53, 1.75);
  caption(s, 'KiCad DRC: 0 violations, 0 unconnected  ·  ERC: 0 errors, 0 warnings', 8.35, 2.83, 4.53);
  img(s, 'gtkwave_crop.png', 3.65, 4.45, 9.23, 1.0);
  caption(s, 'GTKWave: echo falls → distance 749 mm → zone 3 → left motor ON (simulation)', 3.65, 5.45, 9.23);
  card(s, 8.35, 3.15, 4.53, 1.2, 'Raw repository (native files)', [
    'github.com/silentaf/viswa_id1 - .FCStd, .step, .kicad_sch/.kicad_pcb, .v, .xlsx, timestamped commits',
  ], { size: 11, bullets: false });
  note(s, 'Stage 1 → 2:', 'PYNQ-Z2 → Pi 5 + Tang Nano 9K; per-stage latency specs; LiDAR for drop-offs; FEA-driven fillet; CAD clash fix 44 → 48 mm (details on the next slide).', 6.35);
}

// ======================================================================================= 13. iterations
{
  const s = content('Stage 1 → Stage 2 Engineering Iterations');
  table(s, [
    ['Stage 1 said', 'Stage 2 decision', 'Why'],
    ['PYNQ-Z2 does everything', 'Pi 5 (AI) + Tang Nano 9K FPGA (safety island)', '2 × A9 650 MHz vs 4 × A76 2.4 GHz for AI; fault isolation'],
    ['"<10 ms" reflex, "<100 ms" on cover', 'Per-stage specs: echo → motor ≤ 1 ms', 'Echo from 3 m alone takes ≈ 17.5 ms - "<10 ms end-to-end" is impossible'],
    ['Downward ultrasonic for drop-offs', 'Downward TF-Luna LiDAR (−35°)', 'Narrow beam gives a clean floor-distance signal'],
    ['Wristband with 2 motors', 'L / R motors on the chest straps, wired', 'Two motors on one wrist are hard to tell apart; no radio in safety path'],
    ['Custom bone-conduction driver', 'Bluetooth bone-conduction headset', 'Pi 5 has no analog audio; speech is the information channel'],
    ['"< ₹5,500 BOM"', 'Prototype BOM ₹33,945 at 9 Oct quotes', 'Pi 5 + camera alone exceed ₹5,500'],
    ['"250M+", "₹4-6 lakh" competitors', 'Cited 2020 data; SmartCane disclosed', 'Accuracy and honest public-search disclosure'],
    ['10-15 pilot users', 'Stage 3, after ethics approval + O&M instructor', 'Honest scope for a design round'],
  ], 0.45, 1.1, 12.43, [3.3, 4.3, 4.83], { size: 12, rowH: 0.52 });
  note(s, 'Found by our own analysis:', 'FEA → 1.5 mm root fillets; CAD clash → shell 44 → 48 mm; sway simulation → IMU floor baseline; power analysis → event-triggered AI; tests → OCR word-order bug fixed.', 6.35);
}

// ======================================================================================= 14. safety
{
  const s = content('Safety & Hazard Mitigation');
  table(s, [
    ['Failure mode', 'Hazard', 'Embedded fail-safe / mitigation'],
    ['Ultrasonic stuck / unplugged', 'Missed obstacle', 'No-response detector (3 slots) → buzzer "check device" + FAULT_N (simulated)'],
    ['Pi crash / hang', 'No object names / OCR', 'FPGA watchdog → "AI offline" chirp; alert path unaffected (simulated)'],
    ['Bluetooth headset drops', 'No speech', 'Haptics carry all safety alerts; distinct cue'],
    ['Walking sway / tilt', 'False drop-off alarms', 'IMU-corrected floor baseline: 25 → 0 false alarms (simulated)'],
    ['Pi 5 overheats in pod', 'Throttling, slow AI', 'Active cooler + vents in CAD; thermal test in Stage 3'],
    ['Carrier short circuit', 'Pi 5 V rail damage', '500 mA PTC fuse on the header supply'],
    ['Battery fire', 'Burns', 'BIS-certified power bank only - no loose Li-ion cells'],
    ['Alert fatigue', 'User ignores alerts', 'Zone hysteresis + quiet mode (silences "info" only)'],
  ], 0.45, 1.1, 8.4, [2.35, 1.85, 4.2], { size: 11, rowH: 0.5 });
  card(s, 9.05, 1.1, 3.83, 4.95, 'Standards considered in the design (not certified)', [
    ['IEC 62368-1 / IS 13252 - ', 'ICT equipment safety'],
    ['IEC 62133-2 / IS 16046 - ', 'Li-ion (via BIS power bank)'],
    ['IEC 60529 - ', 'IP54 target for the pod'],
    ['ISO 10993-5/-10 - ', 'skin-contact materials (harness)'],
    ['ISO 9999 - ', 'assistive-product classification'],
    ['WPC / ETA - ', 'only pre-certified radio modules'],
  ], { size: 12 });
  note(s, 'Design principle:', 'the cane stays the primary aid - VisionAid only adds warnings, and its alert path is independent of the AI computer.', 6.25);
}

// ======================================================================================= 15. roadmap
{
  const s = content('Roadmap - 4-Month Fabrication Plan');
  const months = [
    ['Nov 2026', ['Order parts + carrier PCB (LionCircuits)', 'FPGA + sensor bring-up on the bench', 'Range, latency (logic analyser at TP4/TP5), power tests']],
    ['Dec 2026', ['PCB assembly; Pi software integration', 'Print + fit enclosure; thermal test in pod', 'India-class dataset (auto-rickshaw, cow, pothole, drain)']],
    ['Jan 2027', ['Ethics approval (institute ethics committee)', 'Supervised trials: sighted blindfolded first', 'Then blind volunteers with an O&M instructor']],
    ['Feb 2027', ['Fix top issues from trials', 'Re-run all Stage 2 tests on hardware', 'Field-test-ready unit for Stage 3']],
  ];
  months.forEach((m, i) => {
    const x = 0.45 + i * 3.15;
    box(s, x, 1.15, 2.95, 0.55, m[0], i % 2 ? SLATE : NAVY, WHITE, 15);
    card(s, x, 1.85, 2.95, 3.0, null, m[1], { size: 15 });
    if (i < 3) arrow(s, x + 2.97, 1.42, x + 3.13, 1.42);
  });
  card(s, 0.45, 5.0, 12.43, 1.15, 'Stage 3 commitment', [
    'A wearable, battery-powered VisionAid prototype ready for supervised functional field testing, with every Stage 2 target (range, alert latency, drop-off distance, runtime, mass) measured on hardware.',
  ], { size: 13, bullets: false, fill: GREEN, line: GREENLINE });
  note(s, 'Research extension:', 'RISC-V soft core (PicoRV32) on the Tang Nano + a tiny spiking neural network to classify sensor patterns (stairs / wall / person) at very low power - once real sensor data exists.', 6.3);
}

// ======================================================================================= 16. challenges
{
  const s = content('Technical Challenges & Risks');
  const cards = [
    ['Ultrasonic crosstalk vs update rate', 'Three sensors firing together hear each other. Sequencing fixes it but limits each direction to one ping per 99 ms (simulated).'],
    ['Enclosure clash found in CAD', 'With the Tang Nano 3D model added, the module clashed with the lid by 182 mm³ - 171 mm³ of it the HDMI connector (CAD interference check).'],
    ['Weight over target', 'Enclosure plastic alone ≈ 156 g if solid (CAD volume); with Pi 5 and sensors the pod likely exceeds 250 g.'],
    ['Budget over the grant', 'At 9 Oct quotes the BOM is ₹33,945 - ₹3,945 over the ₹30k grant; Pi 5, Tang Nano and TF-Luna were out of stock.'],
    ['Battery vs always-on AI', 'With the AI always running, the calculated runtime is 3.1 h - below the 4 h target (cited Pi 5 power).'],
    ['Sway false alarms + coverage gap', 'Simulation: 25 false drop-off alarms in 20 s with a fixed floor baseline; waist-height gap under 1 m ahead.'],
  ];
  cards.forEach((c, i) => {
    const x = 0.45 + (i % 3) * 4.2, y = 1.15 + Math.floor(i / 3) * 2.55;
    card(s, x, y, 4.0, 2.35, c[0], [c[1]], { size: 15, headSize: 16, bullets: false, headColor: RED });
  });
  note(s, 'Source of each risk:', 'our own design files - CAD interference report, FEA study, BOM workbook, FPGA simulation - not assumptions copied from elsewhere.', 6.35);
}

// ======================================================================================= 17. mitigation
{
  const s = content('Potential Solutions & Risk Mitigation');
  const rows = [
    ['Crosstalk vs rate', 'Keep sequencing; Stage 3 option: coded pings to fire in parallel'],
    ['Enclosure clash', 'Done: shell depth 44 → 48 mm (one parameter); interference now 0 mm³'],
    ['Weight', 'v2: 2.0 mm walls + 20 % infill, merge housings, Pi Compute Module later'],
    ['Budget', 'Pi 5 must be ≤ ₹10,555 to fit; re-quote at order time, else team funds cover the gap'],
    ['Battery', 'Done in code: event-triggered AI → 4.3 h (calc., ~50 % AI duty assumed); measure on hardware'],
    ['Sway / gap', 'Done: IMU floor baseline (0 false alarms, sim.); gap: forward sensors −10° in CAD v2'],
    ['Mount corners', 'Done: 1.5 mm root fillets (FEA v2 converged, FoS ≥ 8.7)'],
    ['Pi failure / heat', 'FPGA watchdog + independent alert path (simulated); cooler + vents, thermal test'],
  ];
  table(s, [['Risk', 'Mitigation / backup']].concat(rows), 0.45, 1.15, 8.6, [2.2, 6.4], { size: 13, rowH: 0.56 });
  img(s, 'pcb_3d_top.png', 9.25, 1.15, 3.63, 2.6);
  caption(s, 'Carrier PCB with the Tang Nano 9K model (KiCad)', 9.25, 3.75, 3.63);
  img(s, 'pod_xray_iso.png', 9.25, 4.05, 3.63, 2.15);
  note(s, 'Status:', '"Done" items are already in the design files; the rest are planned and will be verified on hardware in Stage 3.', 6.35);
}

// ======================================================================================= 18. references
{
  const s = content('References & Sources');
  card(s, 0.45, 1.1, 7.0, 5.05, 'References', [
    'Bourne R. et al., Trends in prevalence of blindness and vision impairment, Lancet Global Health 9(2):e130-e143, 2021.',
    'National Blindness & Visual Impairment Survey India 2015-19, AIIMS / MoHFW (indiavisionatlasnpcb.aiims.edu).',
    'Manduchi R., Kurniawan S., Mobility-related accidents experienced by people with visual impairment, Insight 4(2), 2011 (tech. report UCSC-SOE-10-24; 307 respondents).',
    'SmartCane - IIT Delhi / Assistech: ₹3,500 (Snapdeal launch, 2016; entrepreneur.com, electronicsforu.com).',
    'OrCam MyEye 3 Pro US$4,250 (nelowvision.com); Envision Glasses US$1,899 / 3,499 (shop.letsenvision.com) - checked 9 Oct 2026.',
    'Sipeed Tang Nano 9K wiki and pin map; Benewake TF-Luna datasheet; Raspberry Pi 5 / Camera Module 3 product briefs.',
    'Raspberry Pi 5 power (≈ 3.0 W idle, ≈ 8.8 W full load): raspberry.tips power comparison, 2026. Part prices: kspelectronics.in, electronifyindia.com, probots.co.in, thingbits.in (9 Oct 2026).',
    'COCO val2017 (cocodataset.org); YOLOv5n, YOLO11n (Ultralytics); RapidOCR / PP-OCR; Piper TTS (rhasspy). Pothole data: Roboflow Universe "Potholes Detection" (project-ssayl), CC BY 4.0, via Hugging Face Ryukijano/Pothole-detection-Yolov8.',
    'Tools: KiCad 9, FreeCAD + CalculiX + Gmsh, Icarus Verilog, GTKWave, Yosys, nextpnr + Apicula, Vivado 2026.1, FreeRouting.',
  ], { size: 12 });
  card(s, 7.65, 1.1, 5.23, 5.05, 'Image sources', [
    'All diagrams, renders, plots and screenshots in this deck are our own, generated from the project files in github.com/silentaf/viswa_id1 (one exception below):',
    'CAD renders - design/cad (FreeCAD model)',
    'PCB / schematic - design/electronics (KiCad)',
    'FEA plots - design/cad/outputs/fea',
    'Waveforms - design/fpga (testbench); AI / analysis charts - design/pi, design/analysis',
    'Screenshots - docs/screenshots',
    'Exception: the road photos on the pothole slide are from the public dataset above (CC BY 4.0); only the boxes are our model\'s output.',
    'Logos: Vishwakarma Awards / Maker Bhavan Foundation (official template).',
  ], { size: 14 });
}

pres.writeFile({ fileName: path.join(__dirname, 'VisionAid_Stage2_Design_Deck.pptx') }).then((f) => console.log('saved', f, slideNo, 'slides'));
