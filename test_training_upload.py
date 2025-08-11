#!/usr/bin/env python3
"""
Test script for training upload functionality
"""
try:
    import requests
except ImportError:
    print("❌ Error: 'requests' library is not installed.")
    print("Please install it using: pip install requests")
    print("Or run: pip install -r requirements.txt")
    exit(1)

import json
import os

# Configuration
BASE_URL = "http://localhost:8000"
LOGIN_URL = f"{BASE_URL}/auth/login"
TRAINING_CREATE_URL = f"{BASE_URL}/training/create-with-file"

def test_training_upload():
    """Test the training upload functionality"""
    
    # First, we need to login to get an access token
    login_data = {
        "email": "admin@example.com",  # Replace with actual admin email
        "password": "admin123"  # Replace with actual admin password
    }
    
    try:
        # Login to get access token
        login_response = requests.post(LOGIN_URL, json=login_data)
        if login_response.status_code != 200:
            print(f"Login failed: {login_response.status_code} - {login_response.text}")
            return
        
        login_result = login_response.json()
        access_token = login_result.get("access_token")
        
        if not access_token:
            print("No access token received")
            return
        
        print(f"Successfully logged in. Access token: {access_token[:20]}...")
        
        # Prepare training data
        training_data = {
            "title": "Test Training Course",
            "department_id": 1,
            "training_type": "compliance",
            "trainer_id": 1,
            "duration_hours": 8,
            "assigned_date": "2024-12-31T00:00:00",
            "description": "This is a test training course",
            "content_type": "document"
        }
        
        # Create a test file
        test_file_path = "test_document.pdf"
        with open(test_file_path, "wb") as f:
            f.write(b"%PDF-1.4\n%Test PDF content\n")
        
        # Prepare files and data for upload
        files = {
            "file": ("test_document.pdf", open(test_file_path, "rb"), "application/pdf")
        }
        
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        # Make the request
        response = requests.post(
            TRAINING_CREATE_URL,
            data=training_data,
            files=files,
            headers=headers
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Training created successfully! Training ID: {result.get('training_id')}")
        else:
            print(f"Failed to create training: {response.status_code} - {response.text}")
        
        # Clean up test file
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
            
    except Exception as e:
        print(f"Error during test: {str(e)}")

if __name__ == "__main__":
    test_training_upload() 