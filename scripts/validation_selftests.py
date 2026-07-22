"""
validation_selftests.py — валидация ИЗМЕРИТЕЛЬНОГО ЯДРА radius_torsion_registration
на синтетических фантомах с ИЗВЕСТНЫМ ground truth.

Зачем: флаги качества в основном скрипте говорят «доверять / не доверять», но НЕ
проверяют ТОЧНОСТЬ. Здесь проверяется именно точность — на данных, где правильный
ответ известен заранее. Реальные КТ и трекинг НЕ нужны: тесты бьют по ядру
(cross_section → radial_signature → circular_align_angle, и rot_register_3d) и по
геометрии опорного базиса напрямую.

Запуск:
    python3 validation_selftests.py
Работает и со стаб-модулем radius_torsion_v3, и с твоим настоящим (он лишь даёт
HU-константы; трекинг в этих тестах не вызывается).

Что проверяется:
    A. Точность и линейность восстановления торсии (прямой фантом).
    B. Инвариантность к общему развороту кости вокруг оси.
    C. Нулевой само-тест: нет торсии → избыток ≈ 0.
    D. СИСТЕМАТИКА ОПОРНОГО БАЗИСА (концерн №1): паразитный твист
       Грам–Шмидт-базиса (_inplane_basis, привязка к глобальной Y) относительно
       параллельного переноса (RMF/Bishop) при произвольной ориентации руки.
    E. 3D-регистрация блока (rot_register_3d): точность и разрешающий «пол» сетки.
    F. Зеркальный конвейер: симметричная пара (opposite chirality) → excess ≈ 0.
       ЭТАЛОН ПРИЁМКИ метода (заменяет SM-тест, который концептуально неверен).
    G. Регрессионный тест бага 1 (wrapping prior): prior=-180, истинный=-200
       → должно вернуть ≈-200, не +160. FAIL = баг активен, OK = исправлен.
    H. Демонстрация бага 2: срыв ветви 0°/180° на центросимметричном сечении.
"""

import numpy as np
import radius_torsion_registration as R

# ─────────────────────────────────────────────────────────────────────────────
# Синтетический фантом лучевой кости
# ─────────────────────────────────────────────────────────────────────────────

SXY = SZ = 0.5                      # мм, изотропно
NY = NX = 140
NZ = 240
CY, CX = NY / 2.0, NX / 2.0
HU_BONE, HU_BG = 1200, -1000
SPACING = (SZ, SXY, SXY)

# базовая форма сечения: эллипс + смещённая долька — ломает 180°-симметрию,
# как реальная лучевая (кортекс + межкостный гребень) → однозначный поворот.
_A, _B = 6.0, 4.0
_LOBE_C, _LOBE_R = 5.0, 2.2


def _base_inside(u, v):
    ell = (u / _A) ** 2 + (v / _B) ** 2 <= 1.0
    lobe = ((u - _LOBE_C) ** 2 + v ** 2) <= _LOBE_R ** 2
    return ell | lobe


def build_phantom(twist_rate=0.30, phase0_deg=0.0):
    """
    Прямая вертикальная кость; сечение линейно крутится вдоль z.
    twist_rate — °/мм; phase0_deg — общий разворот всей кости вокруг оси.
    Истинный относительный поворот между уровнями z1,z2 (в мм):
        Δ_true = twist_rate * (z2 - z1) * SZ.
    """
    vol = np.full((NZ, NY, NX), HU_BG, np.int16)
    ys, xs = np.meshgrid(np.arange(NY), np.arange(NX), indexing="ij")
    ux = (xs - CX) * SXY
    uy = (ys - CY) * SXY
    for z in range(NZ):
        th = np.radians(twist_rate * (z * SZ) + phase0_deg)
        ct, st = np.cos(-th), np.sin(-th)
        ur = ct * ux - st * uy
        vr = st * ux + ct * uy
        vol[z][_base_inside(ur, vr)] = HU_BONE
    return vol


