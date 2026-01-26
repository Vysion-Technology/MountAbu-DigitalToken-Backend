# API Specification Document
## Mount Abu E-Token Management System
### RESTful API v1.0

---

**Base URL:** `https://api.mountabu.gov.in/api/v1`  
**API Version:** 1.0  
**Authentication:** Bearer JWT Token  
**Content-Type:** application/json  

---

## Table of Contents
1. [Authentication APIs](#1-authentication-apis)
2. [User Management APIs](#2-user-management-apis)
3. [Application APIs](#3-application-apis)
4. [Token APIs](#4-token-apis)
5. [Estimate APIs](#5-estimate-apis)
6. [Inspection APIs](#6-inspection-apis)
7. [Naka (Checkpoint) APIs](#7-naka-checkpoint-apis)
8. [Blacklist Management APIs](#8-blacklist-management-apis)
9. [Report APIs](#9-report-apis)
10. [Notification APIs](#10-notification-apis)
11. [Content Management APIs](#11-content-management-apis)
12. [Analytics APIs](#12-analytics-apis)
13. [Error Codes](#13-error-codes)

---

## Authentication & Headers

### Required Headers
```http
Authorization: Bearer <jwt_token>
Content-Type: application/json
Accept: application/json
X-Request-ID: <uuid>
Accept-Language: en | hi
```

### Token Structure
```json
{
  "accessToken": "eyJhbGciOiJIUzI1NiIs...",
  "refreshToken": "eyJhbGciOiJIUzI1NiIs...",
  "tokenType": "Bearer",
  "expiresIn": 3600,
  "refreshExpiresIn": 604800
}
```

---

## 1. Authentication APIs

### 1.1 Initiate Login

**Endpoint:** `POST /auth/login`  
**Description:** Start the login process for applicants or authorities  
**Authentication:** None  

**Request:**
```json
{
  "userType": "applicant | authority",
  "identifier": "9876543210 | admin@mountabu.gov.in",
  "password": "optional_for_authority"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "sessionId": "sess_abc123xyz",
    "otpSent": true,
    "otpExpiresIn": 300,
    "maskedMobile": "****3210"
  }
}
```

**Response (401 Unauthorized):**
```json
{
  "success": false,
  "error": {
    "code": "AUTH_INVALID_CREDENTIALS",
    "message": "Invalid email or password"
  }
}
```

---

### 1.2 Verify OTP

**Endpoint:** `POST /auth/verify-otp`  
**Description:** Verify OTP and complete login  
**Authentication:** None  

**Request:**
```json
{
  "sessionId": "sess_abc123xyz",
  "otp": "123456"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "accessToken": "eyJhbGciOiJIUzI1NiIs...",
    "refreshToken": "eyJhbGciOiJIUzI1NiIs...",
    "tokenType": "Bearer",
    "expiresIn": 3600,
    "user": {
      "id": "usr_abc123",
      "name": "Rajesh Kumar",
      "mobile": "9876543210",
      "email": "rajesh@example.com",
      "userType": "applicant",
      "aadhaarVerified": true,
      "isBlacklisted": false,
      "createdAt": "2025-10-15T10:30:00Z"
    }
  }
}
```

---

### 1.3 Refresh Token

**Endpoint:** `POST /auth/refresh`  
**Description:** Get new access token using refresh token  
**Authentication:** None  

**Request:**
```json
{
  "refreshToken": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "accessToken": "eyJhbGciOiJIUzI1NiIs...",
    "expiresIn": 3600
  }
}
```

---

### 1.4 Aadhaar Verification

**Endpoint:** `POST /auth/aadhaar-verify`  
**Description:** Verify Aadhaar for applicant KYC  
**Authentication:** Bearer Token  

**Request:**
```json
{
  "aadhaarNumber": "123456789012",
  "otp": "123456"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "verified": true,
    "name": "Rajesh Kumar",
    "maskedAadhaar": "XXXX-XXXX-9012",
    "verifiedAt": "2025-10-15T10:35:00Z"
  }
}
```

---

### 1.5 Logout

**Endpoint:** `POST /auth/logout`  
**Description:** Invalidate current session  
**Authentication:** Bearer Token  

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

---

## 2. User Management APIs

### 2.1 Get Profile

**Endpoint:** `GET /users/profile`  
**Description:** Get current user's profile  
**Authentication:** Bearer Token  

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": "usr_abc123",
    "name": "Rajesh Kumar",
    "mobile": "9876543210",
    "email": "rajesh@example.com",
    "userType": "applicant",
    "aadhaarVerified": true,
    "aadhaarMasked": "XXXX-XXXX-9012",
    "address": {
      "line1": "123 Main Street",
      "line2": "Near Bus Stand",
      "city": "Mount Abu",
      "state": "Rajasthan",
      "pincode": "307501"
    },
    "blacklistStatus": {
      "isBlacklisted": false,
      "consecutiveRejections": 0
    },
    "stats": {
      "totalApplications": 5,
      "approvedApplications": 3,
      "pendingApplications": 1,
      "rejectedApplications": 1,
      "activeTokens": 2
    },
    "createdAt": "2025-10-15T10:30:00Z",
    "updatedAt": "2025-12-20T14:45:00Z"
  }
}
```

---

### 2.2 Update Profile

**Endpoint:** `PUT /users/profile`  
**Description:** Update user profile  
**Authentication:** Bearer Token  

**Request:**
```json
{
  "name": "Rajesh Kumar Singh",
  "email": "rajesh.singh@example.com",
  "address": {
    "line1": "456 New Street",
    "line2": "Near Temple",
    "city": "Mount Abu",
    "state": "Rajasthan",
    "pincode": "307501"
  }
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": "usr_abc123",
    "name": "Rajesh Kumar Singh",
    "updatedAt": "2026-01-18T10:30:00Z"
  },
  "message": "Profile updated successfully"
}
```

---

### 2.3 List Authorities (Admin Only)

**Endpoint:** `GET /users/authorities`  
**Description:** Get list of all authorities  
**Authentication:** Bearer Token (SDM/CMS)  
**Query Parameters:**
- `role`: Filter by role (SDM, CMS_UIT, CMS_ULB, JEN, LAND, LEGAL, ATP, NAKA)
- `status`: active | inactive
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 20)

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "authorities": [
      {
        "id": "auth_xyz789",
        "name": "Dr. Sharma",
        "email": "sharma.sdm@mountabu.gov.in",
        "mobile": "9876543210",
        "role": "SDM",
        "department": "Revenue Department",
        "designation": "Sub-Divisional Magistrate",
        "status": "active",
        "lastLogin": "2026-01-17T09:15:00Z",
        "stats": {
          "filesProcessed": 245,
          "avgProcessingTime": 2.3
        },
        "createdAt": "2024-01-01T00:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 15,
      "totalPages": 1
    }
  }
}
```

---

### 2.4 Create Authority (Admin Only)

**Endpoint:** `POST /users/authorities`  
**Description:** Create new authority user  
**Authentication:** Bearer Token (SDM)  

**Request:**
```json
{
  "name": "Amit Verma",
  "email": "amit.jen@mountabu.gov.in",
  "mobile": "9123456789",
  "role": "JEN",
  "department": "PWD",
  "designation": "Junior Engineer",
  "permissions": ["VIEW_APPLICATIONS", "UPLOAD_INSPECTION", "APPROVE_LAYOUT"]
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "id": "auth_new123",
    "name": "Amit Verma",
    "email": "amit.jen@mountabu.gov.in",
    "role": "JEN",
    "temporaryPassword": "TempPass123!",
    "createdAt": "2026-01-18T11:00:00Z"
  },
  "message": "Authority created successfully. Temporary password sent via email."
}
```

---

## 3. Application APIs

### 3.1 Create Application

**Endpoint:** `POST /applications`  
**Description:** Submit new construction or renovation application  
**Authentication:** Bearer Token (Applicant)  

**Pre-conditions:**
- User must have verified Aadhaar
- User must NOT be blacklisted

**Request:**
```json
{
  "applicationType": "NEW_CONSTRUCTION",
  "zone": "UIT_DENSE",
  "propertyDetails": {
    "plotNumber": "P-123/A",
    "khasraNumber": "456/7",
    "area": 250.5,
    "areaUnit": "SQ_METERS",
    "address": {
      "line1": "Plot No. 123, Sector A",
      "line2": "Near Lake View",
      "city": "Mount Abu",
      "state": "Rajasthan",
      "pincode": "307501"
    },
    "ownerDetails": {
      "name": "Rajesh Kumar",
      "fatherName": "Mohan Kumar",
      "aadhaarNumber": "XXXX-XXXX-9012"
    }
  },
  "constructionDetails": {
    "purpose": "RESIDENTIAL",
    "floors": 2,
    "builtUpArea": 180.0,
    "estimatedCost": 2500000,
    "startDate": "2026-02-01",
    "endDate": "2026-08-31"
  },
  "documentIds": [
    "doc_ownership123",
    "doc_map456",
    "doc_noc789"
  ],
  "termsAccepted": true,
  "declarationAccepted": true
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "applicationId": "APP-2026-00123",
    "applicationType": "NEW_CONSTRUCTION",
    "status": "SUBMITTED",
    "currentAuthority": "SDM",
    "timeline": [
      {
        "status": "SUBMITTED",
        "timestamp": "2026-01-18T12:00:00Z",
        "actor": "Applicant"
      }
    ],
    "estimatedProcessingDays": 7,
    "createdAt": "2026-01-18T12:00:00Z"
  },
  "message": "Application submitted successfully. You will receive updates via SMS."
}
```

**Response (403 Forbidden - Blacklisted User):**
```json
{
  "success": false,
  "error": {
    "code": "USER_BLACKLISTED",
    "message": "You are currently blacklisted due to 3 consecutive rejected applications. Please visit the SDM office for whitelist request.",
    "details": {
      "blacklistedAt": "2026-01-10T10:00:00Z",
      "consecutiveRejections": 3,
      "lastRejectionReason": "Fraudulent documents submitted"
    }
  }
}
```

---

### 3.2 List Applications

**Endpoint:** `GET /applications`  
**Description:** Get list of applications  
**Authentication:** Bearer Token  
**Query Parameters:**
- `status`: SUBMITTED | UNDER_REVIEW | APPROVED | REJECTED | COMPLETED
- `type`: NEW_CONSTRUCTION | RENOVATION
- `zone`: UIT_DENSE | UIT_SCATTERED | ULB_DENSE | ULB_SCATTERED
- `dateFrom`: ISO date
- `dateTo`: ISO date
- `assignedTo`: authority ID (for authorities)
- `page`: Page number
- `limit`: Items per page
- `sortBy`: createdAt | updatedAt | status
- `sortOrder`: asc | desc

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "applications": [
      {
        "applicationId": "APP-2026-00123",
        "applicationType": "NEW_CONSTRUCTION",
        "zone": "UIT_DENSE",
        "status": "UNDER_REVIEW",
        "currentAuthority": "JEN",
        "applicant": {
          "id": "usr_abc123",
          "name": "Rajesh Kumar",
          "mobile": "****3210"
        },
        "propertyAddress": "Plot No. 123, Sector A, Mount Abu",
        "submittedAt": "2026-01-18T12:00:00Z",
        "lastUpdatedAt": "2026-01-18T14:30:00Z",
        "daysInProcess": 1,
        "slaStatus": "ON_TRACK"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 45,
      "totalPages": 3
    },
    "summary": {
      "submitted": 10,
      "underReview": 25,
      "approved": 8,
      "rejected": 2
    }
  }
}
```

---

### 3.3 Get Application Details

**Endpoint:** `GET /applications/:applicationId`  
**Description:** Get detailed application information  
**Authentication:** Bearer Token  

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "applicationId": "APP-2026-00123",
    "applicationType": "NEW_CONSTRUCTION",
    "zone": "UIT_DENSE",
    "status": "UNDER_REVIEW",
    "applicant": {
      "id": "usr_abc123",
      "name": "Rajesh Kumar",
      "mobile": "9876543210",
      "email": "rajesh@example.com",
      "aadhaarVerified": true
    },
    "propertyDetails": {
      "plotNumber": "P-123/A",
      "khasraNumber": "456/7",
      "area": 250.5,
      "areaUnit": "SQ_METERS",
      "address": {
        "line1": "Plot No. 123, Sector A",
        "line2": "Near Lake View",
        "city": "Mount Abu",
        "state": "Rajasthan",
        "pincode": "307501"
      },
      "coordinates": {
        "latitude": 24.5926,
        "longitude": 72.7156
      }
    },
    "constructionDetails": {
      "purpose": "RESIDENTIAL",
      "floors": 2,
      "builtUpArea": 180.0,
      "estimatedCost": 2500000,
      "startDate": "2026-02-01",
      "endDate": "2026-08-31"
    },
    "documents": [
      {
        "id": "doc_ownership123",
        "type": "OWNERSHIP_DEED",
        "name": "Ownership Deed.pdf",
        "url": "https://storage.mountabu.gov.in/docs/...",
        "uploadedAt": "2026-01-18T11:55:00Z",
        "verified": true,
        "verifiedBy": "LAND"
      }
    ],
    "estimates": {
      "hasEstimate": true,
      "estimateId": "est_456",
      "phases": 3,
      "totalMaterials": [
        {"material": "Cement", "quantity": 500, "unit": "bags"},
        {"material": "Sand", "quantity": 50, "unit": "truckloads"},
        {"material": "Bricks", "quantity": 25000, "unit": "pieces"}
      ]
    },
    "tokens": {
      "issued": 2,
      "active": 1,
      "exhausted": 1
    },
    "timeline": [
      {
        "status": "SUBMITTED",
        "timestamp": "2026-01-18T12:00:00Z",
        "actor": "Rajesh Kumar",
        "actorRole": "APPLICANT"
      },
      {
        "status": "SDM_REVIEW",
        "timestamp": "2026-01-18T12:30:00Z",
        "actor": "Dr. Sharma",
        "actorRole": "SDM",
        "comment": "Forwarded for site inspection"
      },
      {
        "status": "JEN_INSPECTION",
        "timestamp": "2026-01-18T14:00:00Z",
        "actor": "Amit Verma",
        "actorRole": "JEN",
        "comment": "Site inspection scheduled"
      }
    ],
    "sla": {
      "expectedCompletionDate": "2026-01-25",
      "daysRemaining": 7,
      "status": "ON_TRACK",
      "delayedStages": []
    },
    "createdAt": "2026-01-18T12:00:00Z",
    "updatedAt": "2026-01-18T14:00:00Z"
  }
}
```

---

### 3.4 Approve Application

**Endpoint:** `POST /applications/:applicationId/approve`  
**Description:** Approve application at current stage  
**Authentication:** Bearer Token (SDM/CMS)  

**Request:**
```json
{
  "comments": "All documents verified. Application approved for token generation.",
  "conditions": [
    "Construction must be completed within 6 months",
    "No deviation from approved plan allowed"
  ],
  "generateTokens": true
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "applicationId": "APP-2026-00123",
    "status": "APPROVED",
    "approvedBy": {
      "id": "auth_xyz789",
      "name": "Dr. Sharma",
      "role": "SDM"
    },
    "approvedAt": "2026-01-18T16:00:00Z",
    "tokensGenerated": true,
    "tokens": [
      {
        "tokenId": "TKN-2026-00123-P1",
        "phase": 1,
        "status": "ACTIVE"
      },
      {
        "tokenId": "TKN-2026-00123-P2",
        "phase": 2,
        "status": "PENDING"
      }
    ],
    "permissionLetter": {
      "documentId": "doc_perm123",
      "url": "https://storage.mountabu.gov.in/permissions/..."
    }
  },
  "message": "Application approved successfully. E-Tokens generated."
}
```

---

### 3.5 Reject Application

**Endpoint:** `POST /applications/:applicationId/reject`  
**Description:** Reject application with reason  
**Authentication:** Bearer Token (Authority)  

**Request:**
```json
{
  "reason": "INVALID_DOCUMENTS",
  "comments": "Ownership deed appears to be tampered. Please submit original verified copy.",
  "rejectionCategory": "DOCUMENT_ISSUE",
  "allowResubmission": true
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "applicationId": "APP-2026-00123",
    "status": "REJECTED",
    "rejectedBy": {
      "id": "auth_land456",
      "name": "Suresh Jain",
      "role": "LAND"
    },
    "rejectedAt": "2026-01-18T15:00:00Z",
    "reason": "INVALID_DOCUMENTS",
    "comments": "Ownership deed appears to be tampered. Please submit original verified copy.",
    "canResubmit": true,
    "applicantBlacklistStatus": {
      "consecutiveRejections": 2,
      "warningIssued": true,
      "warningMessage": "Warning: One more rejected application will result in automatic blacklisting."
    }
  },
  "message": "Application rejected. Applicant notified."
}
```

---

### 3.6 Forward Application

**Endpoint:** `POST /applications/:applicationId/forward`  
**Description:** Forward application to next authority  
**Authentication:** Bearer Token (Authority)  

**Request:**
```json
{
  "forwardTo": "JEN",
  "comments": "Please conduct site inspection and upload geo-tagged photos.",
  "priority": "NORMAL"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "applicationId": "APP-2026-00123",
    "status": "UNDER_REVIEW",
    "currentAuthority": "JEN",
    "forwardedBy": {
      "id": "auth_xyz789",
      "name": "Dr. Sharma",
      "role": "SDM"
    },
    "forwardedTo": {
      "id": "auth_jen123",
      "name": "Amit Verma",
      "role": "JEN"
    },
    "forwardedAt": "2026-01-18T12:30:00Z"
  },
  "message": "Application forwarded to JEN successfully."
}
```

---

### 3.7 Upload Documents

**Endpoint:** `POST /applications/:applicationId/documents`  
**Description:** Upload documents for application  
**Authentication:** Bearer Token (Applicant/Authority)  
**Content-Type:** multipart/form-data  

**Request:**
```
POST /applications/APP-2026-00123/documents
Content-Type: multipart/form-data

file: <binary>
documentType: OWNERSHIP_DEED
description: Original ownership deed from registrar office
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "documentId": "doc_new456",
    "type": "OWNERSHIP_DEED",
    "name": "Ownership_Deed.pdf",
    "size": 1048576,
    "mimeType": "application/pdf",
    "url": "https://storage.mountabu.gov.in/docs/...",
    "uploadedAt": "2026-01-18T12:15:00Z"
  },
  "message": "Document uploaded successfully."
}
```

---

## 4. Token APIs

### 4.1 List Tokens

**Endpoint:** `GET /tokens`  
**Description:** Get list of tokens  
**Authentication:** Bearer Token  
**Query Parameters:**
- `applicationId`: Filter by application
- `status`: ACTIVE | PENDING | EXHAUSTED | EXPIRED | CANCELLED
- `phase`: Phase number
- `page`: Page number
- `limit`: Items per page

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "tokens": [
      {
        "tokenId": "TKN-2026-00123-P1",
        "applicationId": "APP-2026-00123",
        "phase": 1,
        "status": "ACTIVE",
        "materials": [
          {
            "materialType": "CEMENT",
            "approvedQuantity": 200,
            "consumedQuantity": 50,
            "remainingQuantity": 150,
            "unit": "bags"
          },
          {
            "materialType": "SAND",
            "approvedQuantity": 20,
            "consumedQuantity": 5,
            "remainingQuantity": 15,
            "unit": "truckloads"
          }
        ],
        "validFrom": "2026-01-18T00:00:00Z",
        "validUntil": "2026-03-18T23:59:59Z",
        "lastUsedAt": "2026-01-18T10:30:00Z",
        "usageCount": 3
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 5,
      "totalPages": 1
    }
  }
}
```

---

### 4.2 Get Token Details

**Endpoint:** `GET /tokens/:tokenId`  
**Description:** Get detailed token information  
**Authentication:** Bearer Token  

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "tokenId": "TKN-2026-00123-P1",
    "applicationId": "APP-2026-00123",
    "applicant": {
      "id": "usr_abc123",
      "name": "Rajesh Kumar",
      "mobile": "9876543210"
    },
    "propertyAddress": "Plot No. 123, Sector A, Mount Abu",
    "phase": 1,
    "phaseName": "Foundation Work",
    "status": "ACTIVE",
    "materials": [
      {
        "materialType": "CEMENT",
        "materialName": "Cement (50kg bags)",
        "approvedQuantity": 200,
        "consumedQuantity": 50,
        "remainingQuantity": 150,
        "unit": "bags",
        "usagePercentage": 25
      }
    ],
    "validFrom": "2026-01-18T00:00:00Z",
    "validUntil": "2026-03-18T23:59:59Z",
    "qrCode": "data:image/png;base64,iVBORw0KGgo...",
    "shareableLink": "https://token.mountabu.gov.in/v/TKN-2026-00123-P1",
    "usageHistory": [
      {
        "entryId": "entry_001",
        "vehicleNumber": "RJ-14-AB-1234",
        "material": "CEMENT",
        "quantity": 20,
        "unit": "bags",
        "nakaLocation": "Main Gate",
        "entryTime": "2026-01-18T10:30:00Z",
        "verifiedBy": "Naka Incharge 1"
      }
    ],
    "createdAt": "2026-01-18T16:00:00Z",
    "createdBy": {
      "name": "Dr. Sharma",
      "role": "SDM"
    }
  }
}
```

---

### 4.3 Generate QR Code

**Endpoint:** `GET /tokens/:tokenId/qr`  
**Description:** Generate QR code for token  
**Authentication:** Bearer Token  
**Query Parameters:**
- `size`: QR size in pixels (default: 300)
- `format`: png | svg (default: png)

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "tokenId": "TKN-2026-00123-P1",
    "qrCode": "data:image/png;base64,iVBORw0KGgo...",
    "format": "png",
    "size": 300,
    "validUntil": "2026-03-18T23:59:59Z"
  }
}
```

---

### 4.4 Share Token

**Endpoint:** `POST /tokens/:tokenId/share`  
**Description:** Share token with driver  
**Authentication:** Bearer Token (Applicant)  

**Request:**
```json
{
  "driverName": "Ramu Driver",
  "driverMobile": "9123456789",
  "vehicleNumber": "RJ-14-AB-1234",
  "shareMethod": "SMS | WHATSAPP | BOTH",
  "validForHours": 24,
  "materialLimit": {
    "CEMENT": 50,
    "SAND": 5
  }
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "shareId": "share_xyz123",
    "tokenId": "TKN-2026-00123-P1",
    "sharedWith": {
      "name": "Ramu Driver",
      "mobile": "9123456789"
    },
    "vehicleNumber": "RJ-14-AB-1234",
    "shareLink": "https://token.mountabu.gov.in/s/share_xyz123",
    "qrCode": "data:image/png;base64,iVBORw0KGgo...",
    "validUntil": "2026-01-19T12:00:00Z",
    "materialLimit": {
      "CEMENT": 50,
      "SAND": 5
    },
    "messageSent": true
  },
  "message": "Token shared successfully. SMS sent to driver."
}
```

---

## 5. Estimate APIs

### 5.1 Upload Estimate

**Endpoint:** `POST /estimates/upload`  
**Description:** Upload Excel estimate for application  
**Authentication:** Bearer Token (JEN)  
**Content-Type:** multipart/form-data  

**Request:**
```
POST /estimates/upload
Content-Type: multipart/form-data

applicationId: APP-2026-00123
file: <excel_binary>
estimateType: PHASE_WISE | ONE_TIME
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "estimateId": "est_abc123",
    "applicationId": "APP-2026-00123",
    "estimateType": "PHASE_WISE",
    "phases": [
      {
        "phase": 1,
        "name": "Foundation Work",
        "materials": [
          {"material": "CEMENT", "quantity": 200, "unit": "bags"},
          {"material": "SAND", "quantity": 20, "unit": "truckloads"},
          {"material": "AGGREGATE", "quantity": 15, "unit": "truckloads"}
        ]
      },
      {
        "phase": 2,
        "name": "Structure Work",
        "materials": [
          {"material": "CEMENT", "quantity": 300, "unit": "bags"},
          {"material": "STEEL", "quantity": 5, "unit": "tons"}
        ]
      }
    ],
    "totalMaterials": {
      "CEMENT": {"quantity": 500, "unit": "bags"},
      "SAND": {"quantity": 50, "unit": "truckloads"},
      "AGGREGATE": {"quantity": 30, "unit": "truckloads"},
      "STEEL": {"quantity": 5, "unit": "tons"}
    },
    "uploadedAt": "2026-01-18T14:00:00Z",
    "uploadedBy": {
      "id": "auth_jen123",
      "name": "Amit Verma",
      "role": "JEN"
    }
  },
  "message": "Estimate uploaded and parsed successfully."
}
```

---

### 5.2 Get Estimates

**Endpoint:** `GET /estimates/:applicationId`  
**Description:** Get estimates for application  
**Authentication:** Bearer Token  

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "applicationId": "APP-2026-00123",
    "estimates": [
      {
        "estimateId": "est_abc123",
        "version": 1,
        "estimateType": "PHASE_WISE",
        "phases": [...],
        "totalMaterials": {...},
        "status": "APPROVED",
        "uploadedAt": "2026-01-18T14:00:00Z",
        "approvedAt": "2026-01-18T15:00:00Z"
      }
    ]
  }
}
```

---

## 6. Inspection APIs

### 6.1 Create Inspection Report

**Endpoint:** `POST /inspections`  
**Description:** Create site inspection report  
**Authentication:** Bearer Token (JEN)  

**Request:**
```json
{
  "applicationId": "APP-2026-00123",
  "inspectionType": "SITE_VERIFICATION",
  "inspectionDate": "2026-01-18",
  "findings": {
    "siteExists": true,
    "matchesApplication": true,
    "boundaryMarked": true,
    "noEncroachment": true
  },
  "comments": "Site verified. All details match application. Ready for construction.",
  "recommendation": "APPROVE",
  "layoutApproved": true,
  "layoutComments": "Layout as per approved plan"
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "inspectionId": "insp_xyz123",
    "applicationId": "APP-2026-00123",
    "status": "PENDING_PHOTOS",
    "createdAt": "2026-01-18T14:30:00Z"
  },
  "message": "Inspection report created. Please upload geo-tagged photos."
}
```

---

### 6.2 Upload Inspection Photos

**Endpoint:** `POST /inspections/:inspectionId/photos`  
**Description:** Upload geo-tagged photos for inspection  
**Authentication:** Bearer Token (JEN)  
**Content-Type:** multipart/form-data  

**Request:**
```
POST /inspections/insp_xyz123/photos
Content-Type: multipart/form-data

photos[]: <image_1>
photos[]: <image_2>
metadata: {
  "photos": [
    {
      "index": 0,
      "description": "North boundary view",
      "latitude": 24.5926,
      "longitude": 72.7156,
      "capturedAt": "2026-01-18T14:25:00Z"
    }
  ]
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "inspectionId": "insp_xyz123",
    "photosUploaded": 2,
    "photos": [
      {
        "photoId": "photo_001",
        "url": "https://storage.mountabu.gov.in/inspections/...",
        "description": "North boundary view",
        "geoTag": {
          "latitude": 24.5926,
          "longitude": 72.7156,
          "verified": true,
          "withinBoundary": true
        },
        "capturedAt": "2026-01-18T14:25:00Z"
      }
    ],
    "allPhotosVerified": true
  },
  "message": "Photos uploaded and geo-verified successfully."
}
```

---

## 7. Naka (Checkpoint) APIs

### 7.1 Scan Token

**Endpoint:** `POST /naka/scan`  
**Description:** Scan and validate token at checkpoint  
**Authentication:** Bearer Token (Naka Incharge)  

**Request:**
```json
{
  "tokenQR": "TKN-2026-00123-P1",
  "vehicleNumber": "RJ-14-AB-1234",
  "driverMobile": "9123456789",
  "materialType": "CEMENT",
  "quantity": 20,
  "unit": "bags",
  "nakaLocation": {
    "name": "Main Gate",
    "latitude": 24.5900,
    "longitude": 72.7100
  }
}
```

**Response (200 OK - Valid Token):**
```json
{
  "success": true,
  "data": {
    "valid": true,
    "tokenId": "TKN-2026-00123-P1",
    "entryId": "entry_new001",
    "applicant": {
      "name": "Rajesh Kumar",
      "mobile": "9876543210"
    },
    "propertyAddress": "Plot No. 123, Sector A, Mount Abu",
    "materialAllowed": true,
    "quantityAllowed": true,
    "previousBalance": 150,
    "enteredQuantity": 20,
    "newBalance": 130,
    "status": "ENTRY_LOGGED",
    "requiresPhoto": true
  },
  "message": "Token valid. Entry logged. Please upload photos."
}
```

**Response (400 Bad Request - Invalid Token):**
```json
{
  "success": false,
  "error": {
    "code": "TOKEN_INVALID",
    "reason": "EXHAUSTED",
    "message": "Token material quota exhausted. Remaining cement: 0 bags",
    "tokenId": "TKN-2026-00123-P1",
    "applicant": {
      "name": "Rajesh Kumar",
      "mobile": "9876543210"
    }
  }
}
```

---

### 7.2 Upload Entry Photos

**Endpoint:** `POST /naka/entries/:entryId/photos`  
**Description:** Upload geo-tagged photos for entry  
**Authentication:** Bearer Token (Naka Incharge)  
**Content-Type:** multipart/form-data  

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "entryId": "entry_new001",
    "photosUploaded": 2,
    "entryCompleted": true
  },
  "message": "Entry completed with photos."
}
```

---

### 7.3 List Vehicle Entries

**Endpoint:** `GET /naka/entries`  
**Description:** Get list of vehicle entries  
**Authentication:** Bearer Token (Authority)  
**Query Parameters:**
- `dateFrom`: ISO date
- `dateTo`: ISO date
- `vehicleNumber`: Filter by vehicle
- `tokenId`: Filter by token
- `nakaLocation`: Filter by naka
- `page`: Page number
- `limit`: Items per page

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "entries": [
      {
        "entryId": "entry_001",
        "tokenId": "TKN-2026-00123-P1",
        "applicant": "Rajesh Kumar",
        "vehicleNumber": "RJ-14-AB-1234",
        "driverMobile": "9123456789",
        "material": "CEMENT",
        "quantity": 20,
        "unit": "bags",
        "nakaLocation": "Main Gate",
        "entryTime": "2026-01-18T10:30:00Z",
        "verifiedBy": "Naka Incharge 1",
        "hasPhotos": true
      }
    ],
    "pagination": {...},
    "summary": {
      "totalEntries": 45,
      "totalVehicles": 30,
      "materialsSummary": {
        "CEMENT": {"quantity": 500, "unit": "bags"},
        "SAND": {"quantity": 25, "unit": "truckloads"}
      }
    }
  }
}
```

---

## 8. Blacklist Management APIs

### 8.1 List Blacklisted Users

**Endpoint:** `GET /blacklist`  
**Description:** Get list of blacklisted users  
**Authentication:** Bearer Token (SDM/CMS)  
**Query Parameters:**
- `status`: BLACKLISTED | WHITELISTED
- `dateFrom`: Blacklisted from date
- `dateTo`: Blacklisted to date
- `page`: Page number
- `limit`: Items per page

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "users": [
      {
        "userId": "usr_blacklisted001",
        "name": "Suspicious User",
        "mobile": "9999999999",
        "blacklistedAt": "2026-01-10T10:00:00Z",
        "consecutiveRejections": 3,
        "totalRejections": 5,
        "lastRejectionReason": "Fraudulent documents submitted",
        "rejectionHistory": [
          {
            "applicationId": "APP-2025-00555",
            "rejectedAt": "2026-01-08T14:00:00Z",
            "reason": "Invalid ownership"
          },
          {
            "applicationId": "APP-2025-00556",
            "rejectedAt": "2026-01-09T11:00:00Z",
            "reason": "Tampered documents"
          },
          {
            "applicationId": "APP-2025-00557",
            "rejectedAt": "2026-01-10T10:00:00Z",
            "reason": "Fraudulent documents"
          }
        ]
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 12,
      "totalPages": 1
    },
    "summary": {
      "totalBlacklisted": 12,
      "blacklistedThisMonth": 3,
      "whitelistedThisMonth": 2
    }
  }
}
```

---

### 8.2 Get User Rejection History

**Endpoint:** `GET /blacklist/:userId/history`  
**Description:** Get detailed rejection history for user  
**Authentication:** Bearer Token (Authority)  

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "userId": "usr_abc123",
    "name": "Rajesh Kumar",
    "mobile": "9876543210",
    "currentStatus": {
      "isBlacklisted": false,
      "consecutiveRejections": 1,
      "totalRejections": 2,
      "totalApprovals": 3
    },
    "warningLevel": "LOW",
    "rejectionHistory": [
      {
        "applicationId": "APP-2025-00100",
        "applicationType": "NEW_CONSTRUCTION",
        "submittedAt": "2025-06-15T10:00:00Z",
        "rejectedAt": "2025-06-20T14:00:00Z",
        "rejectedBy": {
          "name": "Land Officer",
          "role": "LAND"
        },
        "reason": "DOCUMENT_ISSUE",
        "comments": "Ownership deed not clear",
        "wasConsecutive": false
      },
      {
        "applicationId": "APP-2026-00050",
        "applicationType": "RENOVATION",
        "submittedAt": "2026-01-10T10:00:00Z",
        "rejectedAt": "2026-01-15T11:00:00Z",
        "rejectedBy": {
          "name": "Legal Officer",
          "role": "LEGAL"
        },
        "reason": "INCOMPLETE",
        "comments": "NOC missing",
        "wasConsecutive": true
      }
    ],
    "approvalHistory": [
      {
        "applicationId": "APP-2025-00200",
        "approvedAt": "2025-08-10T16:00:00Z"
      }
    ],
    "blacklistHistory": []
  }
}
```

