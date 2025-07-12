import os
import json
import numpy as np
import logging
from datetime import datetime
from tabulate import tabulate
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from scipy.stats import beta
from scipy.optimize import minimize
from tqdm import tqdm
import hashlib
import joblib
from joblib import Parallel, delayed
import multiprocessing
import time

def _generate_pdf(markdown_text, filename, means, stds, ci_means, ci_stds, pred_intervals):
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    flowables = []
    title_style = styles['Heading1']
    heading2_style = styles['Heading2']
    normal_style = styles['Normal']
    table_header_style = ParagraphStyle(
        'TableHeader', 
        parent=styles['Normal'],
        fontSize=10,
        fontName='Helvetica-Bold',
        alignment=1,
        textColor=colors.white,
        backColor=colors.darkblue
    )
    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontSize=9,
        leading=11,
        alignment=0
    )
    stats_cell_style = ParagraphStyle(
        'StatsCell',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Helvetica-Bold',
        leading=11,
        alignment=1
    )
    lines = markdown_text.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('###'):
            flowables.append(Paragraph(line[4:], title_style))
            flowables.append(Spacer(1, 12))
        elif line.startswith('##'):
            flowables.append(Paragraph(line[3:], heading2_style))
            flowables.append(Spacer(1, 10))
        elif line.startswith('#'):
            flowables.append(Paragraph(line[2:], heading2_style))
            flowables.append(Spacer(1, 10))
        elif '**' in line:
            line = line.replace('**', '<b>', 1)
            line = line.replace('**', '</b>', 1)
            flowables.append(Paragraph(line, normal_style))
            flowables.append(Spacer(1, 6))
        elif line.startswith('|') and i+1 < len(lines) and lines[i+1].startswith('|'):
            table_lines = []
            while i < len(lines) and lines[i].startswith('|'):
                table_lines.append(lines[i])
                i += 1
            i -= 1
            table_data = []
            for t_idx, t_line in enumerate(table_lines):
                if '----' in t_line or all(c in '|:-' for c in t_line):
                    continue
                cells = t_line.strip().split('|')
                cells = [cell.strip() for cell in cells if cell]
                row_data = []
                for c_idx, cell in enumerate(cells):
                    if t_idx == 0:
                        p = Paragraph(cell, table_header_style)
                    elif c_idx == 0 or any(stats_term in cell.lower() for stats_term in ['mean', 'deviation', 'ci for', 'prediction']):
                        p = Paragraph(cell, stats_cell_style)
                    else:
                        p = Paragraph(cell, table_cell_style)
                    row_data.append(p)
                table_data.append(row_data)
            if table_data:
                col_widths = [doc.width / len(table_data[0])] * len(table_data[0])
                if len(col_widths) > 1:
                    col_widths[0] = doc.width * 0.25
                    remaining_width = doc.width * 0.75
                    for j in range(1, len(col_widths)):
                        col_widths[j] = remaining_width / (len(col_widths) - 1)
                table = Table(table_data, colWidths=col_widths)
                table_style = TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 7),
                    ('TOPPADDING', (0, 0), (-1, 0), 7),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BACKGROUND', (0, -5), (-1, -1), colors.lightgrey),
                    ('FONTNAME', (0, -5), (0, -1), 'Helvetica-Bold'),
                ])
                table.setStyle(table_style)
                flowables.append(table)
                flowables.append(Spacer(1, 15))
        else:
            if line.strip():
                flowables.append(Paragraph(line, normal_style))
                flowables.append(Spacer(1, 6))
        i += 1
    doc.build(flowables)

def preprocess_data(data, eps=0.01):
    data = np.clip(data, eps, 1 - eps)
    return data

def fit_beta_mle(data):
    def neg_log_likelihood(params):
        a, b = params
        if a <= 0 or b <= 0:
            return np.inf
        return -np.sum(beta.logpdf(data, a, b))
    m = np.mean(data)
    v = np.var(data, ddof=0)
    if v == 0 or v >= m*(1-m):
        a0, b0 = 1, 1
    else:
        a0 = m * (m*(1 - m)/v - 1)
        b0 = (1 - m) * (m*(1 - m)/v - 1)
    result = minimize(neg_log_likelihood, [a0, b0], method='L-BFGS-B', bounds=[(1e-6, None), (1e-6, None)])
    return result.x if result.success else [a0, b0]