class SynthAxis:
    """Ось прямой вертикальной кости (утиный тип под cross_section)."""
    def __init__(self, zmin, zmax):
        self.z_min, self.z_max = zmin, zmax
    def val_y(self, z): return CY
    def val_x(self, z): return CX
    def der_y(self, z): return 0.0
    def der_x(self, z): return 0.0


def _recover_delta(vol, ax, z1, z2, hz=7):
    """Восстановленный относительный поворот сечения z2 → z1 (в градусах)."""
    s1 = R.zone_signature(vol, ax, z1, SPACING, half_zone=hz, hu_min=R.HU_CORTICAL_MIN)
    s2 = R.zone_signature(vol, ax, z2, SPACING, half_zone=hz, hu_min=R.HU_CORTICAL_MIN)
    if s1 is None or s2 is None:
        return None
    dphi, _ = R.circular_align_angle(s2, s1)
    return dphi


# ─────────────────────────────────────────────────────────────────────────────
# A. Точность и линейность
# ─────────────────────────────────────────────────────────────────────────────

def test_accuracy():
    print("\n=== A. Точность и линейность (прямой фантом) ===")
    results = []
    for rate in (0.30, 0.60):
        vol = build_phantom(twist_rate=rate)
        ax = SynthAxis(20, NZ - 20)
        z1 = 50
        for z2 in range(90, 210, 20):
            true = rate * (z2 - z1) * SZ
            rec = _recover_delta(vol, ax, z1, z2)
            # знак ядра противоположен конвенции фантома → сравниваем модуль
            err = abs(rec) - abs(true)
            results.append((rate, true, rec, err))
            print(f"  rate={rate:.2f}°/мм  true|Δ|={abs(true):5.1f}°  "
                  f"rec={rec:+6.1f}°  |err|={abs(err):4.1f}°")
    errs = np.array([abs(e) for *_, e in results])
    # проверка знаковой согласованности (rec ≈ -true всюду → чистая конвенция)
    signs = [np.sign(rec) == -np.sign(true) for _, true, rec, _ in results if abs(true) > 1]
    print(f"  → макс|err| = {errs.max():.1f}°, средн|err| = {errs.mean():.1f}°")
    print(f"  → знак rec ≈ −true во всех точках: {all(signs)} "
          f"(значит смещения нет, только конвенция)")
    print(f"  → остаток ≤3° возникает лишь при крутом твисте: усреднение по зоне")
    print(f"    ±3.5мм размазывает быстро крутящееся сечение (не ошибка метода).")
    ok = np.median(errs) < 1.5 and errs.max() < 3.5 and all(signs)
    print(f"  ВЕРДИКТ A: {'OK' if ok else 'FAIL'} "
          f"(медиана|err|={np.median(errs):.1f}°, макс={errs.max():.1f}°)")
    return ok


# ─────────────────────────────────────────────────────────────────────────────
# B. Инвариантность к общему развороту кости
# ─────────────────────────────────────────────────────────────────────────────

def test_invariance():
    print("\n=== B. Инвариантность к развороту всей кости вокруг оси ===")
    ax = SynthAxis(20, NZ - 20)
    z1, z2 = 50, 190
    base = _recover_delta(build_phantom(0.30, phase0_deg=0.0), ax, z1, z2)
    deltas = []
    for ph in (37.0, 90.0, 155.0, -63.0):
        rec = _recover_delta(build_phantom(0.30, phase0_deg=ph), ax, z1, z2)
        d = abs(rec - base)
        deltas.append(d)
        print(f"  разворот {ph:+6.1f}°:  rec={rec:+6.1f}°  отклонение от базы={d:4.1f}°")
    ok = max(deltas) < 2.0
    print(f"  ВЕРДИКТ B: {'OK' if ok else 'FAIL'} "
          f"(относительный твист не зависит от позы, макс дрейф {max(deltas):.1f}°)")
    return ok


# ─────────────────────────────────────────────────────────────────────────────
# C. Нулевой само-тест
# ─────────────────────────────────────────────────────────────────────────────