---

### 8.3 Whitelist User

**Endpoint:** `POST /blacklist/:userId/whitelist`  
**Description:** Remove user from blacklist  
**Authentication:** Bearer Token (SDM/CMS only)  

**Request:**
```json
{
  "reason": "User visited office and provided valid original documents. Identity verified in person.",
  "verificationMethod": "IN_PERSON",
  "supportingDocuments": ["doc_verification001"],
  "conditions": [
    "Must submit original documents for next 3 applications",
    "Subject to additional verification"
  ]
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "userId": "usr_blacklisted001",
    "previousStatus": "BLACKLISTED",
    "newStatus": "ACTIVE",
    "whitelistedAt": "2026-01-18T15:00:00Z",
    "whitelistedBy": {
      "id": "auth_xyz789",
      "name": "Dr. Sharma",
      "role": "SDM"
    },
    "conditions": [
      "Must submit original documents for next 3 applications",
      "Subject to additional verification"
    ],
    "consecutiveRejectionsReset": true
  },
  "message": "User whitelisted successfully. SMS notification sent to user."
}
```

---

### 8.4 Manually Blacklist User

**Endpoint:** `POST /blacklist/:userId`  
**Description:** Manually blacklist a user (admin action)  
**Authentication:** Bearer Token (SDM only)  

