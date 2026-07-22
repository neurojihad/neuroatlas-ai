"""
radius_torsion_registration_nov.py — АВТОМАТИЧЕСКИЙ расчёт ИЗБЫТКА торсии лучевой
кости методом регистрации со здоровой контралатеральной стороной.

Идея (новый метод, кандидат на отдельный патент):
  У ребёнка с односторонним поражением (ДЦП) здоровая лучевая кость = личная
  норма пациента. Зеркалим здоровую кость по сагиттальной плоскости (она
  становится «как левая»), приводим её к больной по продольной оси и измеряем
  ОСТАТОЧНУЮ ротацию между уровнями. Разность остаточных ротаций на дистальном
  и проксимальном эпифизах = ИЗБЫТОК торсии (патологическая деформация),
  выраженный сразу относительно нормы пациента, без популяционных таблиц.

  Торсия НЕ измеряется по двум ручным ориентирам (бугристость/вырезка) — вместо
  точки используется ВСЯ форма поперечного сечения эпифиза (угловая радиальная
  сигнатура), а угол находится круговой кросс-корреляцией сигнатур больной и
  зеркальной здоровой кости. Это устраняет главный источник шума прежнего
  метода — «прыгающую» на деформированной кости точку ориентира.

Метод полностью автоматический при заданных seed-точках обеих лучевых костей
(врач указывает «где лучевая» кликом — единственный ручной ввод, как и
оговорено в проекте; никакого автоопределения laterality в коде нет).

Зависит от radius_torsion_v3.py: load_dicom_series, track_from_seed, build_axis, Axis.
"""

import numpy as np
from scipy import ndimage
from skimage import measure, morphology

from scripts.radius_torsion_v3 import (load_dicom_series, track_from_seed, build_axis,
                                       Axis, HU_CORTICAL_MIN, HU_CORTICAL_MAX)


# ─────────────────────────────────────────────────────────────────────────────
# Извлечение поперечного сечения ⊥ ЛОКАЛЬНОЙ оси с единым мировым in-plane базисом
# ─────────────────────────────────────────────────────────────────────────────

def _inplane_basis(tangent_world):
    """
    Ортонормированный in-plane базис (e_u, e_v) ⊥ касательной, привязанный к
    ГЛОБАЛЬНОЙ оси Y (передне-задняя ось мира) — единый для обеих костей, что
    делает углы сечений сравнимыми между больной и здоровой стороной.
    """
    t = tangent_world / (np.linalg.norm(tangent_world) + 1e-12)
    g = np.array([0.0, 1.0, 0.0])
    e_u = g - np.dot(g, t) * t
    if np.linalg.norm(e_u) < 1e-6:
        g = np.array([0.0, 0.0, 1.0])
        e_u = g - np.dot(g, t) * t
    e_u /= np.linalg.norm(e_u)
    e_v = np.cross(t, e_u)
    return e_u, e_v


def cross_section(volume, axis, z_slice, spacing, size_mm=26.0, res=0.4):
    """
    MPR ⊥ локальной касательной оси в точке z_slice; центр = точка оси.
    Возвращает (img, res). spacing = (sz, sxy, sxy) в мм.
    """
    spacing = np.asarray(spacing, float)
    t = np.array([1.0, axis.der_y(z_slice), axis.der_x(z_slice)]) * spacing
    e_u, e_v = _inplane_basis(t)
    c = np.array([z_slice, axis.val_y(z_slice), axis.val_x(z_slice)]) * spacing
    n = int(2 * size_mm / res)
    us = (np.arange(n) - n / 2) * res
    U, V = np.meshgrid(us, us)
    pts = c[None, None, :] + U[..., None] * e_u[None, None, :] + V[..., None] * e_v[None, None, :]
    idx = pts / spacing
    samp = ndimage.map_coordinates(
        volume, [idx[..., 0].ravel(), idx[..., 1].ravel(), idx[..., 2].ravel()],
        order=1, mode="constant", cval=-1000)
    return samp.reshape(n, n), res


def _radius_region(mpr, hu_min=HU_CORTICAL_MIN):
    """
    Костная компонента, ближайшая к центру MPR (= лучевая на оси).

    hu_min управляет порогом: в ДИАФИЗЕ держим жёсткий кортикальный порог
    (HU_CORTICAL_MIN=700) для чистого кольца; в ЭПИФИЗЕ губчатая кость с тонкой
    корой требует мягче (≈400), иначе заполнение дырок даёт лишь осколок коры.
    Слишком низкий порог (≤250) сливает эпифиз с костями запястья — поэтому 400.
    """
    n = mpr.shape[0]; c = n / 2.0
    mask = (mpr >= hu_min) & (mpr <= HU_CORTICAL_MAX)
    mask = morphology.closing(mask, morphology.disk(3))
    mask = ndimage.binary_fill_holes(mask)
    if hu_min < HU_CORTICAL_MIN:
        mask = morphology.opening(mask, morphology.disk(1))  # отсечь перемычки к запястью
    lab = measure.label(mask)
    regs = [r for r in measure.regionprops(lab) if r.area > 40]
    if not regs:
        return None, None
    rad = min(regs, key=lambda r: np.hypot(r.centroid[0] - c, r.centroid[1] - c))
    return lab, rad


def _radius_and_ulna(mpr, hu_min=HU_CORTICAL_MIN):
    """
    Возвращает (lab, rad, uln): лучевая (ближайшая к центру) и локтевая
    (ближайшая к лучевой из остальных костных компонент) на срезе, либо uln=None.
    Локтевая нужна как ЯКОРЬ асимметрии на дистальном уровне (ульнарная вырезка
    обращена к ней) — это снимает 180°-неоднозначность поворота.
    """
    n = mpr.shape[0]; c = n / 2.0
    mask = (mpr >= hu_min) & (mpr <= HU_CORTICAL_MAX)
    mask = morphology.closing(mask, morphology.disk(3))
    mask = ndimage.binary_fill_holes(mask)
    if hu_min < HU_CORTICAL_MIN:
        mask = morphology.opening(mask, morphology.disk(1))
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


def ulna_anchor_deg(mpr, hu_min):
    """
    Азимут направления от центра лучевой к локтевой кости (в той же угловой
    системе, что и radial_signature: degrees(atan2(dy, dx))). Возвращает угол
    или None, если локтевая не найдена.
    """
    _, rad, uln = _radius_and_ulna(mpr, hu_min)
    if rad is None or uln is None:
        return None
    dy = uln.centroid[0] - rad.centroid[0]
    dx = uln.centroid[1] - rad.centroid[1]
    return float(np.degrees(np.arctan2(dy, dx)))


def zone_ulna_anchor(volume, axis, z_center, spacing, half_zone, hu_min):
    """Медианный азимут-якорь к локтевой по зоне (устойчивость к шуму)."""
    angs = []
    for z in range(int(z_center) - half_zone, int(z_center) + half_zone + 1):
        if z < axis.z_min or z > axis.z_max:
            continue
        mpr, _ = cross_section(volume, axis, z, spacing)
        a = ulna_anchor_deg(mpr, hu_min)
        if a is not None:
            angs.append(a)
    if not angs:
        return None
    # круговая медиана
    v = np.exp(1j * np.radians(angs))
    return float(np.degrees(np.angle(np.median(v.real) + 1j * np.median(v.imag))))


def resolve_dphi_anchor(sA, sH, anchor_A, anchor_H):
    """
    Возвращает (dphi, ambig_margin): угол поворота из кросс-корреляции сигнатур,
    но 180°-неоднозначность снята ЯКОРЕМ к локтевой. Из двух кандидатов {dphi,
    dphi+180} выбирается ближайший к (anchor_A − anchor_H). ambig_margin — на
    сколько градусов отвергнутый кандидат дальше (большой = уверенный выбор).
    """
    dphi0, _ = circular_align_angle(sA, sH)
    if anchor_A is None or anchor_H is None:
        return dphi0, None
    expected = (anchor_A - anchor_H + 180) % 360 - 180
    cands = [(dphi0 + 180 * k + 180) % 360 - 180 for k in (0, 1)]
    def dist(a):
        return abs((a - expected + 180) % 360 - 180)
    d0, d1 = dist(cands[0]), dist(cands[1])
    best = cands[0] if d0 <= d1 else cands[1]
    return best, abs(d1 - d0)


def radial_signature(mpr, nbins=360, hu_min=HU_CORTICAL_MIN):
    """
    Угловая радиальная сигнатура r(θ) контура лучевой кости относительно её
    центроида (θ в едином in-plane базисе сечения). Возвращает (sig, area,
    pca_angle_deg, centroid) или None. sig нормирована (вычтено среднее).
    """
    lab, rad = _radius_region(mpr, hu_min=hu_min)
    if rad is None:
        return None
    cy, cx = rad.centroid
    conts = measure.find_contours((lab == rad.label).astype(float), 0.5)
    if not conts:
        return None
    cont = max(conts, key=len)
    if len(cont) < 20:
        return None
    th = np.arctan2(cont[:, 0] - cy, cont[:, 1] - cx)   # [-pi, pi]
    rr = np.hypot(cont[:, 0] - cy, cont[:, 1] - cx)
    # сортируем точки контура по углу и интерполируем r(θ) на равномерную сетку
    o = np.argsort(th)
    ths, rs = th[o], rr[o]
    # расширяем периодически для корректной круговой интерполяции
    ths_ext = np.concatenate([ths - 2 * np.pi, ths, ths + 2 * np.pi])
    rs_ext = np.concatenate([rs, rs, rs])
    grid = -np.pi + (np.arange(nbins) + 0.5) * (2 * np.pi / nbins)
    sig = np.interp(grid, ths_ext, rs_ext)
    pca = np.degrees(rad.orientation)
    return sig - sig.mean(), float(rad.area), pca, (cy, cx)


def zone_signature(volume, axis, z_center, spacing, half_zone=7, step=1,
                   hu_min=HU_CORTICAL_MIN):
    """Средняя радиальная сигнатура по зоне ±half_zone срезов (снижение шума)."""
    sigs = []
    for z in range(int(z_center) - half_zone, int(z_center) + half_zone + 1, step):
        if z < axis.z_min or z > axis.z_max:
            continue
        mpr, _ = cross_section(volume, axis, z, spacing)
        rs = radial_signature(mpr, hu_min=hu_min)
        if rs is not None:
            sigs.append(rs[0])
    if not sigs:
        return None
    return np.mean(sigs, axis=0)


def circular_align_angle(sig_ref, sig_mov, nbins=360):
    """
    Угол (град) поворота sig_mov для совмещения с sig_ref круговой
    кросс-корреляцией. Положительный = поворот против часовой в in-plane базисе.
    """
    f = np.fft.rfft(sig_ref)
    g = np.fft.rfft(sig_mov)
    corr = np.fft.irfft(f * np.conj(g), n=nbins)
    shift = int(np.argmax(corr))
    if shift > nbins // 2:
        shift -= nbins
    return shift * 360.0 / nbins, corr


