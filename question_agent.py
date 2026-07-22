import json
import requests

def normalize_text(text):
    import re
    if not text:
        return ""
    return re.sub(r'[^a-zA-Z0-9]', '', text).strip().lower()

def extract_correct_option(option_val):
    if not option_val:
        return "A"
    val = str(option_val).strip().upper()
    if val in ["A", "B", "C", "D"]:
        return val
    # Check if the string contains a standalone A, B, C, or D
    import re
    match = re.search(r'\b([A-D])\b', val)
    if match:
        return match.group(1)
    # Check if it mentions Option A, Option B, etc.
    for ch in ["A", "B", "C", "D"]:
        if f"OPTION_{ch}" in val or f"OPTION {ch}" in val:
            return ch
    # Fallback to the first letter if it's alphanumeric and in A-D
    if len(val) > 0 and val[0] in ["A", "B", "C", "D"]:
        return val[0]
    return "A"

def generate_questions(subject, api_key, exclude_questions=None, chapters=None):
    """
    Question Generator Agent:
    Connects to the Groq API to dynamically generate 30 multiple-choice questions
    (10 beginner, 10 intermediate, 10 professional/advanced questions) for a given subject.
    Optionally avoids generating questions in exclude_questions and focuses on specific chapters.
    """
    if not api_key:
        raise ValueError("A Groq API Key is required to generate questions. Offline mode is disabled.")
        
    try:
        stages = ["beginner", "intermediate", "professional"]
        questions = []
        
        # Build normalized forms of excluded questions
        excluded_norms = {normalize_text(q) for q in exclude_questions} if exclude_questions else set()
        
        for stage in stages:
            if stage == "beginner":
                prompt_desc = (
                    "foundational concepts, testing core definitions, basic syntax, and standard terminology "
                    "of the subject. Avoid any ambiguity; the question must be straightforward but academic and precise."
                )
            elif stage == "intermediate":
                prompt_desc = (
                    "conceptually deeper, requiring multi-step reasoning, practical code debugging, "
                    "or analytical application of principles to scenarios. These should be challenging, practical questions."
                )
            else:
                prompt_desc = (
                    "highly advanced, professional-grade questions. Focus on complex edge cases, optimization, "
                    "advanced architecture/design patterns, internals, and deep nuances of the subject. These questions "
                    "must test the boundaries of true expertise. Do NOT include general logic puzzles, lateral thinking "
                    "riddles, or trick wording that relies on grammatical traps; they must be strictly, deeply technical."
                )

            exclude_instruction = ""
            if exclude_questions:
                # Format a bullet list of previously asked questions to send to Groq
                exclude_instruction = "\nCRITICAL: Do NOT generate any of the following questions or questions that are highly similar to them:\n" + "\n".join(f"- {q}" for q in exclude_questions)

            chapters_instruction = ""
            if chapters:
                chapters_instruction = f"\nCRITICAL: The questions generated MUST specifically cover the chapters/topics: '{chapters}' within the subject '{subject}'."

            prompt = f"""
            You are an expert educator. Generate exactly 10 multiple-choice questions for the subject '{subject}' at the '{stage.upper()}' difficulty level.
            {chapters_instruction}
            Style of questions: {prompt_desc}
            {exclude_instruction}
            
            Return the result in JSON format as a JSON object with a single key "questions" whose value is a list of exactly 10 question objects.
            Each question object MUST have the following keys:
            - "question": string (the question text)
            - "option_a": string (Option A)
            - "option_b": string (Option B)
            - "option_c": string (Option C)
            - "option_d": string (Option D)
            - "correct_option": string (must be exactly 'A', 'B', 'C', or 'D' corresponding to the correct answer)
            - "trick_explanation": string (explaining the solution, reasoning, and specifically highlighting why the correct option is correct and why others are incorrect)
            
            CRITICAL ACCURACY REQUIREMENT:
            - Every question must be technically and factually accurate.
            - There must be exactly one correct option. The other three options must be plausible but objectively incorrect.
            - Double-check that 'correct_option' corresponds to the option that is actually correct.
            """
            
            stage_questions = []
            last_parsed = []
            
            for attempt in range(3):
                try:
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
                        "temperature": 0.2 + (attempt * 0.1)
                    }
                    
                    response = requests.post(url, headers=headers, json=data, timeout=20)
                    response.raise_for_status()
                    
                    res_json = response.json()
                    text_response = res_json['choices'][0]['message']['content']
                    
                    # Clean and extract JSON object safely
                    text_clean = text_response.strip()
                    parsed_res = json.loads(text_clean)
                    
                    # Extract questions list
                    parsed_questions = []
                    if isinstance(parsed_res, list):
                        parsed_questions = parsed_res
                    elif isinstance(parsed_res, dict):
                        if "questions" in parsed_res:
                            parsed_questions = parsed_res["questions"]
                        elif len(parsed_res) == 1:
                            val = list(parsed_res.values())[0]
                            if isinstance(val, list):
                                parsed_questions = val
                            
                    last_parsed = parsed_questions
                    
                    valid_questions = []
                    seen_in_batch = set()
                    for q in parsed_questions:
                        # Ensure basic keys exist
                        for key in ["question", "option_a", "option_b", "option_c", "option_d", "correct_option", "trick_explanation"]:
                            if key not in q:
                                q[key] = "Value missing"
                        
                        q["correct_option"] = extract_correct_option(q["correct_option"])
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
                    print(f"[Fallback] Using last parsed batch for stage {stage} due to duplicate or API issues.")
                    for q in last_parsed:
                        for key in ["question", "option_a", "option_b", "option_c", "option_d", "correct_option", "trick_explanation"]:
                            if key not in q:
                                q[key] = "Value missing"
                        q["correct_option"] = extract_correct_option(q["correct_option"])
                        q["stage"] = stage
                        stage_questions.append(q)
                    stage_questions = stage_questions[:10]
                else:
                    raise ValueError(f"Could not generate questions for stage {stage} after 3 attempts.")
            
            questions.extend(stage_questions)
            
        if len(questions) == 30:
            return questions
        else:
            raise ValueError(f"Groq returned {len(questions)} questions instead of the required 30.")
            
    except Exception as e:
        raise Exception(f"AI Question Generation failed: {str(e)}")