**Request:**
```json
{
  "reason": "User found to be submitting fraudulent applications on behalf of others",
  "category": "FRAUD",
  "evidence": ["doc_evidence001", "doc_evidence002"],
  "permanent": false
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "userId": "usr_fraud001",
    "status": "BLACKLISTED",
    "blacklistedAt": "2026-01-18T16:00:00Z",
    "blacklistedBy": {
      "id": "auth_xyz789",
      "name": "Dr. Sharma",
      "role": "SDM"
    },
    "reason": "User found to be submitting fraudulent applications on behalf of others",
    "category": "FRAUD",
    "permanent": false,
    "activeTokensCancelled": 2
  },
  "message": "User blacklisted. All active tokens cancelled. User notified."
}
```

---

## 9. Report APIs

### 9.1 Application Reports

**Endpoint:** `GET /reports/applications`  
**Description:** Generate application reports  
**Authentication:** Bearer Token (Authority)  
**Query Parameters:**
- `dateFrom`: Report start date
- `dateTo`: Report end date
- `groupBy`: DAY | WEEK | MONTH
- `type`: NEW_CONSTRUCTION | RENOVATION | ALL
- `zone`: Filter by zone
- `status`: Filter by status

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "reportPeriod": {
      "from": "2026-01-01",
      "to": "2026-01-18"
    },
    "summary": {
      "totalApplications": 156,
      "approved": 89,
      "rejected": 23,
      "pending": 44,
      "approvalRate": 79.46,
      "avgProcessingDays": 4.2
    },
    "byType": {
      "NEW_CONSTRUCTION": 98,
      "RENOVATION": 58
    },
    "trend": [
      {"date": "2026-01-01", "submitted": 12, "approved": 8, "rejected": 2},
      {"date": "2026-01-02", "submitted": 15, "approved": 10, "rejected": 1}
    ]
  }
}
```

---

### 9.2 Token Usage Reports

**Endpoint:** `GET /reports/tokens`  
**Description:** Generate token usage reports  
**Authentication:** Bearer Token (Authority)  

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "reportPeriod": {
      "from": "2026-01-01",
      "to": "2026-01-18"
    },
    "summary": {
      "tokensIssued": 234,
      "tokensActive": 145,
      "tokensExhausted": 67,
      "tokensExpired": 22,
      "totalUsageEvents": 1247
    },
    "materialsSummary": [
      {
        "material": "CEMENT",
        "totalApproved": 50000,
        "totalConsumed": 32500,
        "utilizationRate": 65
      },
      {
        "material": "SAND",
        "totalApproved": 2500,
        "totalConsumed": 1800,
        "utilizationRate": 72
      }
    ]
  }
}
```

