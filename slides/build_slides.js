// Build the presentation deck (PowerPoint).
// Run from the repository root:  npm install && npm run slides
// Input : outputs/results.json, outputs/figures/*.png, data/processed/panel_pwt11.csv,
//         config/authors.json (optional, not tracked by git)
// Output: slides/panel_data_slides.pptx
//
// Design: light theme, grayscale only. Meaning is carried by darkness, borders and
// patterns rather than colour, so the deck also works on a black-and-white printout.
// Slide text is Turkish because the talk is given in Turkish.

const pptxgen = require("pptxgenjs");
const JSZip = require("jszip");
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const RESULT = JSON.parse(fs.readFileSync(path.join(ROOT, "outputs", "results.json"), "utf8"));
const S = RESULT.pwt11;
const K = RESULT.pwt5;
const FIGURE = (name) => path.join(ROOT, "outputs", "figures", name);
const OUTPUT = path.join(__dirname, "panel_data_slides.pptx");
const REPO_URL = "https://github.com/devbarans/panel-data-convergence";
const REPO_LABEL = "github.com/devbarans/panel-data-convergence";

// ---------------------------------------------------------------- cover details
// Personal details live in config/authors.json, which is not committed.
// See config/authors.example.json for the format.
function loadAuthors() {
  const file = path.join(ROOT, "config", "authors.json");
  if (!fs.existsSync(file)) return { course: "", authors: [] };
  const data = JSON.parse(fs.readFileSync(file, "utf8"));
  return { course: data.course || "", authors: (data.authors || []).map((a) => [a.name || "", a.student_id || ""]) };
}
const COVER = loadAuthors();

// ---------------------------------------------------------------- formatting helpers
const MINUS = "−";
const num = (x, d = 2) => {
  const s = Math.abs(x).toFixed(d).replace(".", ",");
  return (x < 0 && Number(Math.abs(x).toFixed(d)) !== 0 ? MINUS : "") + s;
};
const signed = (x, d = 2) => (Number(Math.abs(x).toFixed(d)) !== 0 && x > 0 ? "+" : "") + num(x, d);
const pValue = (p) => (p < 0.001 ? "< 0,001" : num(p, 3));
const thousands = (x) => Math.round(x).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
const stars = (p) => (p < 0.01 ? "***" : p < 0.05 ? "**" : p < 0.1 ? "*" : "");

// ---------------------------------------------------------------- theme (grayscale)
const INK = "111111";
const DARK = "262626";
const MID = "595959";
const SOFT = "8C8C8C";
const CARD = "F2F2F2";
const WHITE = "FFFFFF";
const HEAD = "Cambria";
const BODY = "Calibri";

const ML = 0.6; // left margin (inches)
const CW = 12.133; // content width (inches)

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5 in
pres.title = "Panel Veri Analizi: Büyüme ve Yakınsama, 1973–2023";
pres.subject = "Panel veri ekonometrisi";
pres.author = COVER.authors.map(([name]) => name).join(", ");
pres.company = "";

// ---------------------------------------------------------------- slide masters
pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: WHITE },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: ML, y: 0.62, w: CW, h: 0.85, fontFace: HEAD, fontSize: 34, bold: true, color: INK, align: "left", valign: "middle", margin: 0 }, text: "" } },
    { text: { text: "Panel Veri Analizi · Büyüme ve Yakınsama, 1973–2023", options: { x: ML, y: 7.05, w: 8, h: 0.3, fontFace: BODY, fontSize: 11, color: MID, margin: 0 } } },
  ],
  slideNumber: { x: 12.13, y: 7.05, w: 0.6, h: 0.3, fontFace: BODY, fontSize: 11, color: MID, align: "right" },
});
pres.defineSlideMaster({ title: "COVER", background: { color: WHITE }, objects: [] });

// ---------------------------------------------------------------- drawing helpers
// Light inline markup: **bold** and _{subscript}; "\n" starts a new line.
function runs(str, o = {}) {
  const lines = str.split("\n");
  const out = [];
  lines.forEach((line, i) => {
    const r = parseRuns(line, o);
    if (i < lines.length - 1) r[r.length - 1].options.breakLine = true;
    out.push(...r);
  });
  return out;
}
function parseRuns(str, o = {}) {
  return str
    .split(/(\*\*[^*]+\*\*|_\{[^}]*\})/)
    .filter((t) => t !== "")
    .map((t) => {
      if (t.startsWith("**")) return { text: t.slice(2, -2), options: { ...o, bold: true } };
      if (t.startsWith("_{")) return { text: t.slice(2, -1), options: { ...o, subscript: true } };
      return { text: t, options: { ...o } };
    });
}
function paragraphs(items, o = {}, p = {}) {
  const out = [];
  items.forEach((item, i) => {
    const r = runs(item, { fontFace: BODY, color: INK, ...o });
    Object.assign(r[0].options, p);
    r[r.length - 1].options.breakLine = i < items.length - 1;
    out.push(...r);
  });
  return out;
}
const BULLET = { bullet: { indent: 18 }, paraSpaceAfter: 9 };

function text(s, content, o) {
  if (typeof content === "string" && /\*\*|_\{/.test(content)) {
    content = runs(content, { fontFace: o.fontFace || BODY, fontSize: o.fontSize, color: o.color || INK, bold: o.bold });
  }
  s.addText(content, { fontFace: BODY, color: INK, margin: 0, isTextBox: true, valign: "top", ...o });
}
function card(s, x, y, w, h, o = {}) {
  s.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.08,
    fill: { color: o.fill || CARD }, line: { color: o.line || MID, width: 1 },
    objectName: o.name || "Card",
  });
}
// Clickable link to the code repository, placed in the top-right corner by default.
function repoLink(s, o = {}) {
  const prefix = o.prefix === undefined ? "Kod: " : o.prefix;
  const size = o.fontSize || 11;
  s.addText([
    { text: prefix, options: { fontFace: BODY, fontSize: size, color: MID } },
    { text: REPO_LABEL, options: { fontFace: BODY, fontSize: size, color: o.color || DARK, bold: o.bold, hyperlink: { url: REPO_URL, tooltip: "GitHub: kod ve veri" } } },
  ], { x: o.x ?? ML + CW - 5.2, y: o.y ?? 0.3, w: o.w ?? 5.2, h: o.h ?? 0.3, align: o.align || "right", valign: "middle", margin: 0, isTextBox: true, objectName: "Repository link" });
}
// Section label (top left) and repository link (top right) shared by every content slide.
function slideHeader(s, label) {
  text(s, label.toLocaleUpperCase("tr-TR"), { x: ML, y: 0.3, w: 6.5, h: 0.3, fontSize: 12, bold: true, color: MID, charSpacing: 3, objectName: "Section label" });
  repoLink(s);
}
function title(s, t) {
  s.addText(t, { placeholder: "title" });
}
function circle(s, x, y, d, content, o = {}) {
  s.addShape(pres.ShapeType.ellipse, {
    x, y, w: d, h: d,
    fill: { color: o.fill || INK }, line: { color: INK, width: 1.5 },
    objectName: "Circle",
  });
  s.addText(content, { x, y, w: d, h: d, align: "center", valign: "middle", fontFace: o.font || BODY, fontSize: o.size || 20, bold: true, color: o.color || WHITE, margin: 0, isTextBox: true });
}
function pngSize(file) {
  const b = fs.readFileSync(file);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
}
function image(s, file, x, y, w, h, alt) {
  card(s, x, y, w, h, { fill: WHITE, name: "Figure frame" });
  const pad = 0.12;
  const { w: iw, h: ih } = pngSize(file);
  const ratio = iw / ih;
  let W = w - 2 * pad, H = W / ratio;
  if (H > h - 2 * pad) { H = h - 2 * pad; W = H * ratio; }
  s.addImage({ path: file, x: x + (w - W) / 2, y: y + (h - H) / 2, w: W, h: H, altText: alt });
}
function table(s, rows, o) {
  const size = o.fontSize || 14;
  const border = () => ({ type: "solid", color: MID, pt: 1 });
  const data = rows.map((r, ri) =>
    r.map((c, ci) => ({
      text: typeof c === "string"
        ? runs(c, { fontFace: BODY, fontSize: size, bold: ri === 0 || (o.boldFirstColumn && ci === 0), color: ri === 0 ? WHITE : INK })
        : c.map((x) => ({ text: x.text, options: { fontFace: BODY, fontSize: size, color: INK, ...x.options } })),
      options: {
        fill: { color: ri === 0 ? INK : ri % 2 === 0 ? CARD : WHITE },
        border: [border(), border(), border(), border()],
        valign: "middle",
        align: (o.align && o.align[ci]) || "left",
        margin: o.cellMargin || [0.05, 0.1, 0.05, 0.1],
      },
    }))
  );
  s.addTable(data, { x: o.x, y: o.y, w: o.w, colW: o.colW, rowH: o.rowH, autoPage: false, objectName: o.name || "Table" });
}

