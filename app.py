from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import os
import json
import db_helper
import chart_generator
import question_agent
import analysis_agent

app = Flask(__name__)
app.secret_key = 'antigravity-secret-key-9988776655'

# Initialize database on application startup
db_helper.init_db()

def get_api_key():
    # 1. Try SQLite DB configuration first (allows overriding env/placeholder defaults)
    try:
        db_key = db_helper.get_setting('gemini_api_key', '')
        if db_key:
            return db_key.strip()
    except Exception:
        pass

    # 2. Try environment variable
    key = os.environ.get('GEMINI_API_KEY')
    if key:
        return key.strip()
    
    # 3. Try reading from .env file in project directory
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(env_path):
        try:
            with open(env_path, 'r') as f:
                for line in f:
                    if line.strip() and not line.startswith('#'):
                        parts = line.strip().split('=', 1)
                        if len(parts) == 2 and parts[0].strip() == 'GEMINI_API_KEY':
                            return parts[1].strip().strip('"').strip("'")
        except Exception:
            pass
            
    return ''

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        if 'user_id' in session:
            return redirect(url_for('dashboard'))
        return render_template('login.html')

    email = request.form.get('email', '').strip().lower()
    name = request.form.get('name', '').strip()
    age_str = request.form.get('age', '').strip()
    grade = request.form.get('grade', '').strip()
    
    if not email:
        flash('Email address is required.', 'error')
        return redirect(request.referrer or url_for('login'))
        
    user = db_helper.get_user_by_email(email)
    
    if user:
        # Existing user logs in successfully
        session['user_id'] = user['id']
        session['user_name'] = user['name']
        flash(f"Welcome back, {user['name']}!", 'success')
        return redirect(url_for('dashboard'))
    else:
        # Register new user
        if not name:
            flash('Full name is required for new registration.', 'error')
            return redirect(url_for('index'))
            
        try:
            age = int(age_str) if age_str else None
        except ValueError:
            flash('Age must be a valid number.', 'error')
            return redirect(url_for('index'))
            
        user_id = db_helper.create_user(name, email, age, grade)
        if user_id:
            session['user_id'] = user_id
            session['user_name'] = name
            flash('Account registered successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Failed to create account. Please try again.', 'error')
            return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('index'))
        
    user = db_helper.get_user_by_id(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('index'))
        
    tests = db_helper.get_user_tests(user['id'])
    
    # Generate Global Insights if they have completed tests
    global_insight = None
    completed_tests = [t for t in tests if t['status'] == 'completed']
    if completed_tests:
        # Check if we already have it in the session
        global_insight = session.get('global_insight')
        if not global_insight:
            api_key = get_api_key()
            import insight_agent
            # Convert SQLite rows to dictionary list for serialization
            tests_summary = [dict(t) for t in completed_tests]
            global_insight = insight_agent.generate_global_insights(user['name'], tests_summary, api_key)
            session['global_insight'] = global_insight
            
    return render_template('dashboard.html', user=user, tests=tests, global_insight=global_insight)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        key = request.form.get('gemini_api_key', '').strip()
        db_helper.set_setting('gemini_api_key', key)
        flash('API configuration updated successfully!', 'success')
        return redirect(url_for('settings'))
        
    api_key = get_api_key()
    api_configured = bool(api_key)
    return render_template('settings.html', api_configured=api_configured)

@app.route('/test/setup', methods=['GET', 'POST'])
def setup_test():
    if 'user_id' not in session:
        return redirect(url_for('index'))
        
    api_key = get_api_key()
    api_configured = bool(api_key)
    
    if not api_configured:
        flash('Testing is currently unavailable (no administrator API Key is configured).', 'error')
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        subject = request.form.get('subject', 'Python Programming').strip()
        chapters = request.form.get('chapters', '').strip()
        if not subject:
            subject = 'Python Programming'
        user_id = session['user_id']
        
        # Create test session in db
        test_id = db_helper.create_test_session(user_id, subject, chapters if chapters else None)
        
        try:
            # Fetch previously asked questions for this user and subject to exclude duplicates
            previous_questions = db_helper.get_user_previous_questions(user_id, subject)
            # Generate 30 questions on the spot using Gemini API, excluding duplicates and focusing on chapters
            questions = question_agent.generate_questions(
                subject, api_key, exclude_questions=previous_questions, chapters=chapters if chapters else None
            )
            # Populate questions to db
            db_helper.insert_test_questions(test_id, questions)
            return redirect(url_for('take_test', test_id=test_id))
        except Exception as e:
            # Cleanup failed test session
            db_helper.delete_test_session(test_id)
            flash(f"Test Generation Failed: {str(e)}. Please check your API key / connection and try again.", "error")
            return redirect(url_for('setup_test'))
        
    return render_template('setup_test.html', api_configured=api_configured)

