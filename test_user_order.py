import requests
import json

# Test if user data is being sent correctly
print("Testing order placement with user data...")

# Simulate a logged-in user placing an order
test_data = {
    "message": "I need 3 Paracetamol",
    "user_id": "testuser123",
    "phone": "9876543210"
}

print(f"\nSending request with data: {json.dumps(test_data, indent=2)}")

try:
    response = requests.post(
        "http://127.0.0.1:8000/chat",
        json=test_data,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"\nResponse status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    # Check if order was saved
    print("\n\nChecking user orders endpoint...")
    orders_response = requests.get("http://127.0.0.1:8000/admin/user-orders")
    orders = orders_response.json()
    
    # Find our test order
    test_orders = [o for o in orders if o.get('patient_id') == 'testuser123']
    if test_orders:
        print(f"\nSUCCESS! Found {len(test_orders)} order(s) for testuser123:")
        for order in test_orders[:3]:
            print(f"  - {order.get('product_name')} | Phone: {order.get('phone')} | Qty: {order.get('quantity')}")
    else:
        print("\nFAILED! No orders found for testuser123")
        print(f"Total orders in system: {len(orders)}")
        
except Exception as e:
    print(f"\nERROR: {e}")
