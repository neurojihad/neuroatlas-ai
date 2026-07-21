"""
A/B + timing harness for radius torsion registration performance (NLS-EPIC-10).

Sections:
  NLS-101 — `rot_register_3d`: vectorized occupancy array vs reference Python-set.
  NLS-102 — `cross_section`: MPR cache hits vs cold (cache cleared each call).
  NLS-103 — `block_points_cont`: NumPy batch point collection vs reference Python
            for-loop append (`_block_points_cont_legacy`).
  NLS-104 — `find_homologous_level`: two-stage coarse→fine vs dense one-stage
            (`_find_homologous_level_legacy`).
  GENERAL — combined speedup table (sum of section workloads).

Reference set-based `rot_register_3d`, legacy Python-loop `block_points_cont`,
and legacy dense homologous search live here only (not in production). Only
`radius_torsion_v3` is stubbed; **scipy and skimage are used real when present**
(NLS-102 needs ndimage.map_coordinates; NLS-103/104 need skimage). If skimage
is missing, NLS-102/103/104 SKIP gracefully.

Run:  python scripts/_ab_torsion_perf_check.py
"""

from __future__ import annotations

import importlib
import sys
import time
import types
from pathlib import Path

import numpy as np


def _skimage_available() -> bool:
    """True if real skimage.measure/morphology can be imported (needed for NLS-103)."""
    try:
        import skimage.measure  # noqa: F401
        import skimage.morphology  # noqa: F401
    except ImportError:
        return False
    return True


def _install_import_stubs():
    """Stub only radius_torsion_v3; scipy/skimage stay real when present.

    scipy is always needed (ndimage.map_coordinates). skimage is used real when
    installed (segmentation for NLS-103); only when it is genuinely missing do we
    install an empty stub so the module still imports for NLS-101 and cross_section
    timing (NLS-102) — NLS-102/103 then SKIP because segmentation is unavailable.
    """
    if not _skimage_available() and "skimage" not in sys.modules:
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


# ── NLS-101 helpers ──────────────────────────────────────────────────────────