# ─────────────────────────────────────────────────────────────────────────────
# Профиль сечений вдоль кости (для авто-поиска эпифизов и диагностики)
# ─────────────────────────────────────────────────────────────────────────────

def find_homologous_level(volM, axH, sig_ref, z_guess, spacing,
                          search_half=130, step=2, half_zone=7,
                          hu_min=HU_CORTICAL_MIN):
    """
    Находит на ЗДОРОВОЙ (зеркальной) кости уровень, гомологичный заданному
    уровню больной кости, по СОВПАДЕНИЮ ФОРМЫ сечения: возвращает z, при котором
    усреднённая радиальная сигнатура максимально совмещается (по пику круговой
    кросс-корреляции) с эталонной сигнатурой sig_ref больной кости.

    Анатомически устойчиво и ВОСПРОИЗВОДИМО между сканами (привязка к форме
    эпифиза, а не к номеру среза) — что важно для отслеживания динамики.
    Поиск ограничен окном вокруг грубого прогноза z_guess, чтобы не «зацепиться»
    за похожее по форме сечение запястья при уходе трека на кисть.

    Возвращает (z_best, q_best) или (None, 0.0).
    """
    z0 = max(int(axH.z_min) + half_zone, int(z_guess) - search_half)
    z1 = min(int(axH.z_max) - half_zone, int(z_guess) + search_half)
    best_z, best_q = None, -1.0
    nrm_ref = np.linalg.norm(sig_ref) + 1e-9
    for z in range(z0, z1 + 1, step):
        sH = zone_signature(volM, axH, z, spacing, half_zone, hu_min=hu_min)
        if sH is None:
            continue
        _, corr = circular_align_angle(sig_ref, sH)
        q = float(corr.max() / (nrm_ref * (np.linalg.norm(sH) + 1e-9)))
        if q > best_q:
            best_q, best_z = q, z
    return best_z, best_q


def _bone_area(volume, axis, z, spacing, hu_min=HU_CORTICAL_MIN):
    """
    Площадь кортикального кольца на уровне z (число пикселей >= hu_min в MPR).
    Инвариантна к торсии — используется как признак гомологии вместо формы.
    """
    try:
        mpr, _ = cross_section(volume, axis, int(z), spacing)
        return int(np.sum(mpr >= hu_min))
    except Exception:
        return 0


def find_homologous_level_v2(vol, axA, z_aff, volM, axH, spacing,
                              search_half=0, step=1, half_zone=7,
                              hu_min=HU_CORTICAL_MIN):
    """
    Улучшенный поиск гомологичного уровня здоровой (зеркальной) кости.

    Стратегия: пропорциональная проекция по длине трека (PropOnly).
        t = (z_aff − axA.z_min) / (axA.z_max − axA.z_min)
        z_prop = axH.z_min + t * (axH.z_max − axH.z_min)

    Обоснование выбора PropOnly:
      - Ошибка z: 1–18 срезов vs 36–146 у v1 (поиск по форме).
      - Ошибка excess: на Бызове = 0°, на Сидоренко = 9° (оба лучше v1).
      - Площадная уточнение (search_half > 0) УХУДШАЕТ результат, т.к.
        деформированная кость имеет изменённую площадь сечения — критерий
        «похожая площадь» нарушен именно там, где нужна точность.
      - Оставлен параметр search_half для будущих экспериментов (default=0).

    Возвращает (z_best, q):
      q = 1.0 при PropOnly; < 1 при поиске по площади.
    """
    span_A = max(axA.z_max - axA.z_min, 1.0)
    span_H = axH.z_max - axH.z_min
    t = max(0.0, min(1.0, (z_aff - axA.z_min) / span_A))
    z_prop = int(round(axH.z_min + t * span_H))

    if search_half == 0:
        return z_prop, 1.0   # чистая пропорция — лучшая стратегия

    # Опциональное уточнение по площади (search_half > 0)
    area_aff = _bone_area(vol, axA, z_aff, spacing, hu_min)
    if area_aff == 0:
        return z_prop, 0.5

    z0 = max(int(axH.z_min) + half_zone, z_prop - search_half)
    z1 = min(int(axH.z_max) - half_zone, z_prop + search_half)
    best_z, best_err = z_prop, float('inf')
    for z in range(z0, z1 + 1, step):
        area_h = _bone_area(volM, axH, z, spacing, hu_min)
        if area_h == 0:
            continue
        err = abs(area_h - area_aff)
        if err < best_err:
            best_err, best_z = err, z
    q = max(0.0, 1.0 - best_err / (area_aff + 1e-9))
    return best_z, q


def detect_epiphysis_levels(vol, axA, spacing, smooth=9):
    """
    Автодетекция прокс./дист. уровней лучевой кости по профилю площади сечения.

    prox_level_aff (двухступенчатая логика):
      1. Шейка лучевой кости — анатомически всегда минимум площади в зоне 5-25%
         спана. Ищем последний локальный минимум (prominence > 5% max) в этой зоне:
         конец шейки = начало диафиза ≈ tuberositas radii.
      2. Fallback (нет чёткого минимума): 10% спана.
      Ошибка на 3 верифицир. пациентах с шаг 1 vs шаг 2:
        Бызов: z_min+8% → 12%-евр. даёт Δ+20, минимум площади должен дать ближе.
        Хандуева/Сидоренко: работало и с 12%.

    dist_level_aff (двухступенчатая логика):
      1. Ищем первый пик с prominence > 15% max в дистальных 45% кости.
         Это = начало дистального эпифиза (Бызов Δ+6, Хандуева Δ-33).
      2. Если пиков нет (кость короткая/деформ.):
         последний z > 30% max в дист. 45% = конец надёжного диафиза.
         (Сидоренко Δ-1).

    Возвращает (prox_level_aff, dist_level_aff).
    """
    from scipy.ndimage import median_filter as _mf
    from scipy.signal import find_peaks as _fp
    zs, ar, _ = section_profile(vol, axA, spacing, step=4)
    ar_sm = _mf(ar.astype(float), size=smooth)

    span  = axA.z_max - axA.z_min
    z_min = axA.z_min
    mx    = ar_sm.max()

    # --- prox: минимум площади в зоне 5-25% (шейка лучевой) ---
    mask_prox = (zs > z_min + 0.05 * span) & (zs < z_min + 0.25 * span)
    prox = int(z_min + 0.10 * span)   # fallback: 10%
    if mask_prox.any():
        zp, ap = zs[mask_prox], ar_sm[mask_prox]
        # ищем минимумы (= инвертированные пики): последний в зоне = конец шейки
        mins, mprops = _fp(-ap, prominence=mx * 0.05, distance=5)
        if len(mins) > 0:
            # берём ПОСЛЕДНИЙ минимум в зоне: ближайший к диафизу
            prox = int(zp[mins[-1]])

    # --- dist: пик дистального эпифиза или конец диафиза ---
    start_dist = z_min + 0.45 * span
    mask_dist = zs > start_dist
    dist = int(z_min + 0.85 * span)   # fallback

    if mask_dist.any():
        zd, ad = zs[mask_dist], ar_sm[mask_dist]
        # Ступень 1: первый пик в дист. зоне (prominence > 15% max)
        peaks, props = _fp(ad, prominence=mx * 0.15, distance=10)
        if len(peaks) > 0:
            dist = int(zd[peaks[0]])        # первый (проксим.) дистальный пик
        else:
            # Ступень 2: конец надёжного диафиза (> 30% max)
            above30 = zd[ad > mx * 0.30]
            if len(above30) > 0:
                dist = int(above30[-1])

    return prox, dist


def section_profile(volume, axis, spacing, step=4):
    """Возвращает z, area(z), pca_angle(z) вдоль валидного диапазона оси."""
    zs, ar, pc = [], [], []
    for z in range(int(axis.z_min), int(axis.z_max) + 1, step):
        mpr, _ = cross_section(volume, axis, z, spacing)
        rs = radial_signature(mpr)
        if rs is None:
            continue
        zs.append(z); ar.append(rs[1]); pc.append(rs[2])
    return np.array(zs), np.array(ar), np.array(pc)


# ─────────────────────────────────────────────────────────────────────────────
# 3D РОТАЦИОННАЯ РЕГИСТРАЦИЯ БЛОКА ЭПИФИЗА (основной измеритель)
# ─────────────────────────────────────────────────────────────────────────────
#
# Вместо одного 2D-сечения (нестабильно на «бледном» дистальном эпифизе)
# совмещаем ВЕСЬ 3D-блок эпифиза: поворачиваем здоровый блок вокруг оси и
# максимизируем воксельное ПЕРЕКРЫТИЕ с больным. Интегрирование по многим
# срезам устраняет посрезовый шум. Само перекрытие — встроенная мера
# достоверности: высокое (прокс ≈0.93) = угол надёжен; низкое (дист на
# деформированной кости) = автомат честно сигналит «нужен ручной ввод».

def block_points_cont(volume, axis, zc, spacing, half_block=22, hu=400,
                      res=0.5, size_mm=24):
    """
    Облако точек (s, u, v) лучевой кости в блоке ±half_block срезов вокруг
    уровня zc, в осевых координатах (s вдоль оси, u/v в плоскости среза).

    СВЯЗНАЯ протяжка: на zc берётся компонента, ближайшая к центру; на соседних
    срезах — компонента с максимальным перекрытием маски предыдущего среза.
    Это удерживает трекинг на лучевой и не даёт прихватить кости запястья/локтя.
    """
    n = int(2 * size_mm / res); c = n / 2.0
    zc = int(zc)

    def seg(mpr):
        m = (mpr >= hu) & (mpr <= HU_CORTICAL_MAX)
        m = morphology.closing(m, morphology.disk(2))
        m = ndimage.binary_fill_holes(m)
        if hu < HU_CORTICAL_MIN:
            m = morphology.opening(m, morphology.disk(1))
        return measure.label(m)

    pts = []
    mpr, _ = cross_section(volume, axis, zc, spacing, size_mm=size_mm, res=res)
    lab = seg(mpr)
    regs = [r for r in measure.regionprops(lab) if r.area > 40]
    if not regs:
        return np.empty((0, 3))
    rad = min(regs, key=lambda r: np.hypot(r.centroid[0] - c, r.centroid[1] - c))

    def collect(z, mask):
        ys, xs = np.where(mask)
        s = (z - zc) * spacing[0]
        for uu, vv in zip((xs - c) * res, (ys - c) * res):
            pts.append((s, uu, vv))

    prev = (lab == rad.label)
    collect(zc, prev)
    for dirn in (1, -1):
        pm = prev.copy()
        for k in range(1, half_block + 1):
            z = zc + dirn * k
            if z < axis.z_min or z > axis.z_max:
                break
            mpr, _ = cross_section(volume, axis, z, spacing, size_mm=size_mm, res=res)
            lab = seg(mpr)
            best, bo = None, 0
            for r in measure.regionprops(lab):
                if r.area <= 40:
                    continue
                ov = (pm & (lab == r.label)).sum()
                if ov > bo:
                    bo, best = ov, r
            if best is None:
                break
            pm = (lab == best.label)
            collect(z, pm)
    return np.asarray(pts)


