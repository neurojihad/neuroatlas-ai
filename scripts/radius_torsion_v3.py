"""
radius_torsion_v3.py — полуавтоматический расчёт торсии лучевой кости по DICOM КТ

Версия 3: интерактивный seed-трекинг.
Главное отличие от v2: автоопределение кости заменено на указание точки
пользователем (клик мышью) и трекинг от неё по соседним срезам. Это позволяет
работать с нестандартными укладками (обе руки в одном FOV, рука пересекает
midline), где фиксированное деление FOV по X неприменимо.

Workflow:
  1. python radius_torsion_v3.py <папка_DICOM> [--patient NAME] [--output DIR]
  2. Загрузка серии (полная + прореженная для интерактива)
  3. Окно 1: фронтальный MIP + аксиальный срез, клик → seed point
  4. track_from_seed: трекинг вперёд/назад от seed по ближайшему центроиду
  5. Полиномиальная ось (ст.3, фильтрация выбросов >3σ)
  6. Окно 2: фронтальный MIP с наложенной осью → OK / Re-seed
  7. Поиск кандидатов уровней по prominence ориентира
  8. Окна 3/4: сетка 3×3 MPR-кандидатов, клик → выбор (Enter = автовыбор)
  9. Окно 5: два MPR с линиями углов, значение торсии, Save PDF
 10. Сохранение seed/уровней в training_data.csv для Phase 2 (CNN)

Перенос из v2 (отмечено ✅ в ТЗ):
  load_dicom_series, segment_bones_slice, extract_mpr_slice,
  compute_perpendicular_plane, render_frontal_panel, render_mpr_panel,
  build_pdf_report
Переписано:
  track_from_seed (вместо build_radius_axis_3d),
  measure_angle_landmark (PCA-эллипс + секторный поиск бугристости)
Удалено:
  identify_radius_ulna (не нужна — нет предположений об анатомии/laterality)

Зависимости: pydicom, numpy, scipy, scikit-image, matplotlib, reportlab
"""

import argparse
import csv
import io
import os
import sys
from datetime import datetime
from pathlib import Path

import matplotlib
# ВАЖНО: backend НЕ форсируется в Agg — нужны интерактивные окна.
# Функции рендера в PDF используют savefig() в буфер и работают при любом backend.
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.widgets import Slider, Button
import numpy as np
from scipy import ndimage
from scipy.ndimage import median_filter
from scipy.interpolate import UnivariateSpline
from skimage import measure, morphology

import pydicom

# PDF
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (SimpleDocTemplate, Spacer, Table, TableStyle,
                                Paragraph, Image as RLImage, PageBreak)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# ─────────────────────────────────────────────────────────────────────────────
# Константы (перенос из v2)
# ─────────────────────────────────────────────────────────────────────────────

HU_CORTICAL_MIN = 700
HU_CORTICAL_MAX = 3000
HU_BONE_MIN = 200

# Костное окно для отображения (как в CT Viewer): W1500 / L400
WIN_LEVEL = 400
WIN_WIDTH = 1500

C_BG      = "#0d1117"
C_BONE    = "#e0e0e0"
C_RADIUS  = "#4ade80"
C_ULNA    = "#60a5fa"
C_AXIS    = "#fbbf24"
C_PROX    = "#34d399"
C_DIST    = "#f87171"
C_TEXT    = "#f0f0f0"
C_SUBTEXT = "#9ca3af"
C_ACCENT  = "#6366f1"

# Параметры workflow
DISPLAY_STEP   = 6      # прореживание для интерактивного просмотра
LEVEL_SCAN_STEP = 5     # шаг сканирования вдоль оси при поиске уровней

# Параметры ROI-трекинга (см. track_from_seed)
TRACK_ROI_HALF = 13     # полуразмер окна ROI (px). Меньше половины расстояния
                        # между лучевой и локтевой костями (~27px центр-центр),
                        # чтобы окно не захватывало соседнюю кость и трекер не
                        # перепрыгивал radius↔ulna на участке их сближения.
TRACK_HU       = 400    # порог HU для трекинга (ниже HU_CORTICAL_MIN: захватывает
                        # и кортикаль, и губчатую кость → нет «мерцания» тонкого
                        # кортикального кольца диафиза)
TRACK_MIN_AREA = 15     # мин. площадь компоненты в ROI
TRACK_MAX_JUMP = 9      # px — макс. смещение центроида от ПРОГНОЗА за срез
TRACK_MISS_MAX = 15     # подряд пропущенных срезов до завершения ветви
TRACK_AREA_MERGE = 2.2  # верхний порог роста площади относительно скользящей
                        # медианы: срабатывает при СЛИЯНИИ с соседней костью
                        # (площадь резко удваивается) → срез пропускается.
                        # Нижнего порога нет: тонкий диафиз может временно
                        # «худеть», и площадь плохо отличает radius от ulna.
N_CANDIDATES   = 9      # кандидатов в сетке 3×3
# Анатомическая привязка зон поиска уровней (в срезах):
PROX_BELOW_SEED = 25    # проксимальная зона: от seed-30 ... seed+PROX_*
PROX_ABOVE_SEED = 30
PROX_BACK_SEED  = 30
DIST_FROM_END   = 95    # дистальная зона: [z_max-DIST_FROM_END, z_max-DIST_END_PAD]
DIST_END_PAD    = 12


def _bone_window(img):
    """Нормализация HU в [0,1] по костному окну W1500/L400."""
    lo = WIN_LEVEL - WIN_WIDTH / 2.0
    hi = WIN_LEVEL + WIN_WIDTH / 2.0
    return np.clip((img - lo) / (hi - lo + 1e-9), 0, 1)


# ─────────────────────────────────────────────────────────────────────────────
# 1. ЗАГРУЗКА DICOM  (✅ перенос из v2, добавлен возврат для прореживания)
# ─────────────────────────────────────────────────────────────────────────────

