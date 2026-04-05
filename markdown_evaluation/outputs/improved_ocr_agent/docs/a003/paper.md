# Assignment 2: Classification - Customer Churn Prediction Using Classification Objective: In this assignment, you will build a classification model to predict customer churn. Churn prediction is essential for businesses to identify customers at risk of leaving and take action to retain them. Dataset: Kaggle: Telco Customer Churn Dataset

<!-- document_mode: simple_text -->

<!-- page 1 mode: simple_text -->

• Description: This dataset contains customer data from a telecommunications company, including information about services, account status, and whether the customer churned. It’s one of the most popular datasets for customer churn prediction and works well for classification problems.

• Features: Customer tenure, monthly charges, contract type, payment method, and churn label (Yes/No).

Kaggle: Customer Personality Analysis

• Link: Customer Personality Analysis on Kaggle

• Description: This dataset helps classify customers based on various demographics, purchase behavior, and marketing campaign data. It’s a good fit for a classification task where you can predict which customers will respond to marketing campaigns or predict churn based on customer behavior.

• Features: Includes customer attributes like income, education level, marital status, number of purchases, and complaint counts.

Instructions:

## Data Preprocessing

o Load the dataset using Pandas. o Convert any categorical variables (e.g., ContractType) into numerical values using

one-hot encoding.

o Handle any missing data and scale the features if necessary. o Split the data into training and test sets (e.g., 80% training, 20% testing).

## Train a Classification Model

o Choose a classification algorithm (e.g., Logistic Regression, Decision Tree, or

Random Forest).

o Train the model to predict whether a customer will churn (Churn column).

## Model Evaluation

o Evaluate the model using metrics such as accuracy, precision, recall, F1-score,

and the confusion matrix.

o Plot a ROC curve and calculate the AUC score to assess model performance.

## Analysis

o Write a short analysis explaining how well your model performed. Which features

were most important in predicting churn? Did the model produce any false positives or false negatives?

Submission:

•
Jupyter notebook (.ipynb file) with your code, comments, and explanations.

• A short report (1-2 pages) discussing model performance, feature importance, and any recommendations for improving customer retention.

---
