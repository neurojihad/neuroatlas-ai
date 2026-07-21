"""
A/B-проверка эквивалентности векторной `rot_register_3d` (3D-массив занятости)
и ссылочной set-реализации (Python-`set`, pre-NLS-101) — задача NLS-101.

Ссылочная set-версия живёт здесь (не в production-модуле). Скрипт NumPy-only:
тяжёлые импорты модуля (`skimage`, `radius_torsion_v3`) заглушаются в
sys.modules, поэтому DICOM/PATIENTS end-to-end здесь НЕ прогоняется.

Запуск:  python scripts/_ab_rot_register_check.py
"""

import importlib
import sys
import time
import types
from pathlib import Path

import numpy as np


def _install_import_stubs():
    """Заглушки для scipy / skimage / radius_torsion_v3, чтобы импортировать
    модуль без DICOM и без тяжёлых зависимостей (нужно только ядро регистрации,
    которому достаточно NumPy)."""
    if "scipy" not in sys.modules:
        scipy = types.ModuleType("scipy")
        ndimage = types.ModuleType("scipy.ndimage")
        ndimage.median_filter = lambda *a, **k: None
        scipy.ndimage = ndimage
        sys.modules["scipy"] = scipy
        sys.modules["scipy.ndimage"] = ndimage

    if "skimage" not in sys.modules:
        skimage = types.ModuleType("skimage")
        measure = types.ModuleType("skimage.measure")
        morphology = types.ModuleType("skimage.morphology")
        skimage.measure = measure
        skimage.morphology = morphology
        sys.modules["skimage"] = skimage
        sys.modules["skimage.measure"] = measure
        sys.modules["skimage.morphology"] = morphology

    if "radius_torsion_v3" not in sys.modules:
        rt = types.ModuleType("radius_torsion_v3")
        rt.load_dicom_series = lambda *a, **k: None
        rt.track_from_seed = lambda *a, **k: None
        rt.build_axis = lambda *a, **k: None
        rt.Axis = object
        rt.HU_CORTICAL_MIN = 700
        rt.HU_CORTICAL_MAX = 3000
        sys.modules["radius_torsion_v3"] = rt


def _load_module():
    _install_import_stubs()
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    return importlib.import_module("radius_torsion_registration")


def _synthetic_block(n_points, seed, jitter=0.0, offset=(0.0, 0.0, 0.0)):
    """Синтетический блок эпифиза ~n_points: диск ⊥ оси, протянутый по s.
    Возвращает (N, 3) массив (s, u, v) в мм."""
    rng = np.random.default_rng(seed)
    n_slices = 44
    per = max(1, n_points // n_slices)
    pts = []
    for k in range(n_slices):
        s = (k - n_slices / 2) * 0.5
        # неравномерное несимметричное сечение (несколько «долей»)
        ang = rng.uniform(-np.pi, np.pi, per)
        base = 6.0 + 2.0 * np.cos(ang) + 1.2 * np.cos(3 * ang + 0.7)
        r = base * np.sqrt(rng.uniform(0.0, 1.0, per))
        u = r * np.cos(ang) + offset[1]
        v = r * np.sin(ang) + offset[2]
        s_col = np.full(per, s + offset[0])
        if jitter:
            u = u + rng.normal(0, jitter, per)
            v = v + rng.normal(0, jitter, per)
        pts.append(np.column_stack([s_col, u, v]))
    return np.vstack(pts)


def _rotate(pts, phi_deg):
    th = np.radians(phi_deg); ct, st = np.cos(th), np.sin(th)
    out = pts.copy()
    out[:, 1] = pts[:, 1] * ct - pts[:, 2] * st
    out[:, 2] = pts[:, 1] * st + pts[:, 2] * ct
    return out


def _rot_register_3d_set(ptsA, ptsH, gv=1.0, coarse=3.0, prior=None, window=50.0):
    """Ссылочная (медленная) pre-NLS-101 реализация на Python-`set` — только для A/B."""
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
    best_phi = (best_phi + 180) % 360 - 180
    if prior is None and abs(best_phi) > 90.0:
        alt_phi = best_phi + 180.0 if best_phi < 0 else best_phi - 180.0
        alt_ov = overlap(alt_phi)
        if abs(alt_phi) < abs(best_phi) and alt_ov >= best_ov * 0.97:
            best_phi, best_ov = alt_phi, alt_ov
    return best_phi, best_ov


def main():
    mod = _load_module()
    new_fn = mod.rot_register_3d
    ref_fn = _rot_register_3d_set

    # Больная кость ~20k точек; здоровая = повёрнутая копия + шум/сдвиг уровней.
    ptsA = _synthetic_block(20000, seed=1)
    print(f"synthetic block: ptsA={len(ptsA)} points, ptsH per-case below\n")

    cases = [
        dict(name="prior=None, true=+37deg", true=37.0, jitter=0.15,
             kwargs=dict()),
        dict(name="prior=None, true=-121deg (180-ambig)", true=-121.0,
             jitter=0.15, kwargs=dict()),
        dict(name="prior given, true=+15deg", true=15.0, jitter=0.15,
             kwargs=dict(prior=10.0, window=50.0)),
        dict(name="prior given, true=-8deg, gv=0.5", true=-8.0, jitter=0.1,
             kwargs=dict(prior=-5.0, window=40.0, gv=0.5)),
        dict(name="coarse=5.0, true=+64deg", true=64.0, jitter=0.2,
             kwargs=dict(coarse=5.0)),
        dict(name="degenerate (few points) -> 0,0", true=0.0, jitter=0.0,
             kwargs=dict(), few=True),
    ]

    all_ok = True
    t_ref_total = t_new_total = 0.0
    print(f"{'case':<40} {'phi_ref':>9} {'phi_new':>9} {'ov_ref':>8} "
          f"{'ov_new':>8} {'dphi':>6} {'dov':>8}")
    print("-" * 95)
    for c in cases:
        ptsH = _rotate(ptsA, c["true"])
        rng = np.random.default_rng(99)
        ptsH = ptsH + rng.normal(0, c["jitter"], ptsH.shape) if c["jitter"] else ptsH
        if c.get("few"):
            ptsH = ptsH[:10]

        t0 = time.perf_counter()
        phi_r, ov_r = ref_fn(ptsA, ptsH, **c["kwargs"])
        t_ref = time.perf_counter() - t0

        t0 = time.perf_counter()
        phi_n, ov_n = new_fn(ptsA, ptsH, **c["kwargs"])
        t_new = time.perf_counter() - t0

        t_ref_total += t_ref; t_new_total += t_new
        dphi = abs(phi_r - phi_n); dov = abs(ov_r - ov_n)
        ok = dphi == 0.0 and dov == 0.0
        all_ok &= ok
        print(f"{c['name']:<40} {phi_r:>9.3f} {phi_n:>9.3f} {ov_r:>8.5f} "
              f"{ov_n:>8.5f} {dphi:>6.1f} {dov:>8.1e} "
              f"{'OK' if ok else 'FAIL'}")

    print("-" * 95)
    speed = t_ref_total / t_new_total if t_new_total else float("inf")
    print(f"\nTiming over {len(cases)} cases (set vs array):")
    print(f"  set  (reference): {t_ref_total*1000:8.1f} ms total")
    print(f"  array (new)     : {t_new_total*1000:8.1f} ms total")
    print(f"  speedup         : {speed:6.1f}x")
    print(f"\nA/B verdict: {'ALL EQUAL (dphi=0, dov=0)' if all_ok else 'MISMATCH!'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