def rot_register_3d(ptsA, ptsH, gv=1.0, coarse=3.0, prior=None, window=50.0):
    """
    Угол φ (град) поворота здорового блока вокруг оси, максимизирующий воксельное
    перекрытие с больным, и само перекрытие (доля точек здорового, попавших в
    занятые больным воксели). Грубый перебор + уточнение.

    prior: если задан, поиск ограничен окном ±window вокруг prior — снимает
    90/180-неоднозначность в ПРОФИЛЕ твиста (соседние уровни не прыгают),
    оставляя только физичные изменения угла.

    Возвращает (phi, overlap). overlap — встроенная мера достоверности.
    """
    if len(ptsA) < 50 or len(ptsH) < 50:
        return 0.0, 0.0
    occ = set(zip(np.round(ptsA[:, 0] / gv).astype(int),
                  np.round(ptsA[:, 1] / gv).astype(int),
                  np.round(ptsA[:, 2] / gv).astype(int)))
    sH = ptsH[:, 0]; uH = ptsH[:, 1]; vH = ptsH[:, 2]

    def overlap(phi):
        th = np.radians(phi); ct, st = np.cos(th), np.sin(th)
        u2 = uH * ct - vH * st; v2 = uH * st + vH * ct
        keys = zip(np.round(sH / gv).astype(int),
                   np.round(u2 / gv).astype(int),
                   np.round(v2 / gv).astype(int))
        return sum(1 for k in keys if k in occ) / len(sH)

    grid = np.arange(-180, 180, coarse) if prior is None \
        else np.arange(prior - window, prior + window, coarse)
    best_phi, best_ov = 0.0, -1.0
    for phi in grid:
        ov = overlap(phi)
        if ov > best_ov:
            best_ov, best_phi = ov, float(phi)
    for phi in np.arange(best_phi - coarse, best_phi + coarse, 0.5):
        ov = overlap(phi)
        if ov > best_ov:
            best_ov, best_phi = ov, float(phi)
    # Нормализация: без prior — свернуть в [-180, 180]; с prior — вести
    # unwrapped фазу (prior + shortest-path diff), чтобы континуитет не рвался
    # когда поиск выходит за ±180° (баг 1: prior=-180, истина=-206 → без фикса
    # возвращалось +154, разрывая цепочку).
    if prior is None:
        best_phi = (best_phi + 180) % 360 - 180
    else:
        best_phi = prior + ((best_phi - prior + 180) % 360 - 180)
    # Снятие 180°-ветвевой неоднозначности: если |phi| >= 90°, ищем
    # наименьший |phi| среди кандидатов с overlap в пределах 15% от лучшего.
    # Кандидаты: best_phi, phi±180°, 0°. Анатомически малые повороты
    # реалистичнее экстремальных при поиске без prior (фикс бага 2).
    # Порог 0.85 (15%): срабатывает при реальной близости ветвей.
    if prior is None and abs(best_phi) >= 90.0:
        alt_phi = best_phi + 180.0 if best_phi < 0 else best_phi - 180.0
        alt_ov = overlap(alt_phi)
        ov_zero = overlap(0.0)
        thr = best_ov * 0.85
        # Сначала проверяем 0° (наиболее «нейтральная» ветвь, |phi|=0 минимален)
        if ov_zero >= thr:
            best_phi, best_ov = 0.0, ov_zero
        # Затем ±180° переброс, если |alt| < |best| (и 0° не прошёл)
        elif abs(alt_phi) < abs(best_phi) and alt_ov >= thr:
            best_phi, best_ov = alt_phi, alt_ov
    return best_phi, best_ov


# Порог чистоты анатомического якорного профиля (expected=aA−aH): ниже него —
# якорю можно верить и применять коррекцию ветви; выше — сечение слишком
# симметрично, коррекцию не применяем. Откалибровано: Дзюба нелин 2.8° (чинит),
# Бызов/Сидоренко якорь зашумлён и не участвует (там срыва и нет).
ANCHOR_CLEAN_DEG = 20.0


def twist_profile(volA, axA, volM, axH, prox_aff, prox_hlt, dist_aff,
                  spacing, step=30, half_block=16, ov_gate=0.6,
                  use_ulna_anchor=True, half_zone=7,
                  end_exclude=20, return_endpoint=False):
    """
    Профиль относительного твиста больной кости относительно зеркальной здоровой
    вдоль диафиза (КОМПАРАТИВНЫЙ метод — основной).

    На каждом уровне zA здоровый уровень = prox_hlt+(zA-prox_aff) (жёсткий сдвиг:
    анатомическое соответствие через ручной или авто-якорь prox_hlt). φ
    регистрируется с КОНТИНУИТЕТОМ (prior = предыдущий надёжный φ), overlap —
    мера достоверности. Избыток твиста = накопление φ по надёжному участку
    (overlap>=ov_gate), оценённое робастной линией (устойчиво к выбору
    отдельного среза и воспроизводимо между сканами).

    use_ulna_anchor: если True — стартовая ветвь континуитета (0°/180°) на
      уровне-якоре выбирается не эвристикой rot_register_3d, а ВНЕШНИМ
      анатомическим ориентиром — направлением «лучевая→локтевая» (zone_ulna_anchor).
      Это правильный фикс бага 2 (см. review_notes.md, п.5): для центросимметричных
      сечений voxel-overlap не различает φ и φ+180, и холодный старт якоря может
      сесть на неверную ветвь, а континуитет затем протянет неверную ветвь по
      всему профилю. Якорь снимает эту неоднозначность по анатомии, а не по
      порогу перекрытия. По умолчанию False — ручной калиброванный пайплайн
      (Бызов/Сидоренко) не затрагивается.

    Возвращает (rows[zA,phi,ov], good_rows, excess_span_deg, slope_per100_deg).
    """
    mid = (prox_aff + dist_aff) / 2
    # Исключаем 20 срезов с обоих концов: прокс. бугристость и дист. эпифиз
    # дают искусственно высокий overlap (округлое сечение) и неправильный якорь.
    levels = list(range(int(prox_aff) + end_exclude, int(dist_aff) - end_exclude, step))
    # 1) собрать блоки и глобальную регистрацию на каждом уровне
    pts = {}
    glob = {}
    for zA in levels:
        zH = prox_hlt + (zA - prox_aff)
        hu = HU_CORTICAL_MIN if zA < mid else 500
        pA = block_points_cont(volA, axA, zA, spacing, half_block, hu)
        pH = block_points_cont(volM, axH, zH, spacing, half_block, hu)
        pts[zA] = (pA, pH)
        phi0, ov0 = rot_register_3d(pA, pH)
        # фильтр рассогласования объёмов блоков: сильно разные размеры = уровни
        # не гомологичны (сегментация захватила разное) → уровень ненадёжен
        ratio = (len(pH) + 1) / (len(pA) + 1)
        if ratio < 0.55 or ratio > 1.8:
            ov0 = min(ov0, ov_gate - 0.01)
        glob[zA] = (phi0, ov0)
    # 2) якорь = уровень с макс. overlap (надёжная привязка, без холодного старта)
    anchor = max(levels, key=lambda z: glob[z][1])
    phi_anchor = glob[anchor][0]
    # 2а) снятие 0/180-неоднозначности ветви якоря по анатомическому ориентиру,
    # С ГЕЙТОМ ДОВЕРИЯ. Анатомический якорный профиль expected(z)=aA−aH («направление
    # лучевая→локтевая») однозначен там, где сечение асимметрично. Коррекцию ветви
    # якорного уровня применяем ТОЛЬКО если этот профиль ЧИСТ (нелинейность мала) —
    # тогда якорю можно верить (Дзюба: нелин 2.8° → чинит ветвевой срыв −18.5°→+66°).
    # На зашумлённом якоре (Бызов/Сидоренко: сечение почти симметрично) коррекцию
    # не применяем — там ветвевого срыва и нет, эвристика rot_register_3d верна.
    # anchor_endpoint/anchor_nonlin возвращаются наружу как независимый арбитр ветви.
    anchor_endpoint = anchor_nonlin = None
    if use_ulna_anchor:
        expected_by_z = {}
        for zA in levels:
            zH = prox_hlt + (zA - prox_aff)
            hu = HU_CORTICAL_MIN if zA < mid else 500
            aA = zone_ulna_anchor(volA, axA, zA, spacing, half_zone, hu)
            aH = zone_ulna_anchor(volM, axH, zH, spacing, half_zone, hu)
            if aA is not None and aH is not None:
                expected_by_z[zA] = (aA - aH + 180) % 360 - 180
        if len(expected_by_z) >= 4:
            from scipy.stats import theilslopes
            ez = np.array(sorted(expected_by_z), float)
            ev = np.degrees(np.unwrap(np.radians([expected_by_z[int(z)] for z in ez])))
            sl_e, ic_e, *_ = theilslopes(ev, ez)
            anchor_nonlin = float(np.max(np.abs(ev - (ic_e + sl_e * ez))))
            anchor_endpoint = float(ev[-1] - ev[0])
            if anchor_nonlin < ANCHOR_CLEAN_DEG and anchor in expected_by_z:
                expected = expected_by_z[anchor]
                cands = [(phi_anchor + 180 * k + 180) % 360 - 180 for k in (0, 1)]
                phi_anchor = min(cands, key=lambda a: abs((a - expected + 180) % 360 - 180))
    phi_a = {anchor: phi_anchor}
    ov_a = {anchor: glob[anchor][1]}
    # 3) идти наружу от якоря с континуитетом
    ai = levels.index(anchor)
    prior = phi_anchor
    for z in levels[ai + 1:]:
        phi, ov = rot_register_3d(*pts[z], prior=prior)
        phi_a[z], ov_a[z] = phi, ov
        if ov >= ov_gate:
            prior = phi
    prior = phi_anchor
    for z in reversed(levels[:ai]):
        phi, ov = rot_register_3d(*pts[z], prior=prior)
        phi_a[z], ov_a[z] = phi, ov
        if ov >= ov_gate:
            prior = phi
    rows = np.array([[z, phi_a[z], ov_a[z]] for z in levels], float)
    good = rows[rows[:, 2] >= ov_gate]
    excess_span = slope_per100 = excess_endpoint = None
    if len(good) >= 3:
        ph = np.degrees(np.unwrap(np.radians(good[:, 1])))
        # робастный наклон (Тейл–Сен) — устойчив к остаточным выбросам
        zz = good[:, 0]
        sl = np.median([(ph[j] - ph[i]) / (zz[j] - zz[i])
                        for i in range(len(zz)) for j in range(i + 1, len(zz))])
        slope_per100 = float(sl * 100.0)
        excess_span = float(sl * (zz[-1] - zz[0]))
        # NEW (фантом-валидированная) метрика: разность концов надёжного участка.
        # Небиасирована при любой форме профиля (равномерный/сосредоточенный/дистальный),
        # тогда как slope×span занижает дистально-сосредоточенную торсию (паттерн ДЦП).
        try:
            from scripts.profile_diagnostics import analyze_twist_profile
            excess_endpoint = analyze_twist_profile(zz, ph, sz=spacing[0])["endpoint_clean"]
        except Exception:
            excess_endpoint = float(ph[-1] - ph[0])
    if return_endpoint:
        return (rows, good, excess_span, slope_per100, excess_endpoint,
                anchor_endpoint, anchor_nonlin)
    return rows, good, excess_span, slope_per100


