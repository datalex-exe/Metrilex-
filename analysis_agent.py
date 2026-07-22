import json
import requests

def generate_ai_analysis(subject, user_name, beg_score, beg_total, int_score, int_total, prof_score, prof_total, api_key=None):
    """
    Performance Assessor Agent:
    Evaluates test performance metrics, analyzes strengths and weaknesses,
    and generates detailed educational feedback and actionable tips using Gemini.
    """
    beg_pct = (beg_score / beg_total * 100) if beg_total > 0 else 0
    int_pct = (int_score / int_total * 100) if int_total > 0 else 0
    prof_pct = (prof_score / prof_total * 100) if prof_total > 0 else 0
    total_score = beg_score + int_score + prof_score
    total_qs = beg_total + int_total + prof_total
    total_pct = (total_score / total_qs * 100) if total_qs > 0 else 0
    
    if api_key:
        try:
            prompt = f"""
            You are an educational psychologist and academic tutor. Analyze the following student performance report and generate personalized insights.
            
            Student Name: {user_name}
            Subject: {subject}
            
            Performance Breakdown:
            - Beginner Stage (Easy/Foundational Questions): {beg_score}/{beg_total} ({beg_pct:.1f}%)
            - Intermediate Stage (Hard/Conceptual Questions): {int_score}/{int_total} ({int_pct:.1f}%)
            - Professional Stage (Trick/Lateral Thinking Questions): {prof_score}/{prof_total} ({prof_pct:.1f}%)
            - Overall Performance: {total_score}/{total_qs} ({total_pct:.1f}%)
            
            Based on this data:
            1. Analyze their Strengths and Weaknesses in detail. Focus on the difference between their logical consistency (Intermediate) versus their attention to detail / lateral thinking (Professional) and core knowledge (Beginner).
            2. Write a professional, encouraging, and detailed feedback text (150-250 words) analyzing their performance.
            3. Provide 4-5 concrete, actionable improvement tips.
            
            Format the output strictly as a JSON object with two keys:
            - "feedback": string (the feedback text, formatted with paragraphs)
            - "tips": list of strings (individual actionable recommendations)
            
            Do not include markdown wrappers. Output only the JSON.
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
                "temperature": 0.5
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=15)
            response.raise_for_status()
            
            res_json = response.json()
            text_response = res_json['choices'][0]['message']['content']
            
            text_clean = text_response.strip()
            parsed_analysis = json.loads(text_clean)
            
            return parsed_analysis.get("feedback", ""), parsed_analysis.get("tips", [])
            
        except Exception as e:
            print(f"Analysis generation failed: {e}. Using local fallback analysis.")
            
    # Local fallback heuristics
    feedback = f"Dear {user_name}, you have completed the comprehensive assessment in {subject}. Here is our diagnostic evaluation of your scores: "
    tips = []
    
    if total_pct >= 90:
        feedback += f"Exceptional work! You demonstrated an outstanding mastery of {subject} across all learning phases. You navigated foundational concepts easily, tackled complex problems with strong logic, and avoided the cognitive traps in the trick questions. You display excellent focus and cognitive flexibility."
        tips = [
            "Keep pushing boundaries by attempting open-ended design problems or teaching these topics to peers.",
            "Work on advanced real-world projects or deep academic papers in this subject area.",
            "Challenge yourself with competitive programming, math olympiads, or high-level logical reasoning puzzles.",
            "Maintain your high attention to detail; keep a journal of edge cases or unique rules you encounter."
        ]
    elif total_pct >= 70:
        feedback += f"Well done! You have a solid grasp of {subject}. You did well on the fundamentals (Beginner) and showed good analytical thinking (Intermediate). However, you were occasionally tripped up by the wording or twists in the trick questions (Professional). Improving your detail-oriented scanning will push you to the next level."
        tips = [
            "When faced with complex questions, read them twice and explicitly list what is given versus what is actually asked.",
            "Practice solving 'brain teasers' or logic puzzles regularly to improve lateral thinking.",
            "Review the specific questions you got wrong in the Professional stage and identify the cognitive 'tricks' that misled you.",
            "Build robust debugging skills by walking through code execution or formulas line-by-line."
        ]
    elif total_pct >= 40:
        feedback += f"Good effort! You show a moderate understanding of {subject}. You have a baseline of basic knowledge (Beginner), but encountered challenges when resolving multi-step problems (Intermediate) and trick questions (Professional). Focus on building stronger conceptual models and slowing down to read details carefully."
        tips = [
            "Spend time reviewing core reference materials, tutorials, or textbook chapters to reinforce the foundations.",
            "Break down intermediate problems into smaller, isolated steps. Solve them sequentially instead of trying to process the entire problem at once.",
            "Build cheat-sheets of common formulas, rules, and syntax definitions to boost your conceptual recall.",
            "Set aside distraction-free study blocks and work on practice problems without checking the answers too quickly."
        ]
    else:
        feedback += f"We appreciate your effort in taking this diagnostic test. Your scores indicate that you need to focus on building a stronger foundation in {subject}. Struggling with beginner questions suggests gaps in core definitions. Do not worry—a structured, step-by-step review will help you build confidence."
        tips = [
            "Start with beginner-level books, courses, or interactive tutorials. Focus entirely on definitions and simple syntax.",
            "Create flashcards for essential terms and practice active recall daily.",
            "Work on simple, hands-on exercises daily (e.g. basic coding scripts, simple equations) before moving to advanced tasks.",
            "Seek out structured peer study groups or tutoring to resolve conceptual roadblocks early."
        ]
        
    return feedback, tips
