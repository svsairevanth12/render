from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, flash
import os
import json
from datetime import datetime
import csv
from io import StringIO, BytesIO
import google.generativeai as genai
from google.api_core import retry
from typing import List, Dict, Any
import qrcode
import time
from random import uniform
from collections import deque
from threading import Lock
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Add datetime filter
@app.template_filter('datetime')
def format_datetime(value):
    if not value:
        return ''
    try:
        if isinstance(value, str):
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return value.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        print(f"Error formatting datetime: {str(e)}")
        return str(value)

# Initialize Supabase client
supabase: Client = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

# Configure Gemini API with proper error handling
try:
    genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
    
    # Configure the model with recommended settings from documentation
    generation_config = {
        "temperature": 0.7,
        "top_p": 0.8,
        "top_k": 40,
        "max_output_tokens": 2048,
        "candidate_count": 1
    }

    # Create the model - using gemini-pro for better compatibility
    model = genai.GenerativeModel('gemini-pro')
    print("Gemini model initialized successfully")
except Exception as e:
    print(f"Error initializing Gemini model: {str(e)}")
    model = None

@app.route('/')
def home():
    try:
        # Fetch forms from Supabase, ordered by updated_at
        response = supabase.table('forms').select('*').order('updated_at', desc=True).execute()
        forms = response.data
        return render_template('home.html', forms=forms)
    except Exception as e:
        print(f"Error fetching forms: {str(e)}")
        return render_template('home.html', forms=[])

@app.route('/create')
def create_form():
    return render_template('form_builder.html', form=None)

@app.route('/edit/<int:form_id>')
def edit_form(form_id):
    try:
        # Fetch form from Supabase
        response = supabase.table('forms').select('*').eq('id', form_id).single().execute()
        form = response.data
        
        if form is None:
            return "Form not found", 404
            
        return render_template('form_builder.html', form=form)
    except Exception as e:
        print(f"Error fetching form: {str(e)}")
        return "Error fetching form", 500