# ─────────────────────────────────────────────────────────────────────────────
# СЛОЙ АВТО-ФЛАГОВ КАЧЕСТВА
# ─────────────────────────────────────────────────────────────────────────────
#
# Метод сознательно полуавтоматический: измерительное ядро (трекинг, ось,
# сечения, кросс-корреляция) автоматично, но врач указывает кость и подтверждает
# уровни. Этот слой не заменяет врача, а САМ СИГНАЛИЗИРУЕТ, когда автоматическому
# результату нельзя доверять, чтобы оператор посмотрел глазами именно проблемные
# случаи. Каждая проверка возвращает статус OK/WARN/FAIL и человекочитаемую причину.

# Пороговые значения (px, мм, безразмерные). Подобраны по данным Кондратьева и
# анатомии детской лучевой кости; вынесены в константы для калибровки на наборе.
Q_AXIS_RES_WARN   = 2.5    # остаток оси, px
Q_AXIS_RES_FAIL   = 4.0
Q_LEN_MM_MIN      = 120.0  # ожидаемая длина лучевой кости ребёнка, мм
Q_LEN_MM_MAX      = 260.0
Q_LEN_RATIO_WARN  = 1.25   # асимметрия длины треков больной/здоровой
Q_LEN_RATIO_FAIL  = 1.6
Q_CORR_Q_WARN     = 0.70   # качество совмещения сечений (нормир. пик корреляции)
Q_CORR_Q_FAIL     = 0.50
Q_PEAK_Z_WARN     = 3.0    # резкость пика корреляции (z-оценка над фоном)
Q_PEAK_Z_FAIL     = 1.8
Q_EXCESS_WARN     = 90.0   # |избыток| выше — вероятно рассогласование уровней
Q_EXCESS_FAIL     = 140.0
Q_OVERLAP_WARN    = 0.75   # 3D-перекрытие блока: ниже — угол ненадёжен
Q_OVERLAP_GATE    = 0.60   # ниже — требуется ручная установка ориентира врачом

_SEV = {"OK": 0, "WARN": 1, "FAIL": 2}


def _flag(cond_fail, cond_warn, msg_fail, msg_warn, msg_ok):
    if cond_fail:
        return ("FAIL", msg_fail)
    if cond_warn:
        return ("WARN", msg_warn)
    return ("OK", msg_ok)


def peak_sharpness(corr):
    """
    Резкость пика круговой корреляции: z-оценка максимума над фоном
    (исключая ±5° вокруг пика). Низкое значение = неоднозначный угол поворота
    (например, почти круглое сечение) → измеренному Δφ доверять нельзя.
    """
    corr = np.asarray(corr, float)
    n = len(corr)
    k = int(np.argmax(corr))
    excl = np.ones(n, bool)
    w = max(1, int(round(5 * n / 360)))
    for d in range(-w, w + 1):
        excl[(k + d) % n] = False
    bg = corr[excl]
    return float((corr[k] - bg.mean()) / (bg.std() + 1e-9))


def assess_quality(axis_res_aff, axis_res_hlt, len_mm_aff, len_mm_hlt,
                   levels, span_mm_aff=None, span_mm_hlt=None):
    """
    Собирает флаги качества по всем звеньям и агрегированный вердикт.

    levels: dict уровня -> {q, peak_z, dphi} (или None, если сечение не найдено).
    Возвращает dict: {verdict, checks:[{name,status,detail}], any_fail, any_warn}.
    """
    checks = []

    def add(name, status, detail):
        checks.append({"name": name, "status": status, "detail": detail})

    # 1. Остаток оси
    for side, r in (("больная", axis_res_aff), ("здоровая", axis_res_hlt)):
        st, m = _flag(r > Q_AXIS_RES_FAIL, r > Q_AXIS_RES_WARN,
                      f"ось {side}: остаток {r:.1f}px — кость прослежена плохо",
                      f"ось {side}: остаток {r:.1f}px — повышенный",
                      f"ось {side}: остаток {r:.1f}px — норма")
        add(f"axis_residual_{side}", st, m)

    # 2. Длина трека (анатомическая правдоподобность)
    for side, L in (("больная", len_mm_aff), ("здоровая", len_mm_hlt)):
        bad = L < Q_LEN_MM_MIN or L > Q_LEN_MM_MAX
        st, m = _flag(L > Q_LEN_MM_MAX * 1.3 or L < Q_LEN_MM_MIN * 0.7, bad,
                      f"длина {side} {L:.0f}мм — нефизиологична (трек ушёл на кисть/локоть)",
                      f"длина {side} {L:.0f}мм — вне типичного диапазона",
                      f"длина {side} {L:.0f}мм — правдоподобна")
        add(f"track_length_{side}", st, m)

    # 3. Симметрия ИЗМЕРИТЕЛЬНОГО ПРОЛЁТА (расстояние прокс↔дист уровней, реально
    #    участвующих в расчёте) — содержательнее, чем длина всего трека: трек
    #    может уходить на кисть, но если используемый пролёт симметричен, уровни
    #    сопоставимы. Если пролёты не заданы — откат на длину трека.
    if span_mm_aff is not None and span_mm_hlt is not None:
        ratio = max(span_mm_aff, span_mm_hlt) / (min(span_mm_aff, span_mm_hlt) + 1e-9)
        st, m = _flag(ratio > Q_LEN_RATIO_FAIL, ratio > Q_LEN_RATIO_WARN,
                      f"пролёт прокс↔дист различается в {ratio:.2f}× — уровни не сопоставимы",
                      f"пролёт прокс↔дист различается в {ratio:.2f}× — проверьте уровни",
                      f"измерительный пролёт сопоставим ({ratio:.2f}×): "
                      f"больн {span_mm_aff:.0f}мм / здор {span_mm_hlt:.0f}мм")
        add("span_symmetry", st, m)
    else:
        ratio = max(len_mm_aff, len_mm_hlt) / (min(len_mm_aff, len_mm_hlt) + 1e-9)
        st, m = _flag(ratio > Q_LEN_RATIO_FAIL, ratio > Q_LEN_RATIO_WARN,
                      f"длины костей различаются в {ratio:.2f}× — уровни не сопоставимы",
                      f"длины костей различаются в {ratio:.2f}× — проверьте соответствие уровней",
                      f"длины костей сопоставимы ({ratio:.2f}×)")
        add("length_symmetry", st, m)

    # 4. Качество и резкость совмещения на каждом уровне
    for name in ("prox", "dist"):
        lv = levels.get(name)
        if lv is None:
            add(f"section_{name}", "FAIL", f"уровень {name}: сечение кости не найдено")
            continue
        q, pz = lv["q"], lv["peak_z"]
        st, m = _flag(q < Q_CORR_Q_FAIL, q < Q_CORR_Q_WARN,
                      f"{name}: качество совмещения q={q:.2f} — низкое",
                      f"{name}: качество совмещения q={q:.2f} — пониженное",
                      f"{name}: качество совмещения q={q:.2f} — хорошее")
        add(f"corr_quality_{name}", st, m)
        st, m = _flag(pz < Q_PEAK_Z_FAIL, pz < Q_PEAK_Z_WARN,
                      f"{name}: пик корреляции размыт (z={pz:.1f}) — угол неоднозначен",
                      f"{name}: пик корреляции нерезкий (z={pz:.1f})",
                      f"{name}: пик корреляции резкий (z={pz:.1f})")
        add(f"peak_sharpness_{name}", st, m)

    verdict = "OK"
    for c in checks:
        if _SEV[c["status"]] > _SEV[verdict]:
            verdict = c["status"]
    return {"verdict": verdict, "checks": checks,
            "any_fail": any(c["status"] == "FAIL" for c in checks),
            "any_warn": any(c["status"] == "WARN" for c in checks)}


def assess_excess(excess_deg):
    """Флаг правдоподобности самой величины избытка торсии."""
    a = abs(excess_deg)
    return _flag(a > Q_EXCESS_FAIL, a > Q_EXCESS_WARN,
                 f"избыток {excess_deg:+.0f}° неправдоподобно велик — вероятно рассогласование уровней",
                 f"избыток {excess_deg:+.0f}° велик — перепроверьте уровни",
                 f"избыток {excess_deg:+.0f}° в правдоподобном диапазоне")


def print_quality(report):
    """Печатает компактную сводку флагов для оператора."""
    icon = {"OK": "[ OK ]", "WARN": "[WARN]", "FAIL": "[FAIL]"}
    print(f"  --- КОНТРОЛЬ КАЧЕСТВА: вердикт {icon[report['verdict']]} ---")
    for c in report["checks"]:
        if c["status"] != "OK":
            print(f"    {icon[c['status']]} {c['detail']}")
    if report["verdict"] == "OK":
        print("    все проверки пройдены")


# ─────────────────────────────────────────────────────────────────────────────
# Главная процедура измерения
# ─────────────────────────────────────────────────────────────────────────────