// ---------------------------------------------------------------- data for the cover grid
function readPanel() {
  const lines = fs.readFileSync(path.join(ROOT, "data", "processed", "panel_pwt11.csv"), "utf8").trim().split("\n");
  const header = lines[0].split(",");
  return lines.slice(1).map((line) => {
    // country names may contain commas ("Korea, Republic of"); commas inside quotes are skipped
    const parts = line.match(/("[^"]*"|[^,]*)(,|$)/g).map((x) => x.replace(/,$/, "").replace(/^"|"$/g, ""));
    const row = {};
    header.forEach((h, i) => (row[h] = isNaN(Number(parts[i])) ? parts[i] : Number(parts[i])));
    return row;
  });
}
const PANEL = readPanel();

function grayShade(growth) {
  // maps growth from -2 ... 7 onto light ... dark gray
  const t = Math.max(0, Math.min(1, (growth + 2) / 9));
  const v = Math.round(240 - t * (240 - 26));
  return v.toString(16).padStart(2, "0").repeat(3).toUpperCase();
}
function coverGrid(s, x0, y0) {
  const countries = [["TUR", "Türkiye"], ["USA", "ABD"], ["KOR", "Güney Kore"], ["CHN", "Çin"], ["IND", "Hindistan"], ["BRA", "Brezilya"], ["ARG", "Arjantin"], ["NGA", "Nijerya"]];
  const periods = [...new Set(PANEL.map((r) => r.period))].sort();
  const cell = 0.4, gap = 0.06, labelW = 1.3;
  periods.forEach((p, j) => {
    if (j % 3 === 0)
      text(s, `’${String(p).slice(2)}`, { x: x0 + labelW + j * (cell + gap) - 0.1, y: y0, w: cell + 0.2, h: 0.3, fontSize: 12, color: MID, align: "center" });
  });
  countries.forEach(([code, name], i) => {
    const y = y0 + 0.4 + i * (cell + gap + 0.12);
    text(s, name, { x: x0, y, w: labelW - 0.12, h: cell, fontSize: 14, align: "right", valign: "middle", bold: code === "TUR" });
    periods.forEach((p, j) => {
      const growth = PANEL.find((r) => r.country === code && r.period === p).growth;
      s.addShape(pres.ShapeType.rect, {
        x: x0 + labelW + j * (cell + gap), y, w: cell, h: cell,
        fill: { color: grayShade(growth) }, line: { color: code === "TUR" ? INK : SOFT, width: code === "TUR" ? 2 : 0.75 },
        objectName: `Cell ${code} ${p}`,
      });
    });
  });
  text(s, "Her kare bir ülke-dönem gözlemi (1973–2023, beş yıllık dönemler). Koyu kare: yüksek büyüme, açık kare: düşük büyüme.",
    { x: x0, y: y0 + 0.45 + 8 * (cell + gap + 0.12), w: labelW + periods.length * (cell + gap), h: 0.65, fontSize: 12, color: MID });
}

// ---------------------------------------------------------------- results
const coef = (model, variable, source = S) => source.coefficients.find((c) => c.model === model && c.variable === variable);
const TESTS = S.tests;
const TUR = S.turkey;
const OLS = "pooled", FE = "fe", RE = "re";
const N = S.data.N, TT = S.data.T, OBS = S.data.observations;

// ================================================================= 1. COVER
{
  pres.addSection({ title: "Giriş" });
  const s = pres.addSlide({ masterName: "COVER", sectionTitle: "Giriş" });
  const label = COVER.course ? `${COVER.course} DERSİ · PANEL VERİ` : "EKONOMETRİ · PANEL VERİ";
  text(s, label.toLocaleUpperCase("tr-TR"), { x: ML, y: 1.35, w: 7, h: 0.35, fontSize: 14, bold: true, color: MID, charSpacing: 4 });
  text(s, "Yoksul ülkeler\narayı kapatıyor mu?", { x: ML, y: 1.85, w: 7.0, h: 2.3, fontFace: HEAD, fontSize: 50, bold: true, color: INK, valign: "top" });
  text(s, `Panel veri ile ${N} ülkede ekonomik büyüme, 1973–2023`, { x: ML, y: 4.15, w: 6.6, h: 0.9, fontSize: 24, color: DARK });
  text(s, "Veri: Penn World Table 11.0 (Ekim 2025)\nHavuzlanmış EKK · Sabit etkiler · Rassal etkiler · Hausman ve Mundlak", { x: ML, y: 5.05, w: 6.6, h: 0.75, fontSize: 15, color: MID });
  if (COVER.authors.length) {
    s.addShape(pres.ShapeType.line, { x: ML, y: 5.95, w: 6.4, h: 0, line: { color: INK, width: 1.25 }, objectName: "Divider" });
    text(s, "HAZIRLAYANLAR", { x: ML, y: 6.07, w: 6.4, h: 0.28, fontSize: 11, bold: true, color: MID, charSpacing: 3 });
    COVER.authors.forEach(([name, id], i) => {
      text(s, name, { x: ML, y: 6.4 + i * 0.4, w: 3.6, h: 0.38, fontSize: 18, bold: true, valign: "middle" });
      text(s, id, { x: ML + 3.6, y: 6.4 + i * 0.4, w: 2.8, h: 0.38, fontSize: 18, color: DARK, valign: "middle" });
    });
  }
  repoLink(s, { y: 0.3 });
  coverGrid(s, 7.5, 0.9);
}

// ================================================================= 2. OUTLINE
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Giriş" });
  slideHeader(s,"Giriş");
  title(s, "Sunum akışı");
  const items = [
    ["Soru ve temel kavramlar", "Türkiye ve Kore örneği, veri tipleri, panel verinin tanımı (slayt 3–6)"],
    ["Modeller ve testler", "Havuzlanmış EKK, sabit ve rassal etkiler; F, LM, Hausman, Mundlak (slayt 7–11)"],
    ["Uygulama", "PWT 11.0 verisi, tahminler ve model seçimi (slayt 12–18)"],
    ["Güncel tartışma", "Yakınsama literatürü ve sabit etkilerin rolü (slayt 19)"],
    ["Eski veri, yeni veri", "1991 verisiyle 2025 verisinin karşılaştırması, T'nin etkisi (slayt 20–21)"],
    ["Türkiye ve sonuç", "Türkiye'nin konumu, sınırlılıklar ve çıkarımlar (slayt 22–25)"],
  ];
  const w = 5.95, h = 1.5, gap = 0.233;
  items.forEach((item, i) => {
    const x = ML + (i % 2) * (w + gap);
    const y = 1.75 + Math.floor(i / 2) * (h + 0.22);
    card(s, x, y, w, h);
    circle(s, x + 0.25, y + 0.38, 0.74, String(i + 1), { size: 24 });
    text(s, item[0], { x: x + 1.2, y: y + 0.2, w: w - 1.4, h: 0.4, fontSize: 20, bold: true });
    text(s, item[1], { x: x + 1.2, y: y + 0.65, w: w - 1.4, h: 0.75, fontSize: 15, color: DARK });
  });
}

