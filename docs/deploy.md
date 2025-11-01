# Deploying to Google Cloud Functions

This microservice is designed to run as an HTTP-triggered Cloud Function.

Prerequisites
- Google Cloud SDK installed and authenticated.
- Billing/project set up.

Deploy (example uses Python 3.11 runtime):

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

gcloud functions deploy scrape_news \
  --runtime python311 \
  --trigger-http \
  --entry-point scrape_news \
  --region europe-west1 \
  --allow-unauthenticated
```

Notes
- Ensure `requirements.txt` is present in the function root. Cloud Functions installs packages listed there.
- For local testing use the Functions Framework:
  ```bash
  pip install -r requirements.txt
  functions-framework --target=scrape_news
  ```
