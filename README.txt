SANTOS CONNECT LIVE CUSTOMER WEBSITE
=====================================

STACK
- Python 3
- Flask
- SQLite
- HTML5 / CSS3 / JavaScript

FEATURES
- Customer-facing travel website
- Dubai travel and visa promotion
- Services: flights, visas, hotels, tours, insurance, airport transfers
- Study-abroad destinations: UAE, China, Poland, India
- Relocation-to-Dubai section
- WhatsApp and phone contact buttons
- Customer "Stories" feature
- Stories automatically expire after 25 hours
- Image stories: maximum 2 MB (enforced server-side and in browser)
- Video stories: maximum 30 seconds (validated in browser and rechecked on form submission)
- Admin story manager with password login
- SQLite story storage

RUN LOCALLY
1. python -m venv venv
2. Windows: venv\Scripts\activate
   Linux/macOS: source venv/bin/activate
3. pip install -r requirements.txt
4. python app.py
5. Open http://127.0.0.1:5000

ADMIN
- Open /admin/login
- Default password for local demo: admin123
- BEFORE DEPLOYING: set ADMIN_PASSWORD and SECRET_KEY environment variables.

IMPORTANT FOR PRODUCTION
- Use HTTPS.
- Use a production WSGI server (e.g. Gunicorn on Linux).
- Move uploaded stories to cloud/object storage for a serious production deployment.
- Add database backups and proper admin user management.
- For strict server-side video-duration enforcement, add FFmpeg/ffprobe validation; the current build validates video duration in the customer's/admin browser.