def load_dicom_series(folder: str, dtype=np.float32):
    """
    Загрузка серии DICOM с экономией памяти: сначала читаются только
    заголовки (stop_before_pixels) для сортировки по z, затем объём
    предвыделяется и заполняется срез за срезом. Это исключает двойной
    пик памяти от list+np.stack — критично для серий в 1000+ срезов.

    dtype: np.float32 (точность) либо np.int16 (вдвое меньше памяти; HU
           укладывается в int16, достаточно для сегментации и MPR).
    """
    folder = Path(folder)
    candidates = list(folder.glob("*.dcm")) + list(folder.glob("*.DCM"))
    if not candidates:
        for f in folder.iterdir():
            if f.is_dir():
                continue
            try:
                pydicom.dcmread(str(f), stop_before_pixels=True)
                candidates.append(f)
            except Exception:
                pass

    if not candidates:
        raise FileNotFoundError(f"DICOM не найдены: {folder}")

    def get_z(hdr):
        if hasattr(hdr, "ImagePositionPatient"):
            return float(hdr.ImagePositionPatient[2])
        if hasattr(hdr, "SliceLocation"):
            return float(hdr.SliceLocation)
        return float(getattr(hdr, "InstanceNumber", 0))

    # Читаем только заголовки для сортировки (без пиксельных данных)
    headers = []
    for f in candidates:
        try:
            hdr = pydicom.dcmread(str(f), stop_before_pixels=True)
            headers.append((str(f), hdr, get_z(hdr)))
        except Exception:
            pass
    if not headers:
        raise FileNotFoundError(f"DICOM не читаются: {folder}")

    headers.sort(key=lambda t: t[2])
    z_pos = np.array([t[2] for t in headers])

    ref = headers[len(headers) // 2][1]
    ps = float(getattr(ref, "PixelSpacing", [1, 1])[0]) if hasattr(ref, "PixelSpacing") else 1.0
    st = abs(z_pos[1] - z_pos[0]) if len(z_pos) > 1 else 1.0
    iop = list(getattr(ref, "ImageOrientationPatient", [1, 0, 0, 0, 1, 0]))
    rows = int(ref.Rows)
    cols = int(ref.Columns)

    n = len(headers)
    volume = np.empty((n, rows, cols), dtype=dtype)
    for i, (path, _, _) in enumerate(headers):
        ds = pydicom.dcmread(path)
        a = ds.pixel_array.astype(np.float32)
        a = a * float(getattr(ds, "RescaleSlope", 1)) + float(getattr(ds, "RescaleIntercept", 0))
        volume[i] = a.astype(dtype)
        del ds, a

    meta = {
        "spacing_xy": ps,
        "spacing_z": st,
        "n_slices": n,
        "patient_id": str(getattr(ref, "PatientID", "unknown")),
        "patient_name": str(getattr(ref, "PatientName", "")),
        "study_date": str(getattr(ref, "StudyDate", "")),
        "series_desc": str(getattr(ref, "SeriesDescription", "")),
        "iop": iop,
        "shape": volume.shape,
    }

    print(f"  Загружено {meta['n_slices']} срезов  |  "
          f"spacing {ps:.3f}×{ps:.3f}×{st:.3f} мм  |  "
          f"объём {volume.shape}")
    return volume, z_pos, meta


# ─────────────────────────────────────────────────────────────────────────────
# 2. СЕГМЕНТАЦИЯ  (✅ перенос из v2)
# ─────────────────────────────────────────────────────────────────────────────

def segment_bones_slice(img_hu: np.ndarray):
    """Возвращает labeled-маску и regionprops для всех костных объектов на срезе."""
    mask = (img_hu >= HU_CORTICAL_MIN) & (img_hu <= HU_CORTICAL_MAX)
    mask = morphology.closing(mask, morphology.disk(3))
    mask = ndimage.binary_fill_holes(mask)
    mask = morphology.opening(mask, morphology.disk(2))

    labeled = measure.label(mask)
    regions = [r for r in measure.regionprops(labeled) if r.area > 40]
    return labeled, regions


# ─────────────────────────────────────────────────────────────────────────────
# 3. SEED-ТРЕКИНГ  (ПЕРЕПИСАНО ПОЛНОСТЬЮ — заменяет build_radius_axis_3d)
# ─────────────────────────────────────────────────────────────────────────────

def _roi_bone_centroid(img_hu, prev_y, prev_x,
                       half=TRACK_ROI_HALF, hu=TRACK_HU, min_area=TRACK_MIN_AREA):
    """
    Ищет кость в окне ROI вокруг предсказанной позиции (prev_y, prev_x).

    Ключевое отличие от segment_bones_slice: мягкий порог (HU≥400, а не 700) и
    closing БЕЗ opening — это исключает «мерцание» тонкого кортикального кольца
    диафиза, на котором рвался трекинг v2/первой редакции v3. ROI ограничивает
    поиск так, что трекер физически не может перепрыгнуть на соседнюю кость или
    вторую руку.

    Возвращает (cy, cx, area) в глобальных координатах среза или None.
    """
    ny, nx = img_hu.shape
    y0, y1 = max(0, int(prev_y) - half), min(ny, int(prev_y) + half)
    x0, x1 = max(0, int(prev_x) - half), min(nx, int(prev_x) + half)
    sub = img_hu[y0:y1, x0:x1].astype(np.float32)

    mask = sub >= hu
    mask = morphology.closing(mask, morphology.disk(2))
    mask = ndimage.binary_fill_holes(mask)
    labeled = measure.label(mask)
    regions = [r for r in measure.regionprops(labeled) if r.area > min_area]
    if not regions:
        return None

    # Ближайшая к центру окна компонента (= к предсказанной позиции кости)
    cyl, cxl = prev_y - y0, prev_x - x0
    best = min(regions, key=lambda r: np.hypot(r.centroid[0] - cyl,
                                               r.centroid[1] - cxl))
    return (best.centroid[0] + y0, best.centroid[1] + x0, int(best.area))


def track_from_seed(volume, seed_slice, seed_y, seed_x,
                    max_jump=TRACK_MAX_JUMP, miss_max=TRACK_MISS_MAX):
    """
    ROI-трекинг лучевой кости от точки, указанной пользователем (клик).

    - Идёт вперёд и назад от seed_slice.
    - На каждом срезе ищет кость в окне ROI вокруг позиции с предыдущего
      успешного среза (см. _roi_bone_centroid): мягкий порог + closing без
      opening устойчивы к «мерцанию» сегментации тонкого диафиза.
    - max_jump (px): защита от скачка на соседний объект; при превышении срез
      пропускается, но позиция «прошлого» сохраняется (переживаем разрыв).
    - miss_max: число подряд пропущенных срезов до завершения ветви (конец
      кости / выход из FOV / эпифиз).
    - НЕ использует laterality, fov_split, предположения об анатомии.

    Возвращает: z_arr, y_arr, x_arr — координаты центроидов (отсортированы по z).
    """
    n = volume.shape[0]
    seed_slice = max(0, min(int(round(seed_slice)), n - 1))
    tracked = {}  # z_index -> (y, x)

    # Инициализация на seed-срезе с РЕЦЕНТРИРОВАНИЕМ: клик пользователя может
    # быть смещён от центра кости, из-за чего узкое ROI обрежет кость и занизит
    # площадь. Сначала ловим кость широким окном, затем уточняем позицию и
    # площадь обычным окном уже вокруг найденного центроида.
    start = _roi_bone_centroid(volume[seed_slice], seed_y, seed_x,
                               half=TRACK_ROI_HALF * 2, hu=HU_BONE_MIN)
    if start is None:
        raise ValueError("Рядом с точкой seed не найдено кости. "
                         "Повторите выбор seed точнее по лучевой кости.")
    refined = _roi_bone_centroid(volume[seed_slice], start[0], start[1])
    if refined is not None:
        start = refined
    tracked[seed_slice] = (start[0], start[1])

    def walk(rng, start_pos, start_area):
        """
        Идёт по срезам с ПРОГНОЗОМ позиции (экстраполяция по локальной
        скорости центроида) и контролем площади. Прогноз вместо простого
        «prev» удерживает трекер на изгибах и не даёт перепрыгнуть на
        соседнюю кость в зоне их сближения.
        """
        hist_pos = [start_pos]      # последние принятые (y, x)
        hist_area = [start_area]    # последние принятые площади
        prev = start_pos
        miss = 0
        for i in rng:
            # Прогноз позиции по двум последним точкам (постоянная скорость)
            if len(hist_pos) >= 2:
                vy = hist_pos[-1][0] - hist_pos[-2][0]
                vx = hist_pos[-1][1] - hist_pos[-2][1]
                pred = (prev[0] + vy, prev[1] + vx)
            else:
                pred = prev

            r = _roi_bone_centroid(volume[i], pred[0], pred[1])
            if r is not None:
                d = np.hypot(r[0] - pred[0], r[1] - pred[1])
                # merge-контроль с «прогревом»: включается только после
                # накопления ≥5 принятых площадей (иначе медиана недостоверна).
                if len(hist_area) >= 5:
                    med_area = float(np.median(hist_area[-7:]))
                    merged = r[2] > TRACK_AREA_MERGE * med_area
                else:
                    merged = False
                if d <= max_jump and not merged:
                    tracked[i] = (r[0], r[1])
                    prev = (r[0], r[1])
                    hist_pos.append(prev)
                    hist_area.append(r[2])
                    miss = 0
                    continue
            miss += 1
            if miss > miss_max:
                break

    start_pos = (start[0], start[1])
    walk(range(seed_slice + 1, n), start_pos, start[2])
    walk(range(seed_slice - 1, -1, -1), start_pos, start[2])

    zs = sorted(tracked.keys())
    z_arr = np.array(zs, dtype=float)
    y_arr = np.array([tracked[z][0] for z in zs], dtype=float)
    x_arr = np.array([tracked[z][1] for z in zs], dtype=float)

    print(f"  Трекинг от seed (срез {seed_slice}): найдено {len(zs)} срезов "
          f"[{zs[0]}–{zs[-1]}]")
    return z_arr, y_arr, x_arr


class Axis:
    """
    Ось кости как пара сглаживающих кубических сплайнов y(z), x(z).

    В отличие от полинома ст.3, сплайн корректно описывает длинный
    S-образный изгиб деформированной кости (диапазон в сотни срезов) с
    низким остатком, давая правильные ЛОКАЛЬНЫЕ касательные для построения
    перпендикулярных MPR-плоскостей.

    Методы val_y/val_x — координаты оси; der_y/der_x — производные dy/dz, dx/dz.
    """

    def __init__(self, spl_y, spl_x, z_min, z_max):
        self._sy = spl_y
        self._sx = spl_x
        self._dy = spl_y.derivative()
        self._dx = spl_x.derivative()
        self.z_min = int(z_min)
        self.z_max = int(z_max)

    def val_y(self, z):
        return float(self._sy(z))

    def val_x(self, z):
        return float(self._sx(z))

    def der_y(self, z):
        return float(self._dy(z))

    def der_x(self, z):
        return float(self._dx(z))

    def y_curve(self, z_arr):
        return self._sy(z_arr)

    def x_curve(self, z_arr):
        return self._sx(z_arr)


def build_axis(z_arr, y_arr, x_arr, sigma=3.0, rms_target=1.2):
    """
    Строит ось кости сглаживающими сплайнами с фильтрацией выбросов >sigma·σ.

    Параметр сглаживания s сплайна подбирается так, чтобы остаток (RMS
    отклонения центроидов от оси) был около rms_target px — компромисс между
    следованием за изгибом и устойчивостью к шуму сегментации.

    Возвращает: axis (Axis), residual_px, z, y, x (отфильтрованные центроиды).
    """
    if len(z_arr) < 5:
        raise ValueError(f"Недостаточно срезов для оси ({len(z_arr)}).")

    z, y, x = z_arr.copy(), y_arr.copy(), x_arr.copy()
    n = len(z)

    def make_splines(z, y, x):
        # s = m * rms^2 — целевая суммарная невязка для UnivariateSpline
        m = len(z)
        s = m * (rms_target ** 2)
        sy = UnivariateSpline(z, y, k=3, s=s)
        sx = UnivariateSpline(z, x, k=3, s=s)
        return sy, sx

    sy, sx = make_splines(z, y, x)
    res = np.hypot(y - sy(z), x - sx(z))
    thr = res.mean() + sigma * res.std()
    keep = res <= max(thr, 1e-6)
    if 5 <= keep.sum() < n:
        z, y, x = z[keep], y[keep], x[keep]
        sy, sx = make_splines(z, y, x)

    residual_px = float(np.sqrt(np.mean((y - sy(z)) ** 2 + (x - sx(z)) ** 2)))
    axis = Axis(sy, sx, z.min(), z.max())

    print(f"  Ось: сглаж. сплайн по {len(z)} срезам "
          f"(отброшено {n - len(z)}), остаток {residual_px:.2f} px")
    return axis, residual_px, z, y, x


# ─────────────────────────────────────────────────────────────────────────────
# 3b. ПАТЕНТНЫЙ МЕТОД: прямая ось + перпендикулярные срезы + угол от опоры
# ─────────────────────────────────────────────────────────────────────────────
#
# Метод по патенту (Формула торсии): торсия = Угол B − Угол A, где оба угла
# измеряются от ОБЩЕЙ фронтальной направляющей на срезах, ПЕРПЕНДИКУЛЯРНЫХ оси
# лучевой кости. Ключевой момент, выясненный на данных Кондратьева: измерять
# углы на оригинальных аксиальных срезах НЕЛЬЗЯ — при наклоне/изгибе кости
# азимут ориентира искажается по-разному на проксимальном и дистальном уровнях,
# и торсия уезжает. Поэтому строится ПРЯМАЯ ось и срезы ⊥ ей (как MPR в Philips).


class StraightAxis:
    """
    Прямая ось лучевой кости (хорда прокс→дист) и ортонормированный базис
    (z' вдоль оси, x'/y' в плоскости среза) в ФИЗИЧЕСКИХ координатах (мм).

    Все перпендикулярные срезы используют ОДИН базис (x',y') → углы на разных
    уровнях измеряются в общей системе и их разность (торсия) корректна.
    """

    def __init__(self, p_prox_idx, p_dist_idx, spacing):
        self.spacing = np.asarray(spacing, float)        # (sz, sxy, sxy)
        self.p_prox = np.asarray(p_prox_idx, float)      # концы в индексах (z,y,x)
        self.p_dist = np.asarray(p_dist_idx, float)
        pp = self.p_prox * self.spacing
        pd = self.p_dist * self.spacing
        z = pd - pp
        self.zaxis = z / np.linalg.norm(z)
        g = np.array([0.0, 1.0, 0.0])                    # глоб. Y как опора
        x = g - np.dot(g, self.zaxis) * self.zaxis
        if np.linalg.norm(x) < 1e-6:
            g = np.array([0.0, 0.0, 1.0])
            x = g - np.dot(g, self.zaxis) * self.zaxis
        self.xaxis = x / np.linalg.norm(x)
        self.yaxis = np.cross(self.zaxis, self.xaxis)    # фронтальная опора

    def center_at_z(self, z_slice):
        """Точка на оси (в индексах) с заданной z-компонентой среза."""
        t = (z_slice - self.p_prox[0]) / (self.p_dist[0] - self.p_prox[0] + 1e-9)
        return self.p_prox + t * (self.p_dist - self.p_prox)

    def azimuth_of(self, vec_world):
        """Азимут 3D-вектора (мм) в плоскости ⊥ оси, от фронтальной опоры y'."""
        w = np.asarray(vec_world, float)
        wp = w - np.dot(w, self.zaxis) * self.zaxis
        return np.degrees(np.arctan2(np.dot(wp, self.xaxis), np.dot(wp, self.yaxis)))


def build_straight_axis(z_keep, y_keep, x_keep, spacing, margin=12):
    """
    Прямая ось по концам трека (с небольшим отступом от самых концов, где
    трек наименее надёжен). spacing = (sz, sxy, sxy).
    """
    order = np.argsort(z_keep)
    z, y, x = z_keep[order], y_keep[order], x_keep[order]
    i0 = min(margin, len(z) // 4)
    i1 = max(len(z) - 1 - margin, 3 * len(z) // 4)
    p_prox = np.array([z[i0], y[i0], x[i0]])
    p_dist = np.array([z[i1], y[i1], x[i1]])
    return StraightAxis(p_prox, p_dist, spacing)


def extract_local_perp_mpr(volume, z_slice, axis, saxis, center_idx,
                           size_mm=24.0, res=0.4):
    """
    MPR перпендикулярно ЛОКАЛЬНОЙ касательной оси (сглаж. сплайн axis) в точке
    z_slice — даёт круглое, чистое сечение даже на изгибе. Центр среза =
    центроид кости (center_idx, индексы z,y,x).

    Угол ориентира затем переводится в ЕДИНУЮ опорную систему saxis (через 3D),
    поэтому сечение «локальное», а измерение — «общее». Возвращает:
      mpr, res, (e_u, e_v) — мировые единичные векторы осей MPR (мм).
    """
    spacing = saxis.spacing
    # локальная касательная (в мм), нормированная
    t = np.array([1.0, axis.der_y(z_slice), axis.der_x(z_slice)]) * spacing
    t /= np.linalg.norm(t)
    g = np.array([0.0, 1.0, 0.0])
    e_u = g - np.dot(g, t) * t
    if np.linalg.norm(e_u) < 1e-6:
        g = np.array([0.0, 0.0, 1.0])
        e_u = g - np.dot(g, t) * t
    e_u /= np.linalg.norm(e_u)
    e_v = np.cross(t, e_u)

    c = np.asarray(center_idx, float) * spacing
    n = int(2 * size_mm / res)
    us = (np.arange(n) - n / 2) * res
    U, V = np.meshgrid(us, us)
    pts = c[None, None, :] + U[..., None] * e_u[None, None, :] + V[..., None] * e_v[None, None, :]
    idx = pts / spacing
    samp = ndimage.map_coordinates(
        volume, [idx[..., 0].ravel(), idx[..., 1].ravel(), idx[..., 2].ravel()],
        order=1, mode="constant", cval=-1000)
    return samp.reshape(n, n), res, (e_u, e_v)


def measure_local_to_azimuth(mpr, res, e_uv, saxis, level, manual_uv=None):
    """
    Находит ориентир на ЛОКАЛЬНОМ ⊥-срезе (или берёт ручную точку manual_uv),
    переводит направление центр→ориентир в 3D и возвращает АЗИМУТ в единой
    опорной системе saxis. Это и есть угол A/B патента в общей системе.
    """
    e_u, e_v = e_uv
    lab, rad, uln = _radius_region_at_center(mpr)
    if rad is None:
        return None
    cy, cx = rad.centroid
    if manual_uv is not None:
        lx, ly = float(manual_uv[0]), float(manual_uv[1])
        dev = None
    else:
        cont = max(measure.find_contours((lab == rad.label).astype(float), 0.5), key=len)
        th = np.arctan2(cont[:, 0] - cy, cont[:, 1] - cx)
        rr = np.hypot(cont[:, 0] - cy, cont[:, 1] - cx)
        o = np.argsort(th)
        ths, rs, conto = th[o], rr[o], cont[o]
        w = max(5, len(rs) // 8)
        w += (w % 2 == 0)
        d = rs - median_filter(rs, size=w, mode="wrap")
        if level == "prox":
            k = int(np.argmax(d))
        else:
            if uln is not None:
                ud = np.arctan2(uln.centroid[0] - cy, uln.centroid[1] - cx)
                insec = np.abs(np.angle(np.exp(1j * (ths - ud)))) <= np.radians(80)
                k = int(np.argmin(np.where(insec, d, 1e9)))
            else:
                k = int(np.argmin(d))
        ly, lx = conto[k]
        dev = float(d[k])
    # направление в мире: (столбец u → e_u, строка v → e_v)
    vec_world = (lx - cx) * res * e_u + (ly - cy) * res * e_v
    az = saxis.azimuth_of(vec_world)
    return {"azimuth": az, "lx": lx, "ly": ly, "cx": cx, "cy": cy,
            "dev": dev, "lab": lab, "rad": rad, "uln": uln, "mpr": mpr}


def extract_perp_mpr(volume, center_idx, saxis, size_mm=24.0, res=0.4):
    """
    MPR перпендикулярно ПРЯМОЙ оси (общий базис x',y'). Возвращает изображение
    и функцию duv→3D-направление для перевода точки в азимут.
    Координаты MPR: столбец u вдоль x', строка v вдоль y'; центр = центр оси.
    """
    spacing = saxis.spacing
    c = np.asarray(center_idx, float) * spacing
    n = int(2 * size_mm / res)
    us = (np.arange(n) - n / 2) * res
    U, V = np.meshgrid(us, us)
    pts = (c[None, None, :]
           + U[..., None] * saxis.xaxis[None, None, :]
           + V[..., None] * saxis.yaxis[None, None, :])
    idx = pts / spacing
    samp = ndimage.map_coordinates(
        volume, [idx[..., 0].ravel(), idx[..., 1].ravel(), idx[..., 2].ravel()],
        order=1, mode="constant", cval=-1000)
    return samp.reshape(n, n), us, res


def _radius_region_at_center(mpr):
    """Сегментация: компонента кости, ближайшая к центру MPR (= лучевая на оси)."""
    n = mpr.shape[0]
    c = n / 2.0
    mask = (mpr >= HU_CORTICAL_MIN) & (mpr <= HU_CORTICAL_MAX)
    mask = morphology.closing(mask, morphology.disk(2))
    mask = ndimage.binary_fill_holes(mask)
    lab = measure.label(mask)
    regs = [r for r in measure.regionprops(lab) if r.area > 40]
    if not regs:
        return None, None, None
    rad = min(regs, key=lambda r: np.hypot(r.centroid[0] - c, r.centroid[1] - c))
    others = [r for r in regs if r.label != rad.label]
    uln = (min(others, key=lambda r: np.hypot(r.centroid[0] - rad.centroid[0],
                                              r.centroid[1] - rad.centroid[1]))
           if others else None)
    return lab, rad, uln


def measure_level_patent(mpr, res, saxis, level, manual_uv=None):
    """
    Измеряет угол ориентира на ⊥-срезе от фронтальной опоры.

    level: "prox" → бугристость (макс. выступ контура);
           "dist" → ульнарная вырезка (макс. вогнутость в секторе к локтевой).
    manual_uv: (u_col, v_row) — если задано, точка взята от врача (правка кликом),
               сегментация для точки не используется.

    Возвращает dict с углом (азимут от опоры), точкой ориентира (в пикс. MPR),
    центром кости и т.п., либо None.
    """
    lab, rad, uln = _radius_region_at_center(mpr)
    if rad is None:
        return None
    cy, cx = rad.centroid

    if manual_uv is not None:
        lx, ly = float(manual_uv[0]), float(manual_uv[1])
        dev = None
    else:
        cont = max(measure.find_contours((lab == rad.label).astype(float), 0.5), key=len)
        th = np.arctan2(cont[:, 0] - cy, cont[:, 1] - cx)
        rr = np.hypot(cont[:, 0] - cy, cont[:, 1] - cx)
        o = np.argsort(th)
        ths, rs, conto = th[o], rr[o], cont[o]
        w = max(5, len(rs) // 8)
        w += (w % 2 == 0)
        d = rs - median_filter(rs, size=w, mode="wrap")
        if level == "prox":
            k = int(np.argmax(d))
        else:
            if uln is not None:
                ud = np.arctan2(uln.centroid[0] - cy, uln.centroid[1] - cx)
                insec = np.abs(np.angle(np.exp(1j * (ths - ud)))) <= np.radians(80)
                dd = np.where(insec, d, 1e9)
                k = int(np.argmin(dd))
            else:
                k = int(np.argmin(d))
        ly, lx = conto[k]
        dev = float(d[k])

    # направление центр→ориентир в координатах MPR (u=x', v=y'), затем в 3D
    du = (lx - cx) * res
    dv = (ly - cy) * res
    vec_world = du * saxis.xaxis + dv * saxis.yaxis
    ang = np.degrees(np.arctan2(np.dot(vec_world, saxis.xaxis),
                                np.dot(vec_world, saxis.yaxis)))
    return {"angle_deg": ang, "lx": lx, "ly": ly, "cx": cx, "cy": cy,
            "dev": dev, "lab": lab, "rad": rad, "uln": uln, "mpr": mpr}


def torsion_patent(angle_prox, angle_dist):
    """Торсия = B − A, нормализованная в [−180, 180]."""
    t = angle_dist - angle_prox
    while t > 180:
        t -= 360
    while t < -180:
        t += 360
    return round(t, 1)


# ─────────────────────────────────────────────────────────────────────────────
# 4. MPR  (✅ перенос из v2)
# ─────────────────────────────────────────────────────────────────────────────

def compute_perpendicular_plane(slice_idx, axis, spacing_xy, spacing_z):
    """Параметры плоскости ⊥ оси кости в точке slice_idx."""
    z = float(slice_idx)
    dy_dz = axis.der_y(z)
    dx_dz = axis.der_x(z)

    perp_y = -dy_dz
    perp_x = dx_dz
    norm = np.sqrt(perp_y ** 2 + perp_x ** 2)
    if norm < 1e-9:
        perp_y, perp_x = 0.0, 1.0
    else:
        perp_y /= norm
        perp_x /= norm

    center_y = axis.val_y(z)
    center_x = axis.val_x(z)
    return (center_y, center_x), (perp_y, perp_x)


def extract_mpr_slice(volume, slice_idx, axis,
                      spacing_xy, spacing_z, size_px=120):
    """MPR-срез ⊥ оси кости. Возвращает 2D-массив HU size_px×size_px."""
    (cy, cx), (perp_y, perp_x) = compute_perpendicular_plane(
        slice_idx, axis, spacing_xy, spacing_z)

    e1 = np.array([perp_y, perp_x])
    e2_raw = np.array([1.0, 0.0])
    e2 = e2_raw - np.dot(e2_raw, e1) * e1
    norm2 = np.linalg.norm(e2)
    e2 = np.array([0.0, 1.0]) if norm2 < 1e-9 else e2 / norm2

    half = size_px // 2
    coords_i, coords_j, coords_k = [], [], []
    for pi in range(-half, half):
        for pj in range(-half, half):
            dy = pi * e1[0] + pj * e2[0]
            dx = pi * e1[1] + pj * e2[1]
            coords_i.append(slice_idx)
            coords_j.append(cy + dy)
            coords_k.append(cx + dx)

    interp = ndimage.map_coordinates(
        volume,
        [np.array(coords_i), np.array(coords_j), np.array(coords_k)],
        order=1, mode="constant", cval=HU_CORTICAL_MIN - 100)
    return interp.reshape(size_px, size_px)


# ─────────────────────────────────────────────────────────────────────────────
# 5. ИЗМЕРЕНИЕ УГЛА НА MPR  (⚠ переписано: PCA-эллипс + секторный поиск)
# ─────────────────────────────────────────────────────────────────────────────

def measure_angle_landmark(mpr, level="proximal", expected_dir=None):
    """
    Измерение угла ориентира лучевой кости на MPR-срезе.

    Стратегия:
      1. Сегментировать кость, взять крупнейший объект.
      2. Базовый угол — главная ось PCA эллипса (region.orientation).
         Это устойчивее слабого полярного сигнала (проблема v2).
      3. Уточнение по контуру:
         proximal — локальный МАКСИМУМ радиуса (бугристость, выступ);
                    при заданном expected_dir поиск ограничен сектором ±45°.
         distal   — локальный МИНИМУМ радиуса (ульнарная вырезка, вогнутость).
      4. Угол ориентира = направление от центра к найденной точке.

    Возвращает dict (angle_deg по ориентиру, pca_angle_deg, prominence_px, ...)
    или None.
    """
    mask = (mpr >= HU_CORTICAL_MIN) & (mpr <= HU_CORTICAL_MAX)
    mask = morphology.closing(mask, morphology.disk(3))
    mask = ndimage.binary_fill_holes(mask)

    labeled = measure.label(mask)
    regions = [r for r in measure.regionprops(labeled) if r.area > 30]
    if not regions:
        return None

    region = max(regions, key=lambda r: r.area)
    cy, cx = region.centroid

    # PCA-угол главной оси эллипса
    pca_angle = np.degrees(region.orientation)

    bone_mask = (labeled == region.label).astype(float)
    contours = measure.find_contours(bone_mask, 0.5)
    if not contours:
        return None
    contour = max(contours, key=len)

    ys, xs = contour[:, 0], contour[:, 1]
    dy, dx = ys - cy, xs - cx
    theta = np.arctan2(dy, dx)
    rad = np.hypot(dy, dx)

    order = np.argsort(theta)
    theta_s = theta[order]
    rad_s = rad[order]

    n = len(rad_s)
    if n < 20:
        return None
    win = max(5, n // 8)
    if win % 2 == 0:
        win += 1
    rad_smooth = median_filter(rad_s, size=win, mode="wrap")
    deviation = rad_s - rad_smooth

    # Ограничение сектором ±45° вокруг ожидаемого направления (для бугристости)
    if expected_dir is not None:
        sector = np.abs(np.angle(np.exp(1j * (theta_s - expected_dir)))) <= np.radians(45)
        if sector.sum() >= 5:
            search = np.where(sector)[0]
        else:
            search = np.arange(n)
    else:
        search = np.arange(n)

    dev_search = deviation[search]
    if level == "proximal":
        idx = search[int(np.argmax(dev_search))]
    else:
        idx = search[int(np.argmin(dev_search))]

    lm_theta = theta_s[idx]
    lm_r = rad_s[idx]
    lm_y = cy + lm_r * np.sin(lm_theta)
    lm_x = cx + lm_r * np.cos(lm_theta)

    angle_deg = np.degrees(lm_theta)
    prominence = abs(float(deviation[idx]))
    unitvec = np.array([np.sin(lm_theta), np.cos(lm_theta)])

    return {
        "angle_deg": angle_deg,
        "pca_angle_deg": pca_angle,
        "centroid": (cy, cx),
        "landmark": (lm_y, lm_x),
        "unitvec": unitvec,
        "region": region,
        "labeled": labeled,
        "prominence_px": prominence,
    }


def compute_torsion(angle_prox, angle_dist):
    """Торсия = нормализованная разность углов в [−180, +180]."""
    delta = angle_dist - angle_prox
    while delta > 180:
        delta -= 360
    while delta < -180:
        delta += 360
    return round(delta, 1)


# ─────────────────────────────────────────────────────────────────────────────
# 6а. АВТООПРЕДЕЛЕНИЕ ПОРАЖЁННОЙ КОНЕЧНОСТИ
# ─────────────────────────────────────────────────────────────────────────────

def detect_affected_side(volume, meta,
                         seed_a, seed_b,
                         label_a="left", label_b="right"):
    """
    Определяет поражённую конечность по длине трека диафиза.

    При гемипаретическом ДЦП поражённая рука КОРОЧЕ здоровой —
    хроническая спастичность тормозит рост кости. Длина трека
    (z_max − z_min) × spacing_z надёжно отражает это различие
    в двустороннем КТ-скане.

    Параметры
    ----------
    volume  : 3D-массив HU  (z, y, x)
    meta    : dict из load_dicom_series (нужен spacing_z)
    seed_a  : (z, y, x) — seed первой кости
    seed_b  : (z, y, x) — seed второй кости
    label_a : строка-метка для seed_a (напр. "left")
    label_b : строка-метка для seed_b (напр. "right")

    Возвращает
    ----------
    dict с ключами:
      affected        — метка поражённой стороны (label_a или label_b)
      healthy         — метка здоровой стороны
      axis_affected   — Axis объект поражённой руки
      axis_healthy    — Axis объект здоровой руки
      len_affected_mm — длина трека поражённой, мм
      len_healthy_mm  — длина трека здоровой, мм
      ratio           — len_affected / len_healthy  (норм. < 1.0)
      track_a         — (z, y, x) трек seed_a
      track_b         — (z, y, x) трек seed_b
    """
    spz = float(meta["spacing_z"])

    za, ya, xa = track_from_seed(volume, int(seed_a[0]),
                                 float(seed_a[1]), float(seed_a[2]))
    zb, yb, xb = track_from_seed(volume, int(seed_b[0]),
                                 float(seed_b[1]), float(seed_b[2]))

    ax_a, *_ = build_axis(za, ya, xa)
    ax_b, *_ = build_axis(zb, yb, xb)

    len_a = (ax_a.z_max - ax_a.z_min) * spz   # мм
    len_b = (ax_b.z_max - ax_b.z_min) * spz   # мм

    if len_a <= len_b:
        aff_label, hlt_label = label_a, label_b
        ax_aff, ax_hlt       = ax_a, ax_b
        len_aff, len_hlt     = len_a, len_b
        trk_aff, trk_hlt     = (za,ya,xa), (zb,yb,xb)
    else:
        aff_label, hlt_label = label_b, label_a
        ax_aff, ax_hlt       = ax_b, ax_a
        len_aff, len_hlt     = len_b, len_a
        trk_aff, trk_hlt     = (zb,yb,xb), (za,ya,xa)

    ratio = len_aff / len_hlt if len_hlt > 0 else float("nan")

    print(f"  Авто-детекция поражённой стороны:")
    print(f"    {label_a}: {len_a:.0f} мм  |  {label_b}: {len_b:.0f} мм")
    print(f"    → Поражённая: {aff_label} ({len_aff:.0f} мм, ratio={ratio:.2f})")

    return {
        "affected":       aff_label,
        "healthy":        hlt_label,
        "axis_affected":  ax_aff,
        "axis_healthy":   ax_hlt,
        "len_affected_mm": len_aff,
        "len_healthy_mm":  len_hlt,
        "ratio":           ratio,
        "track_affected":  trk_aff,
        "track_healthy":   trk_hlt,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 6. ПОИСК КАНДИДАТОВ УРОВНЕЙ
# ─────────────────────────────────────────────────────────────────────────────

def find_level_candidates(volume, axis, s_lo, s_hi, meta,
                          level, n_out=N_CANDIDATES):
    """
    Сканирует ось в АБСОЛЮТНОМ диапазоне срезов [s_lo, s_hi], считает
    prominence ориентира, возвращает кандидатов по убыванию prominence.

    Диапазон задаётся анатомически (а не долей трека): проксимальный —
    вокруг seed-точки бугристости, дистальный — у дистального конца кости
    (см. вызовы в run). Это устойчивее к тому, что трек захватывает локоть
    сверху и обрывается до запястья снизу.

    Каждый кандидат: dict {slice_idx, mpr, measurement(prominence, angle, ...)}.
    """
    a, b = int(s_lo), int(s_hi)
    if b <= a:
        a, b = int(axis.z_min), int(axis.z_max)

    candidates = []
    for s in range(a, b + 1, LEVEL_SCAN_STEP):
        mpr = extract_mpr_slice(volume, s, axis,
                                meta["spacing_xy"], meta["spacing_z"])
        m = measure_angle_landmark(mpr, level)
        if m is None:
            continue
        candidates.append({"slice_idx": s, "mpr": mpr, "measurement": m,
                           "prominence": m["prominence_px"]})

    candidates.sort(key=lambda c: c["prominence"], reverse=True)
    return candidates[:n_out]


# ─────────────────────────────────────────────────────────────────────────────
# 7. РЕНДЕР ПАНЕЛЕЙ ДЛЯ PDF  (✅ перенос/адаптация из v2)
# ─────────────────────────────────────────────────────────────────────────────

def render_mpr_panel(mpr, angle_deg, centroid, eigenvec, region, labeled,
                     title, color, level_label, landmark=None):
    """MPR-срез в стиле CT Viewer: контур + линия к ориентиру с углом."""
    fig, ax = plt.subplots(figsize=(4, 4), facecolor=C_BG)
    ax.set_facecolor(C_BG)

    ax.imshow(_bone_window(mpr), cmap="gray", origin="upper",
              interpolation="bilinear")

    if labeled is not None and region is not None:
        bone_mask = (labeled == region.label)
        for c in measure.find_contours(bone_mask.astype(float), 0.5):
            ax.plot(c[:, 1], c[:, 0], color=C_RADIUS, lw=1.8, alpha=0.9)

    if centroid is not None and eigenvec is not None:
        cy, cx = centroid
        if landmark is not None:
            ly, lx = landmark
            ax.plot([cx, lx], [cy, ly], color=C_RADIUS, lw=2.4)
            ax.plot(lx, ly, "o", color=C_AXIS, markersize=8, mew=1.5,
                    markeredgecolor="white", zorder=6)
            ax.plot([cx, 2 * cx - lx], [cy, 2 * cy - ly],
                    color=C_RADIUS, lw=1.0, ls=":", alpha=0.6)
            ax.text(lx + 3, ly - 3, f"{angle_deg:.1f}°",
                    color=C_RADIUS, fontsize=10, fontweight="bold",
                    bbox=dict(facecolor=C_BG, alpha=0.7, edgecolor="none", pad=1))
        else:
            L = max(22, np.sqrt(region.area / np.pi) * 2.0) if region else 25
            ax.annotate("", xy=(cx + eigenvec[1] * L, cy + eigenvec[0] * L),
                        xytext=(cx - eigenvec[1] * L, cy - eigenvec[0] * L),
                        arrowprops=dict(arrowstyle="<->", color=C_RADIUS, lw=2.2))
            ax.text(cx + eigenvec[1] * L + 3, cy + eigenvec[0] * L - 3,
                    f"{angle_deg:.1f}° (PCA)", color="#fbbf24",
                    fontsize=9, fontweight="bold",
                    bbox=dict(facecolor=C_BG, alpha=0.7, edgecolor="none", pad=1))
        ax.plot(cx, cy, "+", color="white", markersize=11, mew=2, zorder=5)

    ax.text(5, 8, level_label, color=color, fontsize=9, fontweight="bold",
            bbox=dict(facecolor=C_BG, alpha=0.8, edgecolor=color, pad=2, lw=1))
    ax.set_xlim(0, mpr.shape[1])
    ax.set_ylim(mpr.shape[0], 0)
    ax.axis("off")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, facecolor=C_BG,
                bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
    buf.seek(0)
    return buf


def render_frontal_panel(volume, axis,
                         z_centroids, y_centroids, x_centroids,
                         prox_idx, dist_idx, z_min, z_max):
    """Фронтальный (корональный) MIP с осью и плоскостями уровней."""
    nz, ny, nx = volume.shape
    bone_vol = np.clip(volume, HU_BONE_MIN, 1800)
    mip_zx = bone_vol.max(axis=1)

    fig, ax = plt.subplots(figsize=(5.0, 5.5), facecolor=C_BG)
    ax.set_facecolor(C_BG)

    vmin, vmax = np.percentile(mip_zx, 2), np.percentile(mip_zx, 99.5)
    norm = np.clip((mip_zx - vmin) / (vmax - vmin + 1e-9), 0, 1)
    ax.imshow(norm, cmap="gray", origin="upper", aspect="auto",
              extent=[0, nx, nz, 0], interpolation="bilinear")

    z_line = np.linspace(z_min, z_max, 200)
    x_line = axis.x_curve(z_line)
    ax.plot(x_line, z_line, color=C_AXIS, lw=1.6, alpha=0.85, label="Ось кости")
    ax.scatter(x_centroids, z_centroids, s=4, color="#fde68a", alpha=0.5, zorder=3)

    def draw_plane(idx, color, label):
        cx = axis.val_x(idx)
        dx_dz = axis.der_x(idx)
        half = 55
        norm_v = np.hypot(1.0, dx_dz)
        perp_x = 1.0 / norm_v
        perp_z = -dx_dz / norm_v
        ax.plot([cx - perp_x * half, cx + perp_x * half],
                [idx - perp_z * half, idx + perp_z * half],
                color=color, lw=2.4, label=label)
        ax.plot(cx, idx, "o", color=color, markersize=6, zorder=5)

    draw_plane(prox_idx, C_PROX, f"Проксим. (срез {prox_idx})")
    draw_plane(dist_idx, C_DIST, f"Дист. (срез {dist_idx})")

    ax.set_xlim(0, nx)
    ax.set_ylim(nz, 0)
    ax.set_xlabel("X (латер.-медиал.)", color=C_SUBTEXT, fontsize=8)
    ax.set_ylabel("Срез (проксим. → дист.)", color=C_SUBTEXT, fontsize=8)
    ax.tick_params(colors=C_SUBTEXT, labelsize=7)
    for s in ax.spines.values():
        s.set_color("#2d3748")
    ax.legend(fontsize=7, facecolor=C_BG, labelcolor=C_TEXT,
              framealpha=0.8, loc="upper right")
    ax.set_title("Контроль плоскостей (фронтальный вид)",
                 color=C_TEXT, fontsize=9, pad=4)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=140, facecolor=C_BG,
                bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
    buf.seek(0)
    return buf


def render_torsion_diagram(torsion_deg, angle_prox, angle_dist):
    """Схема угла торсии — круг с двумя осями."""
    fig, ax = plt.subplots(figsize=(3.2, 3.2), facecolor=C_BG)
    ax.set_facecolor(C_BG)
    ax.set_aspect("equal")

    theta_p = np.radians(angle_prox)
    theta_d = np.radians(angle_dist)
    L = 0.82
    ax.annotate("", xy=(np.cos(theta_p) * L, np.sin(theta_p) * L),
                xytext=(-np.cos(theta_p) * L, -np.sin(theta_p) * L),
                arrowprops=dict(arrowstyle="<->", color=C_PROX, lw=2.5))
    ax.annotate("", xy=(np.cos(theta_d) * L, np.sin(theta_d) * L),
                xytext=(-np.cos(theta_d) * L, -np.sin(theta_d) * L),
                arrowprops=dict(arrowstyle="<->", color=C_DIST, lw=2.5))
    arcs = np.linspace(min(theta_p, theta_d), max(theta_p, theta_d), 60)
    ax.plot(np.cos(arcs) * 0.42, np.sin(arcs) * 0.42, color=C_AXIS, lw=2.2)

    sign = "+" if torsion_deg >= 0 else ""
    ax.text(0, -0.05, f"{sign}{torsion_deg:.1f}°", ha="center", va="center",
            color=C_AXIS, fontsize=20, fontweight="bold")
    ax.text(0, -0.28, "наружная" if torsion_deg >= 0 else "внутренняя",
            ha="center", color=C_SUBTEXT, fontsize=9)

    ax.legend(handles=[mpatches.Patch(color=C_PROX, label="Проксим."),
                       mpatches.Patch(color=C_DIST, label="Дист.")],
              loc="lower center", fontsize=8, facecolor=C_BG,
              labelcolor=C_TEXT, framealpha=0.7, ncol=2,
              bbox_to_anchor=(0.5, -0.18))
    ax.set_xlim(-1.1, 1.1)
    ax.set_ylim(-1.1, 1.1)
    ax.axis("off")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, facecolor=C_BG,
                bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────────────────────
# 8. PDF-ОТЧЁТ  (✅ перенос из v2, обобщён на произвольный набор сторон)
# ─────────────────────────────────────────────────────────────────────────────

def build_pdf_report(results, output_path):
    """Строит PDF-отчёт. results может содержать одну или несколько сторон."""
    doc = SimpleDocTemplate(output_path, pagesize=A4,
                            leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=15 * mm, bottomMargin=15 * mm)
    W, H = A4
    content_width = W - 30 * mm
    story = []

    style_caption = ParagraphStyle("caption", fontName="Helvetica", fontSize=8,
                                   textColor=colors.HexColor(C_SUBTEXT),
                                   alignment=TA_CENTER)
    meta = results["meta"]

    header_data = [[
        Paragraph("<b>НМИЦ ДЕТСКОЙ ТРАВМАТОЛОГИИ И ОРТОПЕДИИ им. Г.И. ТУРНЕРА</b>",
                  ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=9,
                                 textColor=colors.HexColor("#a5b4fc"), alignment=TA_LEFT)),
        Paragraph("<b>ТОРСИЯ ЛУЧЕВОЙ КОСТИ</b>",
                  ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=14,
                                 textColor=colors.white, alignment=TA_CENTER)),
        Paragraph(f"Дата: {datetime.now().strftime('%d.%m.%Y')}",
                  ParagraphStyle("h3", fontName="Helvetica", fontSize=9,
                                 textColor=colors.HexColor(C_SUBTEXT), alignment=TA_RIGHT)),
    ]]
    header_table = Table(header_data, colWidths=[content_width * 0.35,
                                                 content_width * 0.35,
                                                 content_width * 0.30])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0f172a")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -1), 1.5, colors.HexColor(C_ACCENT)),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 4 * mm))

    date_str = ""
    if len(meta["study_date"]) == 8:
        d = meta["study_date"]
        date_str = f"{d[6:8]}.{d[4:6]}.{d[:4]}"
    patient_data = [["Пациент:", str(meta["patient_name"]) or str(meta["patient_id"]),
                     "ID:", meta["patient_id"], "Дата КТ:", date_str]]
    pt = Table(patient_data, colWidths=[22 * mm, 50 * mm, 12 * mm, 30 * mm, 18 * mm, 28 * mm])
    pt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#111827")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor(C_SUBTEXT)),
        ("TEXTCOLOR", (2, 0), (2, -1), colors.HexColor(C_SUBTEXT)),
        ("TEXTCOLOR", (4, 0), (4, -1), colors.HexColor(C_SUBTEXT)),
        ("TEXTCOLOR", (1, 0), (1, -1), colors.white),
        ("TEXTCOLOR", (3, 0), (3, -1), colors.white),
        ("TEXTCOLOR", (5, 0), (5, -1), colors.white),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.HexColor("#2d3748")),
    ]))
    story.append(pt)
    story.append(Spacer(1, 2 * mm))

    warn = Table([[Paragraph(
        "ПОЛУАВТОМАТИЧЕСКИЙ РАСЧЁТ (seed указан оператором) — НЕ ВЕРИФИЦИРОВАН. "
        "Требует обязательной проверки клиницистом перед использованием.",
        ParagraphStyle("warn", fontName="Helvetica-Bold", fontSize=8.5,
                       textColor=colors.white, alignment=TA_CENTER))]],
        colWidths=[content_width])
    warn.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#7c2d12")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#ea580c")),
    ]))
    story.append(warn)
    story.append(Spacer(1, 4 * mm))

    side_keys = [k for k in ("right", "left", "selected") if k in results]
    for n_side, side_key in enumerate(side_keys):
        r = results[side_key]
        side_label = {"right": "ПРАВАЯ РУКА", "left": "ЛЕВАЯ РУКА",
                      "selected": "ВЫБРАННАЯ РУКА"}[side_key]
        side_color = C_DIST if side_key == "left" else C_PROX
        torsion = r["torsion_deg"]
        sign_str = f"+{torsion:.1f}°" if torsion >= 0 else f"{torsion:.1f}°"
        direction = "наружная торсия" if torsion >= 0 else "внутренняя торсия"

        story.append(Paragraph(f"▌ {side_label}", ParagraphStyle(
            "side", fontName="Helvetica-Bold", fontSize=11,
            textColor=colors.HexColor(side_color), spaceBefore=3 * mm, spaceAfter=2 * mm)))

        diag_img = RLImage(render_torsion_diagram(torsion, r["angle_prox"], r["angle_dist"]),
                           width=42 * mm, height=42 * mm)
        result_text = [
            [Paragraph(sign_str, ParagraphStyle("bignum", fontName="Helvetica-Bold",
                       fontSize=28, textColor=colors.HexColor(C_AXIS), alignment=TA_CENTER))],
            [Paragraph(direction, ParagraphStyle("dir", fontName="Helvetica", fontSize=10,
                       textColor=colors.HexColor(C_SUBTEXT), alignment=TA_CENTER))],
            [Spacer(1, 3 * mm)],
            [Paragraph(f"<b>Прокс. угол:</b> {r['angle_prox']:.1f}° &nbsp;&nbsp; "
                       f"<b>Дист. угол:</b> {r['angle_dist']:.1f}°",
                       ParagraphStyle("angles", fontName="Helvetica", fontSize=9,
                       textColor=colors.HexColor(C_TEXT), alignment=TA_CENTER))],
            [Paragraph(f"Срезы: прокс. {r['prox_idx']} / дист. {r['dist_idx']}",
                       ParagraphStyle("slices", fontName="Helvetica", fontSize=8,
                       textColor=colors.HexColor(C_SUBTEXT), alignment=TA_CENTER))],
        ]
        result_inner = Table(result_text, colWidths=[55 * mm])
        result_inner.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0d1117")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
        top_row = Table([[diag_img, result_inner]], colWidths=[46 * mm, 60 * mm])
        top_row.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0d1117")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("LINEAFTER", (0, 0), (0, -1), 0.5, colors.HexColor("#2d3748"))]))
        story.append(top_row)
        story.append(Spacer(1, 4 * mm))

        story.append(Paragraph("① Контроль реконструкции — проверять ПЕРВЫМ",
                     ParagraphStyle("ct", fontName="Helvetica-Bold", fontSize=9,
                     textColor=colors.HexColor(C_AXIS), spaceAfter=2 * mm)))
        frontal_img = RLImage(render_frontal_panel(
            results["volume"], r["axis"],
            r["z_centroids"], r["y_centroids"], r["x_centroids"],
            r["prox_idx"], r["dist_idx"], r["z_min"], r["z_max"]),
            width=content_width * 0.55, height=content_width * 0.55 * 1.1)
        qc_lines = [
            "<b>Контроль плоскостей</b>",
            f"Ось построена по {r['n_axis_slices']} срезам",
            f"Остаток подгонки: {r['residual_px']:.2f} px",
            f"Диапазон трекинга: {r['z_min']}–{r['z_max']}",
            "", "<b>Что проверить:</b>",
            "• плоскости ⊥ оси кости",
            "• уровни на диафизе, не на эпифизах",
            "• ось проходит по центру кости",
            f"Бугристость: {r.get('prominence_prox', 0):.1f}px  "
            f"Вырезка: {r.get('prominence_dist', 0):.1f}px",
        ]
        qc_para = [[Paragraph(line if line else "&nbsp;", ParagraphStyle(
            f"qc{i}", fontName="Helvetica", fontSize=8.5,
            textColor=colors.HexColor(C_TEXT), leading=12))]
            for i, line in enumerate(qc_lines)]
        qc_table = Table(qc_para, colWidths=[content_width * 0.42])
        qc_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0d1117")),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        frontal_row = Table([[frontal_img, qc_table]],
                            colWidths=[content_width * 0.55, content_width * 0.45])
        frontal_row.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(C_BG)),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        story.append(frontal_row)
        story.append(Spacer(1, 4 * mm))

        story.append(Paragraph("② Поперечные срезы и углы",
                     ParagraphStyle("st", fontName="Helvetica-Bold", fontSize=9,
                     textColor=colors.HexColor(C_AXIS), spaceAfter=2 * mm)))
        prox_img = RLImage(render_mpr_panel(
            r["mpr_prox"], r["angle_prox"], r["centroid_prox"], r["eigenvec_prox"],
            r["region_prox"], r["labeled_prox"], "Проксимальный уровень", C_PROX,
            f"Срез {r['prox_idx']}  |  {r['angle_prox']:.1f}°",
            landmark=r.get("landmark_prox")),
            width=content_width * 0.48, height=content_width * 0.48)
        dist_img = RLImage(render_mpr_panel(
            r["mpr_dist"], r["angle_dist"], r["centroid_dist"], r["eigenvec_dist"],
            r["region_dist"], r["labeled_dist"], "Дистальный уровень", C_DIST,
            f"Срез {r['dist_idx']}  |  {r['angle_dist']:.1f}°",
            landmark=r.get("landmark_dist")),
            width=content_width * 0.48, height=content_width * 0.48)
        slices_row = Table([[prox_img, dist_img]],
                           colWidths=[content_width * 0.50, content_width * 0.50])
        slices_row.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(C_BG)),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2)]))
        story.append(slices_row)
        capt_row = Table([[Paragraph("Проксимальный уровень<br/>(зона бугристости)", style_caption),
                           Paragraph("Дистальный уровень<br/>(зона ульнарной вырезки)", style_caption)]],
                         colWidths=[content_width * 0.50, content_width * 0.50])
        capt_row.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(C_BG))]))
        story.append(capt_row)
        story.append(Spacer(1, 6 * mm))
        if n_side < len(side_keys) - 1:
            story.append(PageBreak())

    story.append(Paragraph(
        f"Сформировано автоматически  •  radius_torsion_v3  •  "
        f"{datetime.now().strftime('%d.%m.%Y %H:%M')}  •  Требует верификации клиницистом",
        ParagraphStyle("footer", fontName="Helvetica", fontSize=7,
                       textColor=colors.HexColor("#4b5563"), alignment=TA_CENTER)))
    doc.build(story)
    print(f"  PDF сохранён: {output_path}")