@app.route('/forms', methods=['POST'])
def save_form():
    try:
        data = request.json
        
        if not data.get('title'):
            return jsonify({'error': 'Form title is required'}), 400
            
        if not data.get('fields'):
            return jsonify({'error': 'At least one form field is required'}), 400
            
        # Validate that all fields have labels
        for field in data['fields']:
            if not field.get('label', '').strip():
                return jsonify({'error': 'All fields must have labels'}), 400

        current_time = datetime.now().isoformat()
        
        # Check for duplicate title
        base_title = data['title']
        title = base_title
        counter = 1
        
        while True:
            title_check = supabase.table('forms').select('id').eq('title', title)
            if 'id' in data:
                title_check = title_check.neq('id', data['id'])
            
            response = title_check.execute()
            if not response.data:
                break
                
            title = f"{base_title} ({counter})"
            counter += 1
        
        form_data = {
            'title': title,
            'description': data.get('description', ''),
            'fields': data['fields'],
            'theme': data.get('theme', 'default'),
            'updated_at': current_time
        }
        
        if 'id' in data:
            # Update existing form
            response = supabase.table('forms').update(form_data).eq('id', data['id']).execute()
            form_id = data['id']
        else:
            # Create new form
            form_data['created_at'] = current_time
            response = supabase.table('forms').insert(form_data).execute()
            form_id = response.data[0]['id']
        
        return jsonify({
            'id': form_id,
            'title': title,
            'message': 'Form saved successfully'
        })
    except Exception as e:
        print(f"Error saving form: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/forms/<int:form_id>')
def view_form(form_id):
    try:
        preview_mode = request.args.get('preview', 'false').lower() == 'true'
        
        # Fetch form from Supabase
        response = supabase.table('forms').select('*').eq('id', form_id).single().execute()
        form = response.data
        
        if form is None:
            error_msg = "Form not found"
            return (jsonify({'error': error_msg}), 404) if preview_mode else (render_template('error.html', error=error_msg), 404)
        
        return render_template('form_view.html',
            form=form,
            form_id=form['id'],
            preview_mode=preview_mode)
            
    except Exception as e:
        print(f"Error in view_form: {str(e)}")
        error_msg = "An unexpected error occurred. Please try again."
        return (jsonify({'error': error_msg}), 500) if preview_mode else (render_template('error.html', error=error_msg), 500)

@app.route('/submit-response/<form_id>', methods=['POST'])
def submit_response(form_id):
    try:
        print(f"Attempting to submit response for form {form_id}")
        print(f"Request form data: {request.form}")
        
        # Get form data from database
        form_response = supabase.table('forms').select('*').eq('id', form_id).execute()
        print(f"Form query response: {form_response}")
        
        if not form_response.data:
            print(f"Form {form_id} not found")
            return jsonify({'error': 'Form not found'}), 404
        
        form = form_response.data[0]
        print(f"Found form: {form}")
        
        # Collect response data
        response_data = {}
        for i, field in enumerate(form['fields'], 1):
            field_name = f'field_{i}'
            if field['type'] == 'checkbox':
                values = request.form.getlist(f'{field_name}[]')
                response_data[field_name] = values if values else []
            else:
                value = request.form.get(field_name)
                response_data[field_name] = value if value is not None else ''

            if field.get('required') and not response_data[field_name]:
                error_msg = f'Field "{field["label"]}" is required'
                print(f"Validation error: {error_msg}")
                return jsonify({'error': error_msg}), 400

        # Prepare response data
        current_time = datetime.utcnow().isoformat()
        response_data_to_insert = {
            'form_id': int(form_id),  # Keep as integer since we created table with bigint
            'response_data': response_data,
            'created_at': current_time
        }
        
        print(f"Attempting to save response: {response_data_to_insert}")
        
        # Try to insert the response directly
        try:
            print("Attempting to insert response...")
            result = supabase.table('form_responses').insert(response_data_to_insert).execute()
            print(f"Insert result: {result}")
            
            if not result.data:
                print("No data returned from insert")
                return jsonify({'error': 'Failed to save response'}), 500
                
            response_id = result.data[0].get('id')
            if not response_id:
                print("No response ID in result data")
                return jsonify({'error': 'Failed to get response ID'}), 500
                
            print(f"Successfully saved response with ID: {response_id}")
            return jsonify({
                'message': 'Response submitted successfully',
                'response_id': response_id
            }), 200
            
        except Exception as insert_error:
            error_msg = str(insert_error)
            print(f"Insert error: {error_msg}")
            print(f"Insert error type: {type(insert_error)}")
            if hasattr(insert_error, '__dict__'):
                print(f"Insert error details: {insert_error.__dict__}")
            
            if 'relation "form_responses" does not exist' in error_msg:
                return jsonify({'error': 'The form responses table is not set up in the database. Please run the setup SQL first.'}), 500
            elif 'violates foreign key constraint' in error_msg:
                return jsonify({'error': 'Invalid form ID'}), 400
            else:
                return jsonify({'error': f'Failed to save response: {error_msg}'}), 500
            
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        print(f"Error type: {type(e)}")
        if hasattr(e, '__dict__'):
            print(f"Error details: {e.__dict__}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

@app.route('/forms/<int:form_id>/delete', methods=['POST'])
def delete_form(form_id):
    try:
        # Delete form and its responses from Supabase
        supabase.table('form_responses').delete().eq('form_id', form_id).execute()
        supabase.table('forms').delete().eq('id', form_id).execute()
        
        return jsonify({'message': 'Form deleted successfully'})
    except Exception as e:
        print(f"Error deleting form: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/forms/<int:form_id>/export')
def export_responses(form_id):
    try:
        # Fetch form and responses from Supabase
        form_response = supabase.table('forms').select('*').eq('id', form_id).single().execute()
        form = form_response.data
        
        if not form:
            return "Form not found", 404
            
        responses_response = supabase.table('responses').select('*').eq('form_id', form_id).order('created_at', desc=True).execute()
        responses = responses_response.data
        
        # Create CSV file
        si = StringIO()
        writer = csv.writer(si)
        
        # Write headers
        headers = ['Timestamp']
        for field in form['fields']:
            headers.append(field['label'])
        writer.writerow(headers)
        
        # Write responses
        for response in responses:
            row = [response['created_at']]
            response_data = response['response_data']
            for field in form['fields']:
                row.append(response_data.get(field['id'], ''))
            writer.writerow(row)
        
        output = si.getvalue()
        si.close()
        
        return send_file(
            BytesIO(output.encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'responses_{form_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
    except Exception as e:
        print(f"Error exporting responses: {str(e)}")
        return "Error exporting responses", 500

# Rate limiter for AI generation
class RateLimiter:
    def __init__(self, max_requests=60, time_window=60):  # 60 requests per minute by default
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self.lock = Lock()
        
    def can_make_request(self):
        with self.lock:
            now = time.time()
            
            # Remove old requests
            while self.requests and self.requests[0] < now - self.time_window:
                self.requests.popleft()
            
            # Check if we can make a new request
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True
                
            return False
            
    def get_wait_time(self):
        with self.lock:
            if not self.requests:
                return 0
                
            now = time.time()
            oldest_request = self.requests[0]
            time_passed = now - oldest_request
            
            if time_passed >= self.time_window:
                return 0
                
            return self.time_window - time_passed

@retry.Retry()
def generate_with_backoff(prompt, max_retries=3, initial_delay=1):
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        if max_retries > 0:
            delay = initial_delay * (1 + uniform(-0.1, 0.1))  # Add some jitter
            time.sleep(delay)
            return generate_with_backoff(prompt, max_retries - 1, initial_delay * 2)
        else:
            raise e

@app.route('/generate-form', methods=['POST'])
def generate_form():
    try:
        data = request.json
        description = data.get('description', '')
        
        if not description:
            return jsonify({'error': 'Description is required'}), 400
            
        # Generate form structure using AI
        prompt = f"""Create a form structure based on this description: {description}
        
        Return ONLY a JSON array of form fields, with each field having these properties:
        - id: string (unique identifier like 'field_1', 'field_2', etc.)
        - label: string (display text)
        - type: string (one of: text, number, email, tel, textarea, select, radio, checkbox)
        - required: boolean
        - options: array of strings (only for select, radio, checkbox types)

        Example response format:
        [
            {{"id": "field_1", "label": "Full Name", "type": "text", "required": true}},
            {{"id": "field_2", "label": "Email Address", "type": "email", "required": true}},
            {{"id": "field_3", "label": "Options", "type": "select", "required": false, "options": ["Option 1", "Option 2"]}}
        ]

        Important:
        1. Return ONLY the JSON array, no other text
        2. Make sure all fields have unique IDs
        3. Include options array only for select, radio, and checkbox types
        4. Keep the response focused and relevant to: {description}"""
        
        response = generate_with_backoff(prompt)
        
        try:
            # Clean the response to ensure it's valid JSON
            response_text = response.strip()
            # Remove any markdown code block indicators if present
            response_text = response_text.replace('```json', '').replace('```', '').strip()
            
            # Parse the JSON
            fields = json.loads(response_text)
            
            # Validate the response structure
            if not isinstance(fields, list):
                raise ValueError("Response must be a JSON array")
            
            # Validate each field
            for field in fields:
                required_keys = {'id', 'label', 'type', 'required'}
                if not all(key in field for key in required_keys):
                    raise ValueError(f"Field missing required keys: {required_keys}")
                
                # Ensure options are present for certain field types
                if field['type'] in {'select', 'radio', 'checkbox'}:
                    if 'options' not in field or not isinstance(field['options'], list):
                        field['options'] = ['Option 1', 'Option 2', 'Option 3']
                
                # Ensure proper boolean value for required
                field['required'] = bool(field['required'])
                
                # Ensure unique ID
                if not field['id']:
                    field['id'] = f"field_{fields.index(field) + 1}"
            
            return jsonify({'fields': fields})
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {str(e)}\nResponse was: {response_text}")
            return jsonify({'error': 'Invalid AI response format'}), 500
        except ValueError as e:
            print(f"Validation error: {str(e)}\nResponse was: {response_text}")
            return jsonify({'error': str(e)}), 500
            
    except Exception as e:
        print(f"Error generating form: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/forms/<int:form_id>/share')
def share_form(form_id):
    try:
        # Get form details from Supabase
        response = supabase.table('forms').select('title').eq('id', form_id).single().execute()
        form = response.data
        
        if not form:
            return "Form not found", 404
            
        share_url = request.host_url + f'forms/{form_id}'
        return render_template('share.html', form=form, share_url=share_url)
    except Exception as e:
        print(f"Error sharing form: {str(e)}")
        return "Error sharing form", 500

@app.route('/forms/<int:form_id>/qr')
def generate_qr(form_id):
    try:
        share_url = request.host_url + f'forms/{form_id}'
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(share_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save to BytesIO
        img_io = BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        
        return send_file(img_io, mimetype='image/png')
    except Exception as e:
        print(f"Error generating QR code: {str(e)}")
        return "Error generating QR code", 500

@app.route('/forms/<int:form_id>/responses')
def view_responses(form_id):
    try:
        # Get form data
        form = supabase.table('forms').select('*').eq('id', form_id).execute()
        if not form.data:
            flash('Form not found', 'error')
            return redirect(url_for('home'))
        
        form = form.data[0]
        
        # Get responses for the form
        responses = supabase.table('form_responses').select('*').eq('form_id', form_id).order('created_at', desc=True).execute()
        
        return render_template(
            'responses.html',
            form=form,
            responses=responses.data
        )
    except Exception as e:
        print(f"Error viewing responses: {str(e)}")
        flash('Failed to load responses', 'error')
        return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)