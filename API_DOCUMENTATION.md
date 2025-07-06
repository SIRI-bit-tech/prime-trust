# PrimeTrust Banking API Documentation

## Overview

The PrimeTrust Banking API is a RESTful API that provides secure access to banking services and account management. The API uses JWT authentication and follows REST principles for consistent, predictable behavior.

## Base URL

```
Production: https://your-domain.com/api/v1/
Development: http://localhost:8000/api/v1/
```

## Authentication

The API uses JWT (JSON Web Tokens) for authentication. All authenticated endpoints require a valid Bearer token in the Authorization header.

### Authentication Flow

1. **Login**: POST to `/auth/login/` with username/password
2. **Verify**: POST to `/auth/verify-login/` with the received verification code
3. **Access**: Use the returned JWT token for subsequent requests
4. **Refresh**: Use `/auth/token/refresh/` to get new tokens

### Headers

```
Authorization: Bearer <your-jwt-token>
Content-Type: application/json
```

## API Endpoints

### Authentication Endpoints

#### 1. Login (Initial)
```http
POST /api/v1/auth/login/
```

**Request Body:**
```json
{
    "username": "your_username",
    "password": "your_password"
}
```

**Response:**
```json
{
    "detail": "Login code sent to your email. Please verify to complete login.",
    "requires_verification": true,
    "user_id": 123
}
```

#### 2. Verify Login
```http
POST /api/v1/auth/verify-login/
```

**Request Body:**
```json
{
    "user_id": 123,
    "code": "123456"
}
```

