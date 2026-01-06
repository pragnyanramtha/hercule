"""
Azure Functions entry point for Hercule API.
Wraps the FastAPI app for Azure Functions V2 deployment.
"""
import azure.functions as func
from main import app

# Create Azure Functions app from FastAPI
# This automatically exposes all FastAPI routes as HTTP triggers
app_func = func.AsgiFunctionApp(
    app=app,
    http_auth_level=func.AuthLevel.ANONYMOUS
)