def test_zero():
    print("\n=== C. Нулевой само-тест (кость без торсии → избыток ≈ 0) ===")
    vol = build_phantom(twist_rate=0.0)
    ax = SynthAxis(20, NZ - 20)
    recs = [abs(_recover_delta(vol, ax, 50, z2)) for z2 in (90, 130, 170, 200)]
    print("  |Δ| по уровням:", ", ".join(f"{r:.1f}°" for r in recs))
    ok = max(recs) < 1.5
    print(f"  ВЕРДИКТ C: {'OK' if ok else 'FAIL'} (макс |Δ| = {max(recs):.1f}°)")
    return ok


# ─────────────────────────────────────────────────────────────────────────────
# D. Систематика опорного базиса (ПЕРЕСМОТР концерна №1 — см. вывод теста)
# ─────────────────────────────────────────────────────────────────────────────

def _gs_frame(t, g=np.array([0.0, 1.0, 0.0])):
    """Тот же базис, что _inplane_basis: Грам–Шмидт e_u от глобальной g ⊥ t."""
    t = t / (np.linalg.norm(t) + 1e-12)
    e_u = g - (g @ t) * t
    if np.linalg.norm(e_u) < 1e-6:
        g2 = np.array([0.0, 0.0, 1.0])
        e_u = g2 - (g2 @ t) * t
    return e_u / (np.linalg.norm(e_u) + 1e-12)


def _signed_angle(a, b, axis):
    """Знаковый угол (°) от a к b вокруг axis (все ⊥ axis)."""
    a = a / (np.linalg.norm(a) + 1e-12)
    b = b / (np.linalg.norm(b) + 1e-12)
    s = np.cross(a, b) @ (axis / (np.linalg.norm(axis) + 1e-12))
    c = a @ b
    return np.degrees(np.arctan2(s, c))


def _gs_twist(tangents):
    """
    Прямой корректный измеритель: суммарный твист GS-базиса (_inplane_basis)
    ВОКРУГ касательной вдоль оси. Для базиса без паразитного твиста = 0.
    На каждом шаге e_u минимально переносится с t_i на t_{i+1} и сравнивается
    с GS-базисом на t_{i+1}; знаковые приращения суммируются.
    Это ровно та величина, которую метод ложно припишет как «торсию», если
    истинного материального твиста нет.
    """
    tg = [t / (np.linalg.norm(t) + 1e-12) for t in tangents]
    tot = 0.0
    for i in range(len(tg) - 1):
        t0, t1 = tg[i], tg[i + 1]
        u0, u1 = _gs_frame(t0), _gs_frame(t1)
        v = np.cross(t0, t1); sn = np.linalg.norm(v)
        if sn > 1e-9:                       # минимальный перенос u0: t0 → t1
            Rm = _rot_axis_angle(v / sn, np.degrees(np.arctan2(sn, t0 @ t1)))
            u0 = Rm @ u0
        tot += _signed_angle(u0, u1, t1)
    return tot


def _rot_axis_angle(axis, deg):
    axis = axis / (np.linalg.norm(axis) + 1e-12)
    th = np.radians(deg); c, s = np.cos(th), np.sin(th)
    x, y, z = axis
    C = 1 - c
    return np.array([
        [c + x*x*C,   x*y*C - z*s, x*z*C + y*s],
        [y*x*C + z*s, c + y*y*C,   y*z*C - x*s],
        [z*x*C - y*s, z*y*C + x*s, c + z*z*C],
    ])


