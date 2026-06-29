from flask import Flask, request, jsonify, render_template_string
import uuid
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from database import init_db, add_submission, get_all_submissions, get_submission, submit_appeal, get_analytics_stats
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

# Dashboard HTML template with Premium Glassmorphic UI & Dark Mode
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Provenance Guard — Analytics Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0b0f19;
            --card-bg: rgba(22, 28, 45, 0.4);
            --card-border: rgba(255, 255, 255, 0.08);
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --color-human: #10b981;
            --color-ai: #f43f5e;
            --color-uncertain: #f59e0b;
            --accent-glow: rgba(99, 102, 241, 0.15);
            --primary: #6366f1;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Plus Jakarta Sans', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            min-height: 100vh;
            background-image: 
                radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.1) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(244, 63, 94, 0.05) 0px, transparent 50%);
            padding: 2.5rem 1.5rem;
            line-height: 1.5;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        /* Header */
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 3rem;
            border-bottom: 1px solid var(--card-border);
            padding-bottom: 1.5rem;
        }

        .logo-section h1 {
            font-size: 1.8rem;
            font-weight: 700;
            background: linear-gradient(135deg, #f8fafc 40%, #6366f1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.02em;
        }

        .logo-section p {
            color: var(--text-secondary);
            font-size: 0.9rem;
            margin-top: 0.25rem;
        }

        .status-badge {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            background: rgba(99, 102, 241, 0.1);
            border: 1px solid rgba(99, 102, 241, 0.2);
            padding: 0.5rem 1rem;
            border-radius: 9999px;
            font-size: 0.85rem;
            font-weight: 500;
            color: #818cf8;
        }

        .pulse-dot {
            width: 8px;
            height: 8px;
            background-color: var(--primary);
            border-radius: 50%;
            box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.7);
            animation: pulse 1.5s infinite;
        }

        @keyframes pulse {
            0% {
                transform: scale(0.95);
                box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.7);
            }
            70% {
                transform: scale(1);
                box-shadow: 0 0 0 6px rgba(99, 102, 241, 0);
            }
            100% {
                transform: scale(0.95);
                box-shadow: 0 0 0 0 rgba(99, 102, 241, 0);
            }
        }

        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2.5rem;
        }

        .card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 1.5rem;
            backdrop-filter: blur(12px);
            transition: transform 0.3s ease, border-color 0.3s ease;
        }

        .card:hover {
            transform: translateY(-2px);
            border-color: rgba(255, 255, 255, 0.15);
            box-shadow: 0 10px 20px -10px var(--accent-glow);
        }

        .card-label {
            font-size: 0.85rem;
            font-weight: 500;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.5rem;
        }

        .card-value {
            font-size: 2.2rem;
            font-weight: 700;
            letter-spacing: -0.03em;
        }

        /* Distribution & Visual Representation */
        .distribution-section {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 2rem;
            backdrop-filter: blur(12px);
            margin-bottom: 2.5rem;
        }

        .section-title {
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .bar-chart-container {
            height: 24px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            overflow: hidden;
            display: flex;
            margin-bottom: 1.5rem;
        }

        .chart-segment {
            height: 100%;
            transition: width 0.5s ease;
        }

        .segment-human { background-color: var(--color-human); }
        .segment-ai { background-color: var(--color-ai); }
        .segment-uncertain { background-color: var(--color-uncertain); }

        .legend-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 2rem;
        }

        .legend-item {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .legend-dot {
            width: 12px;
            height: 12px;
            border-radius: 4px;
        }

        .legend-info h4 {
            font-size: 0.95rem;
            font-weight: 600;
        }

        .legend-info p {
            font-size: 0.8rem;
            color: var(--text-secondary);
        }

        /* Table Log styling */
        .log-section {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 2rem;
            backdrop-filter: blur(12px);
            overflow: hidden;
        }

        .table-responsive {
            width: 100%;
            overflow-x: auto;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 0.9rem;
        }

        th {
            padding: 1rem;
            font-weight: 600;
            color: var(--text-secondary);
            border-bottom: 1px solid var(--card-border);
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.05em;
        }

        td {
            padding: 1.25rem 1rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            vertical-align: top;
        }

        tr:last-child td {
            border-bottom: none;
        }

        .badge {
            display: inline-flex;
            align-items: center;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.02em;
        }

        .badge-human {
            background: rgba(16, 185, 129, 0.1);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.2);
        }

        .badge-ai {
            background: rgba(244, 63, 94, 0.1);
            color: #fb7185;
            border: 1px solid rgba(244, 63, 94, 0.2);
        }

        .badge-uncertain {
            background: rgba(245, 158, 11, 0.1);
            color: #fbbf24;
            border: 1px solid rgba(245, 158, 11, 0.2);
        }

        .badge-status-review {
            background: rgba(99, 102, 241, 0.15);
            color: #a5b4fc;
            border: 1px solid rgba(99, 102, 241, 0.3);
        }

        .badge-status-classified {
            background: rgba(255, 255, 255, 0.05);
            color: var(--text-secondary);
            border: 1px solid var(--card-border);
        }

        .text-snippet {
            max-width: 320px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            color: var(--text-secondary);
            font-size: 0.85rem;
        }

        .appeal-bubble {
            margin-top: 0.5rem;
            background: rgba(99, 102, 241, 0.08);
            border-left: 3px solid var(--primary);
            padding: 0.5rem 0.75rem;
            border-radius: 0 8px 8px 0;
            font-size: 0.8rem;
            color: #c7d2fe;
            max-width: 320px;
        }

        .confidence-val {
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header>
            <div class="logo-section">
                <h1>Provenance Guard</h1>
                <p>Creative Attribution Detection Operations</p>
            </div>
            <div class="status-badge">
                <div class="pulse-dot"></div>
                Linguistic Engine Active
            </div>
        </header>

        <!-- Stats Grid -->
        <div class="stats-grid">
            <div class="card">
                <p class="card-label">Total Submissions</p>
                <h2 class="card-value">{{ stats.total_submissions }}</h2>
            </div>
            <div class="card">
                <p class="card-label">Average Confidence</p>
                <h2 class="card-value">{{ (stats.avg_confidence * 100)|int }}%</h2>
            </div>
            <div class="card">
                <p class="card-label">Appeals Lodged</p>
                <h2 class="card-value">{{ stats.total_appeals }}</h2>
            </div>
            <div class="card">
                <p class="card-label">Appeal Rate</p>
                <h2 class="card-value">{{ stats.appeal_rate }}%</h2>
            </div>
        </div>

        <!-- Distribution Breakdown -->
        <div class="distribution-section">
            <h3 class="section-title">Attribution Distribution</h3>
            
            <div class="bar-chart-container">
                <div class="chart-segment segment-human" style="width: {{ percentages.human }}%"></div>
                <div class="chart-segment segment-uncertain" style="width: {{ percentages.uncertain }}%"></div>
                <div class="chart-segment segment-ai" style="width: {{ percentages.ai }}%"></div>
            </div>

            <div class="legend-grid">
                <div class="legend-item">
                    <div class="legend-dot segment-human"></div>
                    <div class="legend-info">
                        <h4>Likely Human ({{ stats.likely_human }})</h4>
                        <p>{{ percentages.human }}% of catalog</p>
                    </div>
                </div>
                <div class="legend-item">
                    <div class="legend-dot segment-uncertain"></div>
                    <div class="legend-info">
                        <h4>Uncertain ({{ stats.uncertain }})</h4>
                        <p>{{ percentages.uncertain }}% of catalog</p>
                    </div>
                </div>
                <div class="legend-item">
                    <div class="legend-dot segment-ai"></div>
                    <div class="legend-info">
                        <h4>Likely AI ({{ stats.likely_ai }})</h4>
                        <p>{{ percentages.ai }}% of catalog</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Recent Logs Table -->
        <div class="log-section">
            <h3 class="section-title">Recent Attribution Log</h3>
            <div class="table-responsive">
                <table>
                    <thead>
                        <tr>
                            <th>Timestamp</th>
                            <th>Creator</th>
                            <th>Text Snippet</th>
                            <th>Scores (LLM/Style)</th>
                            <th>Attribution Verdict</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for entry in logs %}
                        <tr>
                            <td style="color: var(--text-secondary);">{{ entry.timestamp.split('T')[0] }} {{ entry.timestamp.split('T')[1][:5] }}</td>
                            <td style="font-weight: 500;">{{ entry.creator_id }}</td>
                            <td>
                                <div class="text-snippet" title="{{ entry.text }}">{{ entry.text }}</div>
                                {% if entry.appeal_reasoning %}
                                <div class="appeal-bubble">
                                    <strong>Creator Appeal:</strong> "{{ entry.appeal_reasoning }}"
                                </div>
                                {% endif %}
                            </td>
                            <td>
                                <span class="confidence-val" style="color: var(--primary);">{{ (entry.combined_confidence * 100)|int }}%</span> 
                                <span style="font-size: 0.8rem; color: var(--text-secondary);">({{ (entry.llm_score*100)|int }}/{{ ((entry.stylometric_score or 0.5)*100)|int }})</span>
                            </td>
                            <td>
                                {% if entry.attribution == 'likely_human' %}
                                <span class="badge badge-human">Likely Human</span>
                                {% elif entry.attribution == 'likely_ai' %}
                                <span class="badge badge-ai">Likely AI</span>
                                {% else %}
                                <span class="badge badge-uncertain">Uncertain</span>
                                {% endif %}
                            </td>
                            <td>
                                {% if entry.status == 'under_review' %}
                                <span class="badge badge-status-review">Under Review</span>
                                {% else %}
                                <span class="badge badge-status-classified">Classified</span>
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</body>
</html>
"""

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

@app.route("/dashboard", methods=["GET"])
def dashboard():
    stats = get_analytics_stats()
    logs = get_all_submissions(limit=15)
    
    # Calculate percentages for the distribution chart segment widths
    total = stats["total_submissions"]
    percentages = {"human": 0, "ai": 0, "uncertain": 0}
    if total > 0:
        percentages["human"] = int((stats["likely_human"] / total) * 100)
        percentages["ai"] = int((stats["likely_ai"] / total) * 100)
        percentages["uncertain"] = 100 - percentages["human"] - percentages["ai"] # Avoid rounding errors
        
    return render_template_string(DASHBOARD_HTML, stats=stats, logs=logs, percentages=percentages), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