// ================================================================= 3. OPENING QUESTION
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Giriş" });
  slideHeader(s,"Giriş");
  title(s, "1973'te Türkiye, Kore'nin iki katı zengindi");
  image(s, FIGURE("01_turkey_korea.png"), ML, 1.6, 7.9, 4.0, "Türkiye, Güney Kore ve Arjantin'de kişi başı gelir, 1960-2023");
  text(s, "Kaynak: Penn World Table 11.0. Kişi başı reel GSYH (rgdpna / nüfus), 2021 fiyatları, logaritmik eksen.", { x: ML, y: 5.7, w: 7.9, h: 0.4, fontSize: 12, color: MID });
  const g = S.intro;
  card(s, 8.75, 1.6, 3.983, 4.5);
  text(s, paragraphs([
    `**1973:** Türkiye ${num(g.TUR_1973, 1)} bin $, Kore ${num(g.KOR_1973, 1)} bin $. Oran ${num(g.TUR_1973 / g.KOR_1973, 1)}.`,
    `**2023:** Kore ${num(g.KOR_2023, 1)} bin $, Türkiye ${num(g.TUR_2023, 1)} bin $. Kore ${num(g.KOR_2023 / g.TUR_2023, 1)} kat önde.`,
    "**Arjantin:** 1960'ta üçünün en zengini; bugün en geride.",
  ], { fontSize: 17 }, { paraSpaceAfter: 16 }), { x: 9.0, y: 1.85, w: 3.5, h: 4.1 });
  card(s, ML, 6.15, CW, 0.75, { fill: INK, line: INK });
  text(s, "**Soru:** Ülkeler neden farklı hızlarda büyüyor ve yoksul ülkeler zenginlere yetişiyor mu?", { x: ML + 0.3, y: 6.15, w: CW - 0.6, h: 0.75, fontSize: 19, color: WHITE, valign: "middle" });
}

// ================================================================= 4. DATA TYPES
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Giriş" });
  slideHeader(s,"Giriş");
  title(s, "Neden panel veri?");
  const cards = [
    ["Yatay kesit verisi", "Tek bir dönemde çok sayıda ülke. Ülkeler arası farkı görürüz; ancak kurum, kültür ve coğrafya gibi gözlenemeyen farkları kontrol edemeyiz.", 5, 1],
    ["Zaman serisi", "Tek bir ülke, çok sayıda dönem. Zaman içindeki değişimi görürüz; ancak gözlem sayısı azdır ve sonuç tek ülkeye özgüdür.", 1, 5],
    ["Panel veri", "Aynı ülkeler, çok sayıda dönem. Hem ülkeler arası hem zaman içi değişim kullanılır ve gözlenemeyen ülke farkları kontrol edilebilir.", 5, 5],
  ];
  const w = 3.9, gap = (CW - 3 * w) / 2;
  cards.forEach(([name, description, nRows, nCols], i) => {
    const x = ML + i * (w + gap), y = 1.65;
    card(s, x, y, w, 4.3);
    const c = 0.2, g = 0.045;
    const gridW = nCols * c + (nCols - 1) * g;
    const x0 = x + (w - gridW) / 2;
    for (let r = 0; r < nRows; r++)
      for (let k = 0; k < nCols; k++)
        s.addShape(pres.ShapeType.rect, { x: x0 + k * (c + g), y: y + 0.3 + r * (c + g), w: c, h: c, fill: { color: i === 2 ? MID : INK }, line: { color: INK, width: 0.75 }, objectName: "Grid cell" });
    text(s, name, { x: x + 0.25, y: y + 1.65, w: w - 0.5, h: 0.45, fontSize: 22, bold: true, fontFace: HEAD });
    text(s, description, { x: x + 0.25, y: y + 2.15, w: w - 0.5, h: 2.0, fontSize: 16, color: DARK });
  });
  card(s, ML, 6.15, CW, 0.75, { fill: WHITE, line: INK });
  text(s, "Türkiye–Kore farkı tek ülkeye bakarak açıklanamaz. Ülkeleri ve yılları birlikte izlemek gerekir: panel veri.", { x: ML + 0.3, y: 6.15, w: CW - 0.6, h: 0.75, fontSize: 17, valign: "middle" });
}

// ================================================================= 5. DEFINITION
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Giriş" });
  slideHeader(s,"Giriş");
  title(s, "Panel veri nedir?");
  card(s, ML, 1.65, 5.9, 5.2);
  text(s, paragraphs([
    "**Tanım:** Aynı N birimin (ülke, firma, birey) T dönem boyunca izlenmesiyle oluşan veridir.",
    "**İndeks:** Her gözlem (i, t) çiftiyle belirlenir: i = 1,…,N birim; t = 1,…,T dönem.",
    "**Dengeli panel:** Her birim tüm dönemlerde gözlenir (N×T gözlem). **Dengesiz panel:** Bazı gözlemler eksiktir.",
    `**Kısa panel:** N büyük, T küçük. Bu uygulamada N = ${N}, T = ${TT}: kısa ve dengeli panel.`,
  ], { fontSize: 18 }, { ...BULLET, paraSpaceAfter: 14 }), { x: ML + 0.3, y: 1.9, w: 5.3, h: 4.8 });

  text(s, "Veri örneği: Türkiye (10 dönem)", { x: 6.75, y: 1.6, w: 5.98, h: 0.4, fontSize: 19, bold: true, fontFace: HEAD });
  const rows = [["Dönem", "Büyüme (%)", "Yatırım (%)", "Nüfus artışı (%)"]];
  TUR.periods.forEach((p) => rows.push([p.period_label, num(p.growth), num(p.investment, 1), num(p.pop_growth)]));
  table(s, rows, { x: 6.75, y: 2.05, w: 5.98, colW: [1.4, 1.5, 1.5, 1.58], rowH: [0.42, ...Array(10).fill(0.34)], fontSize: 13, align: ["left", "center", "center", "center"], cellMargin: [0.02, 0.1, 0.02, 0.1] });
  text(s, `Uygulamadaki panelde ${N} ülke × ${TT} dönem = ${thousands(OBS)} satır bulunur.`, { x: 6.75, y: 6.35, w: 5.98, h: 0.45, fontSize: 14, color: MID });
}

// ================================================================= 6. ADVANTAGES / CAVEATS
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Giriş" });
  slideHeader(s,"Giriş");
  title(s, "Avantajlar ve dikkat edilecekler");
  const w = 5.95, y = 1.65, h = 5.2;
  card(s, ML, y, w, h);
  card(s, ML + w + 0.233, y, w, h);
  circle(s, ML + 0.3, y + 0.28, 0.6, "+", { size: 26 });
  text(s, "Avantajlar", { x: ML + 1.1, y: y + 0.28, w: 4, h: 0.6, fontSize: 24, bold: true, fontFace: HEAD, valign: "middle" });
  text(s, paragraphs([
    "Gözlenemeyen ülke farklarını (kurum, kültür, coğrafya) kontrol edebiliriz.",
    "N×T gözlem; hem ülkeler arası farkları hem de ülke içi değişimi inceleyebiliriz.",
    "Daha fazla değişkenlik, daha az çoklu doğrusal bağlantı ve daha kesin tahmin.",
    "Zaman içi değişimle dinamik süreçler incelenebilir.",
  ], { fontSize: 19 }, { ...BULLET, paraSpaceAfter: 14 }), { x: ML + 0.3, y: y + 1.15, w: w - 0.6, h: 3.9 });
  const x2 = ML + w + 0.233;
  circle(s, x2 + 0.3, y + 0.28, 0.6, "!", { size: 26, fill: WHITE, color: INK });
  text(s, "Dikkat edilecekler", { x: x2 + 1.1, y: y + 0.28, w: 4.6, h: 0.6, fontSize: 24, bold: true, fontFace: HEAD, valign: "middle" });
  text(s, paragraphs([
    "Aynı ülkenin hataları dönemler arasında ilişkili olabilir (seri korelasyon).",
    "Hata varyansı ülkeden ülkeye değişebilir (değişen varyans).",
    "Ülkeler ortak şoklardan etkilenebilir: 2008 krizi, pandemi (yatay kesit bağımlılığı).",
    "Dengesiz panelde birimlerin seçilerek kaybolması yanlılık yaratabilir.",
  ], { fontSize: 19 }, { ...BULLET, paraSpaceAfter: 14 }), { x: x2 + 0.3, y: y + 1.15, w: w - 0.6, h: 3.9 });
}

