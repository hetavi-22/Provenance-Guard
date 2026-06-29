import os
import json
from groq import Groq
from dotenv import load_dotenv

# Load environmental variables from .env
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is not set in environment or .env file.")

# Initialize the Groq client
client = Groq(api_key=GROQ_API_KEY)

def analyze_text_llm(text: str) -> float:
    """
    Sends the text to Groq API using Llama 3.3 70B model to determine
    the probability that the text is AI-generated.
    Returns a float score between 0.0 (likely human) and 1.0 (likely AI).
    """
    system_prompt = (
        "You are an advanced forensic linguistics analyzer. Your task is to evaluate "
        "the provided text and determine the probability (between 0.0 and 1.0) that "
        "the text is AI-generated (e.g., by a large language model) versus human-written.\n\n"
        "Analyze the text for:\n"
        "1. Structural predictability and lack of variation in sentence patterns.\n"
        "2. High frequency of standard transitions (e.g., 'Furthermore', 'Moreover', 'In conclusion', "
        "'It is important to note', 'Indeed').\n"
        "3. Absence of typical human quirks, colloquialisms, spelling/grammar slips, or unique personal voice.\n"
        "4. Blandness and generic structural layouts.\n\n"
        "Return your response ONLY as a JSON object with the following fields:\n"
        "- \"ai_probability\": A float between 0.0 and 1.0 representing the likelihood that the text is AI-generated.\n"
        "- \"reasoning\": A brief, 1-2 sentence explanation of your decision based on stylistic cues."
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Text to analyze:\n\n{text}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.1  # Low temperature for consistent analysis
        )
        
        content = response.choices[0].message.content
        data = json.loads(content)
        
        # Extract and validate probability
        prob = float(data.get("ai_probability", 0.5))
        # Keep score in [0.0, 1.0] range
        return max(0.0, min(1.0, prob))
        
    except Exception as e:
        print(f"Error calling Groq API: {e}")
        # Default fallback to 0.5 in case of api failure
        return 0.5