# ─────────────────────────────────────────────────────────────────────────────
# 9. ИНТЕРАКТИВНЫЕ ОКНА
# ─────────────────────────────────────────────────────────────────────────────

class SeedSelector:
    """
    Окно 1: выбор seed.
    Левая панель — фронтальный MIP (прореженный) с маркером текущего среза.
    Правая панель — аксиальный срез (костное окно), прокрутка ползунком.
    Клик по правой панели → seed point. Кнопка Confirm seed.
    """

    def __init__(self, volume, meta, step=DISPLAY_STEP):
        self.volume = volume
        self.meta = meta
        self.n = volume.shape[0]
        self.cur = self.n // 2
        self.seed = None  # (slice_idx, y, x)

        bone_vol = np.clip(volume, HU_BONE_MIN, 1800)
        self.mip_zx = bone_vol[::step].repeat(step, axis=0)[:self.n].max(axis=1) \
            if False else bone_vol.max(axis=1)

        self.fig = plt.figure(figsize=(14, 8), facecolor=C_BG)
        self.fig.canvas.manager.set_window_title("Окно 1 — выбор seed")
        self.ax_mip = self.fig.add_axes([0.04, 0.18, 0.40, 0.74])
        self.ax_ax = self.fig.add_axes([0.50, 0.18, 0.46, 0.74])
        for ax in (self.ax_mip, self.ax_ax):
            ax.set_facecolor(C_BG)

        vmin, vmax = np.percentile(self.mip_zx, 2), np.percentile(self.mip_zx, 99.5)
        nm = np.clip((self.mip_zx - vmin) / (vmax - vmin + 1e-9), 0, 1)
        self.ax_mip.imshow(nm, cmap="gray", origin="upper", aspect="auto",
                           extent=[0, volume.shape[2], self.n, 0])
        self.ax_mip.set_title("Фронтальный MIP\n(жёлтая линия = текущий срез)",
                              color=C_TEXT, fontsize=9)
        self.ax_mip.set_xlabel("X", color=C_SUBTEXT, fontsize=8)
        self.ax_mip.set_ylabel("Срез", color=C_SUBTEXT, fontsize=8)
        self.ax_mip.tick_params(colors=C_SUBTEXT, labelsize=7)
        self.cur_line = self.ax_mip.axhline(self.cur, color=C_AXIS, lw=1.5)

        self.im = self.ax_ax.imshow(_bone_window(volume[self.cur]), cmap="gray",
                                    origin="upper", interpolation="bilinear")
        self.ax_ax.set_title(self._axtitle(), color=C_TEXT, fontsize=9)
        self.ax_ax.axis("off")
        self.seed_marker, = self.ax_ax.plot([], [], "o", color=C_DIST,
                                            markersize=12, mew=2,
                                            markeredgecolor="white", zorder=10)

        ax_slider = self.fig.add_axes([0.50, 0.09, 0.46, 0.03], facecolor="#1f2937")
        self.slider = Slider(ax_slider, "Срез", 0, self.n - 1,
                             valinit=self.cur, valstep=1, color=C_ACCENT)
        self.slider.label.set_color(C_TEXT)
        self.slider.valtext.set_color(C_TEXT)
        self.slider.on_changed(self._on_slide)

        ax_btn = self.fig.add_axes([0.04, 0.04, 0.16, 0.06])
        self.btn = Button(ax_btn, "Confirm seed", color="#16a34a", hovercolor="#22c55e")
        self.btn.label.set_color("white")
        self.btn.on_clicked(self._on_confirm)

        self.fig.canvas.mpl_connect("button_press_event", self._on_click)
        self.fig.text(0.04, 0.93,
                      f"{meta['patient_name']} | ID {meta['patient_id']} | срезов {self.n}",
                      color=C_TEXT, fontsize=9)
        self.fig.text(0.50, 0.14,
                      "Прокрутите до среза с лучевой костью и кликните по ней → seed",
                      color=C_SUBTEXT, fontsize=8)

    def _axtitle(self):
        return f"Аксиальный срез {self.cur}  (клик → seed)"

    def _on_slide(self, val):
        self.cur = int(val)
        self.im.set_data(_bone_window(self.volume[self.cur]))
        self.ax_ax.set_title(self._axtitle(), color=C_TEXT, fontsize=9)
        self.cur_line.set_ydata([self.cur, self.cur])
        self.fig.canvas.draw_idle()

    def _on_click(self, event):
        if event.inaxes is self.ax_ax and event.xdata is not None:
            self.seed = (self.cur, float(event.ydata), float(event.xdata))
            self.seed_marker.set_data([event.xdata], [event.ydata])
            self.ax_ax.set_title(f"Seed: срез {self.cur}, "
                                 f"y={event.ydata:.0f}, x={event.xdata:.0f}",
                                 color=C_DIST, fontsize=9)
            self.fig.canvas.draw_idle()

    def _on_confirm(self, event):
        if self.seed is None:
            self.ax_ax.set_title("Сначала кликните по кости!", color=C_DIST, fontsize=10)
            self.fig.canvas.draw_idle()
            return
        plt.close(self.fig)

    def run(self):
        plt.show()
        return self.seed


