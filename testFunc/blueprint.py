import azure.functions as func
import logging
import json
import requests
from azure.storage.blob import BlobServiceClient
import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

connection_string = os.environ["AZURE_STORAGE_CONNECTION_STRING"]

bp = func.Blueprint()

@bp.function_name(name="BlobTriggerFunction")
@bp.blob_trigger(arg_name="myblob", path="newfuncstorage/{name}", connection="funcstoreoam_STORAGE")
def blob_trigger_v2(myblob: func.InputStream):
    logging.info(f"Python blob trigger function processed blob\n"
                 f"Name: {myblob.name}\n"
                 f"Blob Size: {myblob.length} bytes")
   
    blob_url = f"https://funcstoreoam.blob.core.windows.net/{myblob.name}"
    logging.info(f"Blob URL: {blob_url}")
   
    json_data = {
        "content_tags": "stick figure",
        "blob_url": blob_url
    }
   
    # send JSON data to HTTP endpoint w/ error checking
    http_endpoint = "http://localhost:7071/api/overlay"
    try:
        response = requests.post(http_endpoint, json=json_data)
        response.raise_for_status()  
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to send JSON data. Error: {e}")
        return

    if response.status_code == 200:
        logging.info("Successfully sent JSON data to HTTP endpoint.")
    else:
        logging.error(f"Failed to send JSON data. Status code: {response.status_code}")

@bp.function_name(name="OverlayFunction")
@bp.route(route="overlay", methods=["POST"])
def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('HTTP trigger function processed a request.')
   
    try:
        req_body = req.get_json()
        logging.info(f"Request body: {req_body}")
    except ValueError:
        return func.HttpResponse("Invalid JSON format", status_code=400)
   
    content_tags = req_body.get("content_tags")
    blob_url = req_body.get("blob_url")
   
    if not content_tags or not blob_url:
        return func.HttpResponse("Missing required fields", status_code=400)
   
    # get the blob path from the URL
    blob_path = blob_url.replace(f"https://funcstoreoam.blob.core.windows.net/newfuncstorage/", "")
    logging.info(f"Blob path: {blob_path}")
   
    original_container_name = "newfuncstorage"
    modified_container_name = "editfilestorage"

    # Initialize BlobServiceClient
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
   
    try:
        # read the original text file from the blob container
        blob_client = blob_service_client.get_blob_client(container=original_container_name, blob=blob_path)
        logging.info(f"Attempting to download blob: {blob_path} from container: {original_container_name}")
       
        original_content = blob_client.download_blob().readall().decode('utf-8')
        logging.info(f"Original content: {original_content}")
       
        # add JSON contents to the original text file content
        modified_content = original_content + "\n" + json.dumps(req_body)
       
        # create the modified blob path
        modified_blob_path = blob_path.replace(".txt", "_modified.txt")
       
        # write the modified file to the edited file storage container
        modified_blob_client = blob_service_client.get_blob_client(container=modified_container_name, blob=modified_blob_path)
        modified_blob_client.upload_blob(modified_content, overwrite=True)
       
        logging.info(f"Modified blob URL: https://funcstoreoam.blob.core.windows.net/{modified_container_name}/{modified_blob_path}")
       
        return func.HttpResponse(f"Successfully wrote JSON data to the blob. New blob URL: https://funcstoreoam.blob.core.windows.net/{modified_container_name}/{modified_blob_path}", status_code=200)
    except Exception as e:
        logging.error(f"Error processing data: {e}")
        return func.HttpResponse(
            "Failed to process file from the provided blob URL.",
            status_code=500
        )
