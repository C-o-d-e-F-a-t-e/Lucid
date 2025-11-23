import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
import os
import joblib
import tkinter as tk
import nltk
from sklearn.svm import LinearSVC
from flask import Flask,request,render_template
app = Flask(__name__,template_folder='templates')
from metadata_checker import *

data = pd.read_csv('fake_or_real_news.csv')

X = data['text']   
data['label'] = data['label'].map({'FAKE': 0, 'REAL': 1}) 
y = data['label']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
model_path = 'linear_svc_model.joblib'
vectorizer_path = 'tfidf_vectorizer.joblib'

if os.path.exists(model_path) and os.path.exists(vectorizer_path):
    print("Loading model and vectorizer...")
    clf = joblib.load(model_path)
    vectorizer = joblib.load(vectorizer_path)
    
else:
    print("Training model and saving it...")
    vectorizer = TfidfVectorizer(stop_words='english', max_df=0.7)
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)

    clf = LinearSVC()
    clf.fit(X_train_vec, y_train)

    # Save model and vectorizer
    joblib.dump(clf, model_path)
    joblib.dump(vectorizer, vectorizer_path)

@app.route('/text.html', methods=['GET','POST'])
def home1():
    if request.method == 'GET':
        return render_template('text.html')

    # 1️⃣ FIRST HANDLE CSV UPLOAD
    uploaded_csv = request.files.get("upload")
    if uploaded_csv and uploaded_csv.filename != "":
        ext = uploaded_csv.filename.rsplit('.', 1)[-1].lower()
        if ext != "csv":
            return render_template("text.html", result="Only CSV files are allowed.")

        # Save CSV
        os.makedirs("user_datasets", exist_ok=True)
        filepath = f"user_datasets/{uploaded_csv.filename}"
        uploaded_csv.save(filepath)

        # Try to load and retrain
        try:
            user_data = pd.read_csv(filepath)

            if "text" not in user_data.columns or "label" not in user_data.columns:
                return render_template("text.html",
                    result="CSV must contain 'text' and 'label' columns.")

            # Map labels if needed
            if user_data["label"].dtype != int:
                user_data["label"] = user_data["label"].map({"FAKE": 0, "REAL": 1})

            X = user_data["text"]
            y = user_data["label"]

            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42)

            # Retrain vectorizer + model
            vectorizer = TfidfVectorizer(stop_words="english", max_df=0.7)
            X_train_vec = vectorizer.fit_transform(X_train)

            clf = LinearSVC()
            clf.fit(X_train_vec, y_train)

            # Save new model
            joblib.dump(clf, "linear_svc_model.joblib")
            joblib.dump(vectorizer, "tfidf_vectorizer.joblib")

            return render_template(
                "text.html",
                result=f"Dataset uploaded successfully! New model trained on {len(user_data)} samples."
            )

        except Exception as e:
            return render_template("text.html", result=f"Error: {e}")

    # 2️⃣ OTHERWISE HANDLE NORMAL TEXT INPUT
    purl = request.form.get("textInput")
    if purl:
        return render_template('text.html', result=fake_text(purl))

    return render_template("text.html", result="Please enter text or upload a dataset.")

@app.route('/image.html', methods=['GET','POST'])
def home2():
    if request.method == "GET":
        return render_template("image.html")
    
    if request.method == 'POST':
        uploaded_file = request.files.get('uploadimage') or request.files.get('upload')
        
        if uploaded_file and uploaded_file.filename != '':
            ext = uploaded_file.filename.rsplit('.', 1)[-1].lower()
            if ext not in ('png', 'jpg', 'jpeg'):
                return render_template('image.html', result="Only PNG or JPG files are allowed.")
            
            os.makedirs("./uploads", exist_ok=True)   
            
            filepath = f"./uploads/{uploaded_file.filename}"  
            uploaded_file.save(filepath)                 

            return render_template('image.html', result='\n'.join(get_detailed_report(filepath)))
        
        else:
            return render_template('image.html', result="No file uploaded.")

@app.route('/',methods=['GET'])
def home():
    return render_template("news1.html")
def fake_text(purl):
    
    if not purl:
        return "Please enter some news text to check."
    
    vect = vectorizer.transform([purl])
    prediction = clf.predict(vect)
    
    result = "REAL" if prediction[0] == 1 else "FAKE"
    
    text=f"The news is likely : {result} "
    return text

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0',port=5000)
