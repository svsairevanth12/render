# AI-Powered Form Builder

A dynamic form builder application with AI-powered form generation, speech-to-text capabilities, and modern UI.

## Features

- Create custom forms with various field types
- AI-powered form generation using Google's Gemini API
- Speech-to-text input for easy form creation
- Real-time form preview
- Form response collection and management
- Export responses to CSV
- QR code generation for form sharing
- Responsive design with modern UI
- User authentication and form management

## Tech Stack

- Backend: Flask (Python)
- Database: Supabase (PostgreSQL)
- AI: Google Gemini API
- Frontend: Bootstrap 5, JavaScript
- Authentication: Supabase Auth
- Additional: QR Code generation, CSV export

## Local Development Setup

1. Clone the repository:
```bash
git clone <your-repo-url>
cd <repo-name>
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory with the following variables:
```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
GOOGLE_API_KEY=your_google_api_key
FLASK_SECRET_KEY=your_secure_random_key
```

5. Set up the database:
   - Create a Supabase project
   - Run `setup.sql` in Supabase SQL editor
   - Run `create_tables.sql` in Supabase SQL editor

6. Run the application:
```bash
flask run
```

## Deployment on Render

1. Fork this repository

2. Create a new Web Service on Render:
   - Connect your GitHub repository
   - Select Python environment
   - Set build command: `pip install -r requirements.txt`
   - Set start command: `gunicorn app:app`

3. Add environment variables in Render's dashboard:
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `GOOGLE_API_KEY`
   - `FLASK_SECRET_KEY`

4. Deploy the service

## Environment Variables

- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_KEY`: Your Supabase anonymous key
- `GOOGLE_API_KEY`: Your Google API key for Gemini
- `FLASK_SECRET_KEY`: Secret key for Flask sessions

## Database Setup

1. Create a Supabase project
2. Run the SQL scripts in this order:
   - `setup.sql`: Creates main tables
   - `create_tables.sql`: Creates additional tables and functions

## Features in Detail

### AI Form Generation
- Uses Google's Gemini API for intelligent form creation
- Generates appropriate field types based on context
- Supports complex form structures

### Speech-to-Text
- Available for all text inputs
- Real-time transcription
- Support for field labels and options
- Visual feedback during recording

### Form Management
- Create, edit, and delete forms
- Preview forms before publishing
- Share forms via link or QR code
- Collect and export responses

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 