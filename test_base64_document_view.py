#!/usr/bin/env python3
"""
Test script to demonstrate document view with base64 content
"""

try:
    import requests
except ImportError:
    print("❌ Error: 'requests' library is not installed.")
    print("Please install it using: pip install requests")
    print("Or run: pip install -r requirements.txt")
    exit(1)

import json
import base64
import os

# Configuration
BASE_URL = "http://localhost:8000"
LOGIN_URL = f"{BASE_URL}/employee/login"
DOCUMENT_URL = f"{BASE_URL}/document"

def login_and_get_token():
    """Login and get authentication token"""
    login_data = {
        "username": "admin",  # Replace with your admin username
        "password": "admin123"  # Replace with your admin password
    }
    
    response = requests.post(LOGIN_URL, json=login_data)
    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        print(f"Login failed: {response.status_code} - {response.text}")
        return None

def test_document_view_with_base64(token, document_id=1):
    """Test document view endpoint that returns base64 content"""
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"\n🔍 Testing Document View with Base64 (Document ID: {document_id})")
    print("=" * 60)
    
    # Test 1: Get single document with base64
    print("\n1️⃣ Testing GET /document/{id} (with base64):")
    response = requests.get(f"{DOCUMENT_URL}/{document_id}", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success! Document found: {data['title']}")
        print(f"📄 File: {data['file_name']}")
        print(f"📏 Size: {data['file_size']} bytes")
        print(f"🔢 Base64 Length: {len(data['file_base64']) if data['file_base64'] else 0} characters")
        
        if data['file_base64']:
            # Decode a small portion to verify it's valid base64
            try:
                decoded_sample = base64.b64decode(data['file_base64'][:100])
                print(f"✅ Base64 is valid! Sample decoded length: {len(decoded_sample)} bytes")
            except Exception as e:
                print(f"❌ Base64 validation failed: {e}")
        else:
            print("⚠️  No base64 content found")
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")

def test_comprehensive_document_view(token, document_id=1):
    """Test comprehensive document view with traceability and base64"""
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"\n2️⃣ Testing GET /document/{document_id}/view (comprehensive with base64):")
    response = requests.get(f"{DOCUMENT_URL}/{document_id}/view", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        document = data['document']
        print(f"✅ Success! Document: {document['title']}")
        print(f"📄 File: {document['file_name']}")
        print(f"📏 Size: {document['file_size']} bytes")
        print(f"🔢 Base64 Length: {len(document['file_base64']) if document['file_base64'] else 0} characters")
        
        # Show traceability info
        traceability = data['traceability']
        print(f"📋 Traceability Records: {len(traceability.get('review_history', []))}")
        
        # Show permissions
        print(f"🔐 Permissions:")
        print(f"   - Can Edit: {data['can_edit']}")
        print(f"   - Can Review: {data['can_review']}")
        print(f"   - Can Approve: {data['can_approve']}")
        print(f"   - Can Delete: {data['can_delete']}")
        print(f"   - User Role: {data['current_user_role']}")
        
        if document['file_base64']:
            try:
                decoded_sample = base64.b64decode(document['file_base64'][:100])
                print(f"✅ Base64 is valid! Sample decoded length: {len(decoded_sample)} bytes")
            except Exception as e:
                print(f"❌ Base64 validation failed: {e}")
        else:
            print("⚠️  No base64 content found")
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")

def test_all_documents_with_base64(token):
    """Test getting all documents with base64 content"""
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"\n3️⃣ Testing GET /document/all (with base64):")
    response = requests.get(f"{DOCUMENT_URL}/all", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        documents = data['documents']
        print(f"✅ Success! Found {len(documents)} documents")
        
        for i, doc in enumerate(documents[:3], 1):  # Show first 3 documents
            print(f"\n📄 Document {i}: {doc['title']}")
            print(f"   File: {doc['file_name']}")
            print(f"   Size: {doc['file_size']} bytes")
            print(f"   Base64 Length: {len(doc['file_base64']) if doc['file_base64'] else 0} characters")
            
            if doc['file_base64']:
                try:
                    decoded_sample = base64.b64decode(doc['file_base64'][:100])
                    print(f"   ✅ Base64 valid (sample: {len(decoded_sample)} bytes)")
                except Exception as e:
                    print(f"   ❌ Base64 invalid: {e}")
            else:
                print("   ⚠️  No base64 content")
        
        if len(documents) > 3:
            print(f"\n... and {len(documents) - 3} more documents")
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")

def test_document_data_endpoint(token, document_id=1):
    """Test the dedicated document data endpoint"""
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"\n4️⃣ Testing GET /document/{document_id}/data (dedicated base64 endpoint):")
    response = requests.get(f"{DOCUMENT_URL}/{document_id}/data", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success! Document: {data['title']}")
        print(f"📄 File: {data['file_name']}")
        print(f"📏 Size: {data['file_size']} bytes")
        print(f"🔢 Base64 Length: {len(data['file_base64']) if data['file_base64'] else 0} characters")
        
        if data['file_base64']:
            try:
                decoded_sample = base64.b64decode(data['file_base64'][:100])
                print(f"✅ Base64 is valid! Sample decoded length: {len(decoded_sample)} bytes")
                
                # Show first 50 characters of base64
                print(f"🔤 Base64 Preview: {data['file_base64'][:50]}...")
            except Exception as e:
                print(f"❌ Base64 validation failed: {e}")
        else:
            print("⚠️  No base64 content found")
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")

def save_base64_to_file(token, document_id=1, output_file="downloaded_document.pdf"):
    """Download and save base64 content to file"""
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"\n5️⃣ Testing Base64 Download and Save:")
    response = requests.get(f"{DOCUMENT_URL}/{document_id}/data", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if data['file_base64']:
            try:
                # Decode base64 to binary
                pdf_content = base64.b64decode(data['file_base64'])
                
                # Save to file
                with open(output_file, 'wb') as f:
                    f.write(pdf_content)
                
                print(f"✅ Successfully saved {len(pdf_content)} bytes to {output_file}")
                print(f"📄 Original filename: {data['file_name']}")
                print(f"📏 File size: {data['file_size']} bytes")
                
                # Verify file was created
                if os.path.exists(output_file):
                    actual_size = os.path.getsize(output_file)
                    print(f"✅ File created successfully! Size: {actual_size} bytes")
                else:
                    print("❌ File was not created")
                    
            except Exception as e:
                print(f"❌ Failed to save file: {e}")
        else:
            print("⚠️  No base64 content to save")
    else:
        print(f"❌ Failed to get document: {response.status_code} - {response.text}")

def main():
    """Main test function"""
    print("🚀 Testing Document View with Base64 Content")
    print("=" * 60)
    
    # Login and get token
    token = login_and_get_token()
    if not token:
        print("❌ Cannot proceed without authentication token")
        return
    
    print(f"✅ Authentication successful! Token: {token[:20]}...")
    
    # Run all tests
    test_document_view_with_base64(token)
    test_comprehensive_document_view(token)
    test_all_documents_with_base64(token)
    test_document_data_endpoint(token)
    save_base64_to_file(token)
    
    print(f"\n🎉 All tests completed!")
    print(f"\n📋 Summary of Base64-Enabled Endpoints:")
    print(f"   • GET /document/{id} - Single document with base64")
    print(f"   • GET /document/{id}/view - Comprehensive view with base64")
    print(f"   • GET /document/{id}/data - Dedicated base64 endpoint")
    print(f"   • GET /document/all - All documents with base64")
    print(f"   • GET /document/{id}/preview - PDF preview from base64")
    print(f"   • GET /document/{id}/download - PDF download from base64")

if __name__ == "__main__":
    main()