---

### 9.3 Export Report

**Endpoint:** `POST /reports/export`  
**Description:** Export report in PDF/CSV format  
**Authentication:** Bearer Token (Authority)  

**Request:**
```json
{
  "reportType": "APPLICATIONS",
  "format": "PDF",
  "dateFrom": "2026-01-01",
  "dateTo": "2026-01-18",
  "filters": {
    "type": "ALL",
    "zone": "ALL",
    "status": "ALL"
  }
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "reportId": "rpt_xyz123",
    "status": "GENERATING",
    "estimatedTime": 30,
    "downloadUrl": null
  },
  "message": "Report generation started. You will be notified when ready."
}
```

---

## 10. Notification APIs

### 10.1 List Notifications

**Endpoint:** `GET /notifications`  
**Description:** Get user notifications  
**Authentication:** Bearer Token  
**Query Parameters:**
- `read`: true | false | all
- `type`: APPLICATION | TOKEN | SYSTEM
- `page`: Page number
- `limit`: Items per page

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "notifications": [
      {
        "id": "notif_001",
        "type": "APPLICATION",
        "title": "Application Approved",
        "message": "Your application APP-2026-00123 has been approved. E-Tokens generated.",
        "read": false,
        "actionUrl": "/applications/APP-2026-00123",
        "createdAt": "2026-01-18T16:00:00Z"
      }
    ],
    "unreadCount": 5,
    "pagination": {...}
  }
}
```

---

### 10.2 Mark as Read

**Endpoint:** `PUT /notifications/:notificationId/read`  
**Description:** Mark notification as read  
**Authentication:** Bearer Token  

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Notification marked as read"
}
```

