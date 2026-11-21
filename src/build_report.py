"""Build the written report (PDF).

Light theme, grayscale only, readable on a black-and-white photocopy. Every number is read
from outputs/results.json; nothing is typed by hand. The report text is Turkish.

Input : outputs/results.json, outputs/figures/*.png, config/authors.json (optional)
Output: report/panel_data_report.pdf
"""
import json
from pathlib import Path

import matplotlib
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

from authors import load_authors
from paths import FIGURES, REPORT, RESULTS, ROOT

COVER = load_authors()
RESULT = json.loads(RESULTS.read_text(encoding="utf-8"))
S, K = RESULT["pwt11"], RESULT["pwt5"]
OLS, FE, RE = "pooled", "fe", "re"


# ---------------------------------------------------------------- fonts
def register_fonts() -> tuple[str, str]:
    """Carlito/Caladea on Linux, Calibri/Cambria from Microsoft Office on macOS, else DejaVu."""
    crosextra = Path("/usr/share/fonts/truetype/crosextra")
    office = Path("/Applications/Microsoft PowerPoint.app/Contents/Resources/DFonts")
    if (crosextra / "Carlito-Regular.ttf").exists():
        folder, files = crosextra, ["Carlito-Regular", "Carlito-Bold", "Carlito-Italic", "Carlito-BoldItalic",
                                    "Caladea-Bold"]
    elif (office / "Calibri.ttf").exists():
        folder, files = office, ["Calibri", "Calibrib", "Calibrii", "Calibriz", "Cambriab"]
    else:
        folder = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
        files = ["DejaVuSans", "DejaVuSans-Bold", "DejaVuSans-Oblique", "DejaVuSans-BoldOblique", "DejaVuSerif-Bold"]
    for name, file in zip(["Body", "Body-B", "Body-I", "Body-BI", "Heading"], files):
        pdfmetrics.registerFont(TTFont(name, str(folder / f"{file}.ttf")))
    pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-B", italic="Body-I", boldItalic="Body-BI")
    return "Body", "Heading"


BODY, HEADING = register_fonts()
BLACK, DARK, MID, LIGHT, SHADE = (colors.HexColor(h) for h in ("#111111", "#333333", "#6b6b6b", "#bdbdbd", "#f0f0f0"))

STYLES = {
    "body": ParagraphStyle("body", fontName=BODY, fontSize=11, leading=15.5, alignment=TA_JUSTIFY,
                           textColor=BLACK, spaceAfter=7),
    "h1": ParagraphStyle("h1", fontName=HEADING, fontSize=17, leading=21, textColor=BLACK, spaceBefore=6, spaceAfter=8),
    "h2": ParagraphStyle("h2", fontName=HEADING, fontSize=13, leading=17, textColor=BLACK, spaceBefore=8, spaceAfter=5),
    "caption": ParagraphStyle("caption", fontName=BODY, fontSize=9.5, leading=12.5, textColor=DARK,
                              spaceBefore=3, spaceAfter=10),
    "cell": ParagraphStyle("cell", fontName=BODY, fontSize=9.5, leading=12, textColor=BLACK),
    "cell_bold": ParagraphStyle("cell_bold", fontName="Body-B", fontSize=9.5, leading=12, textColor=BLACK),
    "cell_head": ParagraphStyle("cell_head", fontName="Body-B", fontSize=9.5, leading=12, textColor=colors.white),
    "equation": ParagraphStyle("equation", fontName=BODY, fontSize=11.5, leading=17, alignment=TA_CENTER,
                               spaceBefore=4, spaceAfter=10),
    "reference": ParagraphStyle("reference", fontName=BODY, fontSize=10, leading=13.5, leftIndent=14,
                                firstLineIndent=-14, spaceAfter=4, alignment=TA_LEFT),
    "bullet": ParagraphStyle("bullet", fontName=BODY, fontSize=11, leading=15.5, leftIndent=14, bulletIndent=2,
                             spaceAfter=4, alignment=TA_LEFT),
}


# ---------------------------------------------------------------- formatting helpers
def num(x: float, digits: int = 2) -> str:
    """Turkish decimal comma and a true minus sign (no minus for values that round to zero)."""
    s = f"{abs(x):.{digits}f}".replace(".", ",")
    return ("−" if x < 0 and float(f"{abs(x):.{digits}f}") != 0 else "") + s


def p_value(p: float) -> str:
    return "< 0,001" if p < 0.001 else num(p, 3)


def thousands(x: float) -> str:
    return f"{round(x):,}".replace(",", ".")


def stars(p: float) -> str:
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else ""


def coef(model: str, variable: str, source: dict = S):
    return next((c for c in source["coefficients"] if c["model"] == model and c["variable"] == variable), None)


def para(text: str, style: str = "body") -> Paragraph:
    return Paragraph(text, STYLES[style])


def bullets(items: list[str]) -> list:
    return [Paragraph(item, STYLES["bullet"], bulletText="•") for item in items]


def figure(file: str, width_cm: float, caption: str) -> KeepTogether:
    path = FIGURES / file
    w, h = PILImage.open(path).size
    width = width_cm * cm
    return KeepTogether([Image(str(path), width=width, height=width * h / w), para(caption, "caption")])


def table(rows: list[list], col_cm: list[float], align: list[str] | None = None, bold_first=True) -> Table:
    data = []
    for ri, row in enumerate(rows):
        cells = []
        for ci, c in enumerate(row):
            if isinstance(c, str):
                style = "cell_head" if ri == 0 else ("cell_bold" if (bold_first and ci == 0) else "cell")
                ps = ParagraphStyle("x", parent=STYLES[style],
                                    alignment=TA_CENTER if (align and align[ci] == "c") else TA_LEFT)
                c = Paragraph(c, ps)
            cells.append(c)
        data.append(cells)
    t = Table(data, colWidths=[w * cm for w in col_cm], repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), BLACK),
        ("GRID", (0, 0), (-1, -1), 0.6, MID),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    for ri in range(2, len(data), 2):
        style.append(("BACKGROUND", (0, ri), (-1, ri), SHADE))
    t.setStyle(TableStyle(style))
    return t


