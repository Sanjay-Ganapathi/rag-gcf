import functions_framework
import os
from google.cloud import storage
from flask import Flask, jsonify, request
from dotenv import load_dotenv
load_dotenv()

storage_client = storage.Client()


@functions_framework.http
def uploadfile(request):
    if request.method != 'POST':
        return 'Only POST requests are accepted', 405

    bucket_name = os.getenv('BUCKET_NAME')
    print(request.files)
    if 'file' not in request.files:
        return 'No file part in the request.', 400
    files = request.files.getlist('file')
    if not files:
        return 'No files selected for uploading.', 400
    responses = []
    for file in files:
        if file.filename == '':
            responses.append(
                {'filename': 'Unnamed', 'error': 'No file selected for uploading.'})
            continue

        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(file.filename)

        if blob.exists():
            responses.append(
                {'filename': file.filename, 'error': f'File already exists in {bucket_name}.'})
            continue

        blob.upload_from_file(file)

        responses.append({
            'filename': file.filename,
            'message': f'File {file.filename} uploaded to {bucket_name}.',
        })
    return jsonify(responses), 200
