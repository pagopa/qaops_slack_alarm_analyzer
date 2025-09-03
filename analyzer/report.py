import os
from datetime import datetime

def generate_alarm_statistics_html(alarm_stats, date_str):
    """Generate HTML summary statistics of alarms."""
    html = []
    sorted_alarms = sorted(alarm_stats.items(), key=lambda x: len(x[1]), reverse=True)
    
    for alarm_name, alarm_entries in sorted_alarms:
        count = len(alarm_entries)
        ids_str = ', '.join(
            [f"#{alarm['id']} ({alarm['timestamp'].strftime('%d-%m-%Y %H:%M:%S')})" for alarm in alarm_entries[:10]]
        )
        if count > 10:
            ids_str += f" ... and {count - 10} more"
        
        html.append(f"<h3>{count} x {alarm_name}</h3>")
        html.append(f"<p><strong>IDs:</strong> {ids_str}</p>")
        
        if  alarm_entries:
            timestamps = [alarm['timestamp'] for alarm in alarm_entries]
            html.append(generate_hourly_distribution_html(timestamps))
    
    html.append("<hr>")
    return "\n".join(html)

def generate_hourly_distribution_html(timestamps):
    """Generate HTML for 24-hour distribution histogram."""
    from collections import Counter
    hours = [ts.hour for ts in timestamps if ts]
    hour_counts = Counter(hours)
    
    html = []
    html.append("<table>")
    html.append("<thead><tr><th>Hour</th><th>Occurrences</th><th>Visual</th></tr></thead>")
    html.append("<tbody>")
    
    for hour in range(24):
        count = hour_counts.get(hour, 0)
        if count == 0:
            continue
        
        if count <= 2:
            icon = "🔹"
        elif count <= 5:
            icon = "🔸"
        elif count <= 9:
            icon = "🔺"
        else:
            icon = "🔥"
        
        html.append(f"<tr><td>{hour:02d}:00–{(hour + 1) % 24:02d}:00</td><td>{count}</td><td>{icon}</td></tr>")
    
    html.append("</tbody></table>")
    return "\n".join(html)

def get_report_filepath(date_str, mode):
    reports_dir = "reports"
    os.makedirs(reports_dir, exist_ok=True)
    filename = f"alarm_report_{mode}_{date_str}.html"
    return os.path.join(reports_dir, filename)

def generate_html_report(alarm_stats, total_alarms, date_str, mode):
    html_content = f"<h1>Alarm Statistics for {date_str} - {mode}</h1>\n"
    if total_alarms == 0:
        html_content += f"<p>No alarm messages found for {date_str}</p>\n"
    else:
        html_content += f"<p>Total alarm messages: {total_alarms}</p>\n<hr>\n"
        html_content += generate_alarm_statistics_html(alarm_stats, date_str)

    report_path = get_report_filepath(date_str, mode)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    return report_path

def generate_duration_report(durations, date_str, days_back, oldest, latest, num_messages, num_openings, num_closings):
    os.makedirs("reports", exist_ok=True)
    report_filename = f"duration_report_{date_str}.html"
    report_path = os.path.join("reports", report_filename)

    from_str = datetime.fromtimestamp(oldest).strftime('%Y-%m-%d %H:%M:%S')
    to_str = datetime.fromtimestamp(latest).strftime('%Y-%m-%d %H:%M:%S')

    with open(report_path, "w") as f:
        f.write("<html><head><meta charset='UTF-8'><title>Alarm Duration Report</title></head><body>")
        f.write(f"<h1>Alarm Duration Report - {date_str}</h1>")

        # Intestazione dettagliata
        f.write("<pre>")
        f.write(f"Fetching messages from the last {days_back} day(s)...\n")
        f.write(f"from:  {from_str}\n")
        f.write(f"to:    {to_str}\n")
        f.write(f"Fetched {num_messages} messages\n")
        f.write(f"openings {num_openings} openings\n")
        f.write(f"closings {num_closings} closings\n")
        f.write("</pre>")

        # Tabella
        f.write("<h2>Alarm Durations (longest open first)</h2>")
        f.write("<table border='1' cellpadding='5' cellspacing='0'>")
        f.write("<tr><th>Alarm Name</th><th>Alarm ID</th><th>Opened</th><th>Closed</th><th>Duration</th></tr>")

        for alarm_id, alarm_name, open_ts, close_ts, duration in durations:
            open_time = datetime.fromtimestamp(open_ts).strftime('%Y-%m-%d %H:%M:%S')
            dur_str = f"{duration / 3600:.0f} hours" if duration >= 3600 else f"{duration / 60:.0f} minutes"
            
            if close_ts:
                close_time = datetime.fromtimestamp(close_ts).strftime('%Y-%m-%d %H:%M:%S')
            else:
                close_time = "STILL OPEN"

            f.write(f"<tr><td>{alarm_name}</td><td>{alarm_id}</td><td>{open_time}</td><td>{close_time}</td><td>{dur_str}</td></tr>")

        f.write("</table></body></html>")

    return report_path