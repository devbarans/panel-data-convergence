# Panel Veri Analizi: Büyüme ve Yakınsama, 1973–2023

Yoksul ülkeler zengin ülkelere yetişiyor mu? Bu proje, soruyu panel veri ekonometrisiyle cevaplıyor. Penn World Table 11.0 (Ekim 2025) verisiyle 129 ülkenin 1973–2023 dönemi için havuzlanmış EKK, sabit etkiler ve rassal etkiler modelleri tahmin ediliyor; model seçimi ve varsayım testleri yapılıyor. Aynı model 1991'de yayımlanan Penn World Table 5 verisiyle (1960–1985) de tahmin edilerek iki sonuç karşılaştırılıyor.

Tüm tablolar, grafikler, yazılı rapor ve sunum bu depodaki kodla üretilir. Hiçbir sayı elle yazılmaz.

## Araştırma sorusu

Yatırım oranı, nüfus artışı, beşeri sermaye ve başlangıç geliri ülkelerin büyümesiyle nasıl ilişkilidir? Zamanla değişmeyen ülke özellikleri (kurumlar, coğrafya, kültür) kontrol edildiğinde bu ilişkiler nasıl değişir?

## Başlıca bulgular

- F, Hausman (χ²(4) = 104,8) ve kümelenmiş Mundlak (χ²(4) = 34,1) testlerinin hepsi sabit etkiler modelini işaret eder.
- Sabit etkiler yakınsama katsayısı −3,48: yılda yaklaşık %3,8 yakınsama, yarılanma süresi 18 yıl. Havuzlanmış EKK ile bu süre 78 yıl.
- Yatırım oranının 10 puan yüksek olduğu dönemde yıllık büyüme yaklaşık 0,8 puan yüksek (sabit etkiler, p < 0,01).
- 1960–85 verisinde yatay kesit eğimi her dönemde pozitif (ıraksama); 1973–2023 verisinde çoğu dönemde negatif.
- Panel 4 dönemden 10 döneme uzadıkça sabit etkiler katsayısı −5,99'dan −3,48'e iner; bu, Nickell yanlılığıyla uyumludur.

## Veri

| | Ana analiz | Karşılaştırma |
|---|---|---|
| Kaynak | Penn World Table 11.0 (Feenstra, Inklaar ve Timmer; Ekim 2025) | Penn World Table 5 (Summers ve Heston, 1991), R `plm` paketindeki `SumHes` |
| Ham dosya | `data/raw/pwt110.csv` | `data/raw/SumHes.csv` |
| Dönem | 1973–2023, 10 adet beş yıllık dönem | 1960–1985, 5 adet beş yıllık dönem |
| Yapı | N = 129, T = 10, 1.290 gözlem, dengeli | N = 125, T = 5, 625 gözlem, dengeli |

`pwt110.csv`, PWT 11.0'ın resmi Excel dosyasının "Data" sayfasından seçilen sütunlardır: `countrycode, country, year, rgdpna, rgdpe, pop, csh_i, hc`. Ana panele, 1973–2023 arasındaki her yılda bu değişkenleri eksiksiz olan ülkeler alınmıştır.

| Değişken | Tanım |
|---|---|
| `growth` | Kişi başı reel GSYH'nin (rgdpna / pop) dönem içindeki yıllık ortalama log büyümesi (%) |
| `ln_gdp0` | Dönem başında kişi başı reel GSYH'nin logu |
| `investment` | Yatırımın GSYH payı (csh_i), dönemin beş yılının ortalaması (%); PWT 5'te tasarruf oranı |
| `pop_growth` | Nüfusun yıllık ortalama log artışı (%) |
| `ln_hc0` | Dönem başında beşeri sermaye endeksinin (hc) logu |
| `landlocked` | Denize kıyısı olmayan ülke (0/1, zamanla sabit) |

## Model

```
growth_it = b1*ln_gdp0_it + b2*investment_it + b3*pop_growth_it + b4*ln_hc0_it
            + g*landlocked_i + dönem etkileri + mu_i + e_it
```

- **Tahmin ediciler:** havuzlanmış EKK, sabit etkiler (FE), rassal etkiler (RE). Tüm standart hatalar ülke düzeyinde kümelenmiştir.
- **Model seçimi:** F (havuzlanabilirlik), Breusch–Pagan LM, Hausman, Mundlak.
- **Varsayım testleri:** Wooldridge (seri korelasyon), değiştirilmiş Wald (değişen varyans), Pesaran CD (yatay kesit bağımlılığı).
- **Ek analizler:** dönem bazında yatay kesit yakınsama eğimleri, panel uzunluğunun FE katsayısına etkisi (Nickell yanlılığı), Türkiye için gerçekleşen büyüme ile model uyumu.

