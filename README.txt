
Flask project layout (IMPORTANT: 'static' is a top-level folder, not inside 'templates'):

tawrid_kb_flask_verified/
├─ app.py
├─ config.py
├─ requirements.txt
├─ .env.example
├─ uploads/
│  ├─ pdf/
│  │   ├─ 01_supplier/
│  │   ├─ 02_buyer/
│  │   └─ 03_funder/
│  └─ videos/
│      ├─ 01_supplier/
│      ├─ 02_buyer/
│      └─ 03_funder/
├─ static/                 <-- CSS/JS/IMAGES live here
│  ├─ css/
│  │   ├─ normalize.css
│  │   ├─ skeleton.css
│  │   ├─ custom.css
│  │   └─ (plus any others from your original project)
│  ├─ js/
│  │   ├─ jquery.min.js
│  │   └─ site.js
│  └─ images/
│      └─ default-logo.png (if present in your original project)
└─ templates/
   ├─ base.html
   ├─ index.html
   └─ view.html

Run:
  python -m venv .venv
  source .venv/bin/activate   (Windows: .venv\Scripts\activate)
  pip install -r requirements.txt
  cp .env.example .env
  python app.py
