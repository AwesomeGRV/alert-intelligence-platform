import requests
import json

# Test the API endpoints
base_url = "http://localhost:8000"

print("Testing Alert Intelligence Platform API...")
print("=" * 50)

# Test health
try:
    response = requests.get(f"{base_url}/health")
    print(f"Health Check: {response.status_code} - {response.json()}")
except Exception as e:
    print(f"Health Check Error: {e}")

# Test alerts
try:
    response = requests.get(f"{base_url}/api/v1/alerts")
    print(f"Get Alerts: {response.status_code} - Found {len(response.json().get('alerts', []))} alerts")
except Exception as e:
    print(f"Get Alerts Error: {e}")

# Test incidents
try:
    response = requests.get(f"{base_url}/api/v1/incidents")
    print(f"Get Incidents: {response.status_code} - Found {len(response.json().get('incidents', []))} incidents")
except Exception as e:
    print(f"Get Incidents Error: {e}")

# Test dashboard
try:
    response = requests.get(f"{base_url}/api/v1/dashboard/overview")
    print(f"Dashboard Overview: {response.status_code}")
    data = response.json()
    print(f"  - Total Alerts: {data.get('total_alerts', 0)}")
    print(f"  - Total Incidents: {data.get('total_incidents', 0)}")
except Exception as e:
    print(f"Dashboard Error: {e}")

# Test creating an alert
try:
    new_alert = {
        "source": "test",
        "service": "test-service", 
        "severity": "medium",
        "description": "Test alert from Python script"
    }
    response = requests.post(f"{base_url}/api/v1/alerts", json=new_alert)
    print(f"Create Alert: {response.status_code} - {response.json()}")
except Exception as e:
    print(f"Create Alert Error: {e}")

print("=" * 50)
print("API Test Complete!")
