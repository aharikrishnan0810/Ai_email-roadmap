from flask import Flask, jsonify, request, render_template
from gmail_service import fetch_emails, get_gmail_service
from db import create_table_if_not_exists, insert_email
from classifier import classify_email
from db import fetch_stored_emails
from roadmap import generate_study_roadmap
from db import fetch_email_by_id

import os

app = Flask(__name__, template_folder='templates', static_folder='static')

EMAIL_FILTER = os.getenv("EMAIL_FILTER")
MAX_EMAILS = int(os.getenv("MAX_EMAILS", 20))

# --- Pages ---
@app.route("/")
def home_page():
    return render_template("index.html")

@app.route("/inbox")
def inbox_page():
    return render_template("inbox.html")

@app.route("/email/<int:email_id>")
def email_detail_page(email_id):
    return render_template("email_detail.html", email_id=email_id)

@app.route("/roadmap/<int:email_id>")
def roadmap_page(email_id):
    return render_template("roadmap.html", email_id=email_id)

# --- API Endpoints ---
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "running"})

@app.route("/fetch-emails", methods=["POST"])
def fetch_and_store_emails():
    service = get_gmail_service()
    
    # Ignore strict filtering to fetch all recent emails for classification
    emails = fetch_emails(
        service,
        from_email=None, 
        max_results=MAX_EMAILS
    )
    
    print(f"DEBUG: Fetched {len(emails) if emails else 0} emails from Gmail.")


    # emails = fetch_emails(
    #     service,
    #     from_email=EMAIL_FILTER,
    #     max_results=MAX_EMAILS
    # )

    if not emails:
        return jsonify({"message": "No emails found"}), 404

    stored = []

    for e in emails:
        category = classify_email(e["subject"], e["body"])

        insert_email(
            e["gmail_id"],
            e["from"],
            e["subject"],
            e["body"],
            category
        )

        stored.append({
            "from": e["from"],
            "subject": e["subject"],
            "category": category
        })

    return jsonify({
        "message": "Emails processed successfully",
        "count": len(stored),
        "emails": stored
    })

@app.route("/emails", methods=["GET"])
def list_emails():
    category = request.args.get("category")  # Placement / Other
    limit = int(request.args.get("limit", 50))

    emails = fetch_stored_emails(category=category, limit=limit)

    if not emails:
        return jsonify({"message": "No emails found"}), 404

    return jsonify({
        "count": len(emails),
        "emails": emails
    })

@app.route("/api/email/<int:email_id>", methods=["GET"])
def get_email_detail(email_id):
    email = fetch_email_by_id(email_id)
    if not email:
        return jsonify({"message": "Email not found"}), 404
    return jsonify(email)

@app.route("/roadmap/generate/<int:email_id>", methods=["POST"])
def generate_roadmap(email_id):
    email = fetch_email_by_id(email_id)

    if not email:
        return jsonify({"message": "Email not found"}), 404

    combined_text = f"{email['subject']} {email['body']}"
    roadmap = generate_study_roadmap(combined_text)

    return jsonify({
        "email_subject": email["subject"],
        "roadmap": roadmap
    })

if __name__ == "__main__":
    create_table_if_not_exists()
    app.run(debug=True)
