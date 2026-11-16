# Test na Windows (kroky 2w a 2k)

Cíl: ověřit, že experiment na Windows běží přes celou obrazovku, s přesným časováním a se
stejně velkými podněty jako na Macu. Potřebujete asi 30 minut, počítač s Windows, pravítko,
platební kartu (nebo jinou kartu stejné velikosti, např. průkaz) a připojení k internetu.

Když už projekt na počítači je z dřívějšího testu, stačí ho aktualizovat: v PowerShellu
`cd ~\f1-start`, `git pull`, `uv sync` a pokračovat bodem 3. (`git pull` stáhne jen to, co je
na GitHubu ve větvi `main`.)

## 1. Nastavení Windows (před testem i před každým měřením)

1. **Obnovovací frekvence 60 Hz:** Nastavení → Systém → Obrazovka → Upřesnit nastavení
   zobrazení → Obnovovací frekvence. Jiná frekvence program ukončí.
2. **Zapište si** (budou potřeba v bodě 6):
   - rozlišení: Nastavení → Systém → Obrazovka → Rozlišení zobrazení,
   - škálování: tamtéž „Měřítko“ (např. 100 %, 125 %, 150 %),
   - obnovovací frekvenci.
3. Oznámení vypnout (Nerušit / Asistent pro soustředění), notebook do zásuvky, režim napájení
   „Nejvyšší výkon“.

## 2. Instalace (PowerShell)

Pokud chybí git: `winget install --id Git.Git -e`, pak PowerShell zavřít a otevřít znovu.

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

PowerShell zavřít a otevřít znovu, pak:

```powershell
cd ~
git clone https://github.com/stepanzuna/f1-start.git
cd f1-start
uv sync
uv run pytest
```

Na konci má být „passed“ bez „failed“. **Když cokoli selže**, zkopírujte celý výpis chyby
(viz bod 6).

## 3. Simulace (bez klávesnice, asi 3 minuty)

```powershell
uv run main.py --sim --short
uv run check_data.py
```

Otevře se menší okno, program se sám „prokliká“ celým sezením. `check_data.py` má skončit
„OK: data odpovídají specifikaci.“ Během simulace nic nemačkejte.

## 4. Kalibrace a zkrácené sezení (asi 10 minut)

```powershell
uv run main.py --short
```

1. **Kalibrace** (ukáže se jen poprvé a po změně rozlišení): přiložte kartu na obrazovku
   k šedému obdélníku a šipkami upravte jeho šířku na šířku karty (vlevo/vpravo o 1 px,
   nahoru/dolů o 10 px). Enter uloží (funguje až po první šipce).
2. Nick `test_win`, Enter.
3. Na obrazovce nastavení stiskněte **V**: ukáže se vlajka a světla. **Pravítkem změřte** šířku
   a výšku vlajky (má mít 5,0 × 3,0 cm) a průměr jednoho světla (0,8 cm). Enter = zpět.
   Když vlajka nesedí o víc než 2 mm, stiskněte **K**, kalibraci zopakujte a změřte znovu.
4. Čeština (C), Enter.
5. Sledujte: otevřelo se okno **přes celou obrazovku a v popředí**? Jsou texty a světla **ostré**
   (ne rozmazané)? Běží rozsvěcování světel plynule?
6. Projděte instrukce, testovací kolo a 4 bloky. Na Paasově škále jednou změňte výběr (např. 3 → 7).
7. Na závěrečné obrazovce: mezerník ji nesmí zavřít, Escape ano.

## 5. Kontrola dat

```powershell
uv run check_data.py
```

Má skončit „OK“. Výpis si uložte (bod 6).

## 6. Co poslat zpět

Výsledky nemají osobní údaje (nick `test_win`), takže jdou přes GitHub:

```powershell
mkdir docs\diag
copy data\test\test_win_*.csv docs\diag\
copy data\test\test_win_*_meta.json docs\diag\
copy data\test\test_win_*_log.txt docs\diag\
notepad docs\diag\win_poznamky.md
```

Do `win_poznamky.md` napište: rozlišení, škálování, frekvenci, rozměry vlajky a světla v cm
(po kalibraci, přes `V`), jestli bylo okno v popředí a ostré, a případné chybové výpisy.

```powershell
git add docs\diag
git commit -m "Diagnostika Windows (krok 2w)"
git push
```

Když `git push` chce přihlášení a nejde to, pošlete soubory z `docs\diag` jinak (e-mail, flash
disk) a nahrajte je na Macu do `docs/diag/`.