// ================================================================= 7. BASIC MODEL
{
  pres.addSection({ title: "Kuram" });
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Kuram" });
  slideHeader(s,"Kuram");
  title(s, "Temel panel modeli");
  card(s, ML, 1.65, CW, 1.35, { fill: WHITE, line: INK });
  text(s, runs("y_{it} = α + x_{it}′β + μ_{i} + ε_{it}", { fontFace: HEAD, fontSize: 38, bold: true, color: INK }), { x: ML, y: 1.65, w: CW, h: 1.35, align: "center", valign: "middle" });
  const terms = [
    ["y_{it}", "Bağımlı değişken", "i. ülkenin t. dönemdeki kişi başı gelir büyümesi."],
    ["x_{it}", "Açıklayıcı değişkenler", "Başlangıç geliri, yatırım oranı, nüfus artışı, beşeri sermaye."],
    ["μ_{i}", "Ülkeye özgü etki", "Zamanla değişmeyen, gözlenemeyen ülke özellikleri (kurum, kültür, coğrafya)."],
    ["ε_{it}", "İdiyosinkratik hata", "Hem ülkeye hem döneme özgü, tahmin edilemeyen şoklar."],
  ];
  const w = 2.89, gap = (CW - 4 * w) / 3;
  terms.forEach(([symbol, name, description], i) => {
    const x = ML + i * (w + gap), y = 3.25;
    card(s, x, y, w, 2.45);
    text(s, runs(symbol, { fontFace: HEAD, fontSize: 30, bold: true, color: INK }), { x: x + 0.2, y: y + 0.12, w: w - 0.4, h: 0.65, valign: "middle" });
    text(s, name, { x: x + 0.2, y: y + 0.8, w: w - 0.4, h: 0.4, fontSize: 17, bold: true });
    text(s, description, { x: x + 0.2, y: y + 1.22, w: w - 0.4, h: 1.15, fontSize: 15, color: DARK });
  });
  card(s, ML, 5.9, CW, 0.95, { fill: INK, line: INK });
  text(s, "Üç tahmin edicinin farkı, μ_{i} ile ne yapıldığından doğar: yok saymak, ülke başına sabit parametre saymak ya da rassal bir değişken saymak.", { x: ML + 0.3, y: 5.9, w: CW - 0.6, h: 0.95, fontSize: 18, color: WHITE, valign: "middle" });
}

// ================================================================= 8. THREE ESTIMATORS
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Kuram" });
  slideHeader(s,"Kuram");
  title(s, "Üç temel tahmin edici");
  table(s, [
    ["", "Havuzlanmış EKK", "Sabit Etkiler (FE)", "Rassal Etkiler (RE)"],
    ["μ_{i} nasıl ele alınır?", "Yok sayılır; tüm ülkeler aynı kesişimi paylaşır.", "Her ülke için ayrı bir sabit parametre.", "Rassal değişken; hata teriminin parçasıdır."],
    ["Temel varsayım", "μ_{i} = 0 ya da açıklayıcılarla ilişkisiz.", "μ_{i} açıklayıcılarla ilişkili olabilir.", "μ_{i} açıklayıcılarla ilişkisizdir."],
    ["Yöntem", "Tüm gözlemlere EKK uygulanır.", "İçi (within) dönüşüm: ülke ortalamalarından sapmalar.", "Genelleştirilmiş EKK (GLS): kısmi ortalama çıkarma."],
    ["Güçlü yanı", "Basit; zamanla sabit değişkenler tahmin edilir.", "Ülke etkisiyle ilişkiye izin verir.", "Verimlidir; zamanla sabit değişkenler tahmin edilir."],
    ["Sınırlaması", "μ_{i} ilişkiliyse tutarsızdır.", "Zamanla sabit değişkenler (ör. denize kıyısı olmamak) tahmin edilemez.", "μ_{i} ilişkiliyse tutarsızdır."],
  ], { x: ML, y: 1.65, w: CW, colW: [2.0, 3.35, 3.45, 3.333], rowH: [0.6, 0.9, 0.9, 0.95, 0.95, 0.95], fontSize: 15, boldFirstColumn: true });
}

// ================================================================= 9. MODEL SELECTION
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Kuram" });
  slideHeader(s,"Kuram");
  title(s, "Model seçimi: hangi test neyi sınar?");
  const steps = [
    ["1", "F testi", "Havuzlanmış EKK ↔ Sabit etkiler", "H₀: Tüm ülke etkileri eşit.", "H₀ reddedilirse ülke etkileri vardır; havuzlanmış EKK yetersizdir."],
    ["2", "Breusch–Pagan LM", "Havuzlanmış EKK ↔ Rassal etkiler", "H₀: Var(μᵢ) = 0.", "H₀ reddedilirse ülkeye özgü bir varyans bileşeni vardır."],
    ["3", "Hausman testi", "Sabit etkiler ↔ Rassal etkiler", "H₀: μᵢ açıklayıcılarla ilişkisiz (RE tutarlı ve verimli).", "H₀ reddedilirse sabit etkiler tercih edilir."],
  ];
  const w = 3.7, gap = (CW - 3 * w) / 2;
  steps.forEach(([no, name, comparison, h0, decision], i) => {
    const x = ML + i * (w + gap), y = 1.65;
    card(s, x, y, w, 4.2);
    circle(s, x + 0.25, y + 0.25, 0.6, no, { size: 22 });
    text(s, name, { x: x + 1.05, y: y + 0.25, w: w - 1.2, h: 0.6, fontSize: 20, bold: true, fontFace: HEAD, valign: "middle" });
    text(s, comparison, { x: x + 0.25, y: y + 1.05, w: w - 0.5, h: 0.65, fontSize: 16, bold: true });
    text(s, h0, { x: x + 0.25, y: y + 1.75, w: w - 0.5, h: 0.95, fontSize: 16 });
    text(s, decision, { x: x + 0.25, y: y + 2.75, w: w - 0.5, h: 1.3, fontSize: 16, color: DARK });
    if (i < 2) {
      s.addShape(pres.ShapeType.rightArrow, { x: x + w + 0.07, y: y + 1.9, w: gap - 0.14, h: 0.4, fill: { color: INK }, line: { color: INK, width: 1 }, objectName: "Arrow" });
    }
  });
  card(s, ML, 6.05, CW, 0.8, { fill: WHITE, line: INK });
  text(s, "**Mundlak:** Açıklayıcıların ülke ortalamaları RE modeline eklenir. Katsayılar sıfırdan farklıysa RE varsayımı çöker. Kümelenmiş standart hatayla da çalışır.", { x: ML + 0.25, y: 6.05, w: CW - 0.5, h: 0.8, fontSize: 15, valign: "middle" });
}

// ================================================================= 10. ASSUMPTION TESTS
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Kuram" });
  slideHeader(s,"Kuram");
  title(s, "Varsayım testleri ve önlemler");
  table(s, [
    ["Test", "Sıfır hipotezi", "Tespit edilen sorun", "Önlem"],
    ["Wooldridge", "Birinci derece seri korelasyon yoktur.", "Hatalar dönemler arasında ilişkilidir; standart hatalar yanıltıcıdır.", "Ülke düzeyinde kümelenmiş standart hata."],
    ["Değiştirilmiş Wald (Greene)", "Tüm ülkelerde hata varyansı eşittir.", "Gruplara göre değişen varyans.", "Robust ya da kümelenmiş standart hata."],
    ["Pesaran CD", "Ülkeler arasında hata korelasyonu yoktur.", "Yatay kesit bağımlılığı (ortak şoklar).", "Ortak şoklar için dönem etkileri; kalan bağımlılığı ayrıca incele."],
  ], { x: ML, y: 1.65, w: CW, colW: [2.4, 3.2, 3.5, 3.033], rowH: [0.6, 1.1, 1.1, 1.1], fontSize: 15, boldFirstColumn: true });
  card(s, ML, 5.85, CW, 1.0, { fill: INK, line: INK });
  text(s, "Uygulamada tüm standart hatalar ülke düzeyinde kümelendi. Dönem kuklaları 2008 krizi ve pandemi gibi ortak şokları yakalar.", { x: ML + 0.3, y: 5.85, w: CW - 0.6, h: 1.0, fontSize: 17, color: WHITE, valign: "middle" });
}

