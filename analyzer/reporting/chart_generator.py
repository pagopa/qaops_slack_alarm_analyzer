"""
Chart generator for KPI reports using matplotlib.
Generates base64-encoded chart images for embedding in reports.
"""
import io
import base64
from typing import List, Dict, Any
from datetime import datetime
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend
import matplotlib.pyplot as plt


def format_date_for_chart(date_str: str) -> str:
    """
    Format date from DD-MM-YY to Italian abbreviated weekday + day (e.g., 'mar 13').

    Args:
        date_str: Date string in DD-MM-YY format

    Returns:
        Formatted date string (e.g., 'mar 13')
    """
    italian_weekdays = ['lun', 'mar', 'mer', 'gio', 'ven', 'sab', 'dom']

    try:
        date_obj = datetime.strptime(date_str, '%d-%m-%y')
        weekday_abbr = italian_weekdays[date_obj.weekday()]
        day_num = date_obj.day
        return f"{weekday_abbr} {day_num}"
    except ValueError:
        # Fallback to original if parsing fails
        return date_str


def generate_bar_chart(dates: List[str], values: List[int], title: str) -> str:
    """
    Generate a bar chart and return as base64-encoded PNG.

    Args:
        dates: List of date labels
        values: List of values to plot
        title: Chart title

    Returns:
        Base64-encoded PNG image as data URI
    """
    fig, ax = plt.subplots(figsize=(8, 4))

    # Create bar chart
    bars = ax.bar(dates, values, color='#4a90e2', alpha=0.8, edgecolor='#2c5f8d')

    # Customize
    ax.set_title(title, fontsize=12, fontweight='bold', pad=10)
    ax.set_xlabel('Date', fontsize=10)
    ax.set_ylabel('Count', fontsize=10)
    ax.grid(axis='y', alpha=0.3, linestyle='--')

    # Rotate x-axis labels if many dates
    if len(dates) > 10:
        plt.xticks(rotation=45, ha='right')

    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}',
                ha='center', va='bottom', fontsize=9)

    plt.tight_layout()

    # Convert to base64
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')

    return f"data:image/png;base64,{img_base64}"


def generate_line_chart(dates: List[str], metrics: Dict[str, List[int]], title: str) -> str:
    """
    Generate a multi-line chart and return as base64-encoded PNG.

    Args:
        dates: List of date labels
        metrics: Dict of metric_name -> list of values
        title: Chart title

    Returns:
        Base64-encoded PNG image as data URI
    """
    fig, ax = plt.subplots(figsize=(8, 4))

    # Color mapping for different metrics
    colors = {
        'analyzable_alarms': '#28a745',
        'ignored_alarms': '#ffa500',
        'oncall_total': '#ff6b6b',
        'oncall_in_reperibilita': '#ee5a24'
    }

    # Friendly labels
    labels = {
        'analyzable_alarms': 'Analyzable',
        'ignored_alarms': 'Ignored',
        'oncall_total': 'OnCall Total',
        'oncall_in_reperibilita': 'OnCall Reperibilità'
    }

    # Plot each metric
    for metric_name, values in metrics.items():
        color = colors.get(metric_name, '#333')
        label = labels.get(metric_name, metric_name)
        ax.plot(dates, values, marker='o', linewidth=2,
                color=color, label=label, markersize=6)

    # Customize
    ax.set_title(title, fontsize=12, fontweight='bold', pad=10)
    ax.set_xlabel('Date', fontsize=10)
    ax.set_ylabel('Count', fontsize=10)
    ax.grid(alpha=0.3, linestyle='--')
    ax.legend(loc='best', fontsize=9)

    # Rotate x-axis labels if many dates
    if len(dates) > 10:
        plt.xticks(rotation=45, ha='right')

    plt.tight_layout()

    # Convert to base64
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')

    return f"data:image/png;base64,{img_base64}"


