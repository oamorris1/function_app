import azure.functions as func
import logging
import json
import requests
from blueprint import bp


app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

app.register_blueprint(bp)
    
    
