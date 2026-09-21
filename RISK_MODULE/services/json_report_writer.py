import json
import os
from datetime import datetime
from uuid import uuid4


MAX_STORED_REPORTS = 20


def cleanup_old_reports(
    output_dir: str = "reports",
    max_reports: int = MAX_STORED_REPORTS
):
    """
    Keep only latest N timestamped reports.
    latest_report.json is never deleted.
    """

    if not os.path.exists(output_dir):
        return

    report_files = []

    for file_name in os.listdir(output_dir):
        if not file_name.startswith("legal_risk_report_"):
            continue

        if not file_name.endswith(".json"):
            continue

        file_path = os.path.join(
            output_dir,
            file_name
        )

        report_files.append(
            file_path
        )

    report_files.sort(
        key=lambda path: os.path.getmtime(path),
        reverse=True
    )

    old_reports = report_files[max_reports:]

    for old_file in old_reports:
        try:
            os.remove(old_file)
        except Exception:
            pass


def save_json_report(
    report: dict,
    output_dir: str = "reports"
) -> str:
    """
    Save full technical JSON report.

    Saves:
    1. Unique timestamped report
    2. latest_report.json
    3. Keeps only latest MAX_STORED_REPORTS timestamped reports
    """

    os.makedirs(
        output_dir,
        exist_ok=True
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    short_id = uuid4().hex[:6]

    file_name = f"legal_risk_report_{timestamp}_{short_id}.json"

    file_path = os.path.join(
        output_dir,
        file_name
    )

    # Save timestamped report
    with open(
        file_path,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            report,
            f,
            indent=2,
            ensure_ascii=False
        )

    latest_path = os.path.join(
        output_dir,
        "latest_report.json"
    )

    # Save latest report
    with open(
        latest_path,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            report,
            f,
            indent=2,
            ensure_ascii=False
        )

    # Delete old timestamped reports
    cleanup_old_reports(
        output_dir=output_dir
    )

    return file_path