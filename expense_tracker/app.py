import streamlit as st
import pandas as pd
import plotly.express as px
import firebase_admin
from firebase_admin import credentials, firestore
import pytesseract
from PIL import Image
import speech_recognition as sr
import openai
st.markdown("""
<style>

.main {
    background-color: #f5f7fb;
}

.block-container {
    padding-top: 1rem;
    padding-bottom: 1rem;
}

.metric-card {
    background: white;
    padding: 15px;
    border-radius: 15px;
    box-shadow: 0px 3px 8px rgba(0,0,0,0.1);
}

button[kind="primary"] {
    background-color: #3b82f6;
    border-radius: 10px;
}

</style>
""", unsafe_allow_html=True)
# ---------------------------
# Page Setup
# ---------------------------
st.set_page_config(
    page_title="AI Expense Tracker",
    page_icon="💰",
    layout="wide"
)

st.title("💰 AI Smart Expense Tracker")

# ---------------------------
# Firebase Cloud Database
# ---------------------------
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase_key.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ---------------------------
# AI Auto Category
# ---------------------------
def auto_category(note):

    note = note.lower()

    if "food" in note or "restaurant" in note or "lunch" in note:
        return "Food"

    elif "uber" in note or "bus" in note or "travel" in note:
        return "Travel"

    elif "shopping" in note or "amazon" in note:
        return "Shopping"

    elif "bill" in note or "electricity" in note:
        return "Bills"

    else:
        return "Other"

# ---------------------------
# Add Expense
# ---------------------------
st.sidebar.header("Add Expense")

date = st.sidebar.date_input("Date")

note = st.sidebar.text_input("Note")

category = auto_category(note)

st.sidebar.write("AI Category:", category)

amount = st.sidebar.number_input("Amount")

if st.sidebar.button("Add Expense"):

    db.collection("expenses").add({
        "date":str(date),
        "category":category,
        "amount":amount,
        "note":note
    })

    st.sidebar.success("Saved to cloud")

# ---------------------------
# Load Data
# ---------------------------
docs = db.collection("expenses").stream()

data=[]
doc_ids=[]

for d in docs:
    data.append(d.to_dict())
    doc_ids.append(d.id)

df=pd.DataFrame(data)

# ---------------------------
# Smart Dashboard
# ---------------------------
st.subheader("📊 Smart Dashboard")

if not df.empty:

    total=df["amount"].sum()
    avg=df["amount"].mean()
    highest=df["amount"].max()

    c1,c2,c3=st.columns(3)

    with c1:
        st.metric("Total Spent", total)

    with c2:
        st.metric("Average", round(avg,2))

    with c3:
        st.metric("Highest", highest)
# ---------------------------
# Search
# ---------------------------
st.subheader("🔎 Search Expenses")

search = st.text_input("Search note or category")

if search:
    df = df[df.apply(
        lambda row: search.lower() in str(row).lower(),
        axis=1
    )]

# ---------------------------
# Filter
# ---------------------------
st.subheader("📅 Filter")

col1,col2 = st.columns(2)

with col1:
    category_filter = st.selectbox(
        "Filter by Category",
        ["All","Food","Travel","Shopping","Bills","Other"]
    )

with col2:
    date_filter = st.date_input("Filter by Date",None)

if category_filter != "All":
    df = df[df["category"] == category_filter]

if date_filter:
    df = df[df["date"] == str(date_filter)]

# ---------------------------
# Expense Table
# ---------------------------
st.subheader("📋 Expense List")

if not df.empty:

    for i,row in df.iterrows():

        c1,c2,c3,c4,c5,c6=st.columns(6)

        c1.write(row["date"])
        c2.write(row["category"])
        c3.write(row["amount"])
        c4.write(row["note"])

        if c5.button("Edit",key=f"edit{i}"):

            new_amount=st.number_input(
                "New Amount",
                value=row["amount"],
                key=f"amount{i}"
            )

            if st.button("Save",key=f"save{i}"):

                db.collection("expenses").document(doc_ids[i]).update({
                    "amount":new_amount
                })

                st.success("Updated")
                st.rerun()

        if c6.button("Delete",key=f"del{i}"):

            db.collection("expenses").document(doc_ids[i]).delete()

            st.success("Deleted")
            st.rerun()

# ---------------------------
# Category Chart
# ---------------------------
if not df.empty:

    chart=df.groupby("category")["amount"].sum().reset_index()

    fig=px.bar(
        chart,
        x="category",
        y="amount",
        title="Category Spending"
    )

    st.plotly_chart(fig)

# ---------------------------
# Monthly Chart
# ---------------------------
if not df.empty:

    df["date"]=pd.to_datetime(df["date"])

    monthly=df.groupby(
        df["date"].dt.month
    )["amount"].sum()

    st.subheader("📈 Monthly Spending")

    st.line_chart(monthly)

# ---------------------------
# Bill Scanner
# ---------------------------
st.subheader("📷 Scan Bill")

file=st.file_uploader("Upload receipt image")

if file:

    img=Image.open(file)

    text=pytesseract.image_to_string(img)

    st.image(img)

    st.write("Extracted Text:")

    st.write(text)

# ---------------------------
# Voice Expense Entry
# ---------------------------
st.subheader("🎤 Voice Expense")

if st.button("Start Voice Input"):

    r = sr.Recognizer()

    with sr.Microphone() as source:

        st.write("Speak now...")

        audio = r.listen(source)

    try:

        text = r.recognize_google(audio)

        st.write("You said:", text)

    except:

        st.write("Voice not clear")

# ---------------------------
# AI Financial Advisor
# ---------------------------
st.subheader("📊 AI Spending Advice")

if st.button("Analyze Spending"):

    if not df.empty:

        openai.api_key="YOUR_API_KEY"

        prompt=f"Analyze this expense data and give financial advice: {df}"

        response=openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":prompt}]
        )

        st.write(response.choices[0].message.content)