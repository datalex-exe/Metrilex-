import os
import threading
import base64
import requests
import db_helper

def get_emailjs_config():
    """
    Retrieve EmailJS configurations from environment variables.
    """
    return {
        'service_id': os.environ.get('EMAILJS_SERVICE_ID', '').strip(),
        'template_id': os.environ.get('EMAILJS_TEMPLATE_ID', '').strip(),
        'public_key': os.environ.get('EMAILJS_PUBLIC_KEY', '').strip(),
        'private_key': os.environ.get('EMAILJS_PRIVATE_KEY', '').strip()
    }

def get_base64_image_uri(filepath):
    """
    Read an image file and return its base64 data URI representation.
    """
    if not filepath or not os.path.exists(filepath):
        return None
    try:
        with open(filepath, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            return f"data:image/png;base64,{encoded_string}"
    except Exception as e:
        print(f"[EmailJS Service] Error converting chart to base64: {e}")
        return None

def send_results_email(user_email, user_name, subject, score, max_score, feedback, tips_list, chart_path=None):
    """
    Synchronously build the HTML template and send it via the EmailJS REST API.
    """
    config = get_emailjs_config()
    
    if not config['service_id'] or not config['template_id'] or not config['public_key']:
        print("[EmailJS Service] Warning: EmailJS configuration is incomplete. Email cannot be sent.")
        return False

    # Resolve relative URL path to absolute local filesystem path if necessary
    if chart_path:
        rel_path = chart_path.lstrip('/')
        project_dir = os.path.dirname(os.path.abspath(__file__))
        abs_chart_path = os.path.join(project_dir, rel_path)
        if not os.path.exists(abs_chart_path):
            if os.path.exists(chart_path):
                abs_chart_path = chart_path
            else:
                abs_chart_path = None
        chart_path = abs_chart_path

    # Convert chart image to base64 data URI
    chart_image_uri = get_base64_image_uri(chart_path)

    # Calculate statistics
    accuracy = round((score / max_score) * 100, 1) if max_score > 0 else 0
    
    # Formulate recommendations list
    tips_html = ""
    if tips_list:
        for idx, tip in enumerate(tips_list, 1):
            tips_html += f"""
            <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                <td style="padding: 10px; width: 30px; font-weight: bold; color: #a855f7; vertical-align: top;">{idx}</td>
                <td style="padding: 10px; color: #e2e8f0; font-size: 14px; line-height: 1.5;">{tip}</td>
            </tr>
            """
    else:
        tips_html = "<tr><td colspan='2' style='padding: 10px; color: #94a3b8; font-style: italic;'>No custom study strategies generated.</td></tr>"

    # Full styled HTML body matching dark theme
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Assessment Results - Metrilex</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #0b0f19; color: #f1f5f9;">
        <table align="center" border="0" cellpadding="0" cellspacing="0" width="600" style="border-collapse: collapse; background-color: #111827; border: 1px solid #1f2937; border-radius: 12px; margin-top: 20px; margin-bottom: 20px; overflow: hidden; box-shadow: 0 4px 25px rgba(0,0,0,0.5);">
            <!-- Header -->
            <tr>
                <td align="center" style="padding: 30px 20px; background: linear-gradient(135deg, #1e1b4b 0%, #311042 100%); border-bottom: 1px solid #1f2937;">
                    <h1 style="margin: 0; color: #f59e0b; font-size: 28px; font-weight: 800; letter-spacing: -0.5px;">⚡ Metrilex</h1>
                    <p style="margin: 5px 0 0 0; color: #94a3b8; font-size: 14px;">Adaptive Cognitive Diagnostics Report</p>
                </td>
            </tr>
            
            <!-- Body -->
            <tr>
                <td style="padding: 30px 25px;">
                    <p style="margin-top: 0; font-size: 16px; line-height: 1.6; color: #e2e8f0;">
                        Hello <strong>{user_name}</strong>,
                    </p>
                    <p style="font-size: 15px; line-height: 1.6; color: #94a3b8;">
                        Your cognitive diagnostics test is complete. Below are your dynamic performance results and personalized insights.
                    </p>
                    
                    <!-- Stats Section -->
                    <table border="0" cellpadding="0" cellspacing="0" width="100%" style="margin-top: 25px; margin-bottom: 25px;">
                        <tr>
                            <td width="48%" style="padding: 15px; background-color: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); border-radius: 8px; text-align: center;">
                                <div style="font-size: 11px; text-transform: uppercase; color: #94a3b8; font-weight: 600; margin-bottom: 5px;">Total Score</div>
                                <div style="font-size: 28px; font-weight: 800; color: #8b5cf6;">{score} <span style="font-size: 16px; color: #94a3b8; font-weight: normal;">/ {max_score}</span></div>
                            </td>
                            <td width="4%"></td>
                            <td width="48%" style="padding: 15px; background-color: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); border-radius: 8px; text-align: center;">
                                <div style="font-size: 11px; text-transform: uppercase; color: #94a3b8; font-weight: 600; margin-bottom: 5px;">Accuracy Rate</div>
                                <div style="font-size: 28px; font-weight: 800; color: #10b981;">{accuracy}%</div>
                            </td>
                        </tr>
                    </table>
                    
                    <p style="font-size: 14px; margin-bottom: 5px; color: #94a3b8;">Subject Focus:</p>
                    <div style="font-size: 16px; font-weight: bold; background-color: rgba(139,92,246,0.08); border: 1px solid rgba(139,92,246,0.2); padding: 12px; border-radius: 6px; margin-bottom: 25px; color: #c084fc;">
                        📚 {subject}
                    </div>

                    <!-- AI Insights -->
                    <h3 style="font-size: 18px; margin-top: 25px; margin-bottom: 12px; color: #38bdf8; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 5px;">🤖 AI Diagnostic Summary</h3>
                    <div style="font-size: 14px; line-height: 1.6; color: #cbd5e1; background-color: rgba(255,255,255,0.01); border: 1px solid rgba(255,255,255,0.03); padding: 15px; border-radius: 8px; white-space: pre-wrap;">{feedback}</div>

                    <!-- Recommendations -->
                    <h3 style="font-size: 18px; margin-top: 30px; margin-bottom: 12px; color: #a855f7; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 5px;">💡 Study Strategy Recommendations</h3>
                    <table border="0" cellpadding="0" cellspacing="0" width="100%">
                        {tips_html}
                    </table>
                    
                    <!-- Performance Chart -->
                    {f'''
                    <h3 style="font-size: 18px; margin-top: 30px; margin-bottom: 15px; color: #10b981; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 5px;">📊 Performance Chart</h3>
                    <div style="text-align: center; margin-top: 15px; padding: 10px; background-color: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); border-radius: 8px;">
                        <img src="{chart_image_uri}" alt="Performance Breakdown Chart" style="max-width: 100%; border-radius: 6px;" />
                    </div>
                    ''' if chart_image_uri else ''}
                </td>
            </tr>
            
            <!-- Footer -->
            <tr>
                <td style="padding: 20px; background-color: #0f172a; text-align: center; border-top: 1px solid #1f2937; font-size: 12px; color: #64748b;">
                    <div>&copy; 2026 <strong>Metrilex Testing Engine</strong>.</div>
                    <div style="margin-top: 5px;">Your digital metrics analyzer, powered by Gemini.</div>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

    # Package EmailJS payload
    payload = {
        "service_id": config['service_id'],
        "template_id": config['template_id'],
        "user_id": config['public_key'],
        "template_params": {
            "student_email": user_email,
            "subject": f"Metrilex Assessment Results: {subject}",
            "my_html": html_body
        }
    }
    
    # Add optional private key authentication for backend sending security
    if config['private_key']:
        payload["accessToken"] = config['private_key']

    headers = {
        "Content-Type": "application/json"
    }

    try:
        print(f"[EmailJS Service] Dispatched request to EmailJS API for {user_email}...")
        response = requests.post(
            "https://api.emailjs.com/api/v1.0/email/send",
            json=payload,
            headers=headers,
            timeout=15
        )
        if response.status_code == 200:
            print(f"[EmailJS Service] Success: Assessment results sent successfully to {user_email}.")
            return True
        else:
            print(f"[EmailJS Service] Error: Failed to send email. API response ({response.status_code}): {response.text}")
            return False
    except Exception as e:
        print(f"[EmailJS Service] Error: HTTP POST exception. Reason: {e}")
        return False

def send_results_email_async(user_email, user_name, subject, score, max_score, feedback, tips_list, chart_path=None):
    """
    Asynchronously send the assessment results email using a background thread.
    """
    thread = threading.Thread(
        target=send_results_email,
        args=(user_email, user_name, subject, score, max_score, feedback, tips_list, chart_path)
    )
    thread.daemon = True
    thread.start()
    return thread
