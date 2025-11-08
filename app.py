from flask import Flask, render_template, request, redirect, session, url_for, flash
import pandas as pd
import sqlite3
import hashlib
import pickle
import os
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression

app = Flask(__name__)
app.secret_key = "supersecretkey"
DB_PATH = "students.db"

# --------------------- Database Setup ---------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL
                )""")
    c.execute("""CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    city TEXT,
                    result INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )""")
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --------------------- Model Training ---------------------
MODEL_PATH = "models/lung_model.pkl"

if not os.path.exists(MODEL_PATH):
    df = pd.read_csv("survey_lung_cancer.csv")
    df.columns = df.columns.str.strip()

    # Encode correctly
    df["GENDER"] = df["GENDER"].map({'M': 0, 'F': 1})
    df["LUNG_CANCER"] = df["LUNG_CANCER"].map({'YES': 2, 'NO': 1})

    X = df.drop(columns=["LUNG_CANCER"])
    y = df["LUNG_CANCER"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, stratify=y, test_size=0.2, random_state=42)

    model = LogisticRegression(max_iter=500)
    model.fit(X_train, y_train)

    os.makedirs("models", exist_ok=True)
    pickle.dump(model, open(MODEL_PATH, "wb"))
else:
    model = pickle.load(open(MODEL_PATH, "rb"))

# --------------------- Doctor Database ---------------------
DOCTORS = {
    "delhi": [
        "Dr Kamran Ali – Max Super Speciality Hospital Saket, New Delhi – +91 63096 32220",
        "Dr J C Suri – JCS Lung & Sleep Centre, Preet Vihar Delhi – +91 98101 66071",
        "AIIMS Oncology Dept – 011-26588500"
    ],
    "new delhi": [
        "Dr Kamran Ali – Max Super Speciality Hospital Saket – +91 63096 32220",
        "AIIMS Oncology OPD – 011-26588500"
    ],
    "mumbai": [
        "Tata Memorial Hospital – +91 22 2417 7000 – Parel, Mumbai",
        "Dr Bhavna Parikh – +91 98210 62066 – Vile Parle, Mumbai",
        "Dr Sulaiman Ladhani – Kokilaben Dhirubhai Ambani Hospital – Andheri West"
    ],
    "bangalore": [
        "Dr K. Rao – Narayana Health City – 1800 309 0309 – Bommasandra",
        "Kidwai Memorial Institute of Oncology – 080-26094000"
    ],
    "chennai": [
        "Dr L. Venkat – Apollo Main Hospital – 044-2829 3333 – Greams Road",
        "Adyar Cancer Institute – 044-2235 1181"
    ],
    "hyderabad": [
        "Basavatarakam Indo American Cancer Hospital – 040-23551235 – Banjara Hills",
        "Yashoda Cancer Institute – 040-4567 4567"
    ],
    "kolkata": [
        "Tata Medical Center – 033-6605 7000 – New Town",
        "Chittaranjan National Cancer Institute – 033-2476 5101"
    ],
    "ahmedabad": [
        "Gujarat Cancer & Research Institute – 079-2268 8000 – Civil Hospital Campus"
    ],
    "lucknow": [
        "Dr Ram Manohar Lohia Institute of Medical Sciences – 0522-491 8504"
    ],
    "jaipur": [
        "Bhagwan Mahaveer Cancer Hospital & Research Centre – 0141-2700107"
    ],
    "patna": [
        "Mahavir Cancer Sansthan – 0612-2250127 – Phulwarisharif"
    ],
    "bhubaneswar": [
        "AIIMS Bhubaneswar Oncology Dept – 0674-2476789"
    ],
    "kochi": [
        "Amrita Institute of Medical Sciences – 0484-2851234"
    ],
    "thiruvananthapuram": [
        "Regional Cancer Centre (RCC) – 0471-2522222"
    ],
    "guwahati": [
        "Dr B. Barooah Cancer Institute – 0361-2472366"
    ],
    "indore": [
        "CHL Hospitals Oncology Dept – 0731-4774000"
    ],
    "bhopal": [
        "Bhopal Memorial Hospital & Research Centre – 0755-2742212"
    ],
    "amritsar": [
        "Sri Guru Ram Das Institute of Medical Sciences – 0183-2870200"
    ],
    "goa": [
        "Goa Medical College (Oncology Unit) – 0832-245 8700"
    ],
    "puducherry": [
        "JIPMER Regional Cancer Centre – 0413-229 6000"
    ],
    "jammu and kashmir": [
        "Sher-i-Kashmir Institute of Medical Sciences – 0194-240 1013"
    ],
    "chandigarh": [
        "Postgraduate Institute of Medical Education & Research (PGIMER) – 0172-2747585"
    ]
}

# --------------------- Routes ---------------------
@app.route('/')
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect('/home')
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    uname = request.form['username']
    pwd = request.form['password']
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, password_hash FROM users WHERE username=?", (uname,))
    user = c.fetchone()
    conn.close()
    if user and hash_password(pwd) == user[1]:
        session['user_id'] = user[0]
        session['username'] = uname
        flash("Login successful!", "success")
        return redirect('/home')
    else:
        flash("Invalid username or password.", "danger")
        return redirect('/login')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')
    uname = request.form['username']
    pwd = request.form['password']
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (uname, hash_password(pwd)))
        conn.commit()
        flash("Account created successfully! Please log in.", "success")
        return redirect('/login')
    except sqlite3.IntegrityError:
        flash("Username already exists.", "danger")
        return redirect('/signup')
    finally:
        conn.close()

@app.route('/home')
def home():
    if 'user_id' not in session:
        return redirect('/')
    return render_template('home.html', username=session['username'])

@app.route('/predict', methods=['GET', 'POST'])
def predict():
    if 'user_id' not in session:
        return redirect('/')

    if request.method == 'POST':
        try:
            features = [
                int(request.form['GENDER']),
                int(request.form['AGE']),
                int(request.form['SMOKING']),
                int(request.form['YELLOW_FINGERS']),
                int(request.form['ANXIETY']),
                int(request.form['PEER_PRESSURE']),
                int(request.form['CHRONIC_DISEASE']),
                int(request.form['FATIGUE']),
                int(request.form['ALLERGY']),
                int(request.form['WHEEZING']),
                int(request.form['ALCOHOL_CONSUMING']),
                int(request.form['COUGHING']),
                int(request.form['SHORTNESS_OF_BREATH']),
                int(request.form['SWALLOWING_DIFFICULTY']),
                int(request.form['CHEST_PAIN'])
            ]
        except ValueError:
            flash("Please fill all fields correctly!", "danger")
            return redirect('/predict')

        city = request.form['city']
        input_df = pd.DataFrame([features], columns=[
            'GENDER','AGE','SMOKING','YELLOW_FINGERS','ANXIETY','PEER_PRESSURE',
            'CHRONIC_DISEASE','FATIGUE','ALLERGY','WHEEZING','ALCOHOL_CONSUMING',
            'COUGHING','SHORTNESS_OF_BREATH','SWALLOWING_DIFFICULTY','CHEST_PAIN'
        ])

        pred = model.predict(input_df)[0]

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO predictions (user_id, city, result) VALUES (?, ?, ?)",
                  (session['user_id'], city, int(pred)))
        conn.commit()
        conn.close()

        doctors = DOCTORS.get(city.lower(), [])
        return render_template('predict.html', prediction=pred, doctors=doctors, city=city)

    return render_template('predict.html')

@app.route('/history')
def history():
    if 'user_id' not in session:
        return redirect('/')
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM predictions WHERE user_id = ?", conn, params=(session['user_id'],))
    conn.close()
    return render_template('history.html', data=df)

@app.route('/leaving')
def leaving():
    if 'user_id' not in session:
        return redirect('/')
    return render_template('leaving.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect('/')

# ✅ Add this route BELOW logout and ABOVE the main entry point
import pandas as pd
from flask import jsonify

@app.route("/api/lung-data")
def lung_data():
    df = pd.read_csv("static/lung_cancer_data.csv")
    years = sorted(df['Year'].unique().tolist())
    states = df['State'].unique().tolist()

    values = {}
    for y in years:
        subset = df[df['Year'] == y]['Cases'].tolist()
        values[str(y)] = subset

    return jsonify({"years": years, "states": states, "values": values})

# 🧠 Keep this at the very end
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
