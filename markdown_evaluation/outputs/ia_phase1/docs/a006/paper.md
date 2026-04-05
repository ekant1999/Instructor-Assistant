---
title: "CMPE 281 - Assignment: Serverless CRUD API with DynamoDB"
paper_id: 120022211085
source_pdf: "/Users/siddhantraje/Documents/PersonalWork/ChatGPT Apps/NewCloneIA/Instructor-Assistant/markdown_evaluation/pdfs/Hybrid/Assignment6.pdf"
generated_at: "2026-04-05T20:58:30.500117+00:00"
num_figures: 6
num_tables: 0
num_equations: 3
---

CMPE 281 – Assignment: Serverless CRUD API with

DynamoDB

Name: Priya Shah | Student ID: 020176341

Generated sample submission with dummy data, tables, and figures for PDF extraction evaluation.

This sample write-up demonstrates a Lambda function invoked by API Gateway to perform CRUD operations against a DynamoDB table. The report intentionally mirrors a classroom submission format and uses entirely dummy request/response data.

## Services Used

•
AWS Lambda: Executes Python code without managing servers and scales automatically for intermittent
traffic.

•
Amazon DynamoDB: Stores student records in a key-value table with a string partition key named
student_id.

•
Amazon API Gateway: Exposes REST endpoints and forwards structured events to the Lambda handler.

![Figure 1](assets/figures/page_001_vec_001.png)

_Figure 1: Simplified request path from client to database._

## Lambda Handler

The remaining PUT and DELETE branches follow the same event shape, updating or deleting the record after a key lookup.

## API Test Screenshots

![Figure 2](assets/figures/page_002_img_001.png)

_Figure 2: Sample POST request used to add a new record._

![Figure 3](assets/figures/page_003_img_001.png)

_Figure 3: Sample GET request retrieving the stored record._

![Figure 4](assets/figures/page_004_img_001.png)

_Figure 4: PUT request used to update the course field._

![Figure 5](assets/figures/page_004_img_002.png)

_Figure 5: DELETE request for removing the same record._

## DynamoDB State and Functional Results

![Figure 6](assets/figures/page_005_vec_001.png)

_Figure 6: Fabricated table snapshot after the update operation._

$$
/students?student_id=42
$$
> Equation 2 JSON: `assets/equations/equation_0002.json`
> Equation 2 image: `assets/equations/equation_0002.png`

$$
\begin{aligned}
/students?student_id=42 \\
/students?student_id=100 missing key
\end{aligned}
$$
> Equation 3 JSON: `assets/equations/equation_0003.json`
> Equation 3 image: `assets/equations/equation_0003.png`

## Edge Cases, Challenges, and Learnings

Checked whether Item exists in the
lookup response before serializing
output.

GET on missing student_id
Handler returns 404 with a clear JSON
message.

DELETE on missing student_id Deletion is skipped and the client receives a user-facing error.

Added a pre-delete existence check to
avoid silent success.

Unstructured event payload
Initial testing failed because
httpMethod was missing.

Enabled proxy-style integration so the handler receives the full REST event.

• Serverless APIs are convenient for coursework because they eliminate persistent server setup while still exposing realistic cloud integration patterns.

• DynamoDB favors access patterns around the partition key, so request design should align with the table schema from the start.

•
Returning clear status codes for failure cases improves debugging and makes API behavior easier to validate
in a report.
