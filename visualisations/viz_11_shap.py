"""
viz_11_shap.py
==============
GeOS LightGBM — SHAP Interpretation Visualisations
Produces: viz_11_shap_interpretations.png

Three panels
  1. Global summary  — mean |SHAP| per feature (top 20), colour-coded by
                       whether the feature *supports* or *opposes* each class
                       on average (like a SHAP beeswarm in bar form).
  2. Per-class bars  — top 10 SHAP-driving features for each of the three
                       OS energy modes (ENERGY_SAVER / BALANCED / PERFORMANCE).
  3. Waterfall       — single-sample local explanation for one correctly-
                       classified PERFORMANCE sample, showing additive
                       contributions of the top 12 features.

Uses LightGBM's built-in pred_contrib (Tree SHAP) — no extra shap package needed.
Run from the GeOS project root:
    python viz_11_shap.py
"""

import sys
import warnings
warnings.filterwarnings("ignore", category=UserWarning)
sys.path.insert(0, ".")

import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from sklearn.impute import SimpleImputer

from ml_engine.lightgbm_policy import MODEL_FILE
from ml_engine.policy_features import feature_columns
from ml_engine.train_policy_model import DATASET, TARGET_COLUMN

# ── GeOS dark palette ────────────────────────────────────────────────────────
BG_DARK   = "#0B1B18"
BG_PANEL  = "#0F2922"
FG_TEXT   = "#E6FFF2"
SPINE_COL = "#1D6658"
C_GREEN   = "#74C69D"   # ENERGY_SAVER / supports
C_GOLD    = "#E0B34A"   # PERFORMANCE
C_RED     = "#E67E80"   # opposes / waterfall negative
C_BLUE    = "#4AB6E0"   # BALANCED
C_DIM     = "#1B7F6A"   # muted bars

CLASS_COLORS = {
    "ENERGY_SAVER": C_GREEN,
    "BALANCED":     C_BLUE,
    "PERFORMANCE":  C_GOLD,
}

plt.rcParams.update({
    "figure.facecolor":  BG_DARK,
    "axes.facecolor":    BG_PANEL,
    "text.color":        FG_TEXT,
    "axes.labelcolor":   FG_TEXT,
    "xtick.color":       FG_TEXT,
    "ytick.color":       FG_TEXT,
    "axes.spines.top":   False,
    "axes.spines.right": False,
})

TOP_N_GLOBAL     = 20   # features shown in global summary
TOP_N_PER_CLASS  = 10   # features shown per-class
TOP_N_WATERFALL  = 12   # features in waterfall


# ── helpers ──────────────────────────────────────────────────────────────────

def _style_ax(ax):
    for spine in ax.spines.values():
        spine.set_color(SPINE_COL)
    ax.tick_params(colors=FG_TEXT)


def _load_data():
    df = pd.read_csv(DATASET).dropna(subset=[TARGET_COLUMN]).copy()
    feat_cols = feature_columns()
    X = df[feat_cols]
    y = df[TARGET_COLUMN].astype(str)
    return X, y, feat_cols


def _shap_contributions(model, X, feat_cols):
    """
    Returns
    -------
    contribs : ndarray  shape (n_samples, n_features, n_classes)
    classes  : list[str]
    bias     : ndarray  shape (n_classes,)   – per-class bias terms
    """
    estimator = model.named_steps["model"]
    imputer   = model.named_steps["imputer"]
    X_imp     = imputer.transform(X)

    raw = np.asarray(
        estimator.booster_.predict(X_imp, pred_contrib=True)
    )  # shape: (n_samples, n_features*n_classes + n_classes)

    classes   = [str(c) for c in estimator.classes_]
    n_cls     = len(classes)
    n_feats   = len(feat_cols)
    block     = n_feats + 1   # features + intercept per class

    contribs  = np.zeros((len(X), n_feats, n_cls), dtype=float)
    bias      = np.zeros(n_cls, dtype=float)

    for ci in range(n_cls):
        start = ci * block
        contribs[:, :, ci] = raw[:, start : start + n_feats]
        bias[ci]            = raw[:, start + n_feats].mean()

    return contribs, classes, bias


# ── panel 1 – global mean |SHAP| summary ─────────────────────────────────────

