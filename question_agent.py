import json
import requests

def normalize_text(text):
    import re
    if not text:
        return ""
    return re.sub(r'[^a-zA-Z0-9]', '', text).strip().lower()

def generate_questions(subject, api_key, exclude_questions=None, chapters=None):
    """
    Question Generator Agent:
    Connects to the Gemini API to dynamically generate 30 multiple-choice questions
    (10 beginner, 10 intermediate, 10 professional trick questions) for a given subject.
    Optionally avoids generating questions in exclude_questions and focuses on specific chapters.
    """
    if not api_key:
        raise ValueError("A Gemini API Key is required to generate questions. Offline mode is disabled.")
        
    try:
        stages = ["beginner", "intermediate", "professional"]
        questions = []
        
        # Build normalized forms of excluded questions
        excluded_norms = {normalize_text(q) for q in exclude_questions} if exclude_questions else set()
        
        for stage in stages:
            if stage == "beginner":
                prompt_desc = "standard, straightforward, foundational concepts."
            elif stage == "intermediate":
                prompt_desc = "conceptually deeper, requiring multi-step reasoning or application."
            else:
                # Professional stage: trick questions
                prompt_desc = "TRICK questions. The question should have subtle wording, a logical twist, or common misconceptions. Make sure it requires lateral thinking."

            exclude_instruction = ""
            if exclude_questions:
                # Format a bullet list of previously asked questions to send to Gemini
                exclude_instruction = "\nCRITICAL: Do NOT generate any of the following questions or questions that are highly similar to them:\n" + "\n".join(f"- {q}" for q in exclude_questions)

            chapters_instruction = ""
            if chapters:
                chapters_instruction = f"\nCRITICAL: The questions generated MUST specifically cover the chapters/topics: '{chapters}' within the subject '{subject}'."

            prompt = f"""
            You are an expert educator. Generate exactly 10 multiple-choice questions for the subject '{subject}' at the '{stage.upper()}' difficulty level.
            {chapters_instruction}
            Style of questions: {prompt_desc}
            {exclude_instruction}
            
            Return the result in JSON format as a list of 10 objects. Each object MUST have the following keys:
            - "question": string (the question text)
            - "option_a": string (Option A)
            - "option_b": string (Option B)
            - "option_c": string (Option C)
            - "option_d": string (Option D)
            - "correct_option": string (must be exactly 'A', 'B', 'C', or 'D')
            - "trick_explanation": string (explaining the solution, reasoning, and specifically highlighting any trick or twist involved)
            
            Do not wrap in anything else except a valid JSON array. Do not output markdown indicators around JSON like ```json.
            """
            
            stage_questions = []
            last_parsed = []
            
            for attempt in range(3):
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={api_key}"
                    headers = {"Content-Type": "application/json"}
                    data = {
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "responseMimeType": "application/json",
                            "temperature": 0.8 + (attempt * 0.1)  # slightly higher temp on retry
                        }
                    }
                    
                    response = requests.post(url, headers=headers, json=data, timeout=15)
                    response.raise_for_status()
                    
                    res_json = response.json()
                    text_response = res_json['candidates'][0]['content']['parts'][0]['text']
                    
                    # Clean and extract JSON array safely to handle 'Extra data' or markdown wrappers
                    text_clean = text_response.strip()
                    if text_clean.startswith("```"):
                        first_newline = text_clean.find("\n")
                        if first_newline != -1:
                            text_clean = text_clean[first_newline:].strip()
                        if text_clean.endswith("```"):
                            text_clean = text_clean[:-3].strip()
                            
                    start = text_clean.find('[')
                    end = text_clean.rfind(']')
                    if start != -1 and end != -1 and end > start:
                        text_clean = text_clean[start:end+1]
                        
                    parsed_questions = json.loads(text_clean)
                    last_parsed = parsed_questions
                    
                    valid_questions = []
                    seen_in_batch = set()
                    for q in parsed_questions:
                        # Ensure basic keys exist
                        for key in ["question", "option_a", "option_b", "option_c", "option_d", "correct_option", "trick_explanation"]:
                            if key not in q:
                                q[key] = "Value missing"
                        
                        q["correct_option"] = q["correct_option"].strip().upper()
                        if q["correct_option"] not in ["A", "B", "C", "D"]:
                            q["correct_option"] = "A"
                            
                        q["stage"] = stage
                        
                        q_text = q.get("question", "")
                        norm = normalize_text(q_text)
                        
                        # Verify uniqueness against exclusions and within the current batch
                        if norm not in excluded_norms and norm not in seen_in_batch:
                            seen_in_batch.add(norm)
                            valid_questions.append(q)
                    
                    if len(valid_questions) >= 10:
                        stage_questions = valid_questions[:10]
                        # Add newly generated questions to excluded_norms so later stages also avoid them
                        for q in stage_questions:
                            excluded_norms.add(normalize_text(q['question']))
                        break
                    else:
                        print(f"[Warning] Attempt {attempt + 1} for stage {stage} yielded only {len(valid_questions)} unique questions. Retrying...")
                except Exception as e:
                    print(f"[Error] Attempt {attempt + 1} for stage {stage} failed: {e}")
            
            # Fallback if retry loop didn't succeed in finding 10 unique questions
            if not stage_questions:
                if last_parsed:
                    # Fallback to the parsed questions from the last attempt (even if some might be duplicates)
                    # to keep the app operational
                    print(f"[Fallback] Using last parsed batch for stage {stage} due to duplicate or API issues.")
                    for q in last_parsed:
                        for key in ["question", "option_a", "option_b", "option_c", "option_d", "correct_option", "trick_explanation"]:
                            if key not in q:
                                q[key] = "Value missing"
                        q["correct_option"] = q["correct_option"].strip().upper()
                        if q["correct_option"] not in ["A", "B", "C", "D"]:
                            q["correct_option"] = "A"
                        q["stage"] = stage
                        stage_questions.append(q)
                    stage_questions = stage_questions[:10]
                else:
                    raise ValueError(f"Could not generate questions for stage {stage} after 3 attempts.")
            
            questions.extend(stage_questions)
            
        if len(questions) == 30:
            return questions
        else:
            raise ValueError(f"Gemini returned {len(questions)} questions instead of the required 30.")
            
    except Exception as e:
        raise Exception(f"AI Question Generation failed: {str(e)}")