def generate_combination_chart(
    dates: List[str],
    total_alarms: List[int],
    metrics: Dict[str, List[int]],
    title: str
) -> str:
    """
    Generate a combination chart with bars and overlaid lines.

    Args:
        dates: List of date labels
        total_alarms: List of total alarm values for bars
        metrics: Dict of metric_name -> list of values for lines
        title: Chart title

    Returns:
        Base64-encoded PNG image as data URI
    """
    fig, ax1 = plt.subplots(figsize=(10, 5))

    # Format dates for x-axis labels (e.g., 'mar 13')
    formatted_dates = [format_date_for_chart(d) for d in dates]

    # Create bars for total alarms
    bars = ax1.bar(formatted_dates, total_alarms, color='#4a90e2', alpha=0.6,
                   label='Total Alarms', edgecolor='#2c5f8d', width=0.6)

    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        if height > 0:
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}',
                    ha='center', va='bottom', fontsize=9, fontweight='bold')

    # Customize primary axis (bars)
    ax1.set_xlabel('Date', fontsize=10, fontweight='bold')
    ax1.set_ylabel('Count', fontsize=10, fontweight='bold')
    ax1.set_title(title, fontsize=12, fontweight='bold', pad=15)
    ax1.grid(axis='y', alpha=0.3, linestyle='--', zorder=0)

    # Disable x-axis offset to align with table columns
    ax1.margins(x=0.01)

    # Color mapping for different metrics
    colors = {
        'analyzable_alarms': '#28a745',
        'ignored_alarms': '#ffa500',
        'oncall_total': '#ff6b6b',
        'oncall_in_reperibilita': '#ee5a24'
    }

    # Friendly labels
    labels = {
        'analyzable_alarms': 'Analyzable',
        'ignored_alarms': 'Ignored',
        'oncall_total': 'OnCall Total',
        'oncall_in_reperibilita': 'OnCall Reperibilità'
    }

    # Overlay line charts for other metrics
    for metric_name, values in metrics.items():
        color = colors.get(metric_name, '#333')
        label = labels.get(metric_name, metric_name)
        ax1.plot(formatted_dates, values, marker='o', linewidth=2.5,
                color=color, label=label, markersize=7, zorder=5)

    # Configure x-axis ticks
    ax1.set_xticks(range(len(formatted_dates)))
    ax1.set_xticklabels(formatted_dates, rotation=0 if len(formatted_dates) <= 10 else 45,
                        ha='center' if len(formatted_dates) <= 10 else 'right')

    # Add legend
    ax1.legend(loc='upper left', fontsize=9, framealpha=0.9)

    plt.tight_layout(pad=1.5)

    # Convert to base64
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')

    return f"data:image/png;base64,{img_base64}"


def generate_charts_for_product_env(
    product: str,
    environment: str,
    dates: List[str],
    kpi_data: Dict[str, Any]
) -> Dict[str, str]:
    """
    Generate combination chart for a product/environment combination.

    Args:
        product: Product name
        environment: Environment name
        dates: List of dates
        kpi_data: KPI data for this product/environment

    Returns:
        Dict with 'combination_chart' as base64 data URI
    """
    # Extract data for charts
    total_alarms = []
    analyzable_alarms = []
    ignored_alarms = []
    oncall_total = []
    oncall_in_reperibilita = []

    for date in dates:
        data = kpi_data.get(date)
        if data:
            total_alarms.append(data.get('total_alarms', 0))
            analyzable_alarms.append(data.get('analyzable_alarms', 0))
            ignored_alarms.append(data.get('ignored_alarms', 0))
            if environment == 'prod':
                oncall_total.append(data.get('oncall_total', 0) or 0)
                oncall_in_reperibilita.append(data.get('oncall_in_reperibilita', 0) or 0)
        else:
            total_alarms.append(0)
            analyzable_alarms.append(0)
            ignored_alarms.append(0)
            if environment == 'prod':
                oncall_total.append(0)
                oncall_in_reperibilita.append(0)

    # Prepare metrics for line overlay
    metrics = {
        'analyzable_alarms': analyzable_alarms,
        'ignored_alarms': ignored_alarms
    }

    if environment == 'prod':
        metrics['oncall_total'] = oncall_total
        metrics['oncall_in_reperibilita'] = oncall_in_reperibilita

    # Generate combination chart
    combination_chart = generate_combination_chart(
        dates,
        total_alarms,
        metrics,
        f'{product} {environment.upper()} - Metrics Trend'
    )

    return {
        'combination_chart': combination_chart
    }
