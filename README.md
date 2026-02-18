# Interview Bot (Phase 1 + Phase 2 Demo)

## Scope
This repo includes only the demo flows below:
- HR login + dashboard + JD extraction + JD config save
- Candidate register/login + resume upload + evaluation + result JSON storage
- HR candidate list + candidate report view
- Resume view/download route

## Run
1. Create and activate a virtual environment (recommended).
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start the app:
   ```bash
   python app.py
   ```
4. Open:
   - `http://127.0.0.1:5000/hr/login`
   - `http://127.0.0.1:5000/login`

## Default HR Credentials
- Username: `hr`
- Password: `hr@123`
