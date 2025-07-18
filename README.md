# JSEC Express (developed for ITMGT25.03)

**JSEC Express** is a Django-based web application for managing JSEC stalls: orders, carts, checkout, vouchers, admin dashboards, and payment integration via PayMongo.

***JSEC Express is developed by Aiken Eduardo and Sharlize Yu as part of the ITMGT25.03 course this Academic Year 2025-2026, Intersession.***

## Features
- Custom user signup and login
- Stall-based menus and cart system
- Voucher support and checkout logic
- Automated receipts and transaction summaries
- Admin dashboard for stall owners
- PayMongo integration
- Blacklisting system for abusive users

---

## 🛠 Setup Instructions

Follow these steps to run the project locally:

1. Clone the repository

git clone https://github.com/DanielAikenEduardo/jsec-express.git
cd jsec-express

2. Create and activate a virtual environment

macOS/Linux
python3 -m venv env
source env/bin/activate

Windows
python -m venv env
env\Scripts\activate

3. Install dependencies
pip install -r requirements.txt

4. Run initial migrations
python manage.py migrate

5. Load seed data
python manage.py loaddata data.json

6. Start the development server
python manage.py runserver
Then open your browser and visit:
http://127.0.0.1:8000