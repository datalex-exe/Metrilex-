import json
import requests

def generate_global_insights(user_name, tests_summary, api_key=None):
    """
    Insight Agent:
    Analyzes the user's cumulative assessment history across all subjects
    to generate a unified learning profile and customized path forward.
    """
    if not tests_summary:
        return None
        
    # Calculate simple stats
    completed_tests = [t for t in tests_summary if t['status'] == 'completed']
    if not completed_tests:
        return None
        
    avg_score_pct = 0
    total_score = sum(t['score'] for t in completed_tests)
    total_max = sum(t['max_score'] for t in completed_tests)
    if total_max > 0:
        avg_score_pct = (total_score / total_max) * 100
        
    subject_scores = {}
    for t in completed_tests:
        sub = t['subject']
        if sub not in subject_scores:
            subject_scores[sub] = []
        subject_scores[sub].append((t['score'] / t['max_score']) * 100 if t['max_score'] > 0 else 0)
        
    subject_averages = {sub: sum(scores)/len(scores) for sub, scores in subject_scores.items()}
    
    needs_work = [sub for sub, avg in subject_averages.items() if avg < 70]
    
    if api_key:
        try:
            # Prepare summary for Gemini
            history_desc = ""
            for sub, avg in subject_averages.items():
                history_desc += f"- {sub}: {avg:.1f}% average\n"
                
            prompt = f"""
            You are a senior academic advisor and learning psychologist. Analyze the following student's overall assessment record and write a high-level cognitive learning profile.
            
            Student: {user_name}
            Total Assessments: {len(completed_tests)}
            Average Score: {avg_score_pct:.1f}%
            Subject Performance:
            {history_desc}
            
            Based on this history, generate a JSON object with:
            1. "cognitive_profile": A brief, highly professional profile paragraph (60-90 words) summarizing their learning characteristics (e.g. speed, focus areas, overall strength).
            2. "next_focus": The recommended subject or focus area for their next study session (e.g. "Mathematics: focus on formulas" or "Python: practice dictionary comprehensions").
            3. "learning_strategy": A 1-sentence strategic learning recommendation.
            
            Return ONLY the valid JSON object. No markdown wrappers.
            """
            
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.4
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=12)
            response.raise_for_status()
            
            res_json = response.json()
            text_response = res_json['choices'][0]['message']['content']
            
            text_clean = text_response.strip()
            parsed_insights = json.loads(text_clean)
            
            return parsed_insights
            
        except Exception as e:
            print(f"Insight Agent failed to generate dynamic insights: {e}. Using fallback heuristics.")
            
    # Local fallback heuristics
    cognitive_profile = f"Student {user_name} has taken {len(completed_tests)} assessments, showing an overall accuracy of {avg_score_pct:.1f}%. "
    if avg_score_pct >= 85:
        cognitive_profile += "They exhibit excellent comprehension and analytical skills, mastering advanced concepts quickly."
        next_focus = "Challenge yourself with custom advanced topics or programming projects."
        learning_strategy = "Apply your knowledge to real-world tasks to build deep procedural memory."
    elif avg_score_pct >= 70:
        cognitive_profile += "They demonstrate a strong foundation with solid understanding of core concepts, but sometimes require review on edge cases."
        next_focus = needs_work[0] + " (review mistake reviews)" if needs_work else "Review intermediate chapters"
        learning_strategy = "Focus on active recall and spacing your review intervals."
    else:
        cognitive_profile += "They are developing foundational competencies in their subjects. Systematic conceptual review is recommended."
        next_focus = needs_work[0] if needs_work else "Foundational review"
        learning_strategy = "Break down learning materials into smaller chunks and practice daily."
        
    return {
        "cognitive_profile": cognitive_profile,
        "next_focus": next_focus,
        "learning_strategy": learning_strategy
    }