def measure_excess_torsion(vol, seed_aff, seed_hlt, spacing,
                           prox_level_aff=None, dist_level_aff=None,
                           prox_level_hlt=None, dist_level_hlt=None,
                           half_zone=7, verbose=True):
    """
    vol: объём (z,y,x).
    seed_aff/seed_hlt: (slice, y, x) для больной и здоровой лучевой.
    spacing: (sz, sxy, sxy).
    prox/dist_level_aff: z-уровни эпифизов больной кости (если None — авто по area).

    Возвращает dict с избытком торсии и промежуточными величинами.
    Здоровая кость зеркалится (vol[:,:,::-1]) → становится «как больная левая».
    """
    cols = vol.shape[2]
    volM = vol[:, :, ::-1]

    sz = spacing[0]
    zA, yA, xA = track_from_seed(vol, *seed_aff)
    axA, resA, *_ = build_axis(zA, yA, xA)
    sh = seed_hlt
    zH, yH, xH = track_from_seed(volM, sh[0], sh[1], cols - 1 - sh[2])
    axH, resH, *_ = build_axis(zH, yH, xH)
    len_mm_aff = (axA.z_max - axA.z_min) * sz
    len_mm_hlt = (axH.z_max - axH.z_min) * sz

    if prox_level_aff is None or dist_level_aff is None:
        zs, ar, _ = section_profile(vol, axA, spacing)
        mid = zs.mean()
        if prox_level_aff is None:
            sub = zs < mid
            prox_level_aff = int(zs[sub][np.argmax(ar[sub])])
        if dist_level_aff is None:
            sub = zs > mid
            dist_level_aff = int(zs[sub][np.argmax(ar[sub])])

    def corr_level(zlevel):
        tA = (zlevel - axA.z_min) / (axA.z_max - axA.z_min)
        return axH.z_min + tA * (axH.z_max - axH.z_min)

    # Порог сегментации по уровню: диафиз/проксимальный — жёсткий кортикальный
    # (700), дистальный эпифиз — мягче (400) под губчатую кость.
    HU_PROX = HU_CORTICAL_MIN
    HU_DIST = 400

    # Эталонные сигнатуры больной кости на её уровнях
    sigA_prox = zone_signature(vol, axA, prox_level_aff, spacing, half_zone, hu_min=HU_PROX)
    sigA_dist = zone_signature(vol, axA, dist_level_aff, spacing, half_zone, hu_min=HU_DIST)

    # Гомологичные уровни здоровой кости: заданы вручную, иначе по совпадению
    # ФОРМЫ сечения с эталоном больной (воспроизводимо между сканами).
    if prox_level_hlt is None and sigA_prox is not None:
        prox_level_hlt, qhp = find_homologous_level(
            volM, axH, sigA_prox, corr_level(prox_level_aff), spacing,
            half_zone=half_zone, hu_min=HU_PROX)
        if verbose:
            print(f"  гомолог. прокс. уровень здоровой: z={prox_level_hlt} (match q={qhp:.2f})")
    if dist_level_hlt is None and sigA_dist is not None:
        # Прогноз дистали = прокс.гомолог + анатомический пролёт прокс→дист
        # больной кости (инвариантен; не зависит от длины здорового трека,
        # который может уходить на кисть). Окно поиска уже.
        if prox_level_hlt is not None:
            dguess = prox_level_hlt + (dist_level_aff - prox_level_aff)
            shalf = 60
        else:
            dguess, shalf = corr_level(dist_level_aff), 130
        dist_level_hlt, qhd = find_homologous_level(
            volM, axH, sigA_dist, dguess, spacing, search_half=shalf,
            half_zone=half_zone, hu_min=HU_DIST)
        if verbose:
            print(f"  гомолог. дист.  уровень здоровой: z={dist_level_hlt} "
                  f"(прогноз {dguess:.0f}, match q={qhd:.2f})")
    prox_H = prox_level_hlt if prox_level_hlt is not None else corr_level(prox_level_aff)
    dist_H = dist_level_hlt if dist_level_hlt is not None else corr_level(dist_level_aff)

    out = {}
    levels_q = {}
    for name, zA_lv, zH_lv, hu_lv in [("prox", prox_level_aff, prox_H, HU_PROX),
                                      ("dist", dist_level_aff, dist_H, HU_DIST)]:
        sA = zone_signature(vol, axA, zA_lv, spacing, half_zone, hu_min=hu_lv)
        sH = zone_signature(volM, axH, zH_lv, spacing, half_zone, hu_min=hu_lv)
        if sA is None or sH is None:
            out[name] = None
            levels_q[name] = None
            continue
        dphi, corr = circular_align_angle(sA, sH)
        peak = float(corr.max() / (np.linalg.norm(sA) * np.linalg.norm(sH) + 1e-9))
        pz = peak_sharpness(corr)
        ambig = None
        # ДИСТАЛЬ: снимаем 180°-неоднозначность якорем к локтевой кости
        # (ульнарная вырезка обращена к ней). Прокс. кольцо несимметрично —
        # там якорь не нужен.
        if name == "dist":
            aA = zone_ulna_anchor(vol, axA, zA_lv, spacing, half_zone, hu_lv)
            aH = zone_ulna_anchor(volM, axH, zH_lv, spacing, half_zone, hu_lv)
            dphi, ambig = resolve_dphi_anchor(sA, sH, aA, aH)
        out[name] = {"dphi": dphi, "peak": peak, "peak_z": pz,
                     "zA": zA_lv, "zH": zH_lv, "ambig_margin": ambig}
        levels_q[name] = {"q": peak, "peak_z": pz, "dphi": dphi,
                          "ambig_margin": ambig}
        if verbose:
            amb = "" if ambig is None else f", якорь-зазор {ambig:.0f}deg"
            print(f"  {name}: dphi(aff-mirrHealthy) = {dphi:+.1f}deg  "
                  f"(levels aff z={zA_lv}, hlt z={zH_lv:.0f}, q={peak:.2f}, peakZ={pz:.1f}{amb})")

    # слой флагов качества (с симметрией реально используемого пролёта уровней)
    span_mm_aff = abs(dist_level_aff - prox_level_aff) * sz
    span_mm_hlt = abs(dist_H - prox_H) * sz
    quality = assess_quality(resA, resH, len_mm_aff, len_mm_hlt, levels_q,
                             span_mm_aff=span_mm_aff, span_mm_hlt=span_mm_hlt)

    if out.get("prox") and out.get("dist"):
        excess = out["dist"]["dphi"] - out["prox"]["dphi"]
        excess = (excess + 180) % 360 - 180
        out["excess_torsion"] = round(excess, 1)
        ex_st, ex_msg = assess_excess(excess)
        quality["checks"].append({"name": "excess_plausibility",
                                  "status": ex_st, "detail": ex_msg})
        if _SEV[ex_st] > _SEV[quality["verdict"]]:
            quality["verdict"] = ex_st
        quality["any_fail"] = quality["any_fail"] or ex_st == "FAIL"
        quality["any_warn"] = quality["any_warn"] or ex_st == "WARN"
        if verbose:
            print(f"  EXCESS TORSION = dphi_dist - dphi_prox = {out['excess_torsion']:+.1f}deg")

    out["quality"] = quality
    out["axis_residual"] = {"aff": resA, "hlt": resH}
    out["track_len_mm"] = {"aff": len_mm_aff, "hlt": len_mm_hlt}
    if verbose:
        print_quality(quality)
    return out


def measure_excess_torsion_3d(vol, seed_aff, seed_hlt, spacing,
                              prox_level_aff, dist_level_aff,
                              prox_level_hlt=None, dist_level_hlt=None,
                              manual_dist_dphi=None, half_zone=7,
                              half_block=22, verbose=True):
    """
    ОСНОВНОЙ ИЗМЕРИТЕЛЬ (гибрид авто + overlap-гейт).

    - Оси обеих лучевых костей — авто (трекинг от seed).
    - Гомологичные уровни здоровой кости — авто по совпадению формы сечения
      (воспроизводимо между сканами → пригодно для динамики).
    - Угол на каждом уровне — 3D ротационная регистрация блока эпифиза.
    - Перекрытие блока (overlap) = встроенная мера достоверности:
        overlap >= Q_OVERLAP_WARN  → угол надёжен;
        Q_OVERLAP_GATE..WARN       → WARN, желательна проверка;
        overlap <  Q_OVERLAP_GATE  → угол НЕнадёжен: нужен ручной ввод вырезки
                                     (manual_dist_dphi), иначе избыток не выдаётся.
    - manual_dist_dphi: если задан врачом (например, по клику на вырезке),
      используется вместо авто-дистали.

    Возвращает dict: excess_torsion, prox/dist {dphi, overlap}, quality, ...
    """
    cols = vol.shape[2]; volM = vol[:, :, ::-1]; sz = spacing[0]
    HU_PROX, HU_DIST = HU_CORTICAL_MIN, 400

    zA, yA, xA = track_from_seed(vol, *seed_aff)
    axA, resA, *_ = build_axis(zA, yA, xA)
    sh = seed_hlt
    zH, yH, xH = track_from_seed(volM, sh[0], sh[1], cols - 1 - sh[2])
    axH, resH, *_ = build_axis(zH, yH, xH)
    len_mm_aff = (axA.z_max - axA.z_min) * sz
    len_mm_hlt = (axH.z_max - axH.z_min) * sz

    def corr_level(z):
        t = (z - axA.z_min) / (axA.z_max - axA.z_min)
        return axH.z_min + t * (axH.z_max - axH.z_min)

    # гомологичные уровни здоровой кости (по форме сечения)
    if prox_level_hlt is None:
        sAp = zone_signature(vol, axA, prox_level_aff, spacing, half_zone, hu_min=HU_PROX)
        prox_level_hlt, _ = find_homologous_level(
            volM, axH, sAp, corr_level(prox_level_aff), spacing,
            half_zone=half_zone, hu_min=HU_PROX)
    if dist_level_hlt is None:
        sAd = zone_signature(vol, axA, dist_level_aff, spacing, half_zone, hu_min=HU_DIST)
        dguess = prox_level_hlt + (dist_level_aff - prox_level_aff)
        dist_level_hlt, _ = find_homologous_level(
            volM, axH, sAd, dguess, spacing, search_half=60,
            half_zone=half_zone, hu_min=HU_DIST)
    if verbose:
        print(f"  уровни здоровой: прокс z={prox_level_hlt}, дист z={dist_level_hlt}")

    # 3D ротационная регистрация блоков
    def reg(zA_lv, zH_lv, hu):
        pA = block_points_cont(vol, axA, zA_lv, spacing, half_block, hu)
        pH = block_points_cont(volM, axH, zH_lv, spacing, half_block, hu)
        phi, ov = rot_register_3d(pA, pH)
        return phi, ov, len(pA), len(pH)

    phip, ovp, nAp, nHp = reg(prox_level_aff, prox_level_hlt, HU_PROX)
    phid, ovd, nAd, nHd = reg(dist_level_aff, dist_level_hlt, HU_DIST)
    if verbose:
        print(f"  PROX 3D: phi={phip:+.1f}deg overlap={ovp:.2f} (nA={nAp} nH={nHp})")
        print(f"  DIST 3D: phi={phid:+.1f}deg overlap={ovd:.2f} (nA={nAd} nH={nHd})")

    out = {"prox": {"dphi": phip, "overlap": ovp},
           "dist": {"dphi": phid, "overlap": ovd},
           "axis_residual": {"aff": resA, "hlt": resH},
           "track_len_mm": {"aff": len_mm_aff, "hlt": len_mm_hlt},
           "levels": {"prox_aff": prox_level_aff, "dist_aff": dist_level_aff,
                      "prox_hlt": prox_level_hlt, "dist_hlt": dist_level_hlt}}

    # overlap-гейт на дистали
    dist_source = "auto"
    if ovd < Q_OVERLAP_GATE:
        if manual_dist_dphi is not None:
            phid = float(manual_dist_dphi); dist_source = "manual"
            if verbose:
                print(f"  дист. overlap {ovd:.2f} < гейт {Q_OVERLAP_GATE}: "
                      f"взят РУЧНОЙ угол вырезки {phid:+.1f}deg")
        else:
            out["excess_torsion"] = None
            out["need_manual_distal"] = True
            out["dist_source"] = "none"
            if verbose:
                print(f"  дист. overlap {ovd:.2f} < гейт {Q_OVERLAP_GATE}: "
                      f"НУЖЕН РУЧНОЙ КЛИК НА ВЫРЕЗКЕ — избыток не выдан")
    out["dist_source"] = dist_source

    # флаги качества
    span_aff = abs(dist_level_aff - prox_level_aff) * sz
    span_hlt = abs(dist_level_hlt - prox_level_hlt) * sz
    # q дистали: при ручном подтверждении вырезки не штрафуем за низкий overlap
    q_dist_eff = 0.99 if dist_source == "manual" else ovd
    levels_q = {"prox": {"q": ovp, "peak_z": 99}, "dist": {"q": q_dist_eff, "peak_z": 99}}
    quality = assess_quality(resA, resH, len_mm_aff, len_mm_hlt, levels_q,
                             span_mm_aff=span_aff, span_mm_hlt=span_hlt)
    # перекрытие как явные флаги
    for nm, ov in (("prox", ovp), ("dist", ovd)):
        if nm == "dist" and dist_source == "manual":
            st, m = "OK", f"dist: 3D-перекрытие {ov:.2f} низкое, но вырезка подтверждена врачом"
        else:
            st, m = _flag(ov < Q_OVERLAP_GATE, ov < Q_OVERLAP_WARN,
                          f"{nm}: 3D-перекрытие {ov:.2f} < гейт — требуется ручной ориентир",
                          f"{nm}: 3D-перекрытие {ov:.2f} — пониженное",
                          f"{nm}: 3D-перекрытие {ov:.2f} — надёжно")
        quality["checks"].append({"name": f"overlap_{nm}", "status": st, "detail": m})
        if _SEV[st] > _SEV[quality["verdict"]]:
            quality["verdict"] = st

    if out.get("excess_torsion", "x") is not None:
        excess = (phid - phip + 180) % 360 - 180
        out["excess_torsion"] = round(excess, 1)
        if verbose:
            src = "" if dist_source == "auto" else f" [дист={dist_source}]"
            print(f"  ИЗБЫТОК ТОРСИИ = {out['excess_torsion']:+.1f}deg{src}")
    out["quality"] = quality
    if verbose:
        print_quality(quality)
    return out


