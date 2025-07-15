from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime
from typing import Any, Optional

import numpy as np
from numpy.random import default_rng
from scipy.optimize import minimize
from scipy.stats import beta
from tabulate import tabulate
from tqdm import tqdm


def fit_beta_mle(
    x: np.ndarray | list[float],
    eps: float = 1e-10,
    starts: tuple[tuple[float, float], ...] = ((1, 1), (0.5, 0.5)),
) -> tuple[float, float]:
    """Fit beta distribution parameters using maximum likelihood estimation.

    Args:
        x: Input data array to fit beta distribution to.
        eps: Small epsilon value for numerical stability.
        starts: Initial parameter guesses for optimization.

    Returns:
        Tuple of (alpha, beta) parameters for the fitted beta distribution.
    """
    x = np.clip(np.asarray(x, float), eps, 1 - eps)
    m, v = x.mean(), x.var(ddof=0)
    if v != 0 and v < m * (1 - m):
        starts = [(m * (m * (1 - m) / v - 1), (1 - m) * (m * (1 - m) / v - 1))] + list(
            starts
        )
    # Try to fit the beta distribution with the given starts via MLE
    for a0, b0 in starts:
        res = minimize(
            lambda p: -beta.logpdf(x, *p).sum(),
            (max(a0, eps), max(b0, eps)),
            bounds=[(eps, None)] * 2,
            method="L-BFGS-B",
        )
        if res.success:
            return res.x
    # fallback to MoM if applicable and 1;1 otherwise
    if v == 0 or v >= m * (1 - m):
        return (1, 1)
    else:
        return (m * (m * (1 - m) / v - 1), (1 - m) * (m * (1 - m) / v - 1))


def compute_intervals_zoib(
    data: np.ndarray | list[float],
    alpha: float = 0.05,
    B: int = 10_000,
    zo_eps: float = 1e-6,
    beta_eps: float = 1e-10,
    seed: int | None = None,
) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float]]:
    """Compute confidence intervals for zero/one-inflated Beta model.

    Args:
        data: Input data array.
        alpha: Significance level for confidence intervals.
        B: Number of bootstrap samples.
        zo_eps: Epsilon for zero/one point masses.
        beta_eps: Epsilon for beta distribution fitting.
        seed: Random seed for reproducibility.

    Returns:
        Tuple containing (mean_CI, std_CI, prediction_interval) where each
        is a tuple of (lower_bound, upper_bound).
    """
    y = np.asarray(data, float)
    rng = default_rng(
        seed or int.from_bytes(hashlib.sha256(y.tobytes()).digest()[:4], "big")
    )
    n = y.size

    # empirical point masses
    pi0 = np.mean(y <= zo_eps)
    pi1 = np.mean(y >= 1 - zo_eps)
    inside = y[(y > zo_eps) & (y < 1 - zo_eps)]

    # ---- fast paths for degenerate cases -------------------------
    if inside.size == 0:
        if pi0 == 1:  # all zeros
            return (0.0, 0.0), (0.0, 0.0), (0.0, 0.0)
        if pi1 == 1:  # all ones
            return (1.0, 1.0), (0.0, 0.0), (1.0, 1.0)

        # pure Bernoulli mixture
        means = rng.binomial(n, pi1, size=B) / n
        sds = np.sqrt(means * (1 - means))
        preds = rng.binomial(1, pi1, size=B)

        q = (100 * alpha / 2, 100 * (1 - alpha / 2))
        return tuple(np.percentile(arr, q) for arr in (means, sds, preds))

    # ---- interior Beta fitted once -------------------------------
    a_hat, b_hat = fit_beta_mle(inside, beta_eps)

    # ----- 1. draw mixture samples for ALL bootstraps in one go ---
    u = rng.random((B, n))
    z0 = u < pi0
    z1 = (u >= pi0) & (u < pi0 + pi1)
    zc = ~(z0 | z1)

    sample = np.empty((B, n))
    sample[z0] = 0.0
    sample[z1] = 1.0
    sample[zc] = rng.beta(a_hat, b_hat, zc.sum())

    # ----- 2. mixture means & variances ---------------------------
    pi0_b = z0.mean(axis=1)
    pi1_b = z1.mean(axis=1)

    # Beta-component moments (only where interior obs exist)
    beta_mean_b = np.full(B, np.nan)
    beta_var_b = np.zeros(B)

    interior_counts = ((sample > zo_eps) & (sample < 1 - zo_eps)).sum(axis=1)
    need_fit = np.where(interior_counts > 1)[0]

    a_b = np.full(B, np.nan, dtype=float)
    b_b = np.full(B, np.nan, dtype=float)
    for idx in need_fit:
        a_b[idx], b_b[idx] = fit_beta_mle(
            sample[idx, (sample[idx] > zo_eps) & (sample[idx] < 1 - zo_eps)],
            beta_eps,
        )
        beta_mean_b[idx] = a_b[idx] / (a_b[idx] + b_b[idx])
        beta_var_b[idx] = (
            a_b[idx]
            * b_b[idx]
            / ((a_b[idx] + b_b[idx]) ** 2 * (a_b[idx] + b_b[idx] + 1))
        )

    # fallback to Bernoulli where no interior obs
    bern_mean = pi1_b
    bern_var = pi1_b * (1 - pi1_b)

    mu_b = np.where(
        np.isnan(beta_mean_b), bern_mean, pi1_b + (1 - pi0_b - pi1_b) * beta_mean_b
    )

    var_b = np.where(
        np.isnan(beta_mean_b),
        bern_var,
        pi0_b * (0 - mu_b) ** 2
        + pi1_b * (1 - mu_b) ** 2
        + (1 - pi0_b - pi1_b) * beta_var_b,
    )

    sd_b = np.sqrt(var_b)

    # ----- 3. one-step-ahead predictions -----------------------------
    r = rng.random(B)  # one U(0,1) per bootstrap row
    mask0 = r < pi0_b
    mask1 = (r >= pi0_b) & (r < pi0_b + pi1_b)
    maskbeta = ~(mask0 | mask1)  # interior‐Beta rows

    # build result vector
    preds = np.empty(B, dtype=float)
    preds[mask0] = 0.0
    preds[mask1] = 1.0

    # rows that really have interior observations
    valid_beta = maskbeta & (~np.isnan(a_b))
    preds[valid_beta] = rng.beta(a_b[valid_beta], b_b[valid_beta])  # broadcast draw

    # rows with *no* interior data fall back to the global fit
    missing_beta = maskbeta & np.isnan(a_b)
    preds[missing_beta] = rng.beta(a_hat, b_hat, missing_beta.sum())

    # ----- 4. percentiles -----------------------------------------
    q = (100 * alpha / 2, 100 * (1 - alpha / 2))
    ci_mean = tuple(np.percentile(mu_b, q))
    ci_sd = tuple(np.percentile(sd_b, q))
    pi_pred = tuple(np.percentile(preds, q))
    return ci_mean, ci_sd, pi_pred