// ================================================================= 11. DYNAMIC PANELS
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Kuram" });
  slideHeader(s,"Kuram");
  title(s, "Dinamik paneller (kısaca)");
  card(s, ML, 1.65, CW, 1.2, { fill: WHITE, line: INK });
  text(s, runs("y_{it} = ρ y_{i,t−1} + x_{it}′β + μ_{i} + ε_{it}", { fontFace: HEAD, fontSize: 34, bold: true, color: INK }), { x: ML, y: 1.65, w: CW, h: 1.2, align: "center", valign: "middle" });
  const boxes = [
    ["Sorun: Nickell yanlılığı", "Sabit etkiler dönüşümünde gecikmeli bağımlı değişken hata ile ilişkili hale gelir. Yanlılık yaklaşık 1/T mertebesindedir."],
    ["Çözüm: GMM", "Fark GMM (Arellano–Bond) gecikmeli düzeyleri araç olarak kullanır. Sistem GMM (Blundell–Bond) düzey denklemini de ekler."],
    ["Kontroller", "AR(2) testi fark artıklarını, Sargan/Hansen araç kısıtlarını sınar. Araç sayısını sınırlı tutmak gerekir."],
  ];
  const w = 3.9, gap = (CW - 3 * w) / 2;
  boxes.forEach(([name, description], i) => {
    const x = ML + i * (w + gap), y = 3.1;
    card(s, x, y, w, 2.75);
    text(s, name, { x: x + 0.25, y: y + 0.2, w: w - 0.5, h: 0.5, fontSize: 21, bold: true, fontFace: HEAD });
    text(s, description, { x: x + 0.25, y: y + 0.8, w: w - 0.5, h: 1.8, fontSize: 17, color: DARK });
  });
  card(s, ML, 6.05, CW, 0.8, { fill: WHITE, line: INK });
  text(s, "Bizim modelde başlangıç geliri gecikmeli bağımlı değişken gibi davranır. Bu yüzden T'nin etkisine slayt 21'de ayrıca bakıyoruz.", { x: ML + 0.25, y: 6.05, w: CW - 0.5, h: 0.8, fontSize: 16, valign: "middle" });
}

// ================================================================= 12. DATA AND MODEL
{
  pres.addSection({ title: "Uygulama" });
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Uygulama" });
  slideHeader(s,"Uygulama");
  title(s, "Veri ve model");
  card(s, ML, 1.65, 5.2, 3.75);
  text(s, paragraphs([
    "**Kaynak:** Penn World Table 11.0 (Feenstra, Inklaar ve Timmer; Ekim 2025).",
    `**Kapsam:** 1973–2023 tüm yıllarda verisi olan ${N} ülke; on adet beş yıllık dönem.`,
    `**Yapı:** N = ${N}, T = ${TT}, ${thousands(OBS)} gözlem; dengeli panel.`,
  ], { fontSize: 17 }, { ...BULLET, paraSpaceAfter: 12 }), { x: ML + 0.25, y: 1.85, w: 4.7, h: 3.4 });

  const d = S.descriptives;
  const meanSd = (v, digits = 2) => `${num(d[v].mean, digits)} (${num(d[v].std, digits)})`;
  const landlocked = new Set(PANEL.filter((r) => r.landlocked === 1).map((r) => r.country)).size;
  table(s, [
    ["Değişken", "Tanım", "Ort. (Std. s.)"],
    ["Büyüme", "Kişi başı reel GSYH'nin yıllık ortalama log büyümesi (%)", meanSd("growth")],
    ["ln(Başl. GSYH)", "Dönem başı kişi başı reel GSYH'nin logu", meanSd("ln_gdp0")],
    ["Yatırım", "Yatırımın GSYH payı, dönem ortalaması (%)", meanSd("investment", 1)],
    ["Nüfus artışı", "Nüfusun yıllık ortalama log artışı (%)", meanSd("pop_growth")],
    ["ln(Beşeri sermaye)", "Dönem başı beşeri sermaye endeksinin logu (eğitim yılı ve getirisi)", meanSd("ln_hc0")],
    ["Denize kıyısız", "Zamanla sabit 0/1 gösterge", `${landlocked} ülke`],
  ], { x: 6.0, y: 1.65, w: 6.733, colW: [1.75, 3.4, 1.583], rowH: [0.45, 0.6, 0.5, 0.5, 0.5, 0.65, 0.45], fontSize: 13, boldFirstColumn: true });

  card(s, ML, 5.6, CW, 1.25, { fill: INK, line: INK });
  text(s, runs("Büyüme_{it} = β_{1} ln(GSYH_{0})_{it} + β_{2} Yatırım_{it} + β_{3} Nüfus_{it} + β_{4} ln(Beşeri s.)_{it} + γ Kıyısız_{i} + dönem etkileri + μ_{i} + ε_{it}", { fontFace: HEAD, fontSize: 17, bold: true, color: WHITE }), { x: ML + 0.3, y: 5.6, w: CW - 0.6, h: 1.25, align: "center", valign: "middle" });
}

// ================================================================= 13. PANEL STRUCTURE
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Uygulama" });
  slideHeader(s,"Uygulama");
  title(s, "Panel yapısı: ülkeler ve dönemler");
  image(s, FIGURE("02_panel_structure.png"), ML, 1.65, 7.8, 4.2, "Seçili ülkelerin on dönemlik büyüme serileri");
  text(s, "Gri çizgiler: ABD, Güney Kore, Çin, Brezilya, Mısır, Hindistan, İtalya, Meksika, Nijerya, İspanya, Yunanistan, Polonya, Arjantin.", { x: ML, y: 5.95, w: 7.8, h: 0.9, fontSize: 13, color: MID });
  const m = S.period_mean_growth;
  card(s, 8.6, 1.65, 4.133, 5.2);
  text(s, paragraphs([
    "Her çizgi bir ülkenin on dönemlik büyüme serisidir.",
    `Ortalama büyüme 1978–83'te %${num(m["1978"], 1)} ile en düşük, 2003–08'de %${num(m["2003"], 1)} ile en yüksek.`,
    `Pandemiyi içeren 2018–23 döneminde ortalama %${num(m["2018"], 1)}.`,
    "Bu ortak dalgalanmaları dönem etkileri (zaman kuklaları) kontrol eder.",
  ], { fontSize: 17 }, { ...BULLET, paraSpaceAfter: 13 }), { x: 8.85, y: 1.9, w: 3.65, h: 4.8 });
}

// ================================================================= 14. POOLED vs WITHIN
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Uygulama" });
  slideHeader(s,"Uygulama");
  title(s, "Aynı veri, iki farklı cevap");
  image(s, FIGURE("03_pooled_vs_within.png"), ML, 1.65, 8.2, 3.45, "Havuzlanmış veri ile ülke içi sapmaların karşılaştırması");
  const b = S.bivariate_slopes;
  card(s, ML, 5.3, 8.2, 1.55, { fill: INK, line: INK });
  text(s, `Yalnızca başlangıç geliriyle: havuzlanmış eğim ${num(b.pooled)}, ülke ortalamaları çıkarıldığında ${num(b.within)}. Ülke içi ilişki yaklaşık ${Math.round(b.within / b.pooled)} kat güçlü.`, { x: ML + 0.3, y: 5.3, w: 7.6, h: 1.55, fontSize: 18, color: WHITE, valign: "middle" });
  card(s, 9.0, 1.65, 3.733, 5.2);
  text(s, paragraphs([
    "Sol: tüm ülke-dönem gözlemleri. Zengin ve yoksul ülkeler karışık; ilişki neredeyse düz.",
    "Sağ: her ülke kendi ortalamasıyla kıyaslanıyor. Bir ülke kendi ortalamasından zenginleştikçe yavaşlıyor.",
    `Ülke ortalamalarıyla yapılan regresyonun eğimi ${num(b.between)}.`,
  ], { fontSize: 16 }, { ...BULLET, paraSpaceAfter: 12 }), { x: 9.2, y: 1.85, w: 3.35, h: 4.9 });
}