class AxisConfirm:
    """Окно 2: фронтальный MIP с наложенной осью. OK / Re-seed."""

    def __init__(self, volume, axis, z_arr, x_arr, z_min, z_max, residual_px):
        self.decision = None
        self.fig = plt.figure(figsize=(7, 9), facecolor=C_BG)
        self.fig.canvas.manager.set_window_title("Окно 2 — подтверждение оси")
        ax = self.fig.add_axes([0.12, 0.16, 0.82, 0.76])
        ax.set_facecolor(C_BG)

        nz, ny, nx = volume.shape
        mip = np.clip(volume, HU_BONE_MIN, 1800).max(axis=1)
        vmin, vmax = np.percentile(mip, 2), np.percentile(mip, 99.5)
        ax.imshow(np.clip((mip - vmin) / (vmax - vmin + 1e-9), 0, 1),
                  cmap="gray", origin="upper", aspect="auto", extent=[0, nx, nz, 0])
        zl = np.linspace(z_min, z_max, 200)
        ax.plot(axis.x_curve(zl), zl, color=C_AXIS, lw=2.0, label="Ось")
        ax.scatter(x_arr, z_arr, s=6, color="#fde68a", alpha=0.6)
        ax.set_xlim(0, nx)
        ax.set_ylim(nz, 0)
        ax.set_title(f"Проверьте ось кости (остаток {residual_px:.2f} px)",
                     color=C_TEXT, fontsize=10)
        ax.tick_params(colors=C_SUBTEXT, labelsize=7)
        ax.legend(fontsize=8, facecolor=C_BG, labelcolor=C_TEXT)

        ax_ok = self.fig.add_axes([0.15, 0.05, 0.3, 0.07])
        ax_re = self.fig.add_axes([0.55, 0.05, 0.3, 0.07])
        self.btn_ok = Button(ax_ok, "OK — ось верна", color="#16a34a", hovercolor="#22c55e")
        self.btn_re = Button(ax_re, "Re-seed", color="#b91c1c", hovercolor="#ef4444")
        for b in (self.btn_ok, self.btn_re):
            b.label.set_color("white")
        self.btn_ok.on_clicked(self._ok)
        self.btn_re.on_clicked(self._re)

    def _ok(self, e):
        self.decision = "ok"
        plt.close(self.fig)

    def _re(self, e):
        self.decision = "reseed"
        plt.close(self.fig)

    def run(self):
        plt.show()
        return self.decision