def calculate_statistics_for_criterion(
    criterion_values: list[Any],
) -> Optional[
    tuple[float, float, tuple[float, float], tuple[float, float], tuple[float, float]]
]:
    """Calculate statistics for a given criterion.

    Args:
        criterion_values: List of values for the criterion.

    Returns:
        Tuple containing (mean, std, ci_mean, ci_std, pred_interval) or None if
        computation fails.
    """
    numeric_values = []
    for v in criterion_values:
        if isinstance(v, str):
            if v.endswith("%"):
                try:
                    numeric_values.append(float(v.strip("%")) / 100)
                except ValueError:
                    continue
            elif v == "Yes":
                numeric_values.append(1.0)
            elif v == "No":
                numeric_values.append(0.0)
            elif v.replace(".", "", 1).isdigit():
                try:
                    numeric_values.append(float(v))
                except ValueError:
                    continue
            else:
                continue
        elif isinstance(v, (int, float)):
            numeric_values.append(float(v))
    if not numeric_values:
        return 0, 0, (0, 0), (0, 0), (0, 0)
    data = np.array(numeric_values)
    mean = np.mean(data)
    std = np.std(data, ddof=1) if len(data) > 1 else 0
    try:
        ci_mean, ci_std, pred_interval = compute_intervals_zoib(data)
    except Exception as e:
        logging.warning(f"Failed to compute intervals: {e}")
        return None
    return mean, std, ci_mean, ci_std, pred_interval