@app.route('/test/<int:test_id>')
def take_test(test_id):
    if 'user_id' not in session:
        return redirect(url_for('index'))
        
    test = db_helper.get_test_session(test_id)
    if not test or test['user_id'] != session['user_id']:
        flash('Test session not found.', 'error')
        return redirect(url_for('dashboard'))
        
    if test['status'] == 'completed':
        flash('This test has already been completed.', 'info')
        return redirect(url_for('test_results', test_id=test_id))
        
    questions = db_helper.get_test_questions(test_id)
    
    return render_template('test.html', test=test, questions=questions)

@app.route('/test/<int:test_id>/submit', methods=['POST'])
def submit_test(test_id):
    if 'user_id' not in session:
        return redirect(url_for('index'))
        
    test = db_helper.get_test_session(test_id)
    if not test or test['user_id'] != session['user_id']:
        flash('Test session not found.', 'error')
        return redirect(url_for('dashboard'))
        
    if test['status'] == 'completed':
        return redirect(url_for('test_results', test_id=test_id))
        
    questions = db_helper.get_test_questions(test_id)
    
    beg_correct = 0
    beg_total = 0
    int_correct = 0
    int_total = 0
    prof_correct = 0
    prof_total = 0
    total_score = 0
    
    for q in questions:
        student_ans = request.form.get(f'answer_{q["id"]}', '').strip().upper()
        is_correct = (student_ans == q['correct_option'].strip().upper())
        
        # Update question row in db
        db_helper.save_answer(q['id'], student_ans, is_correct)
        
        # Increment stage statistics
        if q['stage'] == 'beginner':
            beg_total += 1
            if is_correct: beg_correct += 1
        elif q['stage'] == 'intermediate':
            int_total += 1
            if is_correct: int_correct += 1
        elif q['stage'] == 'professional':
            prof_total += 1
            if is_correct: prof_correct += 1
            
        if is_correct:
            total_score += 1

    # Update overall test status in DB
    db_helper.update_test_score(test_id, total_score, len(questions))
    
    # Generate Matplotlib chart
    chart_path = chart_generator.generate_performance_chart(
        test_id, beg_correct, beg_total, int_correct, int_total, prof_correct, prof_total
    )
    
    # AI/Rule-based Feedback Generation
    api_key = get_api_key()
    try:
        feedback, tips = analysis_agent.generate_ai_analysis(
            test['subject'], session['user_name'], 
            beg_correct, beg_total, int_correct, int_total, prof_correct, prof_total, 
            api_key
        )
    except Exception as e:
        print(f"Feedback generation failed: {e}. Falling back to rule-based analysis.")
        feedback, tips = analysis_agent.generate_ai_analysis(
            test['subject'], session['user_name'], 
            beg_correct, beg_total, int_correct, int_total, prof_correct, prof_total, 
            None
        )
    
    # Serialize tips list to JSON
    tips_json = json.dumps(tips)
    
    # Save analysis in database
    db_helper.save_test_analysis(
        test_id, beg_correct, beg_total, int_correct, int_total, prof_correct, prof_total,
        chart_path, feedback, tips_json
    )
    
    session.pop('global_insight', None)
    flash('Assessment submitted successfully! Review your analysis below.', 'success')
    return redirect(url_for('test_results', test_id=test_id))

@app.route('/test/<int:test_id>/results')
def test_results(test_id):
    if 'user_id' not in session:
        return redirect(url_for('index'))
        
    test_row = db_helper.get_test_session(test_id)
    if not test_row or test_row['user_id'] != session['user_id']:
        flash('Test session not found.', 'error')
        return redirect(url_for('dashboard'))
        
    if test_row['status'] != 'completed':
        return redirect(url_for('take_test', test_id=test_id))
        
    user_row = db_helper.get_user_by_id(session['user_id'])
    user = dict(user_row) if user_row else None
    test = dict(test_row)
    
    questions = [dict(q) for q in db_helper.get_test_questions(test_id)]
    analysis_row = db_helper.get_test_analysis(test_id)
    if analysis_row:
        analysis = dict(analysis_row)
    else:
        # Safe default dictionary to prevent Jinja2 UndefinedError / None crashes
        analysis = {
            'beginner_correct': 0,
            'beginner_total': 0,
            'intermediate_correct': 0,
            'intermediate_total': 0,
            'professional_correct': 0,
            'professional_total': 0,
            'chart_image_path': None,
            'ai_feedback': "Detailed feedback was not generated for this assessment.",
            'improvement_tips': "[]"
        }
    
    tips = []
    if analysis.get('improvement_tips'):
        try:
            tips = json.loads(analysis['improvement_tips'])
        except Exception:
            tips = []
            
    api_key = get_api_key()
    using_api_key = bool(api_key)
            
    return render_template('results.html', test=test, user=user, questions=questions, analysis=analysis, tips=tips, using_api_key=using_api_key)

if __name__ == '__main__':
    # Serve locally on default port 5000
    app.run(host='0.0.0.0', port=5000, debug=True)
