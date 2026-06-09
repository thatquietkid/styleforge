import requests
import json
import os

base_url = "http://localhost:8000"

print("--- Authenticating with Styleforge ---")
email = "test_genai_user@example.com"
password = "SecurePassword123"

# Authenticate
resp = requests.post(f"{base_url}/api/v1/auth/login", data={"username": email, "password": password})
if resp.status_code == 200:
    token_data = resp.json()
    token = token_data["access_token"]
    print("✓ Successfully authenticated!")
    print(f"Token: {token[:40]}...")
    
    # Hit scratch-or-sketch
    print("\n--- Sending request to scratch-or-sketch GenAI endpoint ---")
    print("Generating Sunflower Sling Dress... (Please wait, this will take ~2 minutes)")
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    # We send the request. (Note: sketch_file is optional, so we test prompt-to-image)
    data = {
        "positive_prompt": "A bright stem green colored sling dress with ghibli studio styled sunflower print",
        "negative_prompt": "pale fabric, washed out colors, low quality, dark color",
        "target_class": "long_sleeve_outwear"
    }
    
    try:
        # High timeout (7 minutes) to cover the full GenAI generation window
        resp = requests.post(
            f"{base_url}/api/v1/genai/generate/scratch-or-sketch",
            headers=headers,
            data=data,
            timeout=420.0
        )
        
        if resp.status_code == 200:
            output_path = os.path.join(os.path.dirname(__file__), "sunflower_sling_dress.png")
            with open(output_path, "wb") as f:
                f.write(resp.content)
            print("\n🎉 SUCCESS!")
            print(f"✓ Image generated successfully and saved to: {output_path}")
        else:
            print(f"\n❌ Request failed with status {resp.status_code}")
            print("Response:", resp.text)
            
    except Exception as e:
        print("\n❌ Error during generation:", e)
else:
    print("❌ Authentication failed:", resp.text)