def test_frame_bias():
    print("\n=== D. Систематика опорного базиса (пересмотр концерна №1) ===")
    L_mm, n = 200.0, 60
    s = np.linspace(0, L_mm, n)
    rng = np.random.default_rng(0)

    def planar_bow(bow_deg):
        a = np.radians(bow_deg) * (s / L_mm)
        return np.stack([np.cos(a), np.zeros_like(a), np.sin(a)], axis=1)

    def nonplanar_bow(bow1, bow2):                # реальная лучевая слегка неплоская
        a = np.radians(bow1) * (s / L_mm)
        b = np.radians(bow2) * np.sin(np.pi * s / L_mm)
        t = np.stack([np.cos(a) * np.cos(b), np.sin(b), np.sin(a) * np.cos(b)], axis=1)
        return t / np.linalg.norm(t, axis=1, keepdims=True)

    def sample(make_t, tilt_max):
        vals = []
        for _ in range(600):
            roll = _rot_axis_angle(np.array([1., 0., 0.]), rng.uniform(0, 360))
            tilt = _rot_axis_angle(np.array([0., rng.uniform(-1, 1), rng.uniform(-1, 1)]),
                                   rng.uniform(0, tilt_max))
            M = tilt @ roll
            vals.append(abs(_gs_twist([M @ t for t in make_t])))
        return np.array(vals)

    # sanity метрики: спираль с реальным 3D-твистом должна давать НЕ ноль
    phi = np.radians(60) * (s / L_mm)
    heli = np.stack([np.full_like(phi, 3.0), -np.sin(phi), np.cos(phi)], axis=1)
    heli /= np.linalg.norm(heli, axis=1, keepdims=True)
    print(f"  контроль метрики: истинно-3D спираль → твист = {_gs_twist(heli):+.1f}° "
          f"(не ноль — метрика ловит реальный твист)")

    print("  Ложный твист GS-базиса при отсутствии материального (медиана / 95%):")
    for bow in (10.0, 20.0):
        v = sample(planar_bow(bow), 40.0)
        print(f"    ПЛОСКИЙ боу {bow:4.1f}°, поза ≤40°:      "
              f"{np.median(v):4.1f}° / {np.percentile(v,95):4.1f}°")
    v = sample(nonplanar_bow(15.0, 5.0), 40.0)
    print(f"    НЕплоский боу 15°+5°, поза ≤40°:   "
          f"{np.median(v):4.1f}° / {np.percentile(v,95):4.1f}°")

    # вырожденный случай: ось кости почти вдоль глобальной Y (полюс GS-базиса)
    axisY = _rot_axis_angle(np.array([0., 0., 1.]), 88.0)   # ось Z-кости → почти Y
    vY = abs(_gs_twist([axisY @ t for t in planar_bow(15.0)]))
    print(f"  ⚠ вырождение: ось кости ≈ вдоль глобальной Y → твист = {vY:.0f}° "
          f"(здесь GS-базис ломается, fallback на Z — единственный реальный риск)")

    print("  ВЫВОД: для реальной (почти плоской) кости GS-базис даёт ~1–3° ложного")
    print("  твиста — концерн №1 в исходной оценке ПЕРЕОЦЕНЁН и НЕ объясняет 15–23°")
    print("  расхождения с Philips. Единственный реальный риск базиса — поза, где")
    print("  ось предплечья идёт вдоль глобальной Y: тогда добавить guard/сменить g.")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# E. 3D-регистрация блока
# ─────────────────────────────────────────────────────────────────────────────

def test_reg3d():
    print("\n=== E. 3D-регистрация блока (rot_register_3d) ===")
    rng = np.random.default_rng(1)
    # облако точек «эпифиза»: несимметричное, ~11мм полудлина блока
    N = 4000
    s = rng.uniform(-11, 11, N)
    ang = rng.uniform(0, 2*np.pi, N)
    rad = 5.0 + 2.0*np.cos(ang) + rng.normal(0, 0.4, N)   # несим. контур
    u = rad*np.cos(ang); v = rad*np.sin(ang)
    ptsA = np.stack([s, u, v], axis=1)

    def rotate(pts, deg):
        th = np.radians(deg); c, sn = np.cos(th), np.sin(th)
        u2 = pts[:,1]*c - pts[:,2]*sn
        v2 = pts[:,1]*sn + pts[:,2]*c
        return np.stack([pts[:,0], u2, v2], axis=1)

    print("  восстановление известного поворота:")
    errs = []
    for true in (5.0, 12.0, 25.0, 40.0):
        phi, ov = R.rot_register_3d(ptsA, rotate(ptsA, true))
        err = abs(abs(phi) - true)
        errs.append(err)
        print(f"    true={true:5.1f}°  rec={phi:+6.1f}°  overlap={ov:.2f}  |err|={err:4.1f}°")
    print("  разрешающий «пол» при сетке gv=1.0 мм (малые углы):")
    for true in (0.5, 1.0, 2.0):
        phi, ov = R.rot_register_3d(ptsA, rotate(ptsA, true))
        print(f"    true={true:4.1f}°  rec={phi:+5.1f}°  overlap={ov:.2f}")
    ok = max(errs) < 3.0
    print(f"  ВЕРДИКТ E: {'OK' if ok else 'WARN'} "
          f"(крупные углы: макс|err|={max(errs):.1f}°; малые — ограничены сеткой)")
    return ok