class LevelSelector:
    """
    Окна 3/4: сетка 3×3 MPR-кандидатов, отсортированных по prominence.
    Клик по ячейке → выбор. Клавиша Enter → автовыбор лучшего (кандидат 0).
    """

    def __init__(self, candidates, level_label, color):
        self.candidates = candidates
        self.selected = None
        self.fig = plt.figure(figsize=(11, 11), facecolor=C_BG)
        self.fig.canvas.manager.set_window_title(f"Выбор уровня — {level_label}")
        self.fig.suptitle(f"{level_label}: кликните лучший срез "
                          f"(Enter = автовыбор #1)\nсортировка по выраженности ориентира",
                          color=C_TEXT, fontsize=11)
        self.axes = []
        for i in range(N_CANDIDATES):
            ax = self.fig.add_subplot(3, 3, i + 1)
            ax.set_facecolor(C_BG)
            if i < len(candidates):
                c = candidates[i]
                ax.imshow(_bone_window(c["mpr"]), cmap="gray", origin="upper",
                          interpolation="bilinear")
                m = c["measurement"]
                bone = (c["mpr"] >= HU_CORTICAL_MIN) & (c["mpr"] <= HU_CORTICAL_MAX)
                lab = measure.label(ndimage.binary_fill_holes(
                    morphology.closing(bone, morphology.disk(3))))
                if m.get("region") is not None:
                    cy, cx = m["centroid"]
                    ly, lx = m["landmark"]
                    ax.plot([cx, lx], [cy, ly], color=color, lw=2.0)
                    ax.plot(lx, ly, "o", color=C_AXIS, markersize=6,
                            markeredgecolor="white")
                ax.set_title(f"#{i+1}  срез {c['slice_idx']}\n"
                             f"prom {c['prominence']:.1f}px  {m['angle_deg']:.0f}°",
                             color=color, fontsize=8)
            else:
                ax.text(0.5, 0.5, "—", color=C_SUBTEXT, ha="center")
            ax.axis("off")
            self.axes.append(ax)

        self.fig.canvas.mpl_connect("button_press_event", self._on_click)
        self.fig.canvas.mpl_connect("key_press_event", self._on_key)

    def _on_click(self, event):
        for i, ax in enumerate(self.axes):
            if event.inaxes is ax and i < len(self.candidates):
                self.selected = self.candidates[i]
                plt.close(self.fig)
                return

    def _on_key(self, event):
        if event.key == "enter" and self.candidates:
            self.selected = self.candidates[0]
            plt.close(self.fig)

    def run(self):
        plt.show()
        if self.selected is None and self.candidates:
            self.selected = self.candidates[0]  # окно закрыли — автовыбор
        return self.selected


