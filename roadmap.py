import os
import re
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from google import genai



# -------------------- ENV SETUP --------------------
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY missing in .env file")

client = genai.Client(api_key=API_KEY)

# Quota-safe model
MODEL_NAME = "models/gemini-flash-latest"


# -------------------- DATE EXTRACTION --------------------
def extract_target_date(text):
    patterns = [
        r"\b\d{1,2}\s(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s\d{4}",
        r"\b\d{1,2}/\d{1,2}/\d{4}",
        r"(January|February|March|April|May|June|July|August|September|October|November|December)\s\d{1,2},\s\d{4}"
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            date_str = match.group()
            for fmt in ("%d %b %Y", "%d/%m/%Y", "%B %d, %Y"):
                try:
                    return datetime.strptime(date_str, fmt)
                except:
                    pass
    return None


# -------------------- PROMPT BUILDER --------------------
def build_roadmap_prompt(email_text, start_date, target_date, total_days, mode):
    return f"""
SYSTEM ROLE:
You are a senior placement preparation mentor and career strategist.

YOUR TASK:
Analyze the given interview or placement-related EMAIL CONTENT and generate a personalized preparation roadmap.

══════════════════════════════════════
CRITICAL HARD RULES (MUST FOLLOW)
══════════════════════════════════════
1. Use ONLY the information explicitly present in the EMAIL CONTENT.
2. DO NOT assume, infer, guess, or hallucinate:
   - Company name
   - Job role
   - Interview/drive dates
   - Event type (hackathon, walk-in, off-campus, etc.)
3. Ignore forwarded-mail headers, email metadata, and sender details.
4. If multiple dates exist:
   - Prefer dates labeled as Interview, Drive, Assessment, or Final Round
   - Ignore registration closing dates
   - Choose the LATEST future interview/drive date
5. If the interview/drive date is in the past:
   - Return a JSON response with status = "interview_completed"
   - Do NOT generate a roadmap
6. Output MUST be STRICT JSON ONLY:
   - No markdown
   - No ```json blocks
   - No explanations
   - No trailing comments

══════════════════════════════════════
EMAIL CONTENT
══════════════════════════════════════
\"\"\"
{email_text}
\"\"\"

══════════════════════════════════════
CONTEXT DATA
══════════════════════════════════════
START DATE: {start_date}
TARGET DATE: {target_date}
TOTAL AVAILABLE TIME: {total_days} days
MODE: {mode}

══════════════════════════════════════
ROADMAP GENERATION RULES
══════════════════════════════════════
1. Extract clearly:
   - Company name
   - Job role
   - Interview/Drive date
2. MODE LOGIC:
   - MODE = DAY → Generate a day-wise roadmap (Day 1, Day 2, …)
   - MODE = HOUR → Generate an hour-wise roadmap (Hour 1–2, Hour 3–4, …)
3. Allocate time based on interview proximity
4. Aptitude MUST be included under Cognitive Skills
5. Follow a logical preparation sequence but compress if time is short
6. Keep content concise, practical, and placement-focused
7. Use clear sequencing for frontend rendering

══════════════════════════════════════
REFERENCE ROADMAP FLOW (GUIDED, NOT FORCED)
══════════════════════════════════════
1. Programming Skills
   - Programming concepts, coding practice, DSA basics
2. Aptitude & Cognitive Skills
   - Quantitative Aptitude, Logical Reasoning, Verbal Ability
3. Interview & Soft Skills
   - HR questions, communication, GD, email writing
4. Company-Specific Preparation
   - Company pattern, role expectations, past questions
5. Mock Interview
   - Technical + HR mock sessions
6. Final Revision & Strategy
   - Weak area revision, interview strategy, confidence building

══════════════════════════════════════
OUTPUT FORMAT (STRICT JSON ONLY)
══════════════════════════════════════

IF INTERVIEW DATE IS IN THE PAST:
{{
  "status": "interview_completed",
  "company": "",
  "job_role": "",
  "message": "The interview or drive date has already passed.",
  "recommended_actions": [
    "Review interview experience",
    "Identify weak technical areas",
    "Improve aptitude and problem-solving speed",
    "Prepare for similar upcoming roles"
  ]
}}

IF INTERVIEW DATE IS IN THE FUTURE:
{{
  "status": "active",
  "company": "",
  "job_role": "",
  "mode": "{mode}",
  "start_date": "{start_date}",
  "target_date": "{target_date}",
  "roadmap": [
    {{
      "sequence_no": 1,
      "time_slot": "",
      "title": "",
      "description": "",
      "tasks": []
    }}
  ]
}}

REMEMBER:
- JSON ONLY
- No markdown
- No explanations
"""




# -------------------- MAIN ROADMAP GENERATOR --------------------
def generate_study_roadmap(email_text):
    today = datetime.today().date()

    target_date = extract_target_date(email_text)
    if target_date:
        target_date = target_date.date()
    else:
        target_date = today + timedelta(days=1)

    total_days = (target_date - today).days
    if total_days <= 0:
        total_days = 1

    # Decide roadmap granularity
    mode = "DAY" if total_days >= 3 else "HOUR"

    prompt = build_roadmap_prompt(
        email_text=email_text,
        start_date=today.strftime("%Y-%m-%d"),
        target_date=target_date.strftime("%Y-%m-%d"),
        total_days=total_days,
        mode=mode
    )

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    raw_text = response.text.strip()
    # Remove markdown code blocks if present
    raw_text = re.sub(r"```json\s*", "", raw_text)
    raw_text = re.sub(r"```\s*", "", raw_text)
    raw_text = raw_text.strip()

    if not raw_text:
        raise ValueError("Empty response from Gemini")

    try:
        roadmap_json = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON returned by Gemini:\n{raw_text}") from e


    # return {
    #     "mode": mode,
    #     "start_date": today.strftime("%Y-%m-%d"),
    #     "target_date": target_date.strftime("%Y-%m-%d"),
    #     "total_days": total_days,
    #     "roadmap": roadmap_json["roadmap"]
    # }
    roadmap_list = roadmap_json.get("roadmap", [])
    if not roadmap_list:
        # If AI did not return roadmap, fallback to default
        roadmap_list = ["No roadmap could be generated from this email."]

    return {
        "mode": mode,
        "start_date": today.strftime("%Y-%m-%d"),
        "target_date": target_date.strftime("%Y-%m-%d"),
        "total_days": total_days,
        "roadmap": roadmap_list
    }