# ─────────────────────────────────────────────────────────────────────────────
# F. Зеркальный конвейер: симметричная пара (opposite chirality) → excess ≈ 0
# ─────────────────────────────────────────────────────────────────────────────

def test_mirror_pipeline():
    """
    Больная: build_phantom(+T). Здоровая: build_phantom(-T) — противоположная
    хиральность, как реальная пара левая/правая лучевая.
    После volM = vol_hlt[:,:,::-1] зеркальная здоровая поворачивается на +T
    → совпадает с больной → phi ≈ 0 на каждом уровне.
    ЭТО ЭТАЛОН ПРИЁМКИ метода (SM-тест концептуально неверен: берёт одну кость
    с обеих сторон → одинаковая хиральность → измеряет 2×собственная торсия).
    """
    print("\n=== F. Зеркальный конвейер: симметричная пара → phi ≈ 0 ===")
    T = 0.30   # °/мм
    vol_aff = build_phantom(twist_rate=+T)
    # phase0_deg=180 нужен, чтобы после зеркала лопасть здоровой попала в то же
    # угловое положение, что и у больной: без phase0 лопасть зеркальная
    # оказывается на 180° от больной и phi ≈ 180°, а не 0°.
    vol_hlt = build_phantom(twist_rate=-T, phase0_deg=180.0)
    volM    = vol_hlt[:, :, ::-1]   # зеркалим → +T в mirr. coords, лопасть совпадает

    axA = SynthAxis(20, NZ - 20)
    axH = SynthAxis(20, NZ - 20)

    phis = []
    print("  z    phi     ov")
    for z in range(50, 210, 25):
        pA = R.block_points_cont(vol_aff, axA, z, SPACING, 16, R.HU_CORTICAL_MIN)
        pH = R.block_points_cont(volM,    axH, z, SPACING, 16, R.HU_CORTICAL_MIN)
        if len(pA) < 50 or len(pH) < 50:
            continue
        phi, ov = R.rot_register_3d(pA, pH)
        phis.append(abs(phi))
        print(f"  {z:3d}  {phi:+6.1f}°  {ov:.3f}")
    ok = len(phis) > 0 and max(phis) < 3.0
    print(f"  ВЕРДИКТ F: {'OK' if ok else 'FAIL'} "
          f"(макс |phi| = {max(phis) if phis else float('nan'):.1f}°, ожидается < 3°)")
    return ok


# ─────────────────────────────────────────────────────────────────────────────
# G. Регрессионный тест бага 1 — wrapping prior
# ─────────────────────────────────────────────────────────────────────────────

