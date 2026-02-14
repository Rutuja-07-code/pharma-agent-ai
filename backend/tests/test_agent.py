# Unit and integration tests
# Agent pipeline test cases

# from backend.app.order_executor import place_order

# # Manual test order
# order = {
#     "medicine_name": "Paracetamol",
#     "quantity": 2
# }

# result = place_order(order)
# print(result)

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.order_executor import place_order

# Manual test order
order = {
    "medicine_name": "Paracetamol",
    "quantity": 3000
}

result = place_order(order)
print(result)