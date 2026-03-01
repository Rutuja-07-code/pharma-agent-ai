# API endpoints documentation

## Send WhatsApp Message (Admin)

`POST /admin/whatsapp/send`

Request body:

```json
{
  "username": "rutuja",
  "phone": "+919999999999",
  "message": "Hi, your order is ready for pickup."
}
```

Notes:
- `message` is required.
- Provide either `phone` or `username` (if username exists in `patient_contacts.csv` with phone).
- Requires Twilio env vars: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and optional `TWILIO_WHATSAPP_FROM`.

## Create Order Record

`POST /orders`

Request body:

```json
{
  "patient_id": "rutuja",
  "username": "rutuja",
  "phone": "+919999999999",
  "medicine_name": "Paracetamol apodiscounter 500 mg Tabletten",
  "quantity": 4,
  "dosage_frequency": "once daily",
  "ordered_at": "2026-03-01T12:00:00Z",
  "unit_price": 2.06,
  "total_price": 8.24
}
```

Required fields:
- `patient_id`
- `username`
- `phone`
- `medicine_name`
- `quantity`
- `dosage_frequency`

## List Orders

`GET /orders`

Query params (all optional):
- `patient_id`
- `username`
- `phone`
- `limit` (default 200, max 1000)