**Response:**
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "user": {
        "id": 123,
        "username": "john_doe",
        "email": "john@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "date_joined": "2024-01-01T00:00:00Z",
        "profile": {
            "phone_number": "+1234567890",
            "address": "123 Main St",
            "city": "New York",
            "state": "NY",
            "zip_code": "10001"
        }
    }
}
```

#### 3. Refresh Token
```http
POST /api/v1/auth/token/refresh/
```

**Request Body:**
```json
{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Response:**
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

#### 4. Logout
```http
POST /api/v1/auth/logout/
```

**Request Body:**
```json
{
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### User Profile Endpoints

#### 1. Get Profile
```http
GET /api/v1/profile/
```

**Response:**
```json
{
    "id": 123,
    "username": "john_doe",
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "date_joined": "2024-01-01T00:00:00Z",
    "profile": {
        "phone_number": "+1234567890",
        "address": "123 Main St",
        "city": "New York",
        "state": "NY",
        "zip_code": "10001",
        "date_of_birth": "1990-01-01",
        "gender": "M",
        "company": "Tech Corp"
    }
}
```

#### 2. Update Profile
```http
PUT /api/v1/profile/update/
```

**Request Body:**
```json
{
    "first_name": "John",
    "last_name": "Doe",
    "profile": {
        "phone_number": "+1234567890",
        "address": "456 Oak Ave",
        "city": "Los Angeles",
        "state": "CA",
        "zip_code": "90210"
    }
}
```

#### 3. Change Password
```http
POST /api/v1/profile/change-password/
```

**Request Body:**
```json
{
    "old_password": "current_password",
    "new_password": "new_password123",
    "confirm_password": "new_password123"
}
```

### Account Endpoints

#### 1. List Accounts
```http
GET /api/v1/accounts/
```

**Response:**
```json
{
    "count": 1,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": 1,
            "account_number": "1234567890",
            "account_type": "checking",
            "balance": "1500.00",
            "routing_number": "021000021",
            "is_active": true,
            "created_at": "2024-01-01T00:00:00Z"
        }
    ]
}
```

#### 2. Account Details
```http
GET /api/v1/accounts/{id}/
```

#### 3. Account Balance
```http
GET /api/v1/accounts/{id}/balance/
```

**Response:**
```json
{
    "account_number": "1234567890",
    "balance": "1500.00",
    "last_updated": "2024-01-15T10:30:00Z"
}
```

#### 4. Account Transactions
```http
GET /api/v1/accounts/{id}/transactions/
```

**Query Parameters:**
- `page`: Page number for pagination
- `page_size`: Number of results per page

#### 5. Deposit Money
```http
POST /api/v1/accounts/{id}/deposit/
```

**Request Body:**
```json
{
    "amount": "100.00",
    "description": "Salary deposit"
}
```

**Response:**
```json
{
    "message": "Deposit successful",
    "transaction": {
        "id": 456,
        "transaction_type": "deposit",
        "amount": "100.00",
        "description": "Salary deposit",
        "reference_number": "DEP-20240115-456",
        "status": "completed",
        "created_at": "2024-01-15T10:30:00Z"
    },
    "new_balance": "1600.00"
}
```

#### 6. Transfer Money
```http
POST /api/v1/accounts/{id}/transfer/
```

**Request Body:**
```json
{
    "recipient_account": "0987654321",
    "amount": "250.00",
    "description": "Monthly payment",
    "transaction_pin": "1234"
}
```

**Response:**
```json
{
    "message": "Transfer successful",
    "transaction": {
        "id": 457,
        "transaction_type": "transfer_out",
        "amount": "250.00",
        "description": "Transfer to 0987654321: Monthly payment",
        "reference_number": "TXN-20240115-457",
        "status": "completed",
        "created_at": "2024-01-15T10:45:00Z"
    },
    "new_balance": "1350.00",
    "recipient": {
        "account_number": "0987654321",
        "name": "Jane Smith"
    }
}
```

### Transaction Endpoints

#### 1. List Transactions
```http
GET /api/v1/transactions/
```

**Query Parameters:**
- `page`: Page number
- `transaction_type`: Filter by type (deposit, withdrawal, transfer_in, transfer_out)
- `ordering`: Sort by field (e.g., `-created_at` for newest first)

#### 2. Recent Transactions
```http
GET /api/v1/transactions/recent/
```

**Response:**
```json
[
    {
        "id": 457,
        "account": {
            "id": 1,
            "account_number": "1234567890",
            "account_type": "checking",
            "balance": "1350.00"
        },
        "transaction_type": "transfer_out",
        "amount": "250.00",
        "description": "Monthly payment",
        "reference_number": "TXN-20240115-457",
        "status": "completed",
        "created_at": "2024-01-15T10:45:00Z"
    }
]
```

#### 3. Transaction Summary
```http
GET /api/v1/transactions/summary/
```

**Response:**
```json
{
    "period": "January 2024",
    "total_deposits": "1000.00",
    "total_withdrawals": "250.00",
    "total_transfers_in": "500.00",
    "net_change": "1250.00",
    "transaction_count": 15
}
```

### Banking Endpoints

#### 1. Account Information
```http
GET /api/v1/banking/account_info/
```

**Response:**
```json
{
    "id": 1,
    "account_number": "1234567890",
    "account_type": "checking",
    "balance": "1350.00",
    "routing_number": "021000021",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z"
}
```

#### 2. Verify Account
```http
POST /api/v1/banking/verify_account/
```

**Request Body:**
```json
{
    "account_number": "0987654321"
}
```

**Response:**
```json
{
    "valid": true,
    "account_holder": "Jane Smith",
    "account_type": "checking"
}
```

#### 3. Dashboard Data
```http
GET /api/v1/banking/dashboard_data/
```

**Response:**
```json
{
    "account": {
        "id": 1,
        "account_number": "1234567890",
        "account_type": "checking",
        "balance": "1350.00",
        "routing_number": "021000021",
        "is_active": true,
        "created_at": "2024-01-01T00:00:00Z"
    },
    "recent_transactions": [
        {
            "id": 457,
            "transaction_type": "transfer_out",
            "amount": "250.00",
            "description": "Monthly payment",
            "reference_number": "TXN-20240115-457",
            "status": "completed",
            "created_at": "2024-01-15T10:45:00Z"
        }
    ],
    "account_holder": "John Doe"
}
```

## Error Handling

### Error Response Format

```json
{
    "error": "Error message",
    "detail": "Detailed error description",
    "code": "error_code"
}
```

### HTTP Status Codes

- `200 OK`: Request successful
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

### Common Error Responses

#### Invalid credentials
```json
{
    "error": "Invalid credentials",
    "detail": "Username or password is incorrect"
}
```

#### Insufficient funds
```json
{
    "error": "Insufficient funds",
    "detail": "Account balance is insufficient for this transaction"
}
```

#### Invalid transaction PIN
```json
{
    "error": "Invalid transaction PIN",
    "detail": "The provided transaction PIN is incorrect"
}
```

## Rate Limiting

The API implements rate limiting to prevent abuse:

- **Anonymous users**: 100 requests per hour
- **Authenticated users**: 1000 requests per hour

Rate limit headers are included in responses:
- `X-RateLimit-Limit`: Total requests allowed
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: Time until limit resets

## Security Features

1. **JWT Authentication**: Secure token-based authentication
2. **Token Rotation**: Refresh tokens are rotated on use
3. **Token Blacklisting**: Logout invalidates tokens
4. **HTTPS Only**: All production traffic encrypted
5. **CORS Protection**: Cross-origin request protection
6. **Rate Limiting**: Prevents abuse and DoS attacks
7. **Input Validation**: All inputs validated and sanitized

## Testing

### Postman Collection

A Postman collection is available for testing API endpoints. Import the collection and:

1. Set the `baseUrl` variable to your API endpoint
2. Use the authentication flow to get tokens
3. Test various endpoints with valid data

### Example cURL Commands

#### Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass123"}'
```

#### Get Account Balance
```bash
curl -X GET http://localhost:8000/api/v1/accounts/1/balance/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### Transfer Money
```bash
curl -X POST http://localhost:8000/api/v1/accounts/1/transfer/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "recipient_account": "0987654321",
    "amount": "100.00",
    "description": "Payment",
    "transaction_pin": "1234"
  }'
```

## API Documentation (Interactive)

Interactive API documentation is available at:
- **Swagger UI**: `/api/docs/`
- **ReDoc**: `/api/redoc/`
- **OpenAPI Schema**: `/api/schema/`

## Support

For API support, please contact:
- Email: api-support@primetrust.com
- Documentation: https://docs.primetrust.com
- Status Page: https://status.primetrust.com

## Changelog

### Version 1.0.0 (2024-01-15)
- Initial API release
- JWT authentication
- Account management endpoints
- Transaction endpoints
- Money transfer functionality
- API documentation 