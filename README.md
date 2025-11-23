🚀 Overview

Lucid is a web application designed to detect manipulated or AI-generated content in texts and images. It offers real-time predictions and features an innovative user-driven dataset integration system that allows continuous model improvement through community contributions.

Project Context: Developed for the UNBREAKING NEWS 2.0 Hackathon - Press & Securinets of Journalism and Cybersecurity

🎯 Problem Statement

The proliferation of fabricated and AI-generated content has created an urgent need for reliable detection mechanisms. Misinformation impacts academic, social, and political domains, making automated verification critical. Lucid addresses this challenge by offering a user-adaptive system capable of classifying content as authentic or fake.

✨ Key Features

Text Authenticity Detection: Classifies news articles as REAL or FAKE using machine learning

Image Analysis: Detects manipulated or AI-generated images

User-Driven Dataset Integration: Allows users to upload datasets to improve model accuracy

Real-time Predictions: Instant analysis with confidence scores

Adaptive Learning: Continuously improves with user contributions

Multi-domain Support: Adapts to various content domains (historical, political, medical)

🏗️ System Architecture

Lucid follows a three-tier client-server architecture:
Frontend Layer

HTML5/CSS3/JavaScript with modern blur effects and responsive design

User-friendly interface for text/image submission and dataset uploads

Real-time result display with confidence indicators

Backend Layer

Flask web server handling HTTP requests and responses

File upload handling for datasets and images

Machine Learning Layer

TF-IDF Vectorization for text feature extraction

LinearSVC Classifier for binary classification (REAL/FAKE)

Joblib persistence for model storage and loading

Retraining pipeline for user-uploaded datasets

📊 Methodology
Data Processing Pipeline

Text Preprocessing: Stopword removal, normalization, cleaning

Feature Extraction: TF-IDF vectorization with max_df=0.7

Model Training: Linear Support Vector Classifier (LinearSVC)

Inference: Real-time prediction with confidence scoring

User Dataset Integration

CSV validation and preprocessing

Incremental model retraining

Persistent model updates

Domain adaptation capabilities

Installation Steps
git clone https://github.com/C-o-d-e-F-a-t-e/Lucid.git
cd Lucid
pip install -r requirements.txt
python app.py
🎮 Usage
Text Analysis

Navigate to the text analysis section

Paste or type the news content you want to verify

Click "Analyze Text" to get instant results

View confidence score and detailed analysis

Image Analysis

Go to the image analysis section

Upload an image file (PNG, JPG, JPEG)

Receive authenticity report with key findings

View manipulation detection results

Dataset Contribution

Access the dataset upload section

Upload a CSV file with 'text' and 'label' columns

Labels must be 'REAL' or 'FAKE'

Contribute to improving the model's accuracy
