# Измерение торсии лучевой кости по КТ — ядро расчёта

По КТ обеих рук измеряется **избыток торсии** лучевой кости (больная − здоровая).
Метод: трекинг кости → продольная ось → перпендикулярные сечения → 3D-регистрация
блоков коры → профиль угла вдоль диафиза → избыток. Python (numpy/scipy/scikit-image/
pydicom/matplotlib/reportlab).

> Занимаетесь производительностью — сразу к разделу **«Горячие места»**: там точные `файл:строка`.

---

## 1. Файлы в этом наборе

| Файл | Что |
|---|---|
| `radius_torsion_registration.py` | **главный модуль**: регистрация, профиль торсии, метрика, флаги качества (~1600 строк) |
| `radius_torsion_v3.py` | зависимость ядра: загрузка DICOM, трекинг кости, построение оси |
| `profile_diagnostics.py` | метрика избытка (endpoint) + оценка нелинейности профиля |
| `validation_selftests.py` | самотесты A–H на синтетике — **запускаются без DICOM** |

`registration` импортирует `v3` и `profile_diagnostics`; `selftests` импортирует `registration`.

---

## 2. Быстрый старт

```bash
pip install numpy scipy scikit-image pydicom matplotlib reportlab
python3 validation_selftests.py     # прогон ядра A–H, DICOM не нужен
```
Python 3.10+. Расчёт — CPU, однопоточный.

Прогон на реальном КТ (когда пришлём обезличенную серию):
```python
import radius_torsion_registration as R, numpy as np
vol, zpos, meta = R.load_dicom_series('<папка_DICOM>', dtype=np.int16)   # (Z,Y,X) int16 HU
spacing = (meta['spacing_z'], meta['spacing_xy'], meta['spacing_xy'])
# seed'ы — точка на лучевой кости каждой руки (пресеты в R.PATIENTS):
rows, good, excess, slope, *_ = R._run_twist_profile(
    vol, spacing, seed_aff=(z,y,x), seed_hlt=(z,y,x),
    prox_level_aff=..., dist_level_aff=..., prox_level_hlt=None)
print('избыток, °:', excess)
```

---

## 3. Поток данных

```
load_dicom_series(folder)          # v3.py:129  — ~850–1070 срезов 512×512 int16 (HU)
   → track_from_seed(vol, seed)    # v3.py:262  — ROI-трекинг кости по срезам
   → build_axis(...)               # v3.py:391  — полиномиальная ось из трека
   → _run_twist_profile(...)       # registration.py:1357  — основная обёртка
        → twist_profile(...)       # registration.py:545   — главный цикл по уровням
             для каждого уровня z:
               block_points_cont() # registration.py:414  — облако точек блока коры
               rot_register_3d()   # registration.py:473  — <<< ГОРЯЧО
             + zone_ulna_anchor()   # registration.py:138  — <<< ГОРЯЧО
```
Результат: `excess` (°), профиль φ(z), флаги качества.

---

## 4. ГОРЯЧИЕ МЕСТА (для оптимизации)

**#1 — `rot_register_3d`  (`radius_torsion_registration.py:473`) — доминирующая стоимость.**
Внутри `overlap(phi)` (строки ~495–498):
```python
keys = zip(np.round(sH/gv).astype(int), np.round(u2/gv).astype(int), np.round(v2/gv).astype(int))
return sum(1 for k in keys if k in occ) / len(sH)     # Python-цикл по ~тысячам точек
```
`overlap` зовётся ~120 раз (грубая сетка углов) + уточнение — и так на КАЖДЫЙ уровень и
КАЖДЫЙ шаг континуитета, на каждого пациента. Построение `set occ` и `sum(1 for ... if in occ)` —
чистый Python.
**Куда копать:** векторизовать членство (хешировать занятые воксели в один int64-ключ,
поворачивать все точки разом матрицей, `np.isin`/разреженная сетка вместо `set`), перебор
углов — батчем/матрично. Здесь основной резерв.

**#2 — `zone_ulna_anchor` + `cross_section`  (`:138`, `:56`).** Считается на каждом уровне
(якорный профиль), каждый вызов — `scipy.ndimage.map_coordinates` по зоне ±7 срезов.
**Куда копать:** кэшировать сечения по z; считать якорный профиль один раз, не в цикле;
допустимо реже (каждый 2-й уровень).

**#3 — `track_from_seed` / `_roi_bone_centroid`  (`v3.py:262`, `:229`).** Посрезовая
сегментация (`skimage.label`/`regionprops`) в маленьком ROI, ~сотни срезов.
**Куда копать:** заменить `regionprops` на дешёвый центроид маски.

**#4 — `load_dicom_series`  (`v3.py:129`).** Чтение ~1000 файлов pydicom — I/O-bound,
тривиально распараллеливается (threads).

**Проверка после оптимизаций:** числа не должны меняться. Ориентир — `validation_selftests.py`
(все A–H = OK).

---

## 5. Данные (DICOM)

Формат: обычная DICOM-серия, осевые срезы, ~850–1070 шт, 512×512, int16 (HU),
spacing_z 0.5–0.75 мм, spacing_xy ~0.9 мм. Скрипт принимает путь к папке с файлами серии
(у файлов нет расширения), читает `load_dicom_series`. Реальную серию пришлём отдельно
(обезличенную).

---

## 6. Тесты

- `python3 validation_selftests.py` — синтетические тесты A–H (DICOM не нужен). Ожидается,
  что все, кроме D (количественная оценка) и H (воспроизводит известное ограничение),
  дают OK. Это эталон приёмки — прогоняйте после любых правок.
```