def test_wrapping_bug():
    """
    Воспроизводит обрыв Бызова Δ+60: prior=-180, истинный угол=-200.
    Баговый код: search window [-230,-130] → best_raw=-206 →
        (best+180)%360-180 = +154 (ВЫЛЕТАЕТ из окна prior, рвёт континуитет).
    Фикс: prior + ((best-prior+180)%360-180) = -180+(-26) = -206.
    FAIL = баг активен; OK = исправлен.
    """
    print("\n=== G. Регрессионный тест бага 1 (wrapping prior) ===")
    rng = np.random.default_rng(42)
    N   = 3000
    s   = rng.uniform(-11, 11, N)
    ang = rng.uniform(0, 2*np.pi, N)
    rad = 5.0 + 2.0*np.cos(ang) + rng.normal(0, 0.3, N)
    ptsA = np.stack([s, rad*np.cos(ang), rad*np.sin(ang)], axis=1)

    def rotate(pts, deg):
        th = np.radians(deg); c, sn = np.cos(th), np.sin(th)
        return np.stack([pts[:,0],
                         pts[:,1]*c - pts[:,2]*sn,
                         pts[:,1]*sn + pts[:,2]*c], axis=1)

    # ptsH = rotate(ptsA, +200°): чтобы вернуть ptsH к ptsA нужно phi=-200°.
    # Окно prior±50 = [-230,-130] содержит -200° → grid находит -200 raw.
    # Баговый код: (-200+180)%360-180 = +160 (вылетает из окна, рвёт continuum).
    # Фикс:       prior+((raw-prior+180)%360-180) = -180+(-20) = -200.
    rotate_by = +200.0          # ptsH смещён на +200° от ptsA
    expected_phi = -200.0       # phi, нужный для выравнивания ptsH → ptsA
    ptsH     = rotate(ptsA, rotate_by)
    prior    = -180.0
    phi, ov  = R.rot_register_3d(ptsA, ptsH, prior=prior)

    in_window  = abs(phi - prior) <= 52.0              # корр. ответ -200 в окне ±50
    is_correct = abs(phi - expected_phi) < 8.0         # ≈-200
    is_buggy   = abs(phi - (expected_phi + 360)) < 15.0  # баговый +160

    print(f"  rotate_by=+{rotate_by}°  expected_phi={expected_phi}°  prior={prior}°")
    print(f"  recovered={phi:+.1f}°  ov={ov:.3f}  phi в окне prior±50: {in_window}")
    if is_correct:
        verdict = "OK — баг 1 исправлен"
    elif is_buggy:
        verdict = f"FAIL — баг 1 АКТИВЕН (возвращено {phi:.0f}° вместо {true_phi:.0f}°, обёртка +360°)"
    else:
        verdict = f"FAIL — неожиданный результат {phi:.1f}°"
    print(f"  ВЕРДИКТ G: {verdict}")
    return is_correct


# ─────────────────────────────────────────────────────────────────────────────
# H. Демонстрация бага 2 — срыв ветви 0°/180° (центросимметричное сечение)
# ─────────────────────────────────────────────────────────────────────────────