class ResultWindow:
    """Окно 5: два финальных MPR с линиями углов, значение торсии, Save PDF."""

    def __init__(self, side_result, on_save):
        r = side_result
        self.on_save = on_save
        self.fig = plt.figure(figsize=(13, 7), facecolor=C_BG)
        self.fig.canvas.manager.set_window_title("Окно 5 — результат")

        for col, (key_mpr, key_ang, lab, color, lm_key, c_key, e_key, reg_key, lblk) in enumerate([
            ("mpr_prox", "angle_prox", "Проксимальный", C_PROX, "landmark_prox",
             "centroid_prox", "eigenvec_prox", "region_prox", "labeled_prox"),
            ("mpr_dist", "angle_dist", "Дистальный", C_DIST, "landmark_dist",
             "centroid_dist", "eigenvec_dist", "region_dist", "labeled_dist")]):
            ax = self.fig.add_axes([0.04 + col * 0.34, 0.18, 0.30, 0.70])
            ax.set_facecolor(C_BG)
            mpr = r[key_mpr]
            ax.imshow(_bone_window(mpr), cmap="gray", origin="upper",
                      interpolation="bilinear")
            region, labeled = r[reg_key], r[lblk]
            if labeled is not None and region is not None:
                for c in measure.find_contours((labeled == region.label).astype(float), 0.5):
                    ax.plot(c[:, 1], c[:, 0], color=color, lw=1.6, alpha=0.9)
            cy, cx = r[c_key]
            lm = r.get(lm_key)
            if lm is not None:
                ly, lx = lm
                ax.plot([cx, lx], [cy, ly], color=color, lw=2.4)
                ax.plot(lx, ly, "o", color=C_AXIS, markersize=8, markeredgecolor="white")
            ax.plot(cx, cy, "+", color="white", markersize=11, mew=2)
            ax.set_title(f"{lab}  срез {r['prox_idx'] if col==0 else r['dist_idx']}\n"
                         f"{r[key_ang]:.1f}°", color=color, fontsize=10)
            ax.axis("off")

        t = r["torsion_deg"]
        self.fig.text(0.72, 0.62, f"{'+' if t>=0 else ''}{t:.1f}°",
                      color=C_AXIS, fontsize=46, fontweight="bold", ha="center")
        self.fig.text(0.72, 0.54, "наружная" if t >= 0 else "внутренняя",
                      color=C_SUBTEXT, fontsize=12, ha="center")
        self.fig.text(0.72, 0.46,
                      f"прокс. {r['angle_prox']:.1f}°   дист. {r['angle_dist']:.1f}°",
                      color=C_TEXT, fontsize=11, ha="center")

        ax_save = self.fig.add_axes([0.63, 0.08, 0.18, 0.08])
        self.btn = Button(ax_save, "Save PDF", color="#2563eb", hovercolor="#3b82f6")
        self.btn.label.set_color("white")
        self.btn.on_clicked(self._save)
        self.saved_path = None

    def _save(self, e):
        self.saved_path = self.on_save()
        self.fig.text(0.72, 0.04, f"Сохранено: {os.path.basename(self.saved_path)}",
                      color=C_PROX, fontsize=9, ha="center")
        self.fig.canvas.draw_idle()

    def run(self):
        plt.show()
        return self.saved_path