---

## 11. Content Management APIs

### 11.1 List Pages

**Endpoint:** `GET /content/pages`  
**Description:** Get website pages for CMS  
**Authentication:** Bearer Token (Admin)  

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "pages": [
      {
        "id": "page_home",
        "slug": "home",
        "title": {
          "en": "Welcome to Mount Abu",
          "hi": "माउंट आबू में आपका स्वागत है"
        },
        "status": "PUBLISHED",
        "lastUpdated": "2026-01-15T10:00:00Z"
      }
    ]
  }
}
```

---

### 11.2 Update Page

**Endpoint:** `PUT /content/pages/:pageId`  
**Description:** Update page content  
**Authentication:** Bearer Token (Admin)  

**Request:**
```json
{
  "title": {
    "en": "Welcome to Mount Abu Municipal Council",
    "hi": "माउंट आबू नगर परिषद में आपका स्वागत है"
  },
  "content": {
    "en": "<p>Mount Abu is...</p>",
    "hi": "<p>माउंट आबू है...</p>"
  },
  "status": "PUBLISHED"
}
```

---

## 12. Analytics APIs

### 12.1 Dashboard Overview

**Endpoint:** `GET /analytics/overview`  
**Description:** Get dashboard analytics overview  
**Authentication:** Bearer Token (Authority)  

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "applications": {
      "pending": 127,
      "approvedToday": 15,
      "rejectedToday": 3
    },
    "tokens": {
      "active": 453,
      "issuedToday": 23
    },
    "vehicleEntries": {
      "today": 47,
      "thisWeek": 312
    },
    "materials": {
      "cementToday": {"quantity": 500, "unit": "bags"},
      "sandToday": {"quantity": 25, "unit": "truckloads"}
    },
    "performance": {
      "avgProcessingDays": 3.8,
      "slaCompliance": 92.5
    },
    "blacklist": {
      "currentlyBlacklisted": 12,
      "whitelistedThisMonth": 3
    }
  }
}
```