def note_box(text: str) -> Table:
    t = Table([[para(text, "body")]], colWidths=[16 * cm])
    t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 1.2, BLACK), ("BACKGROUND", (0, 0), (-1, -1), SHADE),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                           ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
    return t


# ---------------------------------------------------------------- page layout
def footer(c, doc):
    c.saveState()
    c.setFont(BODY, 8.5)
    c.setFillColor(MID)
    c.setStrokeColor(LIGHT)
    c.line(2.5 * cm, 1.6 * cm, A4[0] - 2.5 * cm, 1.6 * cm)
    c.drawString(2.5 * cm, 1.15 * cm, "Panel Veri Analizi · Büyüme ve Yakınsama, 1973–2023")
    c.drawRightString(A4[0] - 2.5 * cm, 1.15 * cm, str(doc.page))
    c.restoreState()


def cover(c, doc):
    c.saveState()
    w, h = A4
    c.setFillColor(BLACK)
    c.rect(0, h - 1.2 * cm, w, 1.2 * cm, stroke=0, fill=1)
    c.setFont("Body-B", 10.5)
    c.setFillColor(MID)
    c.drawString(2.5 * cm, h - 5 * cm, "EKONOMETRİ  ·  PANEL VERİ ANALİZİ")
    c.setFillColor(BLACK)
    c.setFont(HEADING, 30)
    c.drawString(2.5 * cm, h - 7 * cm, "Yoksul ülkeler")
    c.drawString(2.5 * cm, h - 8.3 * cm, "arayı kapatıyor mu?")
    c.setFont(BODY, 15)
    c.setFillColor(DARK)
    c.drawString(2.5 * cm, h - 9.8 * cm, f"Panel veri ile {S['data']['N']} ülkede ekonomik büyüme ve yakınsama, 1973–2023")
    c.setFont(BODY, 11.5)
    c.drawString(2.5 * cm, h - 10.7 * cm, "Veri: Penn World Table 11.0 · Yöntem: Havuzlanmış EKK, sabit etkiler, rassal etkiler")
    c.setStrokeColor(BLACK)
    c.setLineWidth(1.4)
    c.line(2.5 * cm, h - 11.6 * cm, 9 * cm, h - 11.6 * cm)

    authors = COVER["authors"] or [("", "")]
    fields = [("Hazırlayanlar" if i == 0 else "", f"{name}  ·  {sid}" if name else "")
              for i, (name, sid) in enumerate(authors)]
    fields += [("Ders", COVER["course"]), ("Tarih", COVER["date"])]
    y = 8.5 * cm
    for label, value in fields:
        c.setFont("Body-B", 11.5)
        c.setFillColor(BLACK)
        if label:
            c.drawString(2.5 * cm, y, f"{label}:")
        if value:
            c.setFont(BODY, 11.5)
            c.drawString(5.6 * cm, y, value)
        else:
            c.setStrokeColor(LIGHT)
            c.setLineWidth(0.8)
            c.line(5.6 * cm, y - 2, 13.5 * cm, y - 2)
        y -= 0.95 * cm
    c.restoreState()


