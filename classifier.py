def classify_email(subject, body):
    text = f"{subject} {body}".lower()

    strong_keywords = [
        "job role", "job opportunity", "drive", "campus drive",
        "interview", "shortlisted", "selection process",
        "offer letter", "ctc", "package", "salary",
        "joining", "recruitment", "hiring",
        "registration link", "apply", "eligibility criteria",
        "online test", "technical round", "hr round"
    ]

    weak_keywords = [
        "placement coordinator",
        "placement cell",
        "training and placement",
        "tpo",
        "career guidance"
    ]

    non_placement_keywords = [
        "meeting", "circular", "notice", "holiday",
        "exam", "assignment", "attendance",
        "seminar", "workshop", "fee"
    ]

    for word in strong_keywords:
        if word in text:
            return "Placement"

    if any(w in text for w in weak_keywords):
        for ctx in ["company", "drive", "interview", "apply", "job", "role"]:
            if ctx in text:
                return "Placement"
        return "Other"

    for word in non_placement_keywords:
        if word in text:
            return "Other"

    return "Other"
