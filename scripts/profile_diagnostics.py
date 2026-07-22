"""
profile_diagnostics.py — робастная оценка избытка + разделение
«проксимальный выброс» vs «истинная нелинейность профиля (Lim)».

Дроп-ин для twist_profile: подать good-уровни (zz — индексы срезов по возрастанию,
ph — UNWRAPPED phi в градусах). Возвращает набор оценок и флагов.

Идея:
  - Theil-Sen slope×span     — робастная оценка (игнорирует единичные выбросы).
  - Δφ по концам (endpoint)  — НЕробастна: битый конец её раздувает.
  - outliers                 — уровни, далеко отстоящие от робастной линии
                               (обычно проксимальная бугристость/шейка).
  - nonlinearity             — макс. остаток НЕвыбросов от робастной линии:
                               ~0 → профиль линеен (значит зазор ts↔endpoint был
                               выбросом); >порога → реальный дистальный горб (Lim),
                               и тогда slope×span занижает/искажает.
"""
import numpy as np
from scipy.stats import theilslopes


def analyze_twist_profile(zz, ph, sz=0.5, mad_k=2.0):
    zz = np.asarray(zz, float); ph = np.asarray(ph, float)
    sl, intc, _, _ = theilslopes(ph, zz)
    span = zz[-1] - zz[0]
    ts_excess = sl * span                      # робастная оценка
    endpoint_excess = ph[-1] - ph[0]           # НЕробастная (по концам)

    resid = ph - (intc + sl * zz)
    mad = np.median(np.abs(resid - np.median(resid))) + 1e-9
    outlier = np.abs(resid) > mad_k * mad
    keep = ~outlier
    # Вырожденный случай: если МАД мал и все уровни попали в «выбросы» (keep пуст),
    # чистка невозможна — откатываемся на полный набор, чтобы не падать на pk[-1].
    if not keep.any():
        keep = np.ones_like(outlier, dtype=bool)
        outlier = ~keep

    zk, pk = zz[keep], ph[keep]
    endpoint_clean = pk[-1] - pk[0]
    ts_clean = sl * (zk[-1] - zk[0])
    nonlinearity = float(np.max(np.abs(resid[keep]))) if keep.any() else 0.0

    return {
        "ts_excess": round(ts_excess, 1),          # предпочтительная оценка
        "endpoint_excess": round(endpoint_excess, 1),
        "endpoint_clean": round(endpoint_clean, 1),
        "outlier_levels": zz[outlier].astype(int).tolist(),
        "nonlinearity_deg": round(nonlinearity, 1),
        "verdict": ("НЕЛИНЕЙНЫЙ ПРОФИЛЬ (Lim): slope×span искажает"
                    if nonlinearity > 8
                    else ("ВЫБРОС(Ы) на конце: бери ts_excess, чисти уровни "
                          + str(zz[outlier].astype(int).tolist())
                          if outlier.any() else "профиль чистый и линейный")),
    }


if __name__ == "__main__":
    # самопроверка на двух эталонных профилях
    z = np.arange(472, 683, 30)
    lin = -27 + 0.62 * (z - 502); byz = lin.copy(); byz[0] = -76   # линия+выброс
    hump = -30 + 90 * ((z - z[0]) / (z[-1] - z[0])) ** 2.5          # горб Lim
    print("выброс z=472:", analyze_twist_profile(z, byz))
    print("горб (Lim)  :", analyze_twist_profile(z, hump))
