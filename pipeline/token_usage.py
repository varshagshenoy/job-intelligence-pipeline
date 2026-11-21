
import json
from pipeline.config import PROCESSED_DATA_DIR


INPUT_FILE = PROCESSED_DATA_DIR / "extracted_jobs.json"


def generate_token_usage_report():
    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        records = json.load(file)

    measured_records = [
        record for record in records
        if record.get("usage", {}).get("total_tokens") is not None
    ]

    if not measured_records:
        print("No token usage data available yet.")
        print("Existing extractions do not contain historical token counts.")
        return

    total_input = sum(
        record["usage"].get("input_tokens") or 0
        for record in measured_records
    )

    total_output = sum(
        record["usage"].get("output_tokens") or 0
        for record in measured_records
    )

    total_tokens = sum(
        record["usage"].get("total_tokens") or 0
        for record in measured_records
    )

    count = len(measured_records)

    report = {
        "postings_with_usage": count,
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_tokens": total_tokens,
        "average_input_tokens_per_posting": round(total_input / count, 2),
        "average_output_tokens_per_posting": round(total_output / count, 2),
        "average_total_tokens_per_posting": round(total_tokens / count, 2)
    }

    output_file = PROCESSED_DATA_DIR / "token_usage_summary.json"

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)

    print(json.dumps(report, indent=4))
    print(f"Report saved to: {output_file}")


if __name__ == "__main__":
    generate_token_usage_report()