# ─────────────────────────────────────────────────────────────────────────────
# 10. СОХРАНЕНИЕ ДАТАСЕТА ДЛЯ ОБУЧЕНИЯ
# ─────────────────────────────────────────────────────────────────────────────

def save_training_row(output_dir, meta, seed, prox, dist, torsion, manual_ref=""):
    """Сохраняет запись в training_data.csv (датасет для Phase 2 / CNN)."""
    path = str(Path(output_dir) / "training_data.csv")
    fields = ["timestamp", "patient_id", "seed_slice", "seed_y", "seed_x",
              "prox_slice", "prox_x", "prox_y", "dist_slice", "dist_x", "dist_y",
              "torsion_result", "manual_reference"]
    write_header = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if write_header:
            w.writeheader()
        w.writerow({
            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "patient_id": meta["patient_id"],
            "seed_slice": int(seed[0]), "seed_y": round(seed[1], 1), "seed_x": round(seed[2], 1),
            "prox_slice": prox["slice_idx"],
            "prox_x": round(prox["measurement"]["centroid"][1], 1),
            "prox_y": round(prox["measurement"]["centroid"][0], 1),
            "dist_slice": dist["slice_idx"],
            "dist_x": round(dist["measurement"]["centroid"][1], 1),
            "dist_y": round(dist["measurement"]["centroid"][0], 1),
            "torsion_result": torsion,
            "manual_reference": manual_ref,
        })
    print(f"  Запись добавлена в training_data.csv")


# ─────────────────────────────────────────────────────────────────────────────
# 11. ОСНОВНОЙ ЦИКЛ
# ─────────────────────────────────────────────────────────────────────────────

def build_side_result(volume, meta, axis, residual_px,
                      z_keep, y_keep, x_keep, prox_cand, dist_cand, laterality):
    """Собирает dict результата стороны (совместим с build_pdf_report)."""
    mp, md = prox_cand["measurement"], dist_cand["measurement"]
    angle_prox = mp["angle_deg"]
    angle_dist = md["angle_deg"]
    torsion = compute_torsion(angle_prox, angle_dist)
    return {
        "torsion_deg": torsion,
        "angle_prox": round(angle_prox, 1),
        "angle_dist": round(angle_dist, 1),
        "prox_idx": prox_cand["slice_idx"],
        "dist_idx": dist_cand["slice_idx"],
        "mpr_prox": prox_cand["mpr"], "mpr_dist": dist_cand["mpr"],
        "centroid_prox": mp["centroid"], "centroid_dist": md["centroid"],
        "eigenvec_prox": mp["unitvec"], "eigenvec_dist": md["unitvec"],
        "region_prox": mp["region"], "region_dist": md["region"],
        "labeled_prox": mp["labeled"], "labeled_dist": md["labeled"],
        "landmark_prox": mp["landmark"], "landmark_dist": md["landmark"],
        "prominence_prox": mp["prominence_px"], "prominence_dist": md["prominence_px"],
        "axis": axis,
        "z_centroids": z_keep, "y_centroids": y_keep, "x_centroids": x_keep,
        "z_min": int(z_keep.min()), "z_max": int(z_keep.max()),
        "residual_px": residual_px, "n_axis_slices": len(z_keep),
        "laterality": laterality,
    }


def run(dicom_folder, patient_id="", output_dir="", laterality="left"):
    print("\n" + "=" * 60)
    print("ТОРСИЯ ЛУЧЕВОЙ КОСТИ  v3.0  (интерактивный seed-трекинг)")
    print(f"Папка: {dicom_folder}")
    print("=" * 60)

    print("\n[1] Загрузка DICOM...")
    volume, z_pos, meta = load_dicom_series(dicom_folder)
    if patient_id:
        meta["patient_id"] = patient_id

    if not output_dir:
        output_dir = dicom_folder
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # ── Цикл seed → ось → подтверждение ──────────────────────────────────────
    while True:
        print("\n[2] Окно 1: выбор seed...")
        seed = SeedSelector(volume, meta).run()
        if seed is None:
            print("  Seed не выбран — выход.")
            return None
        print(f"  Seed: срез {seed[0]}, y={seed[1]:.1f}, x={seed[2]:.1f}")

        print("\n[3] Трекинг от seed...")
        z_arr, y_arr, x_arr = track_from_seed(volume, seed[0], seed[1], seed[2])
        axis, residual_px, z_keep, y_keep, x_keep = build_axis(
            z_arr, y_arr, x_arr)
        z_min, z_max = int(z_keep.min()), int(z_keep.max())

        print("\n[4] Окно 2: подтверждение оси...")
        decision = AxisConfirm(volume, axis, z_keep, x_keep,
                               z_min, z_max, residual_px).run()
        if decision == "ok":
            break
        print("  Re-seed — повтор выбора.")

    # ── Поиск кандидатов уровней (анатомическая привязка) ────────────────────
    print("\n[5] Поиск кандидатов уровней...")
    seed_slice = int(seed[0])
    prox_lo = max(z_min, seed_slice - PROX_BACK_SEED)
    prox_hi = min(z_max, seed_slice + PROX_ABOVE_SEED + PROX_BELOW_SEED)
    dist_lo = max(z_min, z_max - DIST_FROM_END)
    dist_hi = max(prox_hi + 1, z_max - DIST_END_PAD)
    print(f"  Прокс. зона: срезы {prox_lo}–{prox_hi} (вокруг seed {seed_slice})")
    print(f"  Дист. зона: срезы {dist_lo}–{dist_hi} (у конца кости {z_max})")
    prox_cands = find_level_candidates(volume, axis, prox_lo, prox_hi,
                                       meta, "proximal")
    dist_cands = find_level_candidates(volume, axis, dist_lo, dist_hi,
                                       meta, "distal")
    if not prox_cands or not dist_cands:
        raise ValueError("Не удалось найти кандидатов уровней.")

    print("\n[6] Окно 3: выбор проксимального уровня...")
    prox_sel = LevelSelector(prox_cands, "ПРОКСИМАЛЬНЫЙ (бугристость)", C_PROX).run()
    print(f"  Выбран проксимальный срез {prox_sel['slice_idx']}")

    print("\n[7] Окно 4: выбор дистального уровня...")
    dist_sel = LevelSelector(dist_cands, "ДИСТАЛЬНЫЙ (ульнарная вырезка)", C_DIST).run()
    print(f"  Выбран дистальный срез {dist_sel['slice_idx']}")

    # ── Сборка результата ────────────────────────────────────────────────────
    side = build_side_result(volume, meta, axis, residual_px,
                             z_keep, y_keep, x_keep, prox_sel, dist_sel, laterality)
    print(f"\n  ТОРСИЯ: {side['torsion_deg']:+.1f}°  "
          f"(прокс. {side['angle_prox']:.1f}°, дист. {side['angle_dist']:.1f}°)")

    results = {"meta": meta, "z_pos": z_pos, "volume": volume, "selected": side}

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pid = meta["patient_id"].replace(" ", "_")
    pdf_path = str(Path(output_dir) / f"torsion_v3_{pid}_{timestamp}.pdf")

    def do_save():
        build_pdf_report(results, pdf_path)
        save_training_row(output_dir, meta, seed, prox_sel, dist_sel,
                          side["torsion_deg"])
        return pdf_path

    print("\n[8] Окно 5: результат (Save PDF для сохранения)...")
    saved = ResultWindow(side, do_save).run()
    if saved is None:
        # окно закрыли без сохранения — сохраняем всё равно
        saved = do_save()

    print("\n" + "=" * 60)
    print(f"  Торсия: {side['torsion_deg']:+.1f}°")
    print(f"  PDF: {os.path.basename(saved)}")
    print("=" * 60 + "\n")
    return saved


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Торсия лучевой кости по DICOM КТ — v3 (полуавтомат, seed-трекинг)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Пример:
  python radius_torsion_v3.py ./dicom --patient Кондратьев --output ./results
        """)
    parser.add_argument("dicom_folder")
    parser.add_argument("--patient", default="")
    parser.add_argument("--output", default="")
    parser.add_argument("--side", default="left", choices=["left", "right"],
                        help="Какую руку измеряем (для подписи в отчёте)")
    args = parser.parse_args()

    try:
        run(args.dicom_folder, patient_id=args.patient,
            output_dir=args.output, laterality=args.side)
    except Exception as e:
        print(f"\n[ОШИБКА] {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