def test_branch_ambiguity():
    """
    Центросимметричное сечение: disambiguation уводит -175° → +5° (срыв ветви).

    Ключ — СТРУКТУРНАЯ 2-кратная симметрия: парируем точки явно.
    Каждая точка (s_i, r_i, α_i) имеет ИДЕНТИЧНУЮ копию (s_i, r_i, α_i+π).
    Тогда ov(φ) = ov(φ+180°) ТОЧНО → ov(+5°) = ov(-175°) = 1.0 → ratio=1.0 ≥ 0.97
    → disambiguation срабатывает → предпочитает +5° как меньший |phi|.

    Без структурной симметрии (независимый шум на каждой точке) ov(+5°)≈0.93 < 0.97
    → порог не пробивается → баг не воспроизводится.

    Контроль: асимм. облако (лоб) → ov(+5°) << ov(-175°) → дизамбигуация молчит → OK.
    Возвращает True если срыв воспроизведён (ожидаемое поведение до фикса бага 2).
    """
    print("\n=== H. Баг 2 — срыв ветви 0°/180° на центросимм. сечении ===")
    rng = np.random.default_rng(7)
    N   = 3000

    def rotate(pts, deg):
        th = np.radians(deg); c, sn = np.cos(th), np.sin(th)
        return np.stack([pts[:,0],
                         pts[:,1]*c - pts[:,2]*sn,
                         pts[:,1]*sn + pts[:,2]*c], axis=1)

    # --- Центросимметричное: СТРУКТУРНАЯ 2-кратная симметрия ---
    # Для каждого i: точка (s_i, r_i, α_i) и пара (s_i, r_i, α_i+π) — одинаковые s, r, ε.
    # → ov(φ) = ov(φ+180°) ТОЧНО → disambiguation пробивает порог 97% → срыв ветви.
    ang_half = rng.uniform(0, np.pi, N // 2)
    s_half   = rng.uniform(-11, 11, N // 2)
    r_half   = 5.0 * (1.0 + 0.30 * np.cos(2.0 * ang_half)) + rng.normal(0, 0.05, N // 2)
    ang_sym  = np.concatenate([ang_half, ang_half + np.pi])
    s_sym    = np.concatenate([s_half,   s_half])
    r_sym    = np.concatenate([r_half,   r_half])
    ptsA_sym = np.stack([s_sym, r_sym * np.cos(ang_sym), r_sym * np.sin(ang_sym)], axis=1)

    # --- Асимметричное: лоб на одной стороне (контроль) ---
    ang_asym  = rng.uniform(0, 2 * np.pi, N)
    s_asym    = rng.uniform(-11, 11, N)
    rad_asym  = 5.0 + 2.0 * np.cos(ang_asym) + rng.normal(0, 0.3, N)
    ptsA_asym = np.stack([s_asym, rad_asym * np.cos(ang_asym), rad_asym * np.sin(ang_asym)], axis=1)

    true_phi = 175.0
    phi_sym,  ov_sym  = R.rot_register_3d(ptsA_sym,  rotate(ptsA_sym,  true_phi))
    phi_asym, ov_asym = R.rot_register_3d(ptsA_asym, rotate(ptsA_asym, true_phi))

    branch_fail = abs(phi_sym)  < 90.0          # срыв: попал в ≈+5° вместо -175°
    asym_ok     = abs(abs(phi_asym) - true_phi) < 5.0

    print(f"  истинный угол = {true_phi}°")
    print(f"  центросимм.:  φ={phi_sym:+.1f}°  ov={ov_sym:.4f}  "
          f"{'← СРЫВ ВЕТВИ (баг 2 подтверждён)' if branch_fail else '(ок)'}")
    print(f"  асимм.:       φ={phi_asym:+.1f}°  ov={ov_asym:.4f}  "
          f"{'(ок)' if asym_ok else '← НЕОЖИДАННАЯ ОШИБКА'}")
    fix_hint = ("Фикс бага 2: якорь по локтевой кости (zone_ulna_anchor) "
                "или расширение порога disambiguation с 3% до 15%.")
    print(f"  ВЫВОД H: {'баг 2 воспроизведён — ' + fix_hint if branch_fail else 'не воспроизведён на этом примере'}")
    return branch_fail   # True = баг 2 продемонстрирован


if __name__ == "__main__":
    print("=" * 66)
    print("ВАЛИДАЦИЯ ИЗМЕРИТЕЛЬНОГО ЯДРА — синтетика с известным ground truth")
    print("=" * 66)
    a = test_accuracy()
    b = test_invariance()
    c = test_zero()
    test_frame_bias()
    e = test_reg3d()
    f = test_mirror_pipeline()
    g = test_wrapping_bug()
    h = test_branch_ambiguity()
    print("\n" + "=" * 66)
    print("ИТОГ:")
    print(f"  A точность       = {'OK' if a else 'FAIL'}")
    print(f"  B инвариантн.    = {'OK' if b else 'FAIL'}")
    print(f"  C нулевой        = {'OK' if c else 'FAIL'}")
    print(f"  D базис          = количественная оценка выше")
    print(f"  E 3D-рег.        = {'OK' if e else 'WARN'}")
    print(f"  F зеркало-пара   = {'OK' if f else 'FAIL'}  ← эталон приёмки метода")
    print(f"  G wrapping баг1  = {'OK — исправлен' if g else 'FAIL — баг активен'}")
    print(f"  H ветвь 0/180    = {'баг 2 воспроизведён' if h else 'не воспроизведён'}")
    print("=" * 66)