## Proje yapısı

```
.
├── data/
│   └── raw/                    # ham veri: PWT 11.0 ve PWT 5
├── src/
│   ├── paths.py                # ortak dosya yolları
│   ├── prepare_data.py         # ham veri -> beş yıllık dengeli paneller
│   ├── models.py               # modeller ve testler -> outputs/results.json
│   ├── figures.py              # grafikler (siyah-beyaz baskıya uygun)
│   ├── build_report.py         # yazılı rapor (PDF)
│   ├── authors.py              # kapak bilgilerini yerel ayar dosyasından okur
│   └── run_all.py              # tüm adımları sırayla çalıştırır
├── slides/
│   └── build_slides.js         # sunumu (PowerPoint) üretir
├── config/
│   └── authors.example.json    # kapak bilgileri için örnek dosya
├── requirements.txt
└── package.json
```

Kod çalıştırıldığında şu klasörler oluşur (depoya eklenmez):

- `data/processed/`: beş yıllık paneller
- `outputs/tables/`, `outputs/figures/`, `outputs/results.json`: tablolar, grafikler ve rapor ile sunumun okuduğu tüm sayılar
- `report/panel_data_report.pdf`: yazılı rapor
- `slides/panel_data_slides.pptx`: sunum

## Çalıştırma

Python 3.10 veya üstü gerekir.

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python src/run_all.py
```

Sunumu üretmek için Node.js gerekir:

```bash
npm install
npm run slides
```

Sunumun PDF hâli, PPTX dosyasının PowerPoint ya da LibreOffice ile PDF olarak dışa aktarılmasıyla elde edilir.

### Kapak bilgileri

Hazırlayanların adı, öğrenci numarası ve ders bilgisi depoda tutulmaz. Kapakta görünmeleri için örnek dosyayı kopyalayıp doldurun:

```bash
cp config/authors.example.json config/authors.json
```

Dosya yoksa rapor ve sunum yine üretilir; kapaktaki bu alanlar boş kalır.

## Tasarım

Rapor, sunum ve grafikler açık temada ve yalnızca gri tonlarıyla hazırlanmıştır; siyah-beyaz fotokopide de okunur. Seriler renkle değil çizgi tipi, işaretçi biçimi, tarama deseni ve doğrudan etiketle ayrılır.

## Kaynaklar

- Acemoglu, D. ve Molina, C. (2022). Converging to converge? A comment. *NBER Macroeconomics Annual*, 36.
- Arellano, M. ve Bond, S. (1991). Some tests of specification for panel data. *Review of Economic Studies*, 58(2).
- Baltagi, B. H. (2021). *Econometric Analysis of Panel Data* (6. baskı). Springer.
- Blundell, R. ve Bond, S. (1998). Initial conditions and moment restrictions in dynamic panel data models. *Journal of Econometrics*, 87(1).
- Breusch, T. S. ve Pagan, A. R. (1980). The Lagrange multiplier test and its applications to model specification in econometrics. *Review of Economic Studies*, 47(1).
- Feenstra, R. C., Inklaar, R. ve Timmer, M. P. (2015). The next generation of the Penn World Table. *American Economic Review*, 105(10). Veri: PWT 11.0, www.ggdc.net/pwt
- Hausman, J. A. (1978). Specification tests in econometrics. *Econometrica*, 46(6).
- Islam, N. (1995). Growth empirics: a panel data approach. *Quarterly Journal of Economics*, 110(4).
- Kremer, M., Willis, J. ve You, Y. (2022). Converging to convergence. *NBER Macroeconomics Annual*, 36.
- Mankiw, N. G., Romer, D. ve Weil, D. N. (1992). A contribution to the empirics of economic growth. *Quarterly Journal of Economics*, 107(2).
- Mundlak, Y. (1978). On the pooling of time series and cross section data. *Econometrica*, 46(1).
- Nickell, S. (1981). Biases in dynamic models with fixed effects. *Econometrica*, 49(6).
- Pesaran, M. H. (2021). General diagnostic tests for cross-sectional dependence in panels. *Empirical Economics*, 60.
- Summers, R. ve Heston, A. (1991). The Penn World Table (Mark 5). *Quarterly Journal of Economics*, 106(2).
- Wooldridge, J. M. (2010). *Econometric Analysis of Cross Section and Panel Data* (2. baskı). MIT Press.
