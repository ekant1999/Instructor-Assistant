# a006

<!-- document_mode: hybrid_paper -->

<!-- page 1 mode: hybrid_paper -->

This sample write-up demonstrates a Lambda function invoked by API Gateway to perform CRUD operations against a DynamoDB table. The report intentionally mirrors a classroom submission format and uses entirely dummy request/response data.

## CMPE 281 – Assignment: Serverless CRUD API with

## DynamoDB

Name: Priya Shah | Student ID: 020176341

Generated sample submission with dummy data, tables, and figures for PDF extraction evaluation.

2. Lambda Handler
import json import boto3 dynamodb = boto3.resource('dynamodb') student_table = dynamodb.Table('StudentRecords') def lambda_handler(event, context): method = event['httpMethod']

![Figure 1 on Page 1](a006_assets/figures/a006_page_1_fig_1.png)

---

<!-- page 2 mode: hybrid_paper -->

The remaining PUT and DELETE branches follow the same event shape, updating or deleting the record after a key lookup.

![Figure 1 on Page 2](a006_assets/figures/a006_page_2_fig_1.png)

---

<!-- page 3 mode: ocr -->

<!-- OCR page 3 -->

Figure 3. Sample GET request retrieving the stored record.

---

<!-- page 4 mode: ocr -->

<!-- OCR page 4 -->

Figure 4. PUT request used to update the course field.

Figure 5. DELETE request for removing the same record.

---

<!-- page 5 mode: hybrid_paper -->

## 5. Edge Cases, Challenges, and Learnings

Operation Endpoint Input Expected Result Observed Status
POST /students new JSON record insert new item 200 OK
GET /students?student_id=42 existing key return matching item 200 OK

![Figure 1 on Page 5](a006_assets/figures/a006_page_5_fig_1.png)

---

<!-- page 6 mode: hybrid_paper -->

• Serverless APIs are convenient for coursework because they eliminate persistent server setup while still exposing realistic cloud integration patterns.

• DynamoDB favors access patterns around the partition key, so request design should align with the table schema from the start.

• Returning clear status codes for failure cases improves debugging and makes API behavior easier to validate in a report.

---