// ================================================================= 15. ESTIMATION RESULTS
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Uygulama" });
  slideHeader(s,"Uygulama");
  title(s, "Tahmin sonuçları");
  const cell = (model, variable) => {
    const c = coef(model, variable);
    if (!c) return "—";
    return [
      { text: num(c.estimate, 3) + stars(c.p), options: { bold: true, breakLine: true } },
      { text: `(${num(c.std_error, 3)})`, options: {} },
    ];
  };
  const variables = [["ln_gdp0", "ln(Başlangıç GSYH)"], ["investment", "Yatırım oranı"], ["pop_growth", "Nüfus artışı"], ["ln_hc0", "ln(Beşeri sermaye)"], ["landlocked", "Denize kıyısız"]];
  const rows = [["Bağımlı değişken: büyüme (%)", "Havuzlanmış EKK", "Sabit Etkiler", "Rassal Etkiler"]];
  variables.forEach(([v, label]) => rows.push([label, cell(OLS, v), cell(FE, v), cell(RE, v)]));
  const fit = Object.fromEntries(S.fit.map((x) => [x.model, x]));
  rows.push(["Dönem etkileri", "Evet", "Evet", "Evet"]);
  rows.push(["Gözlem / ülke sayısı", ...Array(3).fill(`${thousands(OBS)} / ${N}`)]);
  rows.push(["R² (ülke içi)", num(fit[OLS].r2_within, 3), num(fit[FE].r2_within, 3), num(fit[RE].r2_within, 3)]);
  table(s, rows, {
    x: ML, y: 1.6, w: CW, colW: [3.8, 2.78, 2.78, 2.773],
    rowH: [0.5, 0.62, 0.62, 0.62, 0.62, 0.62, 0.4, 0.4, 0.4], fontSize: 14, boldFirstColumn: true, align: ["left", "center", "center", "center"],
    cellMargin: [0.03, 0.1, 0.03, 0.1],
  });
  text(s, [{ text: "Parantez içi: ülke düzeyinde kümelenmiş standart hata.  *** p < 0,01   ** p < 0,05   * p < 0,10.  Denize kıyısız göstergesi zamanla sabit olduğundan sabit etkiler modelinde tahmin edilemez (—).", options: { fontFace: BODY, fontSize: 12, color: MID } }], { x: ML, y: 6.5, w: CW, h: 0.5 });
}

// ================================================================= 16. COEFFICIENT PLOT
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Uygulama" });
  slideHeader(s,"Uygulama");
  title(s, "Katsayılar ve yorum");
  image(s, FIGURE("05_coefficients.png"), ML, 1.6, CW, 3.55, "Üç modelin katsayı tahminleri ve güven aralıkları");
  const est = (model, variable) => coef(model, variable).estimate;
  const speed = S.convergence_speed;
  const cards = [
    ["Başlangıç geliri", `FE'de ${num(est(FE, "ln_gdp0"))}: yılda %${num(speed.fe.lambda * 100, 1)} yakınsama, yarılanma ${Math.round(speed.fe.half_life)} yıl. Havuzlanmış EKK'de ${Math.round(speed.pooled.half_life)} yıl.`],
    ["Yatırım oranı", `Yatırım oranı 10 puan yüksek olan dönemde yıllık büyüme ${num(10 * est(FE, "investment"), 1)} puan yüksek (FE, p < 0,01). Üç modelde de anlamlı.`],
    ["Nüfus ve beşeri sermaye", "Nüfus yalnızca EKK'de, beşeri sermaye yalnızca RE'de anlamlı (%5). FE'de ikisi de sıfıra yakın: ülke içinde yavaş değişip ülke etkisine karışıyorlar."],
  ];
  const w = 3.9, gap = (CW - 3 * w) / 2;
  cards.forEach(([name, description], i) => {
    const x = ML + i * (w + gap), y = 5.3;
    card(s, x, y, w, 1.6);
    text(s, name, { x: x + 0.2, y: y + 0.1, w: w - 0.4, h: 0.35, fontSize: 17, bold: true, fontFace: HEAD });
    text(s, description, { x: x + 0.2, y: y + 0.5, w: w - 0.4, h: 1.05, fontSize: 14, color: DARK });
  });
}

// ================================================================= 17. MODEL SELECTION RESULTS
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Uygulama" });
  slideHeader(s,"Uygulama");
  title(s, "Model seçimi testleri");
  const F = TESTS.f_poolability, BP = TESTS.breusch_pagan_lm, H = TESTS.hausman, M = TESTS.mundlak;
  table(s, [
    ["Test", "Sıfır hipotezi", "İstatistik", "p-değeri", "Karar"],
    ["F", "Tüm ülke etkileri eşit", `F(${F.df[0]}; ${thousands(F.df[1])}) = ${num(F.statistic)}`, pValue(F.p), "H₀ reddedilir: ülke etkileri var."],
    ["Breusch–Pagan LM", "Var(μ_{i}) = 0", `χ²(${BP.df}) = ${num(BP.statistic)}`, pValue(BP.p), "H₀ reddedilir: RE, havuzlanmış EKK'den iyi."],
    ["Hausman", "Ülke etkileri açıklayıcılarla ilişkisiz", `χ²(${H.df}) = ${num(H.statistic)}`, pValue(H.p), "H₀ reddedilir: FE tercih edilir."],
    ["Mundlak (kümelenmiş)", "Ülke ortalamalarının katsayıları sıfır", `χ²(${M.df}) = ${num(M.statistic)}`, pValue(M.p), "H₀ reddedilir: Hausman ile aynı sonuç."],
  ], { x: ML, y: 1.65, w: CW, colW: [2.5, 3.0, 2.35, 1.2, 3.083], rowH: [0.55, 0.85, 0.85, 0.85, 0.85], fontSize: 15, boldFirstColumn: true, align: ["left", "left", "center", "center", "left"] });
  card(s, ML, 5.85, CW, 1.0, { fill: INK, line: INK });
  text(s, "**Sonuç:** F → ülke etkileri var. Hausman ve Mundlak → bu etkiler açıklayıcılarla ilişkili. Yorumu sabit etkiler (FE) modeline dayandırıyoruz.", { x: ML + 0.3, y: 5.85, w: CW - 0.6, h: 1.0, fontSize: 17, color: WHITE, valign: "middle" });
}

// ================================================================= 18. ASSUMPTION TEST RESULTS
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Uygulama" });
  slideHeader(s,"Uygulama");
  title(s, "Varsayım testi sonuçları");
  const W = TESTS.wooldridge, MW = TESTS.modified_wald, P = TESTS.pesaran_cd;
  table(s, [
    ["Test", "İstatistik", "p-değeri", "Bulgu"],
    ["Wooldridge (seri korelasyon)", `F(${W.df[0]}; ${W.df[1]}) = ${num(W.statistic)}`, pValue(W.p), "Seri korelasyon yok hipotezi reddedilir."],
    ["Değiştirilmiş Wald (değişen varyans)", `χ²(${MW.df}) = ${thousands(MW.statistic)}`, pValue(MW.p), "Eşit varyans hipotezi reddedilir."],
    ["Pesaran CD (yatay kesit)", `CD = ${num(P.statistic)}`, pValue(P.p), "Dönem etkilerinden sonra kalan bağımlılık anlamlı değil."],
  ], { x: ML, y: 1.65, w: CW, colW: [3.6, 2.6, 1.4, 4.533], rowH: [0.55, 0.7, 0.7, 0.7], fontSize: 15, boldFirstColumn: true, align: ["left", "center", "center", "left"] });

  const se = S.standard_error_comparison;
  const ratio = Object.values(se).map((v) => v.clustered / v.conventional - 1);
  const labels = { ln_gdp0: "ln(Başl. GSYH)", investment: "Yatırım oranı", pop_growth: "Nüfus artışı", ln_hc0: "ln(Beşeri sermaye)" };
  table(s, [
    ["Sabit etkiler", "Klasik SH", "Kümelenmiş SH"],
    ...Object.entries(se).map(([v, x]) => [labels[v], num(x.conventional, 3), num(x.clustered, 3)]),
  ], { x: ML, y: 4.45, w: 6.0, colW: [2.4, 1.7, 1.9], rowH: [0.45, 0.45, 0.45, 0.45, 0.45], fontSize: 15, boldFirstColumn: true, align: ["left", "center", "center"] });
  card(s, 6.85, 4.45, 5.883, 2.25, { fill: INK, line: INK });
  text(s, `Kümelenmiş standart hatalar klasik olanlardan %${Math.round(Math.min(...ratio) * 100)}–%${Math.round(Math.max(...ratio) * 100)} daha büyük. Klasik hatalarla yapılan çıkarım fazla iyimser olurdu.`, { x: 7.1, y: 4.45, w: 5.4, h: 2.25, fontSize: 17, color: WHITE, valign: "middle" });
}

