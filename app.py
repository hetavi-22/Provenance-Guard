from flask import Flask, request, jsonify
import uuid
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from database import init_db, add_submission, get_all_submissions, get_submission, submit_appeal
from detector import analyze_text_llm
from stylometrics import analyze_stylometrics

app = Flask(__name__)

# Initialize database
init_db()

# Initialize Rate Limiter with memory storage
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://"
)

@app.route("/submit", methods=["POST"])
@limiter.limit("10 per minute;100 per day")
def submit():
    data = request.get_json() or {}
    text = data.get("text")
    creator_id = data.get("creator_id")
    
    if not text or not creator_id:
        return jsonify({"error": "Missing required fields: 'text' and 'creator_id'"}), 400
        
    # Generate content ID
    content_id = str(uuid.uuid4())
    
    # Run both detection signals
    llm_score = analyze_text_llm(text)
    stylometric_score = analyze_stylometrics(text)
    
    # Fused Score Formula (Weighted Average)
    combined_score = (0.70 * llm_score) + (0.30 * stylometric_score)
    
    # Uncertainty representation & Calibration mapping
    if combined_score >= 0.65:
        attribution = "likely_ai"
        confidence = combined_score
    elif combined_score <= 0.35:
        attribution = "likely_human"
        confidence = 1.0 - combined_score
    else:
        attribution = "uncertain"
        # Represents confidence in the uncertainty
        confidence = 1.0 - (abs(combined_score - 0.50) / 0.15)
        confidence = max(0.0, min(1.0, confidence)) # Clamp
        
    # Convert confidence to percentage for user display
    confidence_percentage = int(confidence * 100)
    
    # Generate labels based on calibrated thresholds
    if attribution == "likely_ai":
        label_title = "AI-Generated Content"
        label_desc = f"Our system has classified this content as likely AI-generated with high confidence ({confidence_percentage}%). The text displays highly uniform sentence patterns, standard transitions, and structural predictability typical of large language models."
    elif attribution == "likely_human":
        label_title = "Verified Human Writing"
        label_desc = f"Our system has classified this content as human-written with high confidence ({confidence_percentage}%). It exhibits natural variation in sentence structures and high vocabulary diversity, which are characteristic of human authorship."
    else:
        label_title = "Attribution Uncertain"
        label_desc = f"Our system detected mixed signals in this text, exhibiting traits of both human writing and automated text generator patterns (confidence of uncertainty: {confidence_percentage}%). We respect the creator's voice and encourage readers to evaluate the content based on its substance."
        
    # Write to database (audit log)
    add_submission(
        content_id=content_id,
        creator_id=creator_id,
        text=text,
        llm_score=llm_score,
        stylometric_score=stylometric_score,
        combined_confidence=combined_score,
        attribution=attribution
    )
    
    return jsonify({
        "content_id": content_id,
        "attribution": attribution,
        "confidence": round(confidence, 2),
        "label": {
            "title": label_title,
            "description": label_desc
        },
        "status": "classified"
    }), 200

@app.route("/appeal", methods=["POST"])
def appeal():
    data = request.get_json() or {}
    content_id = data.get("content_id")
    creator_reasoning = data.get("creator_reasoning")
    
    if not content_id or not creator_reasoning:
        return jsonify({"error": "Missing required fields: 'content_id' and 'creator_reasoning'"}), 400
        
    # Fetch content details
    submission = get_submission(content_id)
    if not submission:
        return jsonify({"error": f"Submission with content_id '{content_id}' not found"}), 404
        
    # Check if already under review
    if submission.get("status") == "under_review":
        return jsonify({"error": "An appeal for this submission is already under review"}), 409
        
    # Submit appeal
    success = submit_appeal(content_id, creator_reasoning)
    if not success:
        return jsonify({"error": "Failed to update appeal status in the database"}), 500
        
    return jsonify({
        "message": "Appeal received successfully. The content status is now under review.",
        "content_id": content_id,
        "status": "under_review"
    }), 200

@app.route("/log", methods=["GET"])
def get_log():
    submissions = get_all_submissions()
    return jsonify({"entries": submissions}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