def plot_global_summary(ax, contribs, feat_cols, classes):
    # mean |SHAP| averaged across all classes for global importance
    mean_abs = np.mean(np.abs(contribs), axis=(0, 2))   # (n_feats,)
    order    = np.argsort(mean_abs)[-TOP_N_GLOBAL:]
    vals     = mean_abs[order]
    names    = [feat_cols[i] for i in order]

    # direction: positive if avg raw contribution > 0 across all classes
    avg_dir  = np.mean(contribs, axis=(0, 2))
    bar_cols = [C_GREEN if avg_dir[i] >= 0 else C_RED for i in order]

    bars = ax.barh(names, vals, color=bar_cols, edgecolor=SPINE_COL, linewidth=0.8)
    ax.set_title("Global SHAP Summary — Mean |SHAP| per Feature (top 20)",
                 color=FG_TEXT, fontsize=11, fontweight="bold", pad=10)
    ax.set_xlabel("Mean |SHAP contribution|")

    # value labels
    for bar, v in zip(bars, vals):
        ax.text(bar.get_width() + max(vals) * 0.01, bar.get_y() + bar.get_height() / 2,
                f"{v:.4f}", va="center", color=FG_TEXT, fontsize=7.5)

    ax.axvline(vals.mean(), color=C_GOLD, linestyle="--", lw=1.2, alpha=0.8,
               label=f"Mean ({vals.mean():.4f})")

    legend_patches = [
        mpatches.Patch(color=C_GREEN, label="Avg. supports prediction"),
        mpatches.Patch(color=C_RED,   label="Avg. opposes prediction"),
    ]
    ax.legend(handles=legend_patches, facecolor=BG_PANEL, edgecolor=SPINE_COL,
              fontsize=8, loc="lower right")
    ax.grid(axis="x", alpha=0.1, color=SPINE_COL)
    _style_ax(ax)


# ── panel 2 – per-class SHAP bars ────────────────────────────────────────────

def plot_per_class(ax, contribs, feat_cols, classes, class_index):
    cls_name  = classes[class_index]
    cls_color = CLASS_COLORS.get(cls_name, C_DIM)

    cls_contribs = contribs[:, :, class_index]              # (n_samples, n_feats)
    mean_abs     = np.mean(np.abs(cls_contribs), axis=0)   # (n_feats,)
    order        = np.argsort(mean_abs)[-TOP_N_PER_CLASS:]
    vals         = mean_abs[order]
    names        = [feat_cols[i] for i in order]

    avg_dir  = np.mean(cls_contribs, axis=0)
    bar_cols = [cls_color if avg_dir[i] >= 0 else C_RED for i in order]

    bars = ax.barh(names, vals, color=bar_cols, edgecolor=SPINE_COL, linewidth=0.8)
    ax.set_title(f"{cls_name}", color=cls_color, fontsize=10, fontweight="bold", pad=8)
    ax.set_xlabel("Mean |SHAP|", fontsize=8)

    for bar, v in zip(bars, vals):
        ax.text(bar.get_width() + max(vals) * 0.02, bar.get_y() + bar.get_height() / 2,
                f"{v:.4f}", va="center", color=FG_TEXT, fontsize=7)

    ax.grid(axis="x", alpha=0.1, color=SPINE_COL)
    _style_ax(ax)


# ── panel 3 – waterfall for one sample ───────────────────────────────────────