---

## 13. Error Codes

### Standard Error Response Format

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": {},
    "timestamp": "2026-01-18T12:00:00Z",
    "requestId": "req_abc123"
  }
}
```

### Error Code Reference

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `AUTH_INVALID_CREDENTIALS` | 401 | Invalid login credentials |
| `AUTH_OTP_EXPIRED` | 401 | OTP has expired |
| `AUTH_OTP_INVALID` | 401 | Invalid OTP |
| `AUTH_TOKEN_EXPIRED` | 401 | JWT token expired |
| `AUTH_TOKEN_INVALID` | 401 | Invalid JWT token |
| `AUTH_AADHAAR_FAILED` | 400 | Aadhaar verification failed |
| `USER_BLACKLISTED` | 403 | User is blacklisted |
| `USER_NOT_FOUND` | 404 | User not found |
| `ACCESS_DENIED` | 403 | Insufficient permissions |
| `APPLICATION_NOT_FOUND` | 404 | Application not found |
| `APPLICATION_INVALID_STATE` | 400 | Invalid state transition |
| `TOKEN_NOT_FOUND` | 404 | Token not found |
| `TOKEN_EXPIRED` | 400 | Token has expired |
| `TOKEN_EXHAUSTED` | 400 | Token quota exhausted |
| `TOKEN_INVALID` | 400 | Invalid token |
| `DOCUMENT_UPLOAD_FAILED` | 500 | Document upload failed |
| `DOCUMENT_INVALID_TYPE` | 400 | Invalid document type |
| `ESTIMATE_PARSE_FAILED` | 400 | Excel parsing failed |
| `GEOTAG_INVALID` | 400 | Invalid geolocation data |
| `GEOTAG_OUT_OF_BOUNDS` | 400 | Location outside allowed area |
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `SERVER_ERROR` | 500 | Internal server error |

---

## Appendix: Rate Limits

| Endpoint Category | Rate Limit |
|------------------|------------|
| Authentication | 10 requests/minute |
| General API | 100 requests/minute |
| Document Upload | 20 requests/minute |
| Report Export | 5 requests/hour |
| QR Generation | 50 requests/minute |

---

*API Specification for Mount Abu E-Token Management System v1.0*