def compute_intervals(data, alpha=0.05, B=10000, eps=0.01):
    data_bytes = data.tobytes()
    hash_digest = hashlib.sha256(data_bytes).digest()
    seed = int.from_bytes(hash_digest[:4], byteorder='big') % (2**32)
    np.random.seed(seed)
    data = preprocess_data(data, eps)
    a_hat, b_hat = fit_beta_mle(data)
    mu_boot = []
    sigma_boot = []
    pred_boot = []
    for _ in tqdm(range(B), desc="Bootstrap", bar_format="{l_bar}{bar:20}| {n_fmt}/{total_fmt}"):
        sample = beta.rvs(a_hat, b_hat, size=len(data))
        sample = preprocess_data(sample, eps)
        try:
            a_b, b_b = fit_beta_mle(sample)
            mu_b = a_b / (a_b + b_b)
            sigma_b = np.sqrt((a_b * b_b) / ((a_b + b_b)**2 * (a_b + b_b + 1)))
            pred_b = beta.rvs(a_b, b_b)
            mu_boot.append(mu_b)
            sigma_boot.append(sigma_b)
            pred_boot.append(pred_b)
        except:
            continue
    if not mu_boot:
        return (0, 0), (0, 0), (0, 0)
    alpha_interval = [100*alpha/2, 100*(1-alpha/2)]
    ci_mean = np.percentile(mu_boot, alpha_interval)
    ci_sd = np.percentile(sigma_boot, alpha_interval)
    ci_pred = np.percentile(pred_boot, alpha_interval)
    return ci_mean, ci_sd, ci_pred

def calculate_statistics_for_criterion(criterion_name, criterion_values):
    numeric_values = []
    for v in criterion_values:
        if isinstance(v, str):
            if v.endswith('%'):
                try:
                    numeric_values.append(float(v.strip('%'))/100)
                except ValueError:
                    continue
            elif v == "Yes":
                numeric_values.append(1.0)
            elif v == "No":
                numeric_values.append(0.0)
            elif v.replace('.', '', 1).isdigit():
                try:
                    numeric_values.append(float(v))
                except ValueError:
                    continue
            else:
                continue  
        elif isinstance(v, (int, float)):
            numeric_values.append(float(v))
    if not numeric_values:
        return 0, 0, (0,0), (0,0), (0,0)
    data = np.array(numeric_values)
    mean = np.mean(data)
    std = np.std(data, ddof=1) if len(data) > 1 else 0
    try:
        ci_mean, ci_std, pred_interval = compute_intervals(data)
    except Exception as e:
        logging.warning(f"Failed to compute intervals: {e}")
        return None
    return mean, std, ci_mean, ci_std, pred_interval

def process_stage(stage, data, input_directory, output_directory, generate_pdf=False):
    print(f"\n▶ Stage: {stage}")
    stage_file = os.path.join(output_directory, f"report_{stage.lower()}.md")
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(stage_file, "w", encoding="utf-8") as f:
        f.write(f"### Pipeline Stage Report Structure\n\n")
        f.write(f"Pipeline **\"{stage}\"** stage test report\n")
        f.write(f"Start Time: {start_time}\n")
        f.write(f"Processed samples: {input_directory}\n\n")
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

        criteria_types = ['acceptance_criteria', 'quality_attributes']
        for criteria_type in criteria_types:
            print(f"  ► Processing: {criteria_type}")
            if criteria_type == 'acceptance_criteria':
                f.write(f"\n\n### Acceptance Criteria Evaluation\n\n") 
            else:
                f.write(f"\n\n### Quality Attributes Evaluation\n\n") 
            all_criteria = set()
            
            for _sample_id, sample_data in samples:
                if stage in sample_data and criteria_type in sample_data[stage]:
                    all_criteria.update(sample_data[stage][criteria_type].keys())
            if not all_criteria:
                print(f"    ✖ No criteria found")
                f.write(f"No {criteria_type} found for this stage.\n\n")
                continue
            headers = ["Samples/Criteria"] + list(all_criteria)
            table_data = []
            criterion_values = {c: [] for c in all_criteria}

            for sample_id, sample_data in samples:
                row_values = [sample_id]
                for criterion in all_criteria:
                    value = "N/A"
                    if stage in sample_data and criteria_type in sample_data[stage]:
                        value = sample_data[stage][criteria_type].get(criterion, "N/A")
                    row_values.append(value)
                    criterion_values[criterion].append(value)
                table_data.append(row_values)
            print(f"    ⋯ Analyzing {len(all_criteria)} criteria")
            means = []
            stds = []
            ci_means = []
            ci_stds = []
            pred_intervals = []
            for criterion in tqdm(all_criteria, desc="    ⋯ Progress", bar_format="{l_bar}{bar:20}| {n_fmt}/{total_fmt}"):
                mean, std, ci_mean, ci_std, pred_interval = calculate_statistics_for_criterion(
                    criterion, criterion_values[criterion]
                )
                if ci_mean is None:
                    continue
                means.append(mean)
                stds.append(std)
                ci_means.append(ci_mean)
                ci_stds.append(ci_std)
                pred_intervals.append(pred_interval)
            if means:
                table_data.extend([
                    ['Mean'] + [f'{m:.2%}' for m in means],
                    ['Standard Deviation'] + [f'{s:.2%}' for s in stds],
                    ['CI for mean'] + [f'({c[0]:.2%}, {c[1]:.2%})' for c in ci_means],
                    ['CI for standard deviation'] + [f'({c[0]:.2%}, {c[1]:.2%})' for c in ci_stds],
                    ['Prediction interval'] + [f'({p[0]:.2%}, {p[1]:.2%})' for p in pred_intervals]
                ])
                table = tabulate(table_data, headers=headers, tablefmt='pipe', stralign='left', disable_numparse=True)
                f.write(table + "\n\n")
        end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"End Time: {end_time}\n")
    if generate_pdf:
        print(f"  ► Generating PDF")
        with open(stage_file, "r", encoding="utf-8") as f:
            markdown_content = f.read()
        pdf_file = os.path.join(pdf_output_directory, f"report_{stage.lower()}.pdf")
        _generate_pdf(markdown_content, pdf_file, means, stds, ci_means, ci_stds, pred_intervals)
        print(f"    ✓ PDF saved")
    print(f"  ✓ Stage completed")
    return stage_file