// ================================================================= 19. CURRENT DEBATE
{
  pres.addSection({ title: "Güncel tartışma" });
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Güncel tartışma" });
  slideHeader(s,"Güncel tartışma");
  title(s, "Yakınsamaya doğru mu gidiyoruz?");
  image(s, FIGURE("04_convergence.png"), ML, 1.6, 7.9, 3.75, "Her dönem için ayrı yatay kesit regresyonunun eğimi");
  const cs = S.cross_section_slopes;
  card(s, ML, 5.5, 7.9, 1.4, { fill: WHITE, line: INK });
  text(s, `Eski veride (1960–85) her dönemde eğim pozitif: zenginler daha hızlı büyüyor. Yeni veride 2008–13 döneminde eğim ${num(cs["2008"])}: yoksullar daha hızlı. 2018–23'te yeniden ${signed(cs["2018"])}.`, { x: ML + 0.25, y: 5.5, w: 7.4, h: 1.4, fontSize: 15, valign: "middle" });
  card(s, 8.75, 1.6, 3.983, 5.3);
  text(s, paragraphs([
    "**Kremer, Willis ve You (2022):** 1990'lardan bu yana koşulsuz yakınsamaya doğru bir eğilim var.",
    "**Acemoglu ve Molina (2022):** Ülke sabit etkileri konmadan bu eğimler sıfıra doğru yanlı. Sabit etkili modelde yakınsama hep vardı.",
    "**Bizim sonuç:** havuzlanmış eğim küçük, ülke içi eğim belirgin şekilde negatif (slayt 14). Panel verinin farkı tam da burada.",
  ], { fontSize: 15 }, { paraSpaceAfter: 14 }), { x: 8.95, y: 1.8, w: 3.6, h: 5.0 });
}

// ================================================================= 20. OLD DATA / NEW DATA
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Güncel tartışma" });
  slideHeader(s,"Güncel tartışma");
  title(s, "1991 verisi ile 2025 verisi aynı şeyi söylüyor mu?");
  const cell = (model, variable, source) => {
    const c = coef(model, variable, source);
    return c ? num(c.estimate, 3) + stars(c.p) : "—";
  };
  table(s, [
    ["", "Havuzlanmış EKK\nPWT 5, 1960–85", "Havuzlanmış EKK\nPWT 11, 1973–2023", "Sabit Etkiler\nPWT 5, 1960–85", "Sabit Etkiler\nPWT 11, 1973–2023"],
    ["ln(Başlangıç GSYH)", cell(OLS, "ln_gdp0", K), cell(OLS, "ln_gdp0", S), cell(FE, "ln_gdp0", K), cell(FE, "ln_gdp0", S)],
    ["Yatırım / tasarruf oranı", cell(OLS, "investment", K), cell(OLS, "investment", S), cell(FE, "investment", K), cell(FE, "investment", S)],
    ["Nüfus artışı", cell(OLS, "pop_growth", K), cell(OLS, "pop_growth", S), cell(FE, "pop_growth", K), cell(FE, "pop_growth", S)],
    ["N × T", `${K.data.N} × ${K.data.T}`, `${N} × ${TT}`, `${K.data.N} × ${K.data.T}`, `${N} × ${TT}`],
    ["Hausman", "", "", `χ²(${K.tests.hausman.df}) = ${num(K.tests.hausman.statistic, 1)}`, `χ²(${TESTS.hausman.df}) = ${num(TESTS.hausman.statistic, 1)}`],
  ], { x: ML, y: 1.6, w: CW, colW: [2.9, 2.3, 2.3, 2.3, 2.333], rowH: [0.75, 0.55, 0.55, 0.55, 0.5, 0.5], fontSize: 15, boldFirstColumn: true, align: ["left", "center", "center", "center", "center"] });
  text(s, "PWT 5'te tasarruf oranı, PWT 11'de yatırımın GSYH payı kullanıldı. Yeni modelde ayrıca beşeri sermaye ve denize kıyısız göstergesi var; tablo yalnızca ortak değişkenleri gösterir.", { x: ML, y: 5.1, w: CW, h: 0.5, fontSize: 12, color: MID });
  const cards = [
    ["Değişmeyen", "İşaretler aynı: başlangıç geliri negatif, yatırım pozitif. Her iki veride de Hausman FE'yi seçiyor."],
    ["Değişen", `FE yakınsama katsayısı eski veride ${num(coef(FE, "ln_gdp0", K).estimate)}, yeni veride ${num(coef(FE, "ln_gdp0").estimate)}. Nüfus artışının FE etkisi kayboldu.`],
    ["Neden?", "Yeni dönem, yeni ülke kümesi, revize edilmiş veri ve daha uzun panel (T = 5 yerine 10). Son etkiyi bir sonraki slaytta ayırıyoruz."],
  ];
  const w = 3.9, gap = (CW - 3 * w) / 2;
  cards.forEach(([name, description], i) => {
    const x = ML + i * (w + gap), y = 5.65;
    card(s, x, y, w, 1.25);
    text(s, name, { x: x + 0.2, y: y + 0.08, w: w - 0.4, h: 0.35, fontSize: 16, bold: true, fontFace: HEAD });
    text(s, description, { x: x + 0.2, y: y + 0.43, w: w - 0.4, h: 0.8, fontSize: 13, color: DARK });
  });
}

// ================================================================= 21. PANEL LENGTH
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Güncel tartışma" });
  slideHeader(s,"Güncel tartışma");
  title(s, "Panel uzadıkça ne değişiyor?");
  image(s, FIGURE("06_panel_length.png"), ML, 1.6, 7.9, 4.0, "Sabit etkiler katsayısının panel uzunluğuna göre değişimi");
  const effect = S.panel_length_effect;
  const first = effect[0], last = effect[effect.length - 1];
  card(s, 8.75, 1.6, 3.983, 5.3);
  text(s, paragraphs([
    `Aynı ${N} ülke; panel 1973'ten başlayıp her adımda bir dönem uzatılıyor.`,
    `T = ${first.T} iken FE katsayısı ${num(first.estimate)}, T = ${last.T} iken ${num(last.estimate)}.`,
    "Nickell yanlılığı 1/T ile küçülür; katsayının sıfıra doğru gelmesi bununla uyumlu.",
    "Ancak her adımda yeni yıllar da ekleniyor. Bu grafik yanlılığın kanıtı değil, işareti.",
  ], { fontSize: 16 }, { ...BULLET, paraSpaceAfter: 12 }), { x: 8.95, y: 1.8, w: 3.6, h: 5.0 });
  card(s, ML, 5.75, 7.9, 1.15, { fill: INK, line: INK });
  text(s, "Uzun panel, kısa panele göre daha güvenilir bir sabit etkiler tahmini verir. Kesin çözüm için GMM tahmini gerekir.", { x: ML + 0.3, y: 5.75, w: 7.3, h: 1.15, fontSize: 16, color: WHITE, valign: "middle" });
}

// ================================================================= 22. TURKEY
{
  pres.addSection({ title: "Türkiye ve sonuç" });
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Türkiye ve sonuç" });
  slideHeader(s,"Türkiye");
  title(s, "Türkiye: gerçekleşen büyüme ve model");
  image(s, FIGURE("07_turkey.png"), ML, 1.6, 8.0, 3.85, "Türkiye için gerçekleşen büyüme ve sabit etkiler modelinin uyum değeri");
  const rows = [["Dönem", ...TUR.periods.map((p) => p.period_label.slice(2))], ["Fark (puan)", ...TUR.periods.map((p) => signed(p.residual, 1))]];
  table(s, rows, { x: ML, y: 5.6, w: 8.0, colW: [1.3, ...Array(10).fill(0.67)], rowH: [0.5, 0.55], fontSize: 12, boldFirstColumn: true, align: ["left", ...Array(10).fill("center")], cellMargin: [0.02, 0.03, 0.02, 0.05] });
  text(s, "Fark: gerçekleşen büyüme − model değeri.", { x: ML, y: 6.68, w: 8.0, h: 0.3, fontSize: 11, color: MID });
  const byPeriod = (p) => TUR.periods.find((x) => x.period === p);
  const p78 = byPeriod(1978), p98 = byPeriod(1998), p18 = byPeriod(2018);
  card(s, 8.85, 1.6, 3.883, 5.3);
  text(s, paragraphs([
    `1973–2023 ortalama büyüme: Türkiye %${num(TUR.mean_growth)}, ${N} ülke %${num(TUR.sample_mean_growth)}.`,
    `Ülke sabit etkisinde Türkiye ${N} ülke içinde ${TUR.fixed_effect_rank}. sırada.`,
    `Kriz dönemlerinde büyüme modelin altında kalıyor: 1978–83 (${signed(p78.residual, 1)}) ve 1998–03 (${signed(p98.residual, 1)}).`,
    `2018–23'te büyüme modelin ${num(p18.residual, 1)} puan üzerinde. Yatırımın düşmesi ve pandemi, modelde daha düşük büyüme öngörüyor.`,
  ], { fontSize: 15 }, { ...BULLET, paraSpaceAfter: 11 }), { x: 9.05, y: 1.8, w: 3.5, h: 5.0 });
}