# Пресеты пациентов (seed-точки и подтверждённые уровни от врача).
# seed = (z-индекс среза, y, x) в воксельных координатах исходного тома.
# prox_level_hlt: гомологичный проксимальный уровень здоровой кости (если известен).
PATIENTS = {
    "Кондратьев": dict(
        seed_aff=(228, 273.0, 413.0), seed_hlt=(360, 272.0, 95.0),
        prox_level_aff=225, dist_level_aff=525,
        prox_level_hlt=390,       # подтверждённый гомолог (воспр. ±4°)
    ),
    "Дзюба": dict(
        seed_aff=(250, 273.0, 339.0), seed_hlt=(250, 260.0, 120.0),
        prox_level_aff=200, dist_level_aff=500,
        prox_level_hlt=185,
    ),
    # Bilateral scan (обе руки в одном КТ). Больная = ЛЕВАЯ рука = правая часть изобр. (x≈322).
    # Здоровая = правая рука = левая часть изобр. (x≈173, после зеркала → x≈338).
    # Philips эталон: здоровая 15.6°, больная 83.0°, избыток +67.4°.
    # Уровни уточнены по авто-детекции (было prox=430,dist=560 — слишком узко, 4 уровня).
    "Сидоренко": dict(
        seed_aff=(500, 312.0, 322.0), seed_hlt=(500, 294.0, 173.0),
        prox_level_aff=416, dist_level_aff=559,
        prox_level_hlt=472,   # гомолог: z_hlt_start + (prox_aff − z_aff_start)
    ),
    # Bilateral scan, IOP=[1,0,0,0,1,0]. Больная = ПРАВАЯ рука (x≈185, 252мм трек).
    # Здоровая = ЛЕВАЯ рука (x≈368, 326мм трек). 856 срезов, spz=0.5мм.
    # ⚠️ seed_aff col=185 = RADIUS (col=210 = ULNA — неверно).
    # Результат (RADIUS vs RADIUS): избыток +94.5°, наклон +45.0°/100мм, надёжн=8.
    # Philips: здоровая 10.6° (15.3→4.7), больная 82.0° (7.9→89.9), избыток +71.4°.
    # Self-mirror: +25.0°, надёжн=8. Скорр.=+69.5° ≈ Philips +71.4° (дельта 1.9°) ✓
    "Бызов": dict(
        seed_aff=(430, 233, 185), seed_hlt=(430, 266, 368),
        prox_level_aff=392, dist_level_aff=702,
        prox_level_hlt=256,
    ),
    # Bilateral scan. Больная = ЛЕВАЯ рука (x≈105). Здоровая = ПРАВАЯ рука (x≈404).
    # 733 срезов, spz=0.50мм. Результат: избыток −80.9°, наклон −33.7°/100сл, надёжн=9.
    # Знак алго инвертирован vs клиники (клин. пронация = +80.9°).
    # Philips: избыток +100.3° (пронация). |дельта| = 19.4°.
    # Self-mirror: −50.6°, надёжн=10. Скорр. (−80.9)−(−50.6)=−30.3° ≠ Philips — знак.
    "Хандуева": dict(
        seed_aff=(350, 248, 105), seed_hlt=(350, 285, 404),
        prox_level_aff=260, dist_level_aff=620,
        prox_level_hlt=144,
    ),
}


# ─────────────────────────────────────────────────────────────────────────────
# ИНТЕРАКТИВНЫЙ ВЫБОР SEED И УРОВНЕЙ (для новых пациентов)
# ─────────────────────────────────────────────────────────────────────────────

def pick_seeds_interactive(vol, z_fraction=0.4):
    """
    Показывает аксиальный срез на z_fraction от начала тома. Врач кликает
    дважды: сначала на БОЛЬНУЮ лучевую, затем на ЗДОРОВУЮ.
    Возвращает (seed_aff, seed_hlt) как (z, y, x).
    """
    import matplotlib.pyplot as plt
    nz = vol.shape[0]
    z = int(nz * z_fraction)

    fig, ax = plt.subplots(figsize=(9, 9))
    ax.imshow(vol[z], cmap="gray", vmin=-200, vmax=1500, origin="upper")
    ax.set_title(
        f"z = {z}  |  Клик 1: БОЛЬНАЯ лучевая  →  Клик 2: ЗДОРОВАЯ лучевая",
        fontsize=11)
    ax.set_xlabel("x (столбец)")
    ax.set_ylabel("y (строка)")
    fig.tight_layout()

    pts = plt.ginput(2, timeout=120, show_clicks=True)
    plt.close(fig)

    if len(pts) < 2:
        raise RuntimeError("Нужно ровно два клика: больная и здоровая лучевая")

    (x1, y1), (x2, y2) = pts
    seed_aff = (z, round(y1, 1), round(x1, 1))
    seed_hlt = (z, round(y2, 1), round(x2, 1))
    print(f"  seed больной:   z={z}, y={y1:.0f}, x={x1:.0f}")
    print(f"  seed здоровой:  z={z}, y={y2:.0f}, x={x2:.0f}")
    return seed_aff, seed_hlt


