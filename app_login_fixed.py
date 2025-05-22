
import streamlit as st
import fitz
import re
import sqlite3
from fpdf import FPDF
import tempfile
import os

# --- DATABASE SETUP ---
conn = sqlite3.connect("opp_app.db")
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS users (username TEXT, password TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS patients (name TEXT, dob TEXT, gender TEXT, height TEXT, weight TEXT, labs TEXT, notes TEXT)")
conn.commit()

# --- LOGIN SYSTEM ---
def register_user(username, password):
    c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
    conn.commit()

def login_user(username, password):
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    return c.fetchone()

# --- SESSION SETUP ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if 'username' not in st.session_state:
    st.session_state.username = ""

st.title("Optimal Protocol Planner (OPP)")

menu = ["Login", "Register"]
choice = st.sidebar.selectbox("Account", menu)

if choice == "Register":
    st.sidebar.subheader("Create New Account")
    new_user = st.sidebar.text_input("Username")
    new_pass = st.sidebar.text_input("Password", type='password')
    if st.sidebar.button("Register"):
        register_user(new_user, new_pass)
        st.success("Account created! You can now log in.")

elif choice == "Login" and not st.session_state.logged_in:
    st.sidebar.subheader("Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type='password')
    if st.sidebar.button("Login"):
        if login_user(username, password):
            st.session_state.logged_in = True
            st.session_state.username = username
            st.success(f"Welcome, {username}!")
        else:
            st.error("Incorrect username or password.")

# ---- APP CONTENT AFTER LOGIN ----
if st.session_state.logged_in:
    uploaded_file = st.file_uploader("Upload Lab Report or History (PDF)", type=["pdf"])
    name = st.text_input("Patient Name", "Kelly")
    dob = st.text_input("DOB", "07/21/1974")
    gender = st.selectbox("Gender", ["Female", "Male", "Other"])
    height = st.text_input("Height", "5'5\"")
    weight = st.text_input("Weight", "130 lbs")
    labs = {}

    def extract_labs_from_text(text):
        patterns = {
            "Glucose": r"Glucose(?:[^\d]|\s)*(\d+)",
            "Testosterone": r"Testosterone(?:[^\d]|\s)*(\d+)",
            "Estradiol": r"Estradiol(?:[^\d]|\s)*(\d+)",
            "TSH": r"TSH(?:[^\d]|\s)*(\d+\.\d+)",
            "Free T3": r"Free T3(?:[^\d]|\s)*(\d+\.\d+)",
            "Free T4": r"Free T4(?:[^\d]|\s)*(\d+\.\d+)"
        }
        results = {}
        for lab, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                results[lab] = float(match.group(1))
        return results

    if uploaded_file:
        with fitz.open(stream=uploaded_file.read(), filetype="pdf") as doc:
            text = ""
            for page in doc:
                text += page.get_text()

        st.markdown("### 🧾 Extracted Text")
        st.text_area("Raw Text", text, height=150)
        labs = extract_labs_from_text(text)
        st.markdown("### 🔬 Lab Results")
        st.write(labs)

    st.markdown("### 📝 Care Plan Recommendations")
    recommendations = [
        "Tesamorelin (3mg/ml): Reduces abdominal fat. 20 units SQ daily x6 days/week.",
        "Fat Burner Plus Blend: AOD-9604 / MOTs-C / Tesamorelin / Ipamorelin — 20 units SQ daily M-F.",
        "CJC-1295 / Ipamorelin: Promotes recovery and sleep. Inject 5 nights/week.",
        "GHK-Cu / Epithalon: Regeneration and anti-aging. Inject 20 units SQ M-F.",
        "Testosterone therapy pending lab validation."
    ]

    if labs.get("Glucose", 0) > 100:
        st.info("Elevated Glucose: Recommend Tesamorelin and MOTs-C.")
    if labs.get("Testosterone", 100) < 40:
        st.warning("Low Testosterone: Consider Testosterone Cypionate or cream.")
    if labs.get("Estradiol", 100) < 20:
        st.info("Low Estradiol: Evaluate hormone balancing.")
    if labs.get("TSH", 5) > 4.5:
        st.warning("High TSH: Possible hypothyroidism.")

    notes = st.text_area("Provider Notes")

    if st.button("💾 Save Patient Record"):
        lab_summary = str(labs)
        c.execute("INSERT INTO patients (name, dob, gender, height, weight, labs, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (name, dob, gender, height, weight, lab_summary, notes))
        conn.commit()
        st.success("Patient data saved!")

    def export_pdf():
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="Optimal Protocol Planner: AI Care Plan", ln=True, align='C')
        pdf.cell(200, 10, txt=f"Patient: {name}, DOB: {dob}, Gender: {gender}", ln=True)
        pdf.cell(200, 10, txt=f"Height: {height} | Weight: {weight}", ln=True)
        pdf.ln(10)
        for key, value in labs.items():
            pdf.cell(200, 10, txt=f"{key}: {value}", ln=True)
        pdf.ln(5)
        pdf.multi_cell(0, 10, txt="Recommendations:")
        for r in recommendations:
            pdf.multi_cell(0, 10, txt=f"- {r}")
        pdf.ln(5)
        pdf.multi_cell(0, 10, txt=f"Provider Notes: {notes}")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            pdf.output(tmp.name)
            return tmp.name

    if st.button("📄 Export Care Plan to PDF"):
        path = export_pdf()
        with open(path, "rb") as f:
            st.download_button("Download PDF", f, file_name="care_plan.pdf")

    st.markdown("### 🚚 OBP Pharmacy Rx Integration (Coming Soon)")
    st.text_input("Prescriber NPI")
    st.text_input("Clinic Name")
    st.button("Submit Rx Request to OBP")