// ================================================================= 23. LIMITATIONS
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Türkiye ve sonuç" });
  slideHeader(s,"Sonuç");
  title(s, "Sınırlılıklar ve dikkat noktaları");
  const boxes = [
    ["Dinamik yapı", `Başlangıç geliri gecikmeli bağımlı değişken gibi davranır. T = ${TT} ile Nickell yanlılığı azalır ama sıfırlanmaz; GMM bir sonraki adım olabilir.`],
    ["Örneklem", `Dengeli panel için 1973'ten beri verisi olan ${N} ülke alındı. Eski Sovyet ülkeleri gibi 1990 sonrası verisi başlayanlar dışarıda.`],
    ["Ölçüm hatası", "Başlangıç gelirindeki ölçüm hatası hem açıklayıcıya hem büyüme hesabına girer. PWT sürümleri arasında da revizyonlar var."],
    ["Nedensellik", "Katsayılar koşullu ilişkileri gösterir. Yatırım büyümeyi etkilediği kadar büyümeden de etkilenir (ters nedensellik)."],
  ];
  const w = 5.95, h = 2.5, gap = 0.233;
  boxes.forEach(([name, description], i) => {
    const x = ML + (i % 2) * (w + gap), y = 1.65 + Math.floor(i / 2) * (h + 0.2);
    card(s, x, y, w, h);
    circle(s, x + 0.25, y + 0.25, 0.55, String(i + 1), { size: 20 });
    text(s, name, { x: x + 1.0, y: y + 0.25, w: w - 1.2, h: 0.55, fontSize: 21, bold: true, fontFace: HEAD, valign: "middle" });
    text(s, description, { x: x + 0.3, y: y + 0.95, w: w - 0.6, h: 1.45, fontSize: 17, color: DARK });
  });
}

// ================================================================= 24. CONCLUSION
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Türkiye ve sonuç" });
  slideHeader(s,"Sonuç");
  title(s, "Sonuç ve çıkarımlar");
  const speed = S.convergence_speed;
  const points = [
    "Panel veri, ülkeler arası ve zaman içi değişimi birlikte kullanır; gözlenemeyen ülke farklarını kontrol eder.",
    "F, Hausman ve Mundlak testleri aynı yönü gösteriyor: ülke etkileri var ve açıklayıcılarla ilişkili. Sabit etkiler modeli uygun.",
    `Ülkeler kendi denge düzeylerine yaklaşıyor: FE ile yarılanma süresi ${Math.round(speed.fe.half_life)} yıl. Ülke etkisi yok sayılınca ${Math.round(speed.pooled.half_life)} yıl çıkıyor.`,
    `Yatırım oranı ülke içinde de büyümeyle güçlü biçimde ilişkili. 10 puanlık fark yaklaşık ${num(10 * coef(FE, "investment").estimate, 1)} puan büyüme farkı demek.`,
    "1991 verisiyle 2025 verisi aynı yönü gösteriyor; ancak katsayıların büyüklüğü veri sürümüne ve T'ye duyarlı.",
  ];
  points.forEach((point, i) => {
    const y = 1.65 + i * 1.04;
    card(s, ML, y, CW, 0.9);
    circle(s, ML + 0.2, y + 0.13, 0.64, String(i + 1), { size: 22 });
    text(s, runs(point, { fontFace: BODY, fontSize: 17, color: INK }), { x: ML + 1.1, y, w: CW - 1.35, h: 0.9, valign: "middle" });
  });
}

// ================================================================= 25. REFERENCES
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Türkiye ve sonuç" });
  slideHeader(s,"Sonuç");
  title(s, "Kaynaklar");
  const left = [
    "Acemoglu, D. ve Molina, C. (2022). Converging to converge? A comment. NBER Macroeconomics Annual, 36.",
    "Arellano, M. ve Bond, S. (1991). Some tests of specification for panel data. Review of Economic Studies, 58(2).",
    "Baltagi, B. H. (2021). Econometric Analysis of Panel Data (6. baskı). Springer.",
    "Blundell, R. ve Bond, S. (1998). Initial conditions and moment restrictions in dynamic panel data models. Journal of Econometrics, 87(1).",
    "Breusch, T. S. ve Pagan, A. R. (1980). The Lagrange multiplier test and its applications to model specification in econometrics. Review of Economic Studies, 47(1).",
    "Feenstra, R. C., Inklaar, R. ve Timmer, M. P. (2015). The next generation of the Penn World Table. American Economic Review, 105(10). Veri: PWT 11.0 (2025).",
    "Hausman, J. A. (1978). Specification tests in econometrics. Econometrica, 46(6).",
    "Islam, N. (1995). Growth empirics: a panel data approach. Quarterly Journal of Economics, 110(4).",
  ];
  const right = [
    "Kremer, M., Willis, J. ve You, Y. (2022). Converging to convergence. NBER Macroeconomics Annual, 36.",
    "Mankiw, N. G., Romer, D. ve Weil, D. N. (1992). A contribution to the empirics of economic growth. Quarterly Journal of Economics, 107(2).",
    "Mundlak, Y. (1978). On the pooling of time series and cross section data. Econometrica, 46(1).",
    "Nickell, S. (1981). Biases in dynamic models with fixed effects. Econometrica, 49(6).",
    "Pesaran, M. H. (2021). General diagnostic tests for cross-sectional dependence in panels. Empirical Economics, 60.",
    "Summers, R. ve Heston, A. (1991). The Penn World Table (Mark 5). Quarterly Journal of Economics, 106(2).",
    "Wooldridge, J. M. (2010). Econometric Analysis of Cross Section and Panel Data (2. baskı). MIT Press.",
  ];
  const w = 5.95;
  card(s, ML, 1.65, w, 5.2);
  card(s, ML + w + 0.233, 1.65, w, 5.2);
  text(s, paragraphs(left, { fontSize: 13 }, { paraSpaceAfter: 6 }), { x: ML + 0.25, y: 1.8, w: w - 0.5, h: 5.0 });
  text(s, paragraphs(right, { fontSize: 13 }, { paraSpaceAfter: 6 }), { x: ML + w + 0.233 + 0.25, y: 1.8, w: w - 0.5, h: 5.0 });
}

// ================================================================= 26. CLOSING
{
  const s = pres.addSlide({ masterName: "COVER", sectionTitle: "Türkiye ve sonuç" });
  text(s, "Teşekkürler", { x: ML, y: 2.3, w: 6.6, h: 1.4, fontFace: HEAD, fontSize: 60, bold: true, valign: "middle" });
  text(s, "Sorular ve tartışma", { x: ML, y: 3.9, w: 6.6, h: 0.8, fontSize: 28, color: DARK });
  text(s, "Kod ve veri", { x: ML, y: 5.0, w: 6.6, h: 0.35, fontSize: 15, bold: true, color: MID });
  repoLink(s, { prefix: "", x: ML, y: 5.35, w: 6.6, h: 0.45, fontSize: 18, bold: true, color: INK, align: "left" });
  text(s, "python src/run_all.py ile tüm sonuçlar yeniden üretilir.", { x: ML, y: 5.85, w: 6.6, h: 0.35, fontSize: 14, color: MID });
  coverGrid(s, 7.5, 0.9);
}

async function writeDeck() {
  const pptx = await pres.write({ outputType: "nodebuffer" });
  const zip = await JSZip.loadAsync(pptx);
  const contentTypes = "[Content_Types].xml";
  const types = await zip.file(contentTypes).async("string");
  // PptxGenJS declares slide masters that it does not always write; drop those entries.
  const cleaned = types.replace(/<Override PartName="\/(ppt\/slideMasters\/slideMaster\d+\.xml)"[^>]*\/>/g,
    (entry, part) => (zip.file(part) ? entry : ""));
  zip.file(contentTypes, cleaned);
  fs.writeFileSync(OUTPUT, await zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" }));
  console.log("written:", path.relative(ROOT, OUTPUT));
}

writeDeck().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
