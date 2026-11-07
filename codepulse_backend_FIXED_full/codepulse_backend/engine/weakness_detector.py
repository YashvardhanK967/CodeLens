from typing import Any


def classify_topics(
    topic_rows: list[dict[str, Any]],
    minimum_attempts: int = 10,
) -> list[dict[str, Any]]:
    """Classify topics using judged submission acceptance, not eventual completion.

    minimum_attempts is retained as the argument name for compatibility; it now
    means the minimum number of judged submissions required for classification.
    """
    result = []
    for row in topic_rows:
        submissions = row.get("submission_count")
        rate = row.get("submission_success_rate")

        if submissions is None or submissions < minimum_attempts or rate is None:
            classification = "Insufficient Data"
        elif rate >= 80:
            classification = "Strong"
        elif rate >= 65:
            classification = "Good"
        elif rate >= 40:
            classification = "Developing"
        else:
            classification = "Needs Improvement"

        result.append({**row, "classification": classification})
    return result