def generate_report(input_directory, output_directory=None, generate_pdf=False, json_filename=None):
    print(f"\n📊 Report Generation ({'single file' if json_filename else 'all files'})")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    # If no explicit output directory, use the same as input
    if output_directory is None:
        output_directory = input_directory

    data = {}
    json_files = [f for f in os.listdir(input_directory) if f.endswith(".json")]
    # If a specific JSON file is requested, filter the list
    if json_filename:
        if json_filename not in json_files:
            raise FileNotFoundError(f"JSON file '{json_filename}' not found in {input_directory}")
        json_files = [json_filename]
    print(f"⋯ Loading {len(json_files)} JSON files")
    for file in tqdm(json_files, desc="⋯ Progress", bar_format="{l_bar}{bar:20}| {n_fmt}/{total_fmt}"):
        try:
            file_path = os.path.join(input_directory, file)
            with open(file_path, "r", encoding="utf-8") as f:
                data[file] = json.load(f)
        except Exception as e:
            print(f"⚠ Error: {file} - {e}")
    print(f"✓ Loaded {len(data)} files")
    pipeline_stages = ['router_feedback']
    os.makedirs(output_directory, exist_ok=True)
    if generate_pdf:
        global pdf_output_directory
        pdf_output_directory = os.path.join(output_directory, "pdf")
        os.makedirs(pdf_output_directory, exist_ok=True)
    print(f"\n⋯ Processing {len(pipeline_stages)} pipeline stages")
    for stage in tqdm(pipeline_stages, desc="⋯ Progress", bar_format="{l_bar}{bar:20}| {n_fmt}/{total_fmt}"):
        try:
            process_stage(stage, data, input_directory, output_directory, generate_pdf)
        except Exception as e:
            print(f"⚠ Error: stage {stage} - {e}")
    print(f"\n✅ Reports generated in: {output_directory}")
    if generate_pdf:
        print(f"✅ PDFs saved in: {pdf_output_directory}")

# --------------------------- Command-line interface ---------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate markdown (and optional PDF) reports from JSON metrics produced by evaluate_feedback.py."
    )
    parser.add_argument(
        "--input_dir",
        "-i",
        default="results",
        help="Directory containing *.json files with metrics (default: ./results)",
    )
    parser.add_argument(
        "--output_dir",
        "-o",
        default=None,
        help="Directory where the generated reports will be saved (default: same as input dir)",
    )
    parser.add_argument(
        "--json_file",
        "-f",
        default=None,
        help="Process only a specific JSON file inside the input directory",
    )
    parser.add_argument(
        "--pdf",
        action="store_true",
        help="Also create nicely formatted PDF versions of the markdown reports",
    )

    args = parser.parse_args()

    generate_report(
        input_directory=args.input_dir,
        output_directory=args.output_dir,
        generate_pdf=args.pdf,
        json_filename=args.json_file,
    )