def process_stage(
    stage: str, data: dict[str, Any], input_file: str, output_directory: str
) -> str:
    """Process a single pipeline stage and generate markdown report.

    Args:
        stage: Name of the pipeline stage to process.
        data: Dictionary containing loaded JSON data.
        input_file: Path to the input JSON file.
        output_directory: Directory to save generated reports.

    Returns:
        Path to the generated stage report file.
    """
    print(f"\n▶ Stage: {stage}")
    stage_file = os.path.join(output_directory, f"report_{stage.lower()}.md")
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(stage_file, "w", encoding="utf-8") as f:
        f.write("### Pipeline Stage Report Structure\n\n")
        f.write(f'Pipeline **"{stage}"** stage test report\n\n')
        f.write(f"Start Time: {start_time}\n\n")
        f.write(f"Processed samples: {input_file}\n\n")
        # Build a flat list of samples: (sample_id, sample_data) where sample_data contains stage info
        samples = []
        for file_name, file_data in data.items():
            # If file_data has multiple top-level entries (e.g. Task_1, Task_2 ...), treat each as separate sample
            if all(isinstance(v, dict) for v in file_data.values()):
                for inner_name, inner_data in file_data.items():
                    sample_id = inner_name  # e.g. "Task_1"
                    samples.append((sample_id, inner_data))
            else:
                # Fallback to old behaviour: whole file as one sample
                samples.append((file_name, file_data))

        criteria_types = ["acceptance_criteria", "quality_attributes"]
        for criteria_type in criteria_types:
            print(f"  ► Processing: {criteria_type}")
            if criteria_type == "acceptance_criteria":
                f.write("\n\n### Acceptance Criteria Evaluation\n\n")
            else:
                f.write("\n\n### Quality Attributes Evaluation\n\n")
            all_criteria = set()

            for sample_id, sample_data in samples:
                if stage in sample_data and criteria_type in sample_data[stage]:
                    all_criteria.update(sample_data[stage][criteria_type].keys())
            if not all_criteria:
                print("    ✖ No criteria found")
                f.write(f"No {criteria_type} found for this stage.\n\n")
                continue
            headers = ["Samples/Criteria"] + list(all_criteria)
            sample_table_data = []
            criterion_values = {c: [] for c in all_criteria}

            # Build sample data table (one row per sample)
            for sample_id, sample_data in samples:
                row_values = [sample_id]
                for criterion in all_criteria:
                    value = "N/A"
                    if stage in sample_data and criteria_type in sample_data[stage]:
                        value = sample_data[stage][criteria_type].get(criterion, "N/A")
                    row_values.append(
                        f"{value:.2%}" if isinstance(value, float) else value
                    )
                    criterion_values[criterion].append(value)
                sample_table_data.append(row_values)

            # Write sample data table
            f.write("**Sample Data Table**\n\n")
            sample_table = tabulate(
                sample_table_data,
                headers=headers,
                tablefmt="pipe",
                stralign="left",
                disable_numparse=True,
            )
            f.write(sample_table + "\n\n")

            print(f"    ⋯ Analyzing {len(all_criteria)} criteria")
            means = []
            stds = []
            ci_means = []
            ci_stds = []
            pred_intervals = []
            for criterion in tqdm(
                all_criteria,
                desc="    ⋯ Analyzing criteria",
                bar_format="{l_bar}{bar:20}| {n_fmt}/{total_fmt}",
            ):
                mean, std, ci_mean, ci_std, pred_interval = (
                    calculate_statistics_for_criterion(criterion_values[criterion])
                )
                if ci_mean is None:
                    continue
                means.append(mean)
                stds.append(std)
                ci_means.append(ci_mean)
                ci_stds.append(ci_std)
                pred_intervals.append(pred_interval)
            # Build and write aggregated data table
            if means:
                agg_table_data = [
                    ["Mean"] + [f"{m:.2%}" for m in means],
                    ["Standard Deviation"] + [f"{s:.2%}" for s in stds],
                    ["CI for mean"] + [f"({c[0]:.2%}, {c[1]:.2%})" for c in ci_means],
                    ["CI for standard deviation"]
                    + [f"({c[0]:.2%}, {c[1]:.2%})" for c in ci_stds],
                    ["Prediction interval"]
                    + [f"({p[0]:.2%}, {p[1]:.2%})" for p in pred_intervals],
                ]
                f.write("**Aggregated Statistics Table**\n\n")
                agg_table = tabulate(
                    agg_table_data,
                    headers=headers,
                    tablefmt="pipe",
                    stralign="left",
                    disable_numparse=True,
                )
                f.write(agg_table + "\n\n")
        end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"End Time: {end_time}\n")
    print("✓ Stage completed")
    return stage_file


def generate_report(input_file: str, output_directory: str | None = None) -> None:
    """Generate comprehensive reports from a JSON metrics file.

    Args:
        input_file: Path to a JSON file with metrics.
        output_directory: Directory to save generated reports. If None, uses the directory of input_file.
    """
    print("\n📊 Report Generation")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    if output_directory is None:
        output_directory = os.path.dirname(os.path.abspath(input_file)) or "."

    data = {}
    # Accept a single JSON file as input
    if not input_file.endswith(".json"):
        print(f"⚠ Error: input_file must be a .json file, got {input_file}")
        return
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            data[os.path.basename(input_file)] = json.load(f)
    except Exception as e:
        print(f"⚠ Error: {input_file} - {e}")
        return
    print(f"✓ Loaded 1 file")
    pipeline_stages = ["semantic_feedback"]
    os.makedirs(output_directory, exist_ok=True)
    print(f"\n⋯ Processing {len(pipeline_stages)} pipeline stages")
    for stage in tqdm(
        pipeline_stages,
        desc="⋯ Processing stages",
        bar_format="{l_bar}{bar:20}| {n_fmt}/{total_fmt}",
    ):
        try:
            process_stage(stage, data, input_file, output_directory)
        except Exception as e:
            print(f"⚠ Error: stage {stage} - {e}")
    print(f"\n✅ Reports generated in: {output_directory}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate markdown (and optional PDF) reports from JSON metrics produced by evaluate_feedback.py."
    )
    parser.add_argument(
        "--input_file",
        "-i",
        default="evaluation_results.json",
        help="File containing a .json file with metrics (default: ./evaluation_results.json)",
    )
    parser.add_argument(
        "--output_dir",
        "-o",
        default=None,
        help="Directory where the generated reports will be saved (default: same as input file's directory)",
    )

    args = parser.parse_args()

    generate_report(
        input_file=args.input_file,
        output_directory=args.output_dir,
    )
