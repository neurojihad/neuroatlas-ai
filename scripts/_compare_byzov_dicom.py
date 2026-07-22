"""One-off: compare fast vs nov radius torsion on Бызов DICOM (S435870/S20)."""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

SCRIPTS = Path(__file__).resolve().parent
REPO = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import importlib.util

from radius_torsion_v3 import load_dicom_series  # noqa: E402

_fast_spec = importlib.util.spec_from_file_location(
    "radius_torsion_registration", SCRIPTS / "radius_torsion_registration.py"
)
assert _fast_spec and _fast_spec.loader
fast = importlib.util.module_from_spec(_fast_spec)
_fast_spec.loader.exec_module(fast)

# nov imports `scripts.radius_torsion_v3`; alias without a scripts package.
import radius_torsion_v3 as _v3  # noqa: E402

_scripts_pkg = importlib.util.module_from_spec(
    importlib.util.spec_from_loader("scripts", loader=None)
)
sys.modules["scripts"] = _scripts_pkg
sys.modules["scripts.radius_torsion_v3"] = _v3

_nov_spec = importlib.util.spec_from_file_location(
    "radius_torsion_registration_nov", SCRIPTS / "radius_torsion_registration_nov.py"
)
assert _nov_spec and _nov_spec.loader
nov = importlib.util.module_from_spec(_nov_spec)
_nov_spec.loader.exec_module(nov)

PATIENT = "\u0411\u044b\u0437\u043e\u0432"


def find_dicom_series_folder() -> Path:
    for user in Path("c:/Users").iterdir():
        root = user / "Downloads/Export/DICOM/S435870"
        if not root.is_dir():
            continue
        subs = [s for s in root.iterdir() if s.is_dir()]
        if not subs:
            raise FileNotFoundError(f"No series subfolders under {root}")
        return max(subs, key=lambda s: sum(1 for f in s.iterdir() if f.is_file()))
    raise FileNotFoundError("S435870 export not found under c:/Users/*/Downloads")


def run_pipeline(mod, vol, spacing, cfg, label: str) -> dict:
    t0 = time.perf_counter()
    rows, good, excess, slope, ax_a, ax_h, _res_a, _res_h, prox_hlt = mod._run_twist_profile(
        vol,
        spacing,
        seed_aff=cfg["seed_aff"],
        seed_hlt=cfg["seed_hlt"],
        prox_level_aff=cfg["prox_level_aff"],
        dist_level_aff=cfg["dist_level_aff"],
        prox_level_hlt=cfg.get("prox_level_hlt"),
        verbose=True,
    )
    sec = time.perf_counter() - t0
    n_good = 0 if good is None else len(good)
    return {
        "label": label,
        "rows": rows,
        "good": good,
        "excess": excess,
        "slope": slope,
        "prox_hlt": prox_hlt,
        "sec": sec,
        "n_levels": len(rows),
        "n_good": n_good,
        "axis_aff_mm": (ax_a.z_max - ax_a.z_min) * spacing[0],
        "axis_hlt_mm": (ax_h.z_max - ax_h.z_min) * spacing[0],
    }


def main() -> int:
    out_path = SCRIPTS / "_compare_byzov_results.txt"
    lines: list[str] = []

    def log(msg: str) -> None:
        lines.append(msg)
        print(msg, flush=True)

    series = find_dicom_series_folder()
    cfg = dict(fast.PATIENTS[PATIENT])
    log(f"DICOM series folder: {series}")
    log(f"Preset: {PATIENT} prox/dist={cfg['prox_level_aff']}/{cfg['dist_level_aff']} prox_hlt={cfg.get('prox_level_hlt')}")

    vol, _zpos, meta = load_dicom_series(str(series), dtype=np.int16)
    spacing = (meta["spacing_z"], meta["spacing_xy"], meta["spacing_xy"])
    log(f"Volume shape={vol.shape} n_slices={meta['n_slices']} spacing_z={meta['spacing_z']:.4f} mm iop={meta.get('iop')}")

    log("\n=== FAST (scripts/radius_torsion_registration.py) ===")
    rf = run_pipeline(fast, vol, spacing, cfg, "fast")
    log(
        f"FAST: excess={rf['excess']} slope={rf['slope']} "
        f"good={rf['n_good']}/{rf['n_levels']} wall={rf['sec']:.1f}s "
        f"axis_aff={rf['axis_aff_mm']:.0f}mm axis_hlt={rf['axis_hlt_mm']:.0f}mm"
    )

    log("\n=== NOV (radius_torsion_registration_nov.py) ===")
    rn = run_pipeline(nov, vol, spacing, cfg, "nov")
    log(
        f"NOV: excess={rn['excess']} slope={rn['slope']} "
        f"good={rn['n_good']}/{rn['n_levels']} wall={rn['sec']:.1f}s "
        f"axis_aff={rn['axis_aff_mm']:.0f}mm axis_hlt={rn['axis_hlt_mm']:.0f}mm"
    )

    zf = {int(r[0]): (float(r[1]), float(r[2])) for r in rf["rows"]}
    zn = {int(r[0]): (float(r[1]), float(r[2])) for r in rn["rows"]}
    common = sorted(set(zf) & set(zn))
    log("\n=== LEVEL-BY-LEVEL (common z) ===")
    log(f"z\tphi_fast\tov_fast\tphi_nov\tov_nov\tdphi")
    for z in common:
        pf, of_ = zf[z]
        pn, on = zn[z]
        log(f"{z}\t{pf:+.2f}\t{of_:.3f}\t{pn:+.2f}\t{on:.3f}\t{pn - pf:+.2f}")

    if common:
        dphi = [abs(zf[z][0] - zn[z][0]) for z in common]
        dov = [abs(zf[z][1] - zn[z][1]) for z in common]
        worst = max(common, key=lambda z: abs(zf[z][0] - zn[z][0]))
        log("\n=== SUMMARY ===")
        log(f"Common levels: {len(common)} (fast={len(zf)} nov={len(zn)})")
        log(f"|dphi| max={max(dphi):.2f} deg mean={np.mean(dphi):.2f} deg")
        log(f"|dov|  max={max(dov):.4f} mean={np.mean(dov):.4f}")
        log(f"Worst z={worst}: fast {zf[worst]} nov {zn[worst]}")
    fe, ne = rf["excess"], rn["excess"]
    if fe is not None and ne is not None:
        log(f"Excess delta (nov - fast): {ne - fe:+.1f} deg")
    log(f"Wall time: fast {rf['sec']:.1f}s  nov {rn['sec']:.1f}s  (nov {rn['sec'] / rf['sec']:.1f}x slower)")
    log("Reference (preset comment): Philips excess +71.4 deg; fast pipeline ~+94.5 deg")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"\nWrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