def plot_waterfall(ax, contribs, feat_cols, classes, bias,
                   X, y, predictions, target_class="PERFORMANCE"):
    cls_index  = classes.index(target_class) if target_class in classes else 0
    cls_color  = CLASS_COLORS.get(classes[cls_index], C_GOLD)
    correct    = np.array([str(p) == classes[cls_index] for p in predictions])
    true_match = (y.to_numpy() == classes[cls_index])
    mask       = correct & true_match

    if not mask.any():
        ax.text(0.5, 0.5, f"No correctly classified {classes[cls_index]} sample found",
                ha="center", va="center", transform=ax.transAxes, color=FG_TEXT)
        return

    sample_idx  = int(np.flatnonzero(mask)[0])
    feat_shaps  = contribs[sample_idx, :, cls_index]   # (n_feats,)
    base_val    = bias[cls_index]

    # pick top |SHAP| features
    order = np.argsort(np.abs(feat_shaps))[-TOP_N_WATERFALL:]
    order = order[np.argsort(feat_shaps[order])]        # sort by value for waterfall

    names  = [feat_cols[i] for i in order]
    values = feat_shaps[order]
    colors = [C_GREEN if v >= 0 else C_RED for v in values]

    # running cumulative from base
    cumulative  = np.concatenate([[base_val], base_val + np.cumsum(values)])
    bar_lefts   = cumulative[:-1]
    bar_widths  = values

    bars = ax.barh(names, bar_widths, left=bar_lefts,
                   color=colors, edgecolor=SPINE_COL, linewidth=0.8, height=0.6)

    ax.axvline(base_val, color=C_BLUE, linestyle="--", lw=1.3, label=f"Bias ({base_val:.3f})")
    ax.axvline(cumulative[-1], color=cls_color, linestyle="-", lw=1.8,
               label=f"Final logit ({cumulative[-1]:.3f})")

    for bar, v in zip(bars, values):
        xpos = bar.get_x() + bar.get_width() + (0.005 if v >= 0 else -0.005)
        ha   = "left" if v >= 0 else "right"
        ax.text(xpos, bar.get_y() + bar.get_height() / 2,
                f"{v:+.4f}", va="center", ha=ha, color=FG_TEXT, fontsize=7.5)

    ax.set_title(f"Waterfall — Sample #{sample_idx}  →  {classes[cls_index]}",
                 color=cls_color, fontsize=10, fontweight="bold", pad=8)
    ax.set_xlabel("SHAP contribution (additive logit shift)")
    ax.legend(facecolor=BG_PANEL, edgecolor=SPINE_COL, fontsize=8)

    patch_pos = mpatches.Patch(color=C_GREEN, label="Supports prediction")
    patch_neg = mpatches.Patch(color=C_RED,   label="Opposes prediction")
    ax.legend(handles=[patch_pos, patch_neg,
                        mpatches.Patch(color=C_BLUE,  label=f"Bias ({base_val:.3f})"),
                        mpatches.Patch(color=cls_color, label=f"Final logit ({cumulative[-1]:.3f})")],
              facecolor=BG_PANEL, edgecolor=SPINE_COL, fontsize=7.5)

    ax.grid(axis="x", alpha=0.1, color=SPINE_COL)
    _style_ax(ax)


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    print("Loading model and dataset…")
    model       = joblib.load(MODEL_FILE)
    X, y, feat_cols = _load_data()

    print(f"  Dataset: {len(X):,} rows, {len(feat_cols)} features")
    print("Computing Tree SHAP contributions (this may take ~30 s)…")

    # subsample for speed — 4 000 rows is plenty for reliable means
    rng = np.random.default_rng(42)
    idx = rng.choice(len(X), size=min(4000, len(X)), replace=False)
    X_sub = X.iloc[idx].reset_index(drop=True)
    y_sub = y.iloc[idx].reset_index(drop=True)

    contribs, classes, bias = _shap_contributions(model, X_sub, feat_cols)
    predictions = model.predict(X_sub)

    print(f"  Classes: {classes}")
    print("Rendering figure…")

    # ── layout: tall figure, 3 rows
    # row 0 spans all cols  → global summary (wide horizontal bars)
    # row 1 has 3 sub-cols  → per-class bars
    # row 2 spans all cols  → waterfall
    fig = plt.figure(figsize=(20, 24))
    fig.suptitle(
        "GeOS LightGBM — Tree SHAP Interpretation Dashboard",
        fontsize=16, color=FG_TEXT, fontweight="bold", y=0.99
    )

    gs = fig.add_gridspec(
        3, 3,
        height_ratios=[1.6, 1.4, 1.4],
        hspace=0.45,
        wspace=0.38,
        left=0.12, right=0.97,
        top=0.96,  bottom=0.04,
    )

    # Panel 1 — global summary (spans all 3 columns)
    ax_global = fig.add_subplot(gs[0, :])
    plot_global_summary(ax_global, contribs, feat_cols, classes)

    # Panel 2 — per-class (one subplot per class)
    for ci, cls_name in enumerate(classes):
        ax_cls = fig.add_subplot(gs[1, ci])
        plot_per_class(ax_cls, contribs, feat_cols, classes, ci)

    # Panel 3 — waterfall for the highest-confidence class by default
    ax_wf = fig.add_subplot(gs[2, :])

    # pick whichever class has the most correctly-classified samples for demo
    best_class = max(classes, key=lambda c: np.sum(
        (np.array([str(p) for p in predictions]) == c) &
        (y_sub.to_numpy() == c)
    ))
    plot_waterfall(ax_wf, contribs, feat_cols, classes, bias,
                   X_sub, y_sub, predictions, target_class=best_class)

    out = "viz_11_shap_interpretations.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.show()
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