def _synthetic_block(n_points, seed, jitter=0.0, offset=(0.0, 0.0, 0.0)):
    rng = np.random.default_rng(seed)
    n_slices = 44
    per = max(1, n_points // n_slices)
    pts = []
    for k in range(n_slices):
        s = (k - n_slices / 2) * 0.5
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
    th = np.radians(phi_deg)
    ct, st = np.cos(th), np.sin(th)
    out = pts.copy()
    out[:, 1] = pts[:, 1] * ct - pts[:, 2] * st
    out[:, 2] = pts[:, 1] * st + pts[:, 2] * ct
    return out


def _rot_register_3d_set(ptsA, ptsH, gv=1.0, coarse=3.0, prior=None, window=50.0):
    """Reference pre-NLS-101 Python-set implementation — A/B only."""
    if len(ptsA) < 50 or len(ptsH) < 50:
        return 0.0, 0.0
    occ = set(zip(np.round(ptsA[:, 0] / gv).astype(int),
                  np.round(ptsA[:, 1] / gv).astype(int),
                  np.round(ptsA[:, 2] / gv).astype(int)))
    sH = ptsH[:, 0]
    uH = ptsH[:, 1]
    vH = ptsH[:, 2]

    def overlap(phi):
        th = np.radians(phi)
        ct, st = np.cos(th), np.sin(th)
        u2 = uH * ct - vH * st
        v2 = uH * st + vH * ct
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


def run_nls101(mod) -> bool:
    print("=" * 95)
    print("NLS-101  rot_register_3d  —  set (reference) vs occupancy array (production)")
    print("=" * 95)

    new_fn = mod.rot_register_3d
    ref_fn = _rot_register_3d_set
    ptsA = _synthetic_block(20000, seed=1)
    print(f"synthetic block: ptsA={len(ptsA)} points\n")

    cases = [
        dict(name="prior=None, true=+37deg", true=37.0, jitter=0.15, kwargs=dict()),
        dict(name="prior=None, true=-121deg (180-ambig)", true=-121.0, jitter=0.15, kwargs=dict()),
        dict(name="prior given, true=+15deg", true=15.0, jitter=0.15,
             kwargs=dict(prior=10.0, window=50.0)),
        dict(name="prior given, true=-8deg, gv=0.5", true=-8.0, jitter=0.1,
             kwargs=dict(prior=-5.0, window=40.0, gv=0.5)),
        dict(name="coarse=5.0, true=+64deg", true=64.0, jitter=0.2, kwargs=dict(coarse=5.0)),
        dict(name="degenerate (few points) -> 0,0", true=0.0, jitter=0.0, kwargs=dict(), few=True),
    ]

    all_ok = True
    t_ref_total = t_new_total = 0.0
    print(f"{'case':<40} {'phi_ref':>9} {'phi_new':>9} {'ov_ref':>8} "
          f"{'ov_new':>8} {'dphi':>6} {'dov':>8}")
    print("-" * 95)
    for c in cases:
        ptsH = _rotate(ptsA, c["true"])
        rng = np.random.default_rng(99)
        if c["jitter"]:
            ptsH = ptsH + rng.normal(0, c["jitter"], ptsH.shape)
        if c.get("few"):
            ptsH = ptsH[:10]

        t0 = time.perf_counter()
        phi_r, ov_r = ref_fn(ptsA, ptsH, **c["kwargs"])
        t_ref = time.perf_counter() - t0

        t0 = time.perf_counter()
        phi_n, ov_n = new_fn(ptsA, ptsH, **c["kwargs"])
        t_new = time.perf_counter() - t0

        t_ref_total += t_ref
        t_new_total += t_new
        dphi = abs(phi_r - phi_n)
        dov = abs(ov_r - ov_n)
        ok = dphi == 0.0 and dov == 0.0
        all_ok &= ok
        print(f"{c['name']:<40} {phi_r:>9.3f} {phi_n:>9.3f} {ov_r:>8.5f} "
              f"{ov_n:>8.5f} {dphi:>6.1f} {dov:>8.1e} {'OK' if ok else 'FAIL'}")

    speed = t_ref_total / t_new_total if t_new_total else float("inf")
    print("-" * 95)
    print(f"Timing ({len(cases)} cases):")
    print(f"  set  (reference): {t_ref_total * 1e3:8.1f} ms total")
    print(f"  array (new)     : {t_new_total * 1e3:8.1f} ms total")
    print(f"  speedup         : {speed:6.1f}x")
    print(f"Equivalence      : {'ALL EQUAL (dphi=0, dov=0)' if all_ok else 'MISMATCH!'}\n")
    return all_ok, {
        "id": "NLS-101",
        "name": "rot_register_3d (set → occupancy array)",
        "t_ref_ms": t_ref_total * 1e3,
        "t_new_ms": t_new_total * 1e3,
        "speedup": speed,
    }


# ── NLS-102 helpers ──────────────────────────────────────────────────────────

class _FakeAxis:
    """Minimal axis stand-in for cross_section / block_points_cont.

    Smooth linear centerline (val_y/val_x) with constant tangent (der_y/der_x)
    and a valid z-range (z_min/z_max, used by block_points_cont). Defaults
    reproduce the original NLS-102 timing centerline; NLS-103 passes a centered,
    near-vertical axis matching its synthetic bone cylinder.
    """

    def __init__(self, y0=100.0, dy=0.45, x0=200.0, dx=0.25,
                 der_y=0.012, der_x=-0.008, z_min=0, z_max=200):
        self._y0, self._dy = y0, dy
        self._x0, self._dx = x0, dx
        self._der_y, self._der_x = der_y, der_x
        self.z_min = z_min
        self.z_max = z_max

    def der_y(self, z):
        return self._der_y

    def der_x(self, z):
        return self._der_x

    def val_y(self, z):
        return self._y0 + self._dy * float(z)

    def val_x(self, z):
        return self._x0 + self._dx * float(z)


def _cross_section_workload(mod, volume, axis, spacing, z_values, repeats_per_z=3):
    """Simulate zone_signature-like repeated MPR requests."""
    imgs = []
    for _ in range(repeats_per_z):
        for z in z_values:
            img, _ = mod.cross_section(volume, axis, z, spacing)
            imgs.append(img)
    return imgs


def run_nls102(mod) -> bool:
    print("=" * 95)
    print("NLS-102  cross_section MPR cache  —  cold (clear each call) vs warm (cached repeats)")
    print("=" * 95)

    try:
        import scipy.ndimage  # noqa: F401 — must be real, not stubbed
    except ImportError:
        print("SKIP: scipy not installed — cross_section benchmark needs ndimage.map_coordinates\n")
        return True, None

    rng = np.random.default_rng(0)
    volume = rng.integers(-200, 1200, size=(120, 256, 256), dtype=np.int16)
    axis = _FakeAxis()
    spacing = (0.5, 0.4, 0.4)
    n_unique = 20
    z_values = list(range(40, 40 + n_unique))
    n_calls = n_unique * 3  # each z requested 3× (like zone_signature ±half_zone)

    mod.clear_cross_section_cache()
    mod._CROSS_SECTION_STATS["hits"] = 0
    mod._CROSS_SECTION_STATS["misses"] = 0

    # Cold: every call is a miss (empty dict between calls; stats accumulate).
    t0 = time.perf_counter()
    for rep in range(3):
        for z in z_values:
            mod._CROSS_SECTION_CACHE.clear()
            mod.cross_section(volume, axis, z, spacing)
    t_cold = time.perf_counter() - t0
    cold_stats = mod.cross_section_cache_stats()

    mod.clear_cross_section_cache()

    # Warm: realistic pattern — 3 passes over same z set (2nd/3rd pass mostly hits).
    t0 = time.perf_counter()
    imgs = _cross_section_workload(mod, volume, axis, spacing, z_values, repeats_per_z=3)
    t_warm = time.perf_counter() - t0
    warm_stats = mod.cross_section_cache_stats()

    # Equivalence: first slice vs cached re-fetch.
    mod.clear_cross_section_cache()
    img_a, _ = mod.cross_section(volume, axis, z_values[0], spacing)
    img_b, _ = mod.cross_section(volume, axis, z_values[0], spacing)
    equal = np.array_equal(img_a, img_b)
    same_obj = img_a is img_b

    speed = t_cold / t_warm if t_warm else float("inf")
    print(f"volume shape {volume.shape}, {n_unique} unique z × 3 repeats = {n_calls} MPR calls")
    print(f"\nCold (cache cleared before every call):")
    print(f"  time   : {t_cold * 1e3:8.1f} ms  ({n_calls} calls, all misses)")
    print(f"  stats  : {cold_stats}")
    print(f"\nWarm (3× repeat same z pattern, cache on):")
    print(f"  time   : {t_warm * 1e3:8.1f} ms  ({n_calls} calls)")
    print(f"  stats  : {warm_stats}  (expected ~{n_unique} misses, ~{n_calls - n_unique} hits)")
    print(f"  speedup: {speed:6.1f}x  (warm vs cold total time)")
    print(f"\nEquivalence: cached MPR equals fresh ({equal}), same object on hit ({same_obj})\n")
    return equal, {
        "id": "NLS-102",
        "name": "cross_section MPR cache (cold → warm)",
        "t_ref_ms": t_cold * 1e3,
        "t_new_ms": t_warm * 1e3,
        "speedup": speed,
    }


# ── NLS-103 helpers ──────────────────────────────────────────────────────────

def _block_points_cont_legacy(mod, volume, axis, zc, spacing,
                              half_block=22, hu=400, res=0.5, size_mm=24):
    """Pre-NLS-103 `block_points_cont` body — Python for-loop append (A/B only).

    Verbatim copy of the old collect() loop; segmentation / connected-component
    tracking are identical to production, so only the point-building path differs.
    Skimage/scipy helpers are pulled from the loaded module namespace.
    """
    measure = mod.measure
    morphology = mod.morphology
    ndimage = mod.ndimage
    HU_CORTICAL_MIN = mod.HU_CORTICAL_MIN
    HU_CORTICAL_MAX = mod.HU_CORTICAL_MAX

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
    mpr, _ = mod.cross_section(volume, axis, zc, spacing, size_mm=size_mm, res=res)
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
            mpr, _ = mod.cross_section(volume, axis, z, spacing, size_mm=size_mm, res=res)
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


def _make_bone_volume(nz=80, ny=128, nx=128, cy=64.0, cx=64.0, r_vox=20, hu=900):
    """Synthetic volume with a vertical high-HU bone cylinder around (cy, cx).

    A solid disk (radius r_vox) repeated over every axial slice so cross_section
    + morphology segments one central component on each slice — enough for
    block_points_cont's connected-component tracking to collect a point cloud.
    """
    volume = np.full((nz, ny, nx), -1000, dtype=np.int16)
    yy, xx = np.ogrid[:ny, :nx]
    disk = (yy - cy) ** 2 + (xx - cx) ** 2 <= r_vox ** 2
    volume[:, disk] = hu
    return volume


def run_nls103(mod) -> bool:
    print("=" * 95)
    print("NLS-103  block_points_cont  —  Python for-loop append (reference) vs NumPy batch (production)")
    print("=" * 95)

    if not _skimage_available():
        print("SKIP: scikit-image not installed — block_points_cont needs "
              "morphology/measure (install via `poetry install --with ml` or pip)\n")
        return True, None
    try:
        import scipy.ndimage  # noqa: F401 — must be real
    except ImportError:
        print("SKIP: scipy not installed — block_points_cont needs ndimage\n")
        return True, None

    nz, ny, nx = 80, 128, 128
    # Wide cylinder: fills most of the ±size_mm MPR so each slice yields many
    # bone pixels — the point-collection path (where legacy loops in Python) then
    # accounts for a meaningful share of block_points_cont, exposing the batch win.
    r_vox = 55
    volume = _make_bone_volume(nz, ny, nx, cy=64.0, cx=64.0, r_vox=r_vox, hu=900)
    axis = _FakeAxis(y0=64.0, dy=0.0, x0=64.0, dx=0.0,
                     der_y=0.0, der_x=0.0, z_min=0, z_max=nz - 1)
    spacing = (0.5, 0.4, 0.4)
    zc = nz // 2
    kwargs = dict(half_block=22, hu=400, res=0.5, size_mm=24)

    # Warm the MPR cache first: cross_section is identical for both paths and
    # would otherwise dominate/skew timing. This isolates the point-collection
    # difference (Python loop vs NumPy batch).
    mod.clear_cross_section_cache()
    new_pts = mod.block_points_cont(volume, axis, zc, spacing, **kwargs)
    legacy_pts = _block_points_cont_legacy(mod, volume, axis, zc, spacing, **kwargs)

    if len(new_pts) == 0:
        print("FAIL: no points collected — synthetic bone was not segmented\n")
        return False, None

    equal = (new_pts.shape == legacy_pts.shape) and np.array_equal(new_pts, legacy_pts)

    repeats = 5
    t0 = time.perf_counter()
    for _ in range(repeats):
        _block_points_cont_legacy(mod, volume, axis, zc, spacing, **kwargs)
    t_legacy = time.perf_counter() - t0

    t0 = time.perf_counter()
    for _ in range(repeats):
        mod.block_points_cont(volume, axis, zc, spacing, **kwargs)
    t_new = time.perf_counter() - t0

    speed = t_legacy / t_new if t_new else float("inf")
    print(f"volume shape {volume.shape}, vertical bone cylinder r={r_vox}vox HU=900")
    print(f"block: zc={zc}, half_block={kwargs['half_block']}  →  n_points={len(new_pts)}")
    print(f"\nEquivalence: new vs legacy points equal ({equal}); "
          f"shapes {new_pts.shape} vs {legacy_pts.shape}")
    print(f"\nTiming ({repeats} calls each, MPR cache warm):")
    print(f"  legacy (Python loop): {t_legacy * 1e3:8.1f} ms total")
    print(f"  batch  (NumPy)      : {t_new * 1e3:8.1f} ms total")
    print(f"  speedup             : {speed:6.1f}x  (legacy vs new total time)\n")
    return equal, {
        "id": "NLS-103",
        "name": "block_points_cont (Python loop → NumPy batch)",
        "t_ref_ms": t_legacy * 1e3,
        "t_new_ms": t_new * 1e3,
        "speedup": speed,
    }


# ── NLS-104 helpers ──────────────────────────────────────────────────────────

def _find_homologous_level_legacy(mod, volM, axH, sig_ref, z_guess, spacing,
                                  search_half=130, step=2, half_zone=7,
                                  hu_min=None):
    """Pre-NLS-104 dense one-stage search (step only) — A/B reference."""
    if hu_min is None:
        hu_min = mod.HU_CORTICAL_MIN
    z0 = max(int(axH.z_min) + half_zone, int(z_guess) - search_half)
    z1 = min(int(axH.z_max) - half_zone, int(z_guess) + search_half)
    best_z, best_q = None, -1.0
    nrm_ref = np.linalg.norm(sig_ref) + 1e-9
    for z in range(z0, z1 + 1, step):
        sH = mod.zone_signature(volM, axH, z, spacing, half_zone, hu_min=hu_min)
        if sH is None:
            continue
        _, corr = mod.circular_align_angle(sig_ref, sH)
        q = float(corr.max() / (nrm_ref * (np.linalg.norm(sH) + 1e-9)))
        if q > best_q:
            best_q, best_z = q, z
    return best_z, best_q


def _make_peaked_bone_volume(nz=160, ny=96, nx=96, z_true=80, spacing_xy=0.5):
    """
    Synthetic volume: elliptical cortical ring whose eccentricity peaks at z_true.
    Homologous search should recover z_true (or nearest step) from a signature
    taken at that level.
    """
    vol = np.full((nz, ny, nx), -100, dtype=np.int16)
    cy, cx = ny / 2.0, nx / 2.0
    yy, xx = np.mgrid[0:ny, 0:nx]
    for z in range(nz):
        # eccentricity peaks at z_true (elongated ellipse), rounder away from it
        t = abs(z - z_true) / max(z_true, nz - z_true)
        ecc = 0.55 * (1.0 - t)  # 0 at ends, 0.55 at peak
        a = 14.0 * (1.0 + ecc)   # semi-axis along y
        b = 14.0 * (1.0 - ecc)   # semi-axis along x
        ry = (yy - cy) / a
        rx = (xx - cx) / b
        r = np.sqrt(ry * ry + rx * rx)
        mask = (r >= 0.75) & (r <= 1.05)
        sl = vol[z]
        sl[mask] = 900
        # soft fill for hole-fill / contour stability
        fill = r < 0.75
        sl[fill] = 450
    return vol


def run_nls104(mod) -> bool:
    print("=" * 95)
    print("NLS-104  find_homologous_level  —  dense one-stage (legacy) vs two-stage coarse→fine")
    print("=" * 95)

    if not _skimage_available():
        print("SKIP: scikit-image not installed — find_homologous_level needs "
              "skimage.measure/morphology\n")
        return True, None
    try:
        import scipy.ndimage  # noqa: F401
    except ImportError:
        print("SKIP: scipy not installed\n")
        return True, None

    z_true = 80
    half_zone = 3  # smaller zone for faster A/B (still multi-slice)
    search_half = 50
    step = 2
    spacing = (0.5, 0.5, 0.5)
    volume = _make_peaked_bone_volume(nz=160, z_true=z_true)
    axis = _FakeAxis(y0=volume.shape[1] / 2.0, dy=0.0,
                     x0=volume.shape[2] / 2.0, dx=0.0,
                     der_y=0.0, der_x=0.0,
                     z_min=0, z_max=volume.shape[0] - 1)

    mod.clear_cross_section_cache()
    sig_ref = mod.zone_signature(volume, axis, z_true, spacing, half_zone,
                                 hu_min=mod.HU_CORTICAL_MIN)
    if sig_ref is None:
        print("FAIL: could not build sig_ref at z_true (segmentation empty)\n")
        return False, None

    # Intentionally offset guess so search must walk the window
    z_guess = z_true + 28
    kwargs = dict(search_half=search_half, step=step, half_zone=half_zone,
                  hu_min=mod.HU_CORTICAL_MIN)

    mod.clear_cross_section_cache()
    t0 = time.perf_counter()
    z_leg, q_leg = _find_homologous_level_legacy(
        mod, volume, axis, sig_ref, z_guess, spacing, **kwargs)
    t_legacy = time.perf_counter() - t0

    mod.clear_cross_section_cache()
    t0 = time.perf_counter()
    z_new, q_new = mod.find_homologous_level(
        volume, axis, sig_ref, z_guess, spacing, **kwargs)
    t_new = time.perf_counter() - t0

    # Same peak expected: two-stage refine covers ±coarse_step with fine step
    z_ok = (z_leg is not None and z_new is not None
            and abs(int(z_leg) - int(z_new)) <= step)
    near_true = z_new is not None and abs(int(z_new) - z_true) <= step
    speed = t_legacy / t_new if t_new else float("inf")

    # Expected call counts (approx): dense vs coarse+fine
    z0 = max(int(axis.z_min) + half_zone, int(z_guess) - search_half)
    z1 = min(int(axis.z_max) - half_zone, int(z_guess) + search_half)
    coarse_step = max(step * 4, 8)
    n_dense = len(range(z0, z1 + 1, step))
    n_coarse = len(range(z0, z1 + 1, coarse_step))
    n_fine = len(range(0, 2 * coarse_step + 1, step))  # upper bound ±coarse

    print(f"volume {volume.shape}, z_true={z_true}, z_guess={z_guess}, "
          f"search_half={search_half}, step={step}, coarse_step={coarse_step}")
    print(f"approx zone_signature calls: dense≈{n_dense}, "
          f"two-stage≈{n_coarse}+≤{n_fine}")
    print(f"\nlegacy (dense):  z={z_leg}  q={q_leg:.4f}  {t_legacy * 1e3:8.1f} ms")
    print(f"two-stage (new): z={z_new}  q={q_new:.4f}  {t_new * 1e3:8.1f} ms")
    print(f"speedup:         {speed:6.1f}x")
    print(f"Equivalence:     |z_new−z_legacy|≤step ({z_ok}); "
          f"|z_new−z_true|≤step ({near_true})\n")
    return z_ok and near_true, {
        "id": "NLS-104",
        "name": "find_homologous_level (dense → coarse+fine)",
        "t_ref_ms": t_legacy * 1e3,
        "t_new_ms": t_new * 1e3,
        "speedup": speed,
    }


def _print_general_speedup(rows):
    """Print combined speedup table for all tickets that reported timings."""
    print("=" * 95)
    print("GENERAL SPEEDUP  —  NLS-EPIC-10 performance tickets (synthetic A/B)")
    print("=" * 95)
    print(f"{'ticket':<10} {'component':<52} {'ref ms':>9} {'new ms':>9} {'speedup':>9}")
    print("-" * 95)
    t_ref_sum = t_new_sum = 0.0
    n = 0
    for r in rows:
        if r is None:
            continue
        print(f"{r['id']:<10} {r['name']:<52} "
              f"{r['t_ref_ms']:9.1f} {r['t_new_ms']:9.1f} {r['speedup']:8.1f}x")
        t_ref_sum += r["t_ref_ms"]
        t_new_sum += r["t_new_ms"]
        n += 1
    print("-" * 95)
    if n == 0:
        print("(no timed sections — all skipped)")
        return
    overall = t_ref_sum / t_new_sum if t_new_sum else float("inf")
    print(f"{'TOTAL':<10} {'sum of section workloads (not full patient run)':<52} "
          f"{t_ref_sum:9.1f} {t_new_sum:9.1f} {overall:8.1f}x")
    print()
    print("Note: TOTAL is sum of isolated micro-benchmarks (NLS-101..104), not wall-clock")
    print("      of a full DICOM patient pipeline. Use main script + stopwatch for that.")
    print()


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    mod = _load_module()
    ok101, m101 = run_nls101(mod)
    ok102, m102 = run_nls102(mod)
    ok103, m103 = run_nls103(mod)
    ok104, m104 = run_nls104(mod)

    _print_general_speedup([m101, m102, m103, m104])

    print("=" * 95)
    overall = ok101 and ok102 and ok103 and ok104
    print(f"OVERALL: {'PASS' if overall else 'FAIL'}  "
          f"(NLS-101 {'OK' if ok101 else 'FAIL'}, "
          f"NLS-102 {'OK' if ok102 else 'FAIL'}, "
          f"NLS-103 {'OK' if ok103 else 'FAIL'}, "
          f"NLS-104 {'OK' if ok104 else 'FAIL'})")
    print("=" * 95)
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