def pick_levels_interactive(vol, spacing):
    """
    Интерактивный выбор уровней проксимального и дистального эпифизов
    на больной кости. Слева — текущий аксиальный срез, справа — фронтальная
    MIP с маркерами.

    Клавиши:
      ← / →            перемотать на 1 срез
      PageUp / PageDown перемотать на 10 срезов
      P                отметить ПРОКСИМАЛЬНЫЙ уровень (бугристость лучевой)
      D                отметить ДИСТАЛЬНЫЙ уровень (ульнарная вырезка)
      Enter / Q        подтвердить и выйти (требует обоих уровней)

    Возвращает (prox_level_aff, dist_level_aff).
    """
    import matplotlib.pyplot as plt

    nz = vol.shape[0]
    sz, sxy = spacing[0], spacing[1]
    state = {"z": nz // 2, "prox": None, "dist": None, "done": False}

    # Фронтальная MIP (max по Y) — один раз, для ориентации
    cor_mip = vol.max(axis=1)   # shape (nz, nx)

    fig, (ax_ax, ax_cor) = plt.subplots(1, 2, figsize=(15, 7))
    fig.subplots_adjust(left=0.05, right=0.97, wspace=0.15)

    ext = [0, nz * sz, 0, vol.shape[2] * sxy]
    ax_cor.imshow(cor_mip.T, cmap="gray", vmin=-200, vmax=1500,
                  origin="lower", aspect="auto", extent=ext)
    ax_cor.set_title("Фронтальная MIP — ориентация")
    ax_cor.set_xlabel("z, мм")
    ax_cor.set_ylabel("x, мм")
    cur_line  = ax_cor.axvline(state["z"] * sz, color="yellow",  lw=1.2, label="текущий")
    prox_line = ax_cor.axvline(-999,            color="cyan",    lw=1.5, ls="--", label="прокс (P)")
    dist_line = ax_cor.axvline(-999,            color="magenta", lw=1.5, ls="--", label="дист (D)")
    ax_cor.legend(loc="upper right", fontsize=8)

    im_ax = ax_ax.imshow(vol[state["z"]], cmap="gray", vmin=-200, vmax=1500,
                         origin="upper")
    title_ax = ax_ax.set_title("")

    def redraw():
        z = state["z"]
        im_ax.set_data(vol[z])
        marks = []
        if state["prox"] is not None:
            marks.append(f"P={state['prox']}")
        if state["dist"] is not None:
            marks.append(f"D={state['dist']}")
        hint = "  |  ".join(marks) if marks else "—"
        title_ax.set_text(
            f"z = {z}  ({z * sz:.1f} мм)        {hint}\n"
            "← → ±1 срез  |  PgUp/PgDn ±10  |  P = прокс  |  D = дист  |  Enter/Q = OK")
        cur_line.set_xdata([z * sz, z * sz])
        if state["prox"] is not None:
            prox_line.set_xdata([state["prox"] * sz, state["prox"] * sz])
        if state["dist"] is not None:
            dist_line.set_xdata([state["dist"] * sz, state["dist"] * sz])
        fig.canvas.draw_idle()

    def on_key(event):
        z = state["z"]
        k = event.key
        if k == "right":
            state["z"] = min(nz - 1, z + 1)
        elif k == "left":
            state["z"] = max(0, z - 1)
        elif k == "pagedown":
            state["z"] = min(nz - 1, z + 10)
        elif k == "pageup":
            state["z"] = max(0, z - 10)
        elif k in ("p", "P"):
            state["prox"] = state["z"]
            print(f"  → ПРОКСИМАЛЬНЫЙ уровень: z = {state['prox']}")
        elif k in ("d", "D"):
            state["dist"] = state["z"]
            print(f"  → ДИСТАЛЬНЫЙ уровень:    z = {state['dist']}")
        elif k in ("enter", "q", "Q"):
            if state["prox"] is not None and state["dist"] is not None:
                state["done"] = True
                plt.close(fig)
                return
            else:
                missing = []
                if state["prox"] is None:
                    missing.append("P (прокс)")
                if state["dist"] is None:
                    missing.append("D (дист)")
                print(f"  Ещё не отмечено: {', '.join(missing)}")
        redraw()

    fig.canvas.mpl_connect("key_press_event", on_key)
    redraw()
    plt.show()

    if not state["done"]:
        raise RuntimeError("Уровни не выбраны — отмените и повторите")

    p, d = state["prox"], state["dist"]
    if p > d:
        p, d = d, p
        print("  (прокс и дист поменяны местами — правильный порядок сохранён)")
    print(f"  ИТОГО: прокс z = {p}, дист z = {d}")
    return p, d


def detect_radius_bone(vol, seed1, seed2, spacing,
                       compare_frac=(0.55, 0.80),
                       hu_min=400, roi_mm=15.0, verbose=True):
    """
    Определяет, какой из двух seed указывает на лучевую кость (radius),
    а какой — на локтевую (ulna).

    Принцип: в дистальной половине предплечья площадь поперечного сечения
    radius ВСЕГДА больше, чем ulna. Трекируем оба seed независимо, сравниваем
    средние площади в зоне compare_frac (55-80% трека), где два трека ещё
    разделены в пространстве.

    Параметры
    ----------
    vol         : (z, y, x) объём HU.
    seed1,seed2 : (z, y, x) — два seed в одном предплечье.
    spacing     : (sz, sxy, sxy).
    compare_frac: (start_frac, end_frac) — диапазон трека для сравнения
                  (0.55–0.80 даёт дистальную треть без зоны слияния).
    hu_min      : порог HU для кортикальной кости.
    roi_mm      : радиус ROI вокруг центроида в мм.
    verbose     : печатать вывод.

    Возвращает
    ----------
    (radius_seed, ulna_seed) — seeds в порядке (radius, ulna).
    """
    from scripts.radius_torsion_v3 import track_from_seed
    from scipy import ndimage as _nd

    sz, sxy = spacing[0], spacing[1]
    px2mm2  = sxy * sxy
    roi_px  = max(8, int(roi_mm / sxy))

    def bone_area_in_zone(seed):
        """Средняя площадь кортикальной кости в заданной зоне трека."""
        z_tr, y_tr, x_tr = track_from_seed(vol, *seed)
        if len(z_tr) < 20:
            return 0.0
        z_arr = np.array(z_tr); y_arr = np.array(y_tr); x_arr = np.array(x_tr)
        z_lo = z_arr[0] + compare_frac[0] * (z_arr[-1] - z_arr[0])
        z_hi = z_arr[0] + compare_frac[1] * (z_arr[-1] - z_arr[0])
        step  = max(1, int(0.03 * len(z_arr)))   # ~3% шаг по треку
        areas = []
        for z_idx in range(int(z_lo), int(z_hi), step):
            if z_idx >= vol.shape[0]:
                break
            slc = vol[z_idx]
            y_c = float(np.interp(z_idx, z_arr, y_arr))
            x_c = float(np.interp(z_idx, z_arr, x_arr))
            r0 = max(0, int(y_c) - roi_px); r1 = min(slc.shape[0], int(y_c) + roi_px)
            c0 = max(0, int(x_c) - roi_px); c1 = min(slc.shape[1], int(x_c) + roi_px)
            patch = slc[r0:r1, c0:c1]
            labeled, n = _nd.label(patch > hu_min)
            if n == 0:
                continue
            # Выбрать blob ближайший к центроиду трека (не просто любой)
            best_area, best_dist = 0, 1e9
            for lbl in range(1, n + 1):
                pix = np.where(labeled == lbl)
                if len(pix[0]) < 5:
                    continue
                cy = pix[0].mean() + r0
                cx = pix[1].mean() + c0
                dist = np.hypot(cy - y_c, cx - x_c)
                if dist < best_dist:
                    best_dist = dist
                    best_area = len(pix[0]) * px2mm2
            if best_area > 0:
                areas.append(best_area)
        return np.mean(areas) if areas else 0.0

    a1 = bone_area_in_zone(seed1)
    a2 = bone_area_in_zone(seed2)

    if verbose:
        print(f"  detect_radius: seed1 {tuple(int(s) for s in seed1)} "
              f"→ ср.площадь в зоне {compare_frac} = {a1:.0f} mm²")
        print(f"  detect_radius: seed2 {tuple(int(s) for s in seed2)} "
              f"→ ср.площадь в зоне {compare_frac} = {a2:.0f} mm²")

    if a1 >= a2:
        if verbose:
            print(f"  → seed1 = RADIUS (крупнее), seed2 = ULNA")
        return seed1, seed2
    else:
        if verbose:
            print(f"  → seed2 = RADIUS (крупнее), seed1 = ULNA")
        return seed2, seed1


def _run_twist_profile(vol, spacing, seed_aff, seed_hlt,
                       prox_level_aff=None, dist_level_aff=None,
                       prox_level_hlt=None, verbose=True,
                       step=None, use_ulna_anchor=True):
    # use_ulna_anchor=True по умолчанию (с ГЕЙТОМ по чистоте якорного профиля внутри
    # twist_profile): безвреден там, где ветвевого срыва нет (Бызов/Сидоренко —
    # побитово то же), и чинит срыв там, где он есть (Дзюба: −18.5°→+66°, арбитр —
    # якорный профиль с нелин 2.7°). Разрешение Дзюбы: experiments_cowork/resolve_dzyba.py.
    # step=None → АВТО-выбор по длине span (пациент-зависимо): глобальный дефолт
    # неверен (Бызову нужен ~30 из-за аномалии z=457–517, Сидоренко ~15 — короткое окно).
    """
    Общий путь запуска twist_profile: трекинг → оси → гомолог → профиль.
    Если prox_level_aff/dist_level_aff не заданы — авто-детекция по профилю
    площади (detect_epiphysis_levels). Полностью автоматический при заданных seeds.
    Возвращает (rows, good, excess_span, slope_per100, axA, axH, resA, resH, prox_level_hlt).
    """
    cols = vol.shape[2]
    volM = vol[:, :, ::-1]
    sz = spacing[0]

    zA, yA, xA = track_from_seed(vol, *seed_aff)
    axA, resA, *_ = build_axis(zA, yA, xA)
    sh = seed_hlt
    zH, yH, xH = track_from_seed(volM, sh[0], sh[1], cols - 1 - sh[2])
    axH, resH, *_ = build_axis(zH, yH, xH)

    # Авто-детекция уровней если не заданы
    if prox_level_aff is None or dist_level_aff is None:
        pa, da = detect_epiphysis_levels(vol, axA, spacing)
        if prox_level_aff is None:
            prox_level_aff = pa
            if verbose:
                print(f"  авто prox_level_aff = {prox_level_aff} (12% от z_min)")
        if dist_level_aff is None:
            dist_level_aff = da
            if verbose:
                print(f"  авто dist_level_aff = {dist_level_aff} (эпифиз-детект.)")

    # АВТО-выбор шага по длине span (~11 целевых уровней), пациент-зависимо.
    # Естественно даёт Бызову ~30 (span 310), Сидоренко ~15 (span 143) — то, что
    # раньше приходилось задавать вручную. Глобального дефолта нет.
    if step is None:
        span_sl = int(dist_level_aff) - int(prox_level_aff)
        step = int(np.clip(round(span_sl / 11.0 / 5.0) * 5, 10, 35))
        if verbose:
            print(f"  авто step = {step} (span {span_sl} срезов → ~11 уровней)")

    if verbose:
        print(f"  ось больной:   z {axA.z_min:.0f}–{axA.z_max:.0f}, "
              f"остаток {resA:.1f} px, длина {(axA.z_max - axA.z_min) * sz:.0f} мм")
        print(f"  ось здоровой:  z {axH.z_min:.0f}–{axH.z_max:.0f}, "
              f"остаток {resH:.1f} px, длина {(axH.z_max - axH.z_min) * sz:.0f} мм")

    # гомолог прокс. уровня здоровой кости (v2: пропорция по полному спану)
    if prox_level_hlt is None:
        prox_level_hlt, qhp = find_homologous_level_v2(
            vol, axA, prox_level_aff,
            volM, axH, spacing,
            hu_min=HU_CORTICAL_MIN)
        if verbose:
            print(f"  гомолог прокс. здоровой: z = {prox_level_hlt} (q = {qhp:.2f}, авто-v2)")
    else:
        if verbose:
            print(f"  гомолог прокс. здоровой: z = {prox_level_hlt} (из пресета)")

    rows, good, excess_span, slope, excess_end, anchor_end, anchor_nl = twist_profile(
        vol, axA, volM, axH,
        prox_level_aff, prox_level_hlt, dist_level_aff, spacing,
        step=step, use_ulna_anchor=use_ulna_anchor, return_endpoint=True)

    # ── Выбор основной метрики + флаг качества ────────────────────────────────
    # endpoint (разность концов надёжного участка) — основная метрика: на фантоме
    # и на пациентах с эталоном Philips (Сидоренко Δ−3.9°, Бызов Δ−9.9°) она
    # устойчивее slope×span, которая раздувается на нелинейном профиле. Но endpoint
    # вырождается при малом числе уровней → откат на slope×span, если уровней < 5
    # или профиль сильно нелинеен.
    n_good = 0 if good is None else len(good)
    nonlin = None
    outliers = []
    if good is not None and n_good >= 3:
        try:
            from scripts.profile_diagnostics import analyze_twist_profile
            ph = np.degrees(np.unwrap(np.radians(good[:, 1])))
            diag = analyze_twist_profile(good[:, 0], ph, sz=spacing[0])
            nonlin = diag["nonlinearity_deg"]
            outliers = diag["outlier_levels"]
        except ImportError:
            pass

    # endpoint предпочтителен именно на нелинейном профиле (slope×span там
    # раздувается: Бызов slope×span +108° vs endpoint +61.5° при Philips +71.4°).
    # Откат на slope×span только при вырождении endpoint (мало уровней).
    use_endpoint = (n_good >= 4) and (excess_end is not None)
    excess = excess_end if use_endpoint else excess_span
    # ПРОГ-ФЛАГ качества. Три независимых сигнала:
    #  (1) мало уровней (<4) — endpoint вырождается;
    #  (2) высокая нелинейность (>25°) — регистрация «скачет»;
    #  (3) ВЕТВЕВОЕ РАССОГЛАСОВАНИЕ: если анатомический якорный профиль ЧИСТ
    #      (anchor_nl < ANCHOR_CLEAN_DEG) и его знак ПРОТИВОРЕЧИТ знаку результата —
    #      значит континуитет сидит на неверной ветви 0/180 (случай Дзюбы). Это
    #      принципиальнее прежнего флага: ловит срыв знака даже при гладком профиле.
    #      (Полный джиттер-IQR по границам — в magnitude_reliability для офлайн-аудита.)
    branch_conflict = (anchor_nl is not None and anchor_nl < ANCHOR_CLEAN_DEG
                       and anchor_end is not None and excess is not None
                       and abs(anchor_end) > 15.0 and abs(excess) > 15.0
                       and (anchor_end > 0) != (excess > 0))
    manual_review = (n_good < 4) or (nonlin is not None and nonlin > 25.0) \
        or (excess is not None and abs(excess) > Q_EXCESS_FAIL) or branch_conflict

    if verbose:
        es = f"{excess_span:+.1f}" if excess_span is not None else "—"
        ee = f"{excess_end:+.1f}" if excess_end is not None else "—"
        nl = f"{nonlin:.1f}" if nonlin is not None else "—"
        an = f"{anchor_end:+.1f}/{anchor_nl:.0f}°" if anchor_end is not None else "—"
        prim = "endpoint" if use_endpoint else "slope×span"
        print(f"  [профиль] ОСНОВНАЯ={excess:+.1f}° ({prim}) | "
              f"endpoint={ee}° | slope×span={es}° | нелинейность={nl}° | уровней={n_good}")
        print(f"  [якорь]  анатомический арбитр ветви: endpoint/нелин = {an}")
        if outliers and len(outliers) <= 3:
            print(f"  [профиль] выброс на уровнях {outliers} → вероятно флейр бугристости")
        if manual_review:
            reason = ("уровней<4" if n_good < 4 else
                      ("ВЕТВЕВОЙ СРЫВ: якорь ({:+.0f}°) против результата ({:+.0f}°)".format(anchor_end, excess)
                       if branch_conflict else
                       (f"нелинейность {nl}°>25 (регистрация скачет)"
                        if (nonlin is not None and nonlin > 25.0)
                        else f"|избыток|>{Q_EXCESS_FAIL:.0f}°")))
            print(f"  ⚠ ФЛАГ: НУЖЕН РУЧНОЙ ПРОСМОТР ({reason}) — авто-результату доверять нельзя")
        else:
            print(f"  ✓ авто-результат надёжен (уровней={n_good}, нелинейность={nl}°, "
                  f"якорь согласован)")

    return rows, good, excess, slope, axA, axH, resA, resH, prox_level_hlt


def _plot_twist_profile(rows, good, excess, slope, patient_name, spacing):
    """Выводит итоговый график профиля твиста."""
    import matplotlib.pyplot as plt
    sz = spacing[0]

    fig, ax = plt.subplots(figsize=(9, 5))
    zall = rows[:, 0] * sz
    phi_u = np.degrees(np.unwrap(np.radians(rows[:, 1])))
    ov = rows[:, 2]

    low = ov < Q_OVERLAP_GATE
    ax.scatter(zall[low], phi_u[low], c="lightgray", s=30, zorder=2,
               label=f"overlap < {Q_OVERLAP_GATE} (исключён)")
    sc = ax.scatter(zall[~low], phi_u[~low],
                    c=ov[~low], cmap="viridis", s=50,
                    vmin=0.6, vmax=1.0, zorder=3, label="надёжные уровни")

    if good is not None and len(good) >= 3:
        ph_g = np.degrees(np.unwrap(np.radians(good[:, 1])))
        zg = good[:, 0] * sz
        ax.plot(zg, ph_g, "k--", lw=1, zorder=4)
        z0, z1 = zg[0], zg[-1]
        ax.plot([z0, z1], [ph_g[0], ph_g[0] + slope / 100.0 * (z1 - z0)],
                "r-", lw=2, zorder=5,
                label=f"наклон {slope:+.1f}°/100 мм → избыток {excess:+.0f}°")

    ax.set_xlabel("z, мм (проксималь → дисталь)")
    ax.set_ylabel("φ (°), unwrapped")
    title = (f"{patient_name}  |  избыток торсии {excess:+.0f}°  "
             f"(наклон {slope:+.1f}°/100 мм)") if excess is not None else patient_name
    ax.set_title(title)
    ax.legend(fontsize=9)
    plt.colorbar(sc, ax=ax, label="overlap")
    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(
        description="Избыток торсии лучевой кости (профиль твиста, 3D-регистрация)")
    ap.add_argument("folder", help="папка DICOM серии")
    ap.add_argument("--patient", default=None,
                    help="имя пресета из PATIENTS (Кондратьев / Дзюба / ...)")
    ap.add_argument("--interactive", "-i", action="store_true",
                    help="интерактивный выбор seed и уровней мышью/клавишами "
                         "(для нового пациента)")
    ap.add_argument("--name", default="Новый",
                    help="имя нового пациента (используется с --interactive)")
    # ручные переопределения поверх пресета или интерактивного выбора
    ap.add_argument("--seed-aff", help="z,y,x больной лучевой")
    ap.add_argument("--seed-hlt", help="z,y,x здоровой лучевой")
    ap.add_argument("--prox",     type=int, help="уровень бугристости (больная)")
    ap.add_argument("--dist",     type=int, help="уровень вырезки (больная)")
    ap.add_argument("--prox-hlt", type=int,
                    help="гомологичный прокс. уровень здоровой (если известен из пресета)")
    a = ap.parse_args()

    vol, zpos, meta = load_dicom_series(a.folder, dtype=np.int16)
    spacing = (meta["spacing_z"], meta["spacing_xy"], meta["spacing_xy"])

    cfg = dict(PATIENTS.get(a.patient or "", {}))
    patient_name = a.patient or a.name

    if a.interactive:
        print("\n=== Шаг 1: выбор seed-точек ===")
        print("  Найдите диафиз, кликните на БОЛЬНУЮ кость, затем на ЗДОРОВУЮ.")
        sa, sh = pick_seeds_interactive(vol)
        cfg["seed_aff"] = sa
        cfg["seed_hlt"] = sh

        print("\n=== Шаг 2: выбор уровней (больная кость) ===")
        print("  Найдите бугристость (P) и ульнарную вырезку (D).")
        p, d = pick_levels_interactive(vol, spacing)
        cfg["prox_level_aff"] = p
        cfg["dist_level_aff"] = d
        cfg.pop("prox_level_hlt", None)   # гомолог пересчитаем авто

    # ручные переопределения CLI
    if a.seed_aff:
        cfg["seed_aff"] = tuple(float(x) for x in a.seed_aff.split(","))
    if a.seed_hlt:
        cfg["seed_hlt"] = tuple(float(x) for x in a.seed_hlt.split(","))
    if a.prox:
        cfg["prox_level_aff"] = a.prox
    if a.dist:
        cfg["dist_level_aff"] = a.dist
    if a.prox_hlt:
        cfg["prox_level_hlt"] = a.prox_hlt

    missing = [k for k in ("seed_aff", "seed_hlt", "prox_level_aff", "dist_level_aff")
               if not cfg.get(k)]
    if missing:
        raise SystemExit(
            f"Не хватает параметров: {missing}.\n"
            "Укажите --patient <имя>  или  --interactive  "
            "или передайте --seed-aff / --seed-hlt / --prox / --dist вручную.")

    print(f"\n{'='*60}")
    print(f"Пациент: {patient_name}")
    print(f"  seed_aff  = {cfg['seed_aff']}")
    print(f"  seed_hlt  = {cfg['seed_hlt']}")
    print(f"  прокс     = {cfg['prox_level_aff']},  дист = {cfg['dist_level_aff']}")
    if cfg.get("prox_level_hlt"):
        print(f"  прокс_hlt = {cfg['prox_level_hlt']}")
    print("=" * 60)

    rows, good, excess, slope, axA, axH, resA, resH, found_prox_hlt = _run_twist_profile(
        vol, spacing,
        seed_aff=cfg["seed_aff"],
        seed_hlt=cfg["seed_hlt"],
        prox_level_aff=cfg["prox_level_aff"],
        dist_level_aff=cfg["dist_level_aff"],
        prox_level_hlt=cfg.get("prox_level_hlt"),
        verbose=True,
    )

    print(f"\n{'='*60}")
    if excess is not None:
        print(f"  ИЗБЫТОК ТОРСИИ  = {excess:+.0f}°  (наклон {slope:+.1f}°/100 мм)")
        n_good = len(good) if good is not None else 0
        print(f"  Надёжных точек профиля: {n_good} / {len(rows)}")
    else:
        print(f"  ИЗБЫТОК НЕ ОПРЕДЕЛЁН — недостаточно надёжных уровней "
              f"(overlap < гейт {Q_OVERLAP_GATE})")
    print("=" * 60)

    # Для нового пациента — печатаем строку пресета для копирования в PATIENTS
    if a.interactive or (a.patient is None):
        sa = cfg["seed_aff"]; sh = cfg["seed_hlt"]
        p  = cfg["prox_level_aff"]; d = cfg["dist_level_aff"]
        print(f"\n--- Строка пресета (скопируй в PATIENTS) ---")
        print(f'    "{patient_name}": dict(')
        print(f'        seed_aff=({sa[0]}, {sa[1]}, {sa[2]}),')
        print(f'        seed_hlt=({sh[0]}, {sh[1]}, {sh[2]}),')
        print(f'        prox_level_aff={p}, dist_level_aff={d},')
        print(f'        prox_level_hlt={found_prox_hlt},')
        print(f'    ),')

    _plot_twist_profile(rows, good, excess, slope, patient_name, spacing)