# ---------------------------------------------------------------- content
def content() -> list:
    N, T, OBS = S["data"]["N"], S["data"]["T"], S["data"]["observations"]
    tests = S["tests"]
    slopes = S["bivariate_slopes"]
    speed = S["convergence_speed"]
    intro = S["intro"]
    tur = S["turkey"]
    desc = S["descriptives"]
    story = []

    # 1 ------------------------------------------------------------------
    story.append(para("1. Giriş", "h1"))
    story.append(para(
        f"1973'te Türkiye'de kişi başı gelir {num(intro['TUR_1973'], 1)} bin dolar, Güney Kore'de "
        f"{num(intro['KOR_1973'], 1)} bin dolardı (2021 fiyatlarıyla). Türkiye yaklaşık iki kat öndeydi. 2023'e "
        f"gelindiğinde tablo tersine döndü: Kore {num(intro['KOR_2023'], 1)} bin, Türkiye {num(intro['TUR_2023'], 1)} "
        "bin dolar. Aynı dönemde Arjantin, 1960'ta üç ülkenin en zengini iken en geriye düştü (Şekil 1)."))
    story.append(para(
        "Bu tablo büyüme iktisadının eski bir sorusunu yeniden gündeme getiriyor: Ülkeler neden farklı hızlarda "
        "büyür ve yoksul ülkeler zengin ülkelere yetişir mi? Solow modeline göre her ülke kendi denge gelir düzeyine "
        "yaklaşır; denge düzeyinden uzak olan ülke daha hızlı büyür. Buna <i>koşullu yakınsama</i> denir. Ancak bu "
        "denge düzeyini belirleyen kurumlar, coğrafya ve kültür gibi özelliklerin büyük kısmı doğrudan gözlenemez."))
    story.append(para(
        "Bu çalışmada soruya panel veri yöntemleriyle yaklaşıyoruz. Penn World Table'ın Ekim 2025'te yayımlanan "
        f"11.0 sürümünden {N} ülkenin 1973–2023 verisiyle havuzlanmış EKK, sabit etkiler ve rassal etkiler modellerini "
        "tahmin ediyor, aralarında F, Breusch–Pagan, Hausman ve Mundlak testleriyle seçim yapıyoruz. Ayrıca aynı modeli "
        "1991'de yayımlanan eski Penn World Table (sürüm 5) verisiyle tahmin edip iki sonucu karşılaştırıyoruz."))
    story.append(figure("01_turkey_korea.png", 15.5,
                        "<b>Şekil 1.</b> Türkiye, Güney Kore ve Arjantin'de kişi başı reel GSYH, 1960–2023 (bin $, "
                        "2021 fiyatları, logaritmik eksen). Kaynak: PWT 11.0, rgdpna / nüfus."))

    # 2 ------------------------------------------------------------------
    story.append(para("2. Panel veri", "h1"))
    story.append(para(
        "Ekonometride kullanılan veriler yapılarına göre üç ana gruba ayrılır. <b>Yatay kesit verisi</b> tek bir "
        "dönemde çok sayıda birimi gözler; örneğin 2023 yılında 129 ülkenin geliri. <b>Zaman serisi</b> tek bir "
        "birimi çok sayıda dönem boyunca izler; örneğin Türkiye'nin 1973–2023 büyüme oranları. <b>Panel veri</b> "
        "ise aynı birimleri birden çok dönem boyunca izler ve iki boyutu birleştirir."))
    story.append(para(
        "Panel veride her gözlem iki indeksle tanımlanır: i = 1, …, N birimi, t = 1, …, T dönemi gösterir. Her "
        "birim her dönemde gözleniyorsa panel <b>dengeli</b>, eksik gözlem varsa <b>dengesizdir</b>. N büyük ve T "
        f"küçükse <b>kısa panel</b>, T büyükse <b>uzun panel</b> söz konusudur. Bu çalışmadaki veri N = {N}, T = {T} "
        f"ile dengeli ve kısa bir paneldir; toplam {thousands(OBS)} gözlem içerir."))
    story.append(para(
        "Panel verinin en önemli avantajı, zamanla değişmeyen ve gözlenemeyen birim farklarını kontrol etmeye izin "
        "vermesidir. Yatay kesit regresyonunda bir ülkenin kurumları ile yatırım oranı birlikte hareket ediyorsa, "
        "yatırımın etkisi ile kurumların etkisi birbirinden ayrılamaz. Panelde aynı ülkenin farklı dönemleri "
        "karşılaştırılabildiği için bu sorun büyük ölçüde ortadan kalkar. Bunun yanında daha fazla gözlem ve "
        "değişkenlik, daha kesin tahminler sağlar. Öte yandan aynı ülkenin hatalarının dönemler arasında ilişkili "
        "olması (seri korelasyon), hata varyansının ülkeden ülkeye değişmesi ve ülkelerin ortak şoklardan "
        "etkilenmesi (yatay kesit bağımlılığı) gibi sorunlar ayrıca ele alınmalıdır."))

    # 3 ------------------------------------------------------------------
    story.append(para("3. Model ve tahmin ediciler", "h1"))
    story.append(para("Temel doğrusal panel modeli şöyle yazılır:"))
    story.append(para("y<sub>it</sub> = α + x<sub>it</sub>′β + μ<sub>i</sub> + ε<sub>it</sub>", "equation"))
    story.append(para(
        "Burada y<sub>it</sub> bağımlı değişken, x<sub>it</sub> açıklayıcı değişkenler, μ<sub>i</sub> ülkeye özgü "
        "ve zamanla değişmeyen etki, ε<sub>it</sub> ise hem ülkeye hem döneme özgü hatadır. Üç temel tahmin edici "
        "arasındaki fark μ<sub>i</sub>'nin nasıl ele alındığından doğar."))
    story.append(table([
        ["", "Havuzlanmış EKK", "Sabit Etkiler (FE)", "Rassal Etkiler (RE)"],
        ["μ<sub>i</sub>", "Yok sayılır, tüm ülkeler aynı kesişimi paylaşır.", "Her ülke için ayrı bir sabit parametredir.",
         "Rassal değişkendir, hata teriminin parçasıdır."],
        ["Varsayım", "μ<sub>i</sub> = 0 ya da açıklayıcılarla ilişkisiz.", "μ<sub>i</sub> açıklayıcılarla ilişkili olabilir.",
         "μ<sub>i</sub> açıklayıcılarla ilişkisizdir."],
        ["Yöntem", "Tüm gözlemlere EKK.", "Ülke ortalamalarından sapmalar (within).", "GLS: kısmi ortalama çıkarma."],
        ["Sınırlama", "μ<sub>i</sub> ilişkiliyse tutarsız.", "Zamanla sabit değişkenler tahmin edilemez.",
         "μ<sub>i</sub> ilişkiliyse tutarsız."],
    ], [2.6, 4.4, 4.5, 4.5]))
    story.append(para("<b>Tablo 1.</b> Üç tahmin edicinin karşılaştırması.", "caption"))
    story.append(para(
        "Tahmin ediciler arasında seçim üç testle yapılır. <b>F testi</b> tüm ülke etkilerinin eşit olduğu "
        "hipotezini sınar; reddedilirse havuzlanmış EKK yetersizdir. <b>Breusch–Pagan LM testi</b> ülke etkisi "
        "varyansının sıfır olduğunu sınar; reddedilirse rassal etkiler havuzlanmış EKK'ye tercih edilir. "
        "<b>Hausman testi</b> FE ve RE katsayıları arasındaki farkın sistematik olup olmadığına bakar. Fark "
        "anlamlıysa ülke etkileri açıklayıcılarla ilişkilidir, RE tutarsızdır ve FE tercih edilir. Hausman testi "
        "klasik varsayımlara dayandığı için ayrıca <b>Mundlak</b> yaklaşımı kullanılır: açıklayıcıların ülke "
        "ortalamaları RE modeline eklenir ve bu ortalamaların katsayıları kümelenmiş standart hatalarla sınanır."))

    # 4 ------------------------------------------------------------------
    story.append(para("4. Veri", "h1"))
    story.append(para(
        "Veri, Groningen Üniversitesi'nin yayımladığı Penn World Table 11.0'dan (Feenstra, Inklaar ve Timmer, 2015; "
        "sürüm 11.0, Ekim 2025) alınmıştır. Bu sürüm 185 ülkeyi 1950–2023 dönemi için kapsar. Dengeli bir panel "
        f"elde etmek için 1973–2023 arasındaki tüm yıllarda gerekli değişkenleri eksiksiz olan {N} ülke seçildi. "
        "Eski Sovyet ülkeleri gibi verisi 1990'dan sonra başlayan ülkeler bu nedenle örnekleme girmedi."))
    story.append(para(
        "Büyüme regresyonlarında yıllık dalgalanmaları ve konjonktür etkisini azaltmak için yaygın olan yol, "
        "veriyi beş yıllık dönemlere bölmektir (Islam, 1995). Bu çalışmada on dönem kullanıldı: 1973–78, 1978–83, "
        "…, 2018–23. Değişkenler aşağıdaki gibi tanımlandı:"))
    story.append(table([
        ["Değişken", "Tanım", "Ortalama", "Std. sapma"],
        ["Büyüme", "Kişi başı reel GSYH'nin dönem içindeki yıllık ortalama log büyümesi (%)",
         num(desc["growth"]["mean"]), num(desc["growth"]["std"])],
        ["ln(Başlangıç GSYH)", "Dönem başında kişi başı reel GSYH'nin logu (rgdpna / nüfus)",
         num(desc["ln_gdp0"]["mean"]), num(desc["ln_gdp0"]["std"])],
        ["Yatırım oranı", "Yatırımın GSYH içindeki payı, dönemin beş yılının ortalaması (%)",
         num(desc["investment"]["mean"], 1), num(desc["investment"]["std"], 1)],
        ["Nüfus artışı", "Nüfusun dönem içindeki yıllık ortalama log artışı (%)",
         num(desc["pop_growth"]["mean"]), num(desc["pop_growth"]["std"])],
        ["ln(Beşeri sermaye)", "Dönem başında beşeri sermaye endeksinin logu (eğitim yılı ve getirisine dayanır)",
         num(desc["ln_hc0"]["mean"]), num(desc["ln_hc0"]["std"])],
        ["Denize kıyısız", "Ülkenin denize kıyısı yoksa 1, zamanla sabit", "", ""],
    ], [3.4, 8.4, 2.1, 2.1], ["l", "l", "c", "c"]))
    story.append(para(f"<b>Tablo 2.</b> Değişkenler ve betimsel istatistikler (N = {N}, T = {T}, "
                      f"{thousands(OBS)} gözlem).", "caption"))
    story.append(para(
        "Model, Mankiw, Romer ve Weil (1992) ile Islam (1995) çizgisinde beşeri sermayeyle genişletilmiş bir "
        "Solow büyüme regresyonudur:"))
    story.append(para(
        "Büyüme<sub>it</sub> = β<sub>1</sub> ln(GSYH<sub>0</sub>)<sub>it</sub> + β<sub>2</sub> Yatırım<sub>it</sub> "
        "+ β<sub>3</sub> Nüfus<sub>it</sub> + β<sub>4</sub> ln(BS)<sub>it</sub> + γ Kıyısız<sub>i</sub> "
        "+ λ<sub>t</sub> + μ<sub>i</sub> + ε<sub>it</sub>", "equation"))
    story.append(para(
        "λ<sub>t</sub> dönem etkileridir ve 2008 krizi ya da pandemi gibi tüm ülkeleri aynı anda etkileyen şokları "
        "yakalar. β<sub>1</sub> yakınsama katsayısıdır: negatifse, diğer koşullar sabitken daha zengin başlayan "
        "dönem daha yavaş büyümeyle ilişkilidir. Tüm modellerde standart hatalar ülke düzeyinde kümelenmiştir."))
    story.append(figure("02_panel_structure.png", 15.5,
                        "<b>Şekil 2.</b> Seçili ülkelerin on dönemlik büyüme serileri. Kalın çizgi Türkiye, kesikli "
                        f"çizgi {N} ülkenin ortalamasıdır."))

    # 5 ------------------------------------------------------------------
    story.append(para("5. Bulgular", "h1"))
    story.append(para("5.1. Havuzlanmış ilişki ve ülke içi ilişki", "h2"))
    story.append(para(
        "Model sonuçlarına geçmeden önce Şekil 3 panel verinin neden önemli olduğunu gösteriyor. Sol panelde "
        "tüm ülke-dönem gözlemleri bir arada; büyüme ile başlangıç geliri arasındaki eğim yalnızca "
        f"{num(slopes['pooled'])}. Sağ panelde ise her ülkenin değerleri kendi ortalamasından çıkarılmış; eğim "
        f"{num(slopes['within'])} olur. Yani bir ülke <i>kendi ortalamasına göre</i> zenginleştiği dönemlerde "
        "belirgin biçimde yavaşlıyor. Havuzlanmış veride bu ilişki, ülkeler arasındaki kalıcı farklar tarafından "
        "örtülüyor."))
    story.append(figure("03_pooled_vs_within.png", 15.5,
                        "<b>Şekil 3.</b> Büyüme ile başlangıç geliri: havuzlanmış veri (solda) ve ülke "
                        "ortalamalarından sapmalar (sağda). Doğrular iki değişkenli EKK eğimleridir."))

    story.append(para("5.2. Tahmin sonuçları", "h2"))
    rows = [["Bağımlı değişken: büyüme (%)", "Havuzlanmış EKK", "Sabit Etkiler", "Rassal Etkiler"]]
    for variable, label in [("ln_gdp0", "ln(Başlangıç GSYH)"), ("investment", "Yatırım oranı"),
                            ("pop_growth", "Nüfus artışı"), ("ln_hc0", "ln(Beşeri sermaye)"),
                            ("landlocked", "Denize kıyısız"), ("const", "Sabit")]:
        row = [label]
        for model in (OLS, FE, RE):
            c = coef(model, variable)
            row.append("—" if c is None else
                       f"<b>{num(c['estimate'], 3)}{stars(c['p'])}</b><br/>({num(c['std_error'], 3)})")
        rows.append(row)
    fit = {x["model"]: x for x in S["fit"]}
    rows += [["Dönem etkileri", "Evet", "Evet", "Evet"],
             ["Gözlem / ülke", *[f"{thousands(OBS)} / {N}"] * 3],
             ["R² (ülke içi)", *[num(fit[m]["r2_within"], 3) for m in (OLS, FE, RE)]]]
    story.append(table(rows, [5.2, 3.6, 3.6, 3.6], ["l", "c", "c", "c"]))
    story.append(para("<b>Tablo 3.</b> Tahmin sonuçları. Parantez içinde ülke düzeyinde kümelenmiş standart hatalar. "
                      "*** p &lt; 0,01; ** p &lt; 0,05; * p &lt; 0,10. FE modelinde zamanla sabit değişkenler ülke "
                      "etkisinin içinde kaldığı için tahmin edilemez (—).", "caption"))

    fe_inv, fe_gdp = coef(FE, "investment"), coef(FE, "ln_gdp0")
    story.append(para(
        "<b>Başlangıç geliri.</b> Katsayı üç modelde de negatif ve anlamlıdır, ancak büyüklükleri çok farklıdır: "
        f"havuzlanmış EKK'de {num(coef(OLS, 'ln_gdp0')['estimate'])}, FE'de {num(fe_gdp['estimate'])}. Beş yıllık "
        "büyüme katsayısından yıllık yakınsama hızı hesaplanabilir. FE tahmini yılda yaklaşık "
        f"%{num(speed['fe']['lambda'] * 100, 1)} yakınsamaya karşılık gelir; bir ülke kendi denge düzeyine olan "
        f"uzaklığının yarısını yaklaşık {round(speed['fe']['half_life'])} yılda kapatır. Havuzlanmış EKK ile bu süre "
        f"{round(speed['pooled']['half_life'])} yıldır. Aradaki fark, ülke etkisinin yok sayılmasından kaynaklanır."))
    story.append(para(
        "<b>Yatırım oranı.</b> Üç modelde de pozitif ve %1 düzeyinde anlamlıdır. FE tahminine göre yatırım "
        f"oranının 10 puan yüksek olduğu dönemde yıllık büyüme yaklaşık {num(10 * fe_inv['estimate'], 1)} puan "
        "yüksektir. Bu, ülkeler arası farklardan değil, aynı ülkenin farklı dönemlerinden elde edilen bir ilişkidir."))
    story.append(para(
        "<b>Nüfus artışı ve beşeri sermaye.</b> Havuzlanmış EKK ve RE'de nüfus artışı negatif, beşeri sermaye pozitif "
        "çıkar; FE'de ikisi de sıfırdan ayırt edilemez. Bu iki değişken bir ülke içinde yavaş değişir. Ülke "
        "ortalamaları çıkarıldığında geriye az değişkenlik kalır ve etkileri büyük ölçüde ülke sabit etkisine "
        "karışır. Bu, FE yönteminin bilinen bir maliyetidir. Denize kıyısız olmak negatif ama anlamsızdır."))
    story.append(figure("05_coefficients.png", 16,
                        "<b>Şekil 4.</b> Üç modelin katsayıları ve %95 güven aralıkları (kümelenmiş standart hata)."))

    story.append(para("5.3. Model seçimi", "h2"))
    F_, BP, H, M = tests["f_poolability"], tests["breusch_pagan_lm"], tests["hausman"], tests["mundlak"]
    story.append(table([
        ["Test", "Sıfır hipotezi", "İstatistik", "p-değeri", "Karar"],
        ["F", "Tüm ülke etkileri eşit", f"F({F_['df'][0]}; {thousands(F_['df'][1])}) = {num(F_['statistic'])}",
         p_value(F_['p']), "Ülke etkileri var"],
        ["Breusch–Pagan LM", "Var(μ<sub>i</sub>) = 0", f"χ²({BP['df']}) = {num(BP['statistic'])}", p_value(BP['p']),
         "RE &gt; havuzlanmış EKK"],
        ["Hausman", "μ<sub>i</sub> açıklayıcılarla ilişkisiz", f"χ²({H['df']}) = {num(H['statistic'])}",
         p_value(H['p']), "FE &gt; RE"],
        ["Mundlak (kümelenmiş)", "Ülke ortalamalarının katsayıları sıfır", f"χ²({M['df']}) = {num(M['statistic'])}",
         p_value(M['p']), "FE &gt; RE"],
    ], [3.4, 4.3, 3.4, 1.8, 3.1], ["l", "l", "c", "c", "l"]))
    story.append(para("<b>Tablo 4.</b> Model seçimi testleri.", "caption"))
    story.append(para(
        "F testi ülke etkilerinin olmadığı hipotezini açıkça reddeder; havuzlanmış EKK uygun değildir. Breusch–Pagan "
        "testi de ülkeye özgü bir varyans bileşeni olduğunu gösterir. Hausman testi ve ondan bağımsız olarak "
        "kümelenmiş standart hatalarla yapılan Mundlak testi, ülke etkilerinin açıklayıcılarla ilişkili olduğunu "
        "gösterir. Bu nedenle yorumlarımızı sabit etkiler modeline dayandırıyoruz. Sezgisel olarak bu sonuç "
        "şaşırtıcı değildir: iyi kurumlara sahip bir ülkenin hem yatırım oranı yüksek hem de denge geliri yüksektir."))

    story.append(para("5.4. Varsayım testleri", "h2"))
    W, MW, CD = tests["wooldridge"], tests["modified_wald"], tests["pesaran_cd"]
    se = S["standard_error_comparison"]
    ratio = [v["clustered"] / v["conventional"] - 1 for v in se.values()]
    story.append(table([
        ["Test", "Sıfır hipotezi", "İstatistik", "p-değeri"],
        ["Wooldridge", "Birinci derece seri korelasyon yok", f"F({W['df'][0]}; {W['df'][1]}) = {num(W['statistic'])}",
         p_value(W['p'])],
        ["Değiştirilmiş Wald", "Tüm ülkelerde hata varyansı eşit", f"χ²({MW['df']}) = {thousands(MW['statistic'])}",
         p_value(MW['p'])],
        ["Pesaran CD", "Ülkeler arasında hata korelasyonu yok", f"CD = {num(CD['statistic'])}", p_value(CD['p'])],
    ], [3.6, 6.4, 4.0, 2.0], ["l", "l", "c", "c"]))
    story.append(para("<b>Tablo 5.</b> FE modeli için varsayım testleri.", "caption"))
    story.append(para(
        "Hatalarda hem seri korelasyon hem de ülkeler arasında değişen varyans vardır. Bu durumda klasik standart "
        "hatalar güvenilmezdir. Ülke düzeyinde kümelenmiş standart hatalar her iki soruna karşı da dayanıklıdır; "
        f"bu çalışmada FE katsayılarının kümelenmiş standart hataları klasik olanlardan %{round(min(ratio) * 100)} ile "
        f"%{round(max(ratio) * 100)} arasında daha büyüktür. Pesaran CD testi, dönem etkileri modele girdikten sonra "
        "ülkeler arasında anlamlı bir hata korelasyonu kalmadığını gösterir."))

    # 6 ------------------------------------------------------------------
    story.append(para("6. Güncel tartışma: yakınsamaya doğru mu?", "h1"))
    cs = S["cross_section_slopes"]
    story.append(para(
        "1990'larda yapılan çalışmalar, yoksul ülkelerin zenginlere koşulsuz olarak yetiştiğine dair bir kanıt "
        "bulamamıştı. Kremer, Willis ve You (2022) son otuz yılın verisini inceleyerek 1990'lardan bu yana koşulsuz "
        "yakınsamaya doğru bir eğilim olduğunu ve 2000'lerden itibaren yoksul ülkelerin ortalamada daha hızlı "
        "büyüdüğünü gösterdi. Acemoglu ve Molina (2022) ise bu çalışmaya yazdıkları yorumda, ülke sabit etkileri "
        "konmadan hesaplanan yakınsama katsayılarının sıfıra doğru yanlı olduğunu ve bu yanlılığın zaman içinde "
        "değişebileceğini savundu. Bu tartışma, panel veride sabit etkilerin neden önemli olduğunun güncel bir örneğidir."))
    story.append(para(
        "Şekil 5'te her beş yıllık dönem için ayrı bir yatay kesit regresyonu yapılmış ve büyümenin başlangıç "
        "gelirine eğimi çizilmiştir. Eski veride (PWT 5, 1960–85) eğim her dönemde pozitiftir, yani zengin ülkeler "
        f"daha hızlı büyümüştür. Yeni veride eğim çoğu dönemde negatiftir ve 2008–13 döneminde {num(cs['2008'])} ile en "
        f"düşük değerine iner. 2018–23 döneminde ise yeniden pozitiftir ({num(cs['2018'])}); pandemi döneminin bu "
        "eğilimi bozup bozmadığı ilerideki verilerle görülecektir."))
    story.append(figure("04_convergence.png", 15.5,
                        "<b>Şekil 5.</b> Koşulsuz yakınsama: her dönem için büyümenin başlangıç gelirine yatay kesit "
                        "eğimi. Pozitif değer ıraksamayı, negatif değer yakınsamayı gösterir."))
    story.append(para(
        "Şekildeki eğimler küçüktür ve dönemden döneme oynaktır. Buna karşılık sabit etkiler modelindeki ülke içi "
        f"yakınsama katsayısı ({num(fe_gdp['estimate'])}) hem büyük hem de kesin olarak tahmin edilmiştir. Bu sonuç, "
        "Acemoglu ve Molina'nın vurguladığı gibi, ülkelerin ortak bir düzeye değil kendi denge düzeylerine "
        "yakınsadığı görüşüyle uyumludur."))

    # 7 ------------------------------------------------------------------
    story.append(para("7. Eski veri, yeni veri ve panelin uzunluğu", "h1"))
    story.append(para(
        "Aynı model 1991'de yayımlanan Penn World Table 5 verisiyle (Summers ve Heston, 1991; 125 ülke, 1960–85, "
        "T = 5) de tahmin edildi. Bu veri setinde yatırım oranı yerine tasarruf oranı, beşeri sermaye yerine OPEC "
        "ve komünist rejim göstergeleri bulunur. Tablo 6 ortak değişkenlerin sonuçlarını karşılaştırır."))

    def cell(model, variable, source):
        c = coef(model, variable, source)
        return f"{num(c['estimate'], 3)}{stars(c['p'])}"

    story.append(table([
        ["", "Havuzlanmış EKK<br/>PWT 5, 1960–85", "Havuzlanmış EKK<br/>PWT 11, 1973–2023",
         "Sabit Etkiler<br/>PWT 5, 1960–85", "Sabit Etkiler<br/>PWT 11, 1973–2023"],
        ["ln(Başlangıç GSYH)", cell(OLS, "ln_gdp0", K), cell(OLS, "ln_gdp0", S), cell(FE, "ln_gdp0", K),
         cell(FE, "ln_gdp0", S)],
        ["Yatırım / tasarruf", cell(OLS, "investment", K), cell(OLS, "investment", S), cell(FE, "investment", K),
         cell(FE, "investment", S)],
        ["Nüfus artışı", cell(OLS, "pop_growth", K), cell(OLS, "pop_growth", S), cell(FE, "pop_growth", K),
         cell(FE, "pop_growth", S)],
        ["N × T", f"{K['data']['N']} × {K['data']['T']}", f"{N} × {T}", f"{K['data']['N']} × {K['data']['T']}",
         f"{N} × {T}"],
        ["Hausman", "", "", f"χ²({K['tests']['hausman']['df']}) = {num(K['tests']['hausman']['statistic'], 1)}",
         f"χ²({H['df']}) = {num(H['statistic'], 1)}"],
    ], [3.6, 3.1, 3.1, 3.1, 3.1], ["l", "c", "c", "c", "c"]))
    story.append(para("<b>Tablo 6.</b> Eski ve yeni veriyle sonuçlar. Kümelenmiş standart hatalara göre anlamlılık: "
                      "*** p &lt; 0,01; ** p &lt; 0,05. Yeni modelde ayrıca beşeri sermaye ve denize kıyısız göstergesi "
                      "bulunur.", "caption"))
    story.append(para(
        "İşaretler iki veride de aynıdır ve Hausman testi her iki veride FE'yi seçer. Buna karşılık FE yakınsama "
        f"katsayısı eski veride {num(coef(FE, 'ln_gdp0', K)['estimate'])}, yeni veride {num(fe_gdp['estimate'])} olur ve "
        "nüfus artışının FE etkisi kaybolur. Bu farkın birkaç kaynağı vardır: farklı dönem, farklı ülke kümesi, "
        "yıllar içinde revize edilmiş ulusal hesaplar ve panelin uzunluğu."))
    length = S["panel_length_effect"]
    story.append(para(
        "Son etkiyi ayırmak için aynı ülkelerle panel 1973'ten başlatılıp her adımda bir dönem uzatıldı (Şekil 6). "
        "Bu modelde başlangıç geliri, gelir düzeyi cinsinden yazıldığında gecikmeli bağımlı değişkendir. Nickell "
        "(1981), böyle modellerde FE tahmininin yaklaşık 1/T mertebesinde yanlı olduğunu göstermiştir. "
        f"T = {length[0]['T']} iken katsayı {num(length[0]['estimate'])}, T = {T} iken "
        f"{num(length[-1]['estimate'])} olur. Katsayının panel uzadıkça sıfıra doğru gelmesi Nickell "
        "yanlılığıyla uyumludur. Ancak her adımda yeni yıllar da eklendiği için bu grafik yanlılığın kesin kanıtı "
        "değildir; daha kesin bir sonuç için fark ya da sistem GMM tahmincileri (Arellano ve Bond, 1991; Blundell ve "
        "Bond, 1998) kullanılmalıdır."))
    story.append(figure("06_panel_length.png", 14,
                        "<b>Şekil 6.</b> Panel uzunluğuna göre FE yakınsama katsayısı ve %95 güven aralığı. Tüm "
                        f"tahminler aynı {N} ülkeyle yapılmıştır."))

    # 8 ------------------------------------------------------------------
    story.append(para("8. Türkiye", "h1"))
    periods = {x["period"]: x for x in tur["periods"]}
    story.append(para(
        f"Türkiye'nin 1973–2023 ortalama yıllık büyümesi %{num(tur['mean_growth'])}'dir; örneklem ortalaması "
        f"%{num(tur['sample_mean_growth'])}. Tahmin edilen ülke sabit etkisine göre Türkiye {N} ülke arasında "
        f"{tur['fixed_effect_rank']}. sıradadır. Şekil 7, her dönem için gerçekleşen büyümeyi FE modelinin uyum "
        "değeriyle karşılaştırır."))
    story.append(figure("07_turkey.png", 15.5,
                        "<b>Şekil 7.</b> Türkiye: gerçekleşen büyüme, FE modelinin uyum değeri ve tüm ülkelerin "
                        "dönem ortalaması."))
    story.append(para(
        "Model, Türkiye'nin kriz dönemlerinde büyümeyi olduğundan yüksek gösterir: 1978–83'te fark "
        f"{num(periods[1978]['residual'], 1)}, 1998–03'te {num(periods[1998]['residual'], 1)} puandır. Bu dönemler "
        "1970'lerin sonundaki ödemeler dengesi krizine ve 1999 depremi ile 2001 bankacılık krizine denk gelir; yatırım "
        "ve nüfus gibi yavaş değişen değişkenler bu tür şokları yakalayamaz. 2018–23 döneminde ise büyüme modelin "
        f"{num(periods[2018]['residual'], 1)} puan üzerindedir. Bu dönemde yatırım oranı düşmüş, başlangıç geliri "
        "yükselmiş ve pandemiyi içeren dönem etkisi tüm ülkelerde büyümeyi aşağı çekmiştir; dolayısıyla model daha "
        "düşük bir büyüme bekler. (Nüfus artışı da yavaşlamıştır, ancak FE modelinde nüfus katsayısı sıfıra yakın "
        "olduğundan bu, beklenen büyümeyi değiştirmez.) Gerçekleşen yüksek büyümenin modeldeki değişkenlerle "
        "açıklanamayan bir kısmı vardır."))

    # 9 ------------------------------------------------------------------
    story.append(para("9. Sınırlılıklar", "h1"))
    story += bullets([
        "<b>Dinamik yapı.</b> Başlangıç geliri gecikmeli bağımlı değişken gibi davrandığı için FE tahmini Nickell "
        f"yanlılığı taşıyabilir. T = {T} ile yanlılık azalır ama sıfırlanmaz.",
        "<b>Örneklem seçimi.</b> Dengeli panel için yalnızca 1973'ten beri verisi olan ülkeler alındı. Daha kısa "
        "geçmişi olan ülkeleri içeren dengesiz bir panel sonuçları değiştirebilir.",
        "<b>Ölçüm hatası ve veri revizyonları.</b> Başlangıç gelirindeki ölçüm hatası hem açıklayıcı değişkene hem "
        "büyüme hesabına girer. PWT sürümleri arasındaki revizyonlar da tahminleri etkileyebilir.",
        "<b>Nedensellik.</b> Katsayılar koşullu ilişkileri gösterir. Yatırım büyümeyi etkilediği gibi büyümeden de "
        "etkilenir; nedensel bir yorum için araç değişken ya da GMM gibi yöntemler gerekir.",
    ])

    # 10 -----------------------------------------------------------------
    story.append(para("10. Sonuç", "h1"))
    story.append(para(
        f"Bu çalışmada {N} ülkenin 1973–2023 verisiyle beşeri sermayeyle genişletilmiş bir büyüme regresyonu panel "
        "veri yöntemleriyle tahmin edildi. F, Breusch–Pagan, Hausman ve Mundlak testleri aynı sonuca işaret ediyor: "
        "ülkeye özgü etkiler vardır ve açıklayıcı değişkenlerle ilişkilidir; dolayısıyla sabit etkiler modeli uygundur."))
    story.append(para(
        "Ülke etkileri kontrol edildiğinde güçlü bir koşullu yakınsama ortaya çıkıyor: ülkeler kendi denge "
        f"düzeylerine olan uzaklıklarının yarısını yaklaşık {round(speed['fe']['half_life'])} yılda kapatıyor. Ülke "
        f"etkileri yok sayıldığında bu süre {round(speed['pooled']['half_life'])} yıla çıkıyor. Yatırım oranı, aynı "
        "ülke içinde de büyümeyle güçlü ve anlamlı biçimde ilişkili. 1991 verisiyle 2025 verisi aynı yönü gösteriyor; "
        "ancak katsayıların büyüklüğü veri sürümüne ve panelin uzunluğuna duyarlı."))
    story.append(para(
        "Kısacası, \"yoksul ülkeler arayı kapatıyor mu?\" sorusunun cevabı hangi yöntemin kullanıldığına bağlıdır. "
        "Havuzlanmış veri zayıf ve oynak bir ilişki gösterirken, panel verinin ülke içi boyutu belirgin bir "
        "yakınsamayı ortaya çıkarır. Bu fark, panel veri yöntemlerinin büyüme çalışmalarındaki önemini açıkça gösterir."))
    story.append(Spacer(1, 6))
    story.append(note_box(
        "<b>Kod ve tekrar üretilebilirlik.</b> Tüm sonuçlar, grafikler, sunum ve bu rapor projedeki Python koduyla "
        "üretilmiştir. <font face='Body-B'>python src/run_all.py</font> komutu veriyi hazırlar, modelleri tahmin "
        "eder, grafikleri çizer ve raporu yeniden oluşturur."))

    # References ----------------------------------------------------------
    story.append(PageBreak())
    story.append(para("Kaynaklar", "h1"))
    for ref in [
        "Acemoglu, D. ve Molina, C. (2022). Converging to converge? A comment. <i>NBER Macroeconomics Annual</i>, 36, 425–442.",
        "Arellano, M. ve Bond, S. (1991). Some tests of specification for panel data: Monte Carlo evidence and an application to employment equations. <i>Review of Economic Studies</i>, 58(2), 277–297.",
        "Baltagi, B. H. (2021). <i>Econometric Analysis of Panel Data</i> (6. baskı). Springer.",
        "Blundell, R. ve Bond, S. (1998). Initial conditions and moment restrictions in dynamic panel data models. <i>Journal of Econometrics</i>, 87(1), 115–143.",
        "Breusch, T. S. ve Pagan, A. R. (1980). The Lagrange multiplier test and its applications to model specification in econometrics. <i>Review of Economic Studies</i>, 47(1), 239–253.",
        "Feenstra, R. C., Inklaar, R. ve Timmer, M. P. (2015). The next generation of the Penn World Table. <i>American Economic Review</i>, 105(10), 3150–3182. Veri: Penn World Table 11.0 (Ekim 2025), www.ggdc.net/pwt.",
        "Hausman, J. A. (1978). Specification tests in econometrics. <i>Econometrica</i>, 46(6), 1251–1271.",
        "Islam, N. (1995). Growth empirics: a panel data approach. <i>Quarterly Journal of Economics</i>, 110(4), 1127–1170.",
        "Kremer, M., Willis, J. ve You, Y. (2022). Converging to convergence. <i>NBER Macroeconomics Annual</i>, 36, 337–412.",
        "Mankiw, N. G., Romer, D. ve Weil, D. N. (1992). A contribution to the empirics of economic growth. <i>Quarterly Journal of Economics</i>, 107(2), 407–437.",
        "Mundlak, Y. (1978). On the pooling of time series and cross section data. <i>Econometrica</i>, 46(1), 69–85.",
        "Nickell, S. (1981). Biases in dynamic models with fixed effects. <i>Econometrica</i>, 49(6), 1417–1426.",
        "Pesaran, M. H. (2021). General diagnostic tests for cross-sectional dependence in panels. <i>Empirical Economics</i>, 60, 13–50.",
        "Summers, R. ve Heston, A. (1991). The Penn World Table (Mark 5): an expanded set of international comparisons, 1950–1988. <i>Quarterly Journal of Economics</i>, 106(2), 327–368.",
        "Wooldridge, J. M. (2010). <i>Econometric Analysis of Cross Section and Panel Data</i> (2. baskı). MIT Press.",
    ]:
        story.append(para(ref, "reference"))
    return story


def main() -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(REPORT), pagesize=A4, leftMargin=2.5 * cm, rightMargin=2.5 * cm,
                            topMargin=2.2 * cm, bottomMargin=2.2 * cm,
                            title="Panel Veri Analizi: Büyüme ve Yakınsama, 1973–2023",
                            author=", ".join(name for name, _ in COVER["authors"]),
                            subject="Panel veri ekonometrisi")
    doc.build([PageBreak()] + content(), onFirstPage=cover, onLaterPages=footer)
    print("written:", REPORT.relative_to(ROOT))


if __name__ == "__main__":
    main()
