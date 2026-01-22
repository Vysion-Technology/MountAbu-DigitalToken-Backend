# Database Schema Documentation
## Mount Abu E-Token Management System
### PostgreSQL Database Design

---

**Database:** PostgreSQL 15+  
**Schema Version:** 1.0  
**Character Set:** UTF-8  

---

## Table of Contents
1. [Schema Overview](#1-schema-overview)
2. [Core Tables](#2-core-tables)
3. [Application Tables](#3-application-tables)
4. [Token Tables](#4-token-tables)
5. [Blacklist & Audit Tables](#5-blacklist--audit-tables)
6. [Content Management Tables](#6-content-management-tables)
7. [Indexes & Performance](#7-indexes--performance)
8. [Sample Queries](#8-sample-queries)

---

## 1. Schema Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DATABASE SCHEMA OVERVIEW                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  CORE TABLES          APPLICATION TABLES       TOKEN TABLES             │
│  ├── users            ├── applications         ├── tokens               │
│  ├── authorities      ├── documents            ├── token_usage          │
│  ├── roles            ├── estimates            ├── token_shares         │
│  ├── permissions      ├── estimate_phases      └── vehicle_entries      │
│  └── sessions         ├── inspections                                   │
│                       └── inspection_photos    BLACKLIST TABLES         │
│                                                ├── blacklist_status     │
│  CONTENT TABLES       NOTIFICATION TABLES      ├── rejection_history    │
│  ├── pages            ├── notifications        └── blacklist_audit      │
│  ├── notices          └── sms_logs                                      │
│  └── tenders                                   AUDIT TABLES             │
│                                                ├── audit_logs           │
│                                                └── activity_logs        │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Tables

### 2.1 users

Stores all user information (applicants and authorities).

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Basic Information
    user_type VARCHAR(20) NOT NULL CHECK (user_type IN ('APPLICANT', 'AUTHORITY')),
    name VARCHAR(255) NOT NULL,
    mobile VARCHAR(15) UNIQUE,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255), -- Only for authorities
    
    -- Aadhaar (for applicants)
    aadhaar_number_encrypted VARCHAR(500),
    aadhaar_verified BOOLEAN DEFAULT FALSE,
    aadhaar_verified_at TIMESTAMP,
    aadhaar_name VARCHAR(255),
    
    -- Address
    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100) DEFAULT 'Rajasthan',
    pincode VARCHAR(10),
    
    -- Authority-specific fields
    role_id UUID REFERENCES roles(id),
    department VARCHAR(100),
    designation VARCHAR(100),
    
    -- Status
    status VARCHAR(20) DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'INACTIVE', 'SUSPENDED')),
    email_verified BOOLEAN DEFAULT FALSE,
    mobile_verified BOOLEAN DEFAULT FALSE,
    
    -- Language preference
    preferred_language VARCHAR(5) DEFAULT 'en' CHECK (preferred_language IN ('en', 'hi')),
    
    -- Metadata
    last_login_at TIMESTAMP,
    login_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id),
    
    -- Soft delete
    deleted_at TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE
);

-- Partial unique index for non-deleted users
CREATE UNIQUE INDEX idx_users_mobile_unique ON users(mobile) WHERE is_deleted = FALSE;
CREATE UNIQUE INDEX idx_users_email_unique ON users(email) WHERE is_deleted = FALSE;
```

### 2.2 roles

Role definitions for authorities.

```sql
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    name VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    hierarchy_level INTEGER NOT NULL, -- Lower = higher authority
    
    -- Workflow settings
    can_approve BOOLEAN DEFAULT FALSE,
    can_reject BOOLEAN DEFAULT FALSE,
    can_forward BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed data
INSERT INTO roles (name, display_name, hierarchy_level, can_approve, can_reject, can_forward) VALUES
('SDM', 'Sub-Divisional Magistrate', 1, TRUE, TRUE, TRUE),
('CMS_UIT', 'Commissioner (UIT)', 2, TRUE, TRUE, TRUE),
('CMS_ULB', 'Commissioner (ULB)', 2, TRUE, TRUE, TRUE),
('JEN', 'Junior Engineer', 3, FALSE, FALSE, TRUE),
('LAND', 'Land Department Officer', 4, FALSE, TRUE, TRUE),
('LEGAL', 'Legal Department Officer', 4, FALSE, TRUE, TRUE),
('ATP', 'Assistant Town Planner', 4, FALSE, TRUE, TRUE),
('NAKA', 'Naka Incharge', 5, FALSE, FALSE, FALSE);
```

### 2.3 permissions

Granular permissions for role-based access.

```sql
CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    category VARCHAR(50), -- APPLICATION, TOKEN, USER, CONTENT, REPORT
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE role_permissions (
    role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID REFERENCES permissions(id) ON DELETE CASCADE,
    
    PRIMARY KEY (role_id, permission_id)
);

-- Seed permissions
INSERT INTO permissions (name, category, description) VALUES
('VIEW_APPLICATIONS', 'APPLICATION', 'View application list and details'),
('CREATE_APPLICATION', 'APPLICATION', 'Create new applications'),
('APPROVE_APPLICATION', 'APPLICATION', 'Approve applications'),
('REJECT_APPLICATION', 'APPLICATION', 'Reject applications'),
('FORWARD_APPLICATION', 'APPLICATION', 'Forward to next authority'),
('UPLOAD_INSPECTION', 'APPLICATION', 'Upload inspection reports'),
('APPROVE_LAYOUT', 'APPLICATION', 'Approve construction layouts'),
('VIEW_TOKENS', 'TOKEN', 'View tokens'),
('GENERATE_TOKENS', 'TOKEN', 'Generate e-tokens'),
('SCAN_TOKENS', 'TOKEN', 'Scan tokens at naka'),
('MANAGE_USERS', 'USER', 'Create/update authority users'),
('VIEW_BLACKLIST', 'USER', 'View blacklisted users'),
('WHITELIST_USER', 'USER', 'Whitelist blacklisted users'),
('MANAGE_CONTENT', 'CONTENT', 'Manage website content'),
('VIEW_REPORTS', 'REPORT', 'View reports'),
('EXPORT_REPORTS', 'REPORT', 'Export reports');
```

### 2.4 sessions

User session management.

```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Token info
    access_token_hash VARCHAR(255) NOT NULL,
    refresh_token_hash VARCHAR(255) NOT NULL,
    
    -- Session details
    device_info JSONB,
    ip_address INET,
    user_agent TEXT,
    
    -- Expiry
    access_token_expires_at TIMESTAMP NOT NULL,
    refresh_token_expires_at TIMESTAMP NOT NULL,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    revoked_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_active ON sessions(is_active, access_token_expires_at);
```

---

## 3. Application Tables

### 3.1 applications

Main application table.

```sql
CREATE TABLE applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Application reference
    application_number VARCHAR(50) NOT NULL UNIQUE, -- Format: APP-YYYY-NNNNN
    
    -- Type and zone
    application_type VARCHAR(30) NOT NULL CHECK (application_type IN ('NEW_CONSTRUCTION', 'RENOVATION')),
    zone VARCHAR(30) NOT NULL CHECK (zone IN ('UIT_DENSE', 'UIT_SCATTERED', 'ULB_DENSE', 'ULB_SCATTERED')),
    
    -- Applicant
    applicant_id UUID NOT NULL REFERENCES users(id),
    
    -- Property details (JSONB for flexibility)
    property_details JSONB NOT NULL,
    /*
    {
        "plotNumber": "P-123/A",
        "khasraNumber": "456/7",
        "area": 250.5,
        "areaUnit": "SQ_METERS",
        "address": {
            "line1": "...",
            "line2": "...",
            "city": "Mount Abu",
            "state": "Rajasthan",
            "pincode": "307501"
        },
        "coordinates": {
            "latitude": 24.5926,
            "longitude": 72.7156
        },
        "ownerDetails": {
            "name": "...",
            "fatherName": "...",
            "aadhaarMasked": "XXXX-XXXX-9012"
        }
    }
    */
    
    -- Construction details
    construction_details JSONB NOT NULL,
    /*
    {
        "purpose": "RESIDENTIAL",
        "floors": 2,
        "builtUpArea": 180.0,
        "estimatedCost": 2500000,
        "startDate": "2026-02-01",
        "endDate": "2026-08-31"
    }
    */
    
    -- Status workflow
    status VARCHAR(30) NOT NULL DEFAULT 'SUBMITTED',
    current_authority_role VARCHAR(30),
    current_authority_id UUID REFERENCES users(id),
    
    -- Processing
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_action_at TIMESTAMP,
    approved_at TIMESTAMP,
    rejected_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- Approval details
    approved_by UUID REFERENCES users(id),
    rejection_reason TEXT,
    rejection_category VARCHAR(50),
    approval_conditions JSONB, -- Array of conditions
    
    -- Permission document
    permission_document_url TEXT,
    permission_generated_at TIMESTAMP,
    
    -- Terms
    terms_accepted BOOLEAN DEFAULT FALSE,
    terms_accepted_at TIMESTAMP,
    declaration_accepted BOOLEAN DEFAULT FALSE,
    
    -- SLA tracking
    sla_deadline TIMESTAMP,
    sla_status VARCHAR(20) DEFAULT 'ON_TRACK',
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Soft delete
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMP
);

-- Status enum values
-- SUBMITTED, SDM_REVIEW, CMS_REVIEW, LAND_VERIFICATION, LEGAL_VERIFICATION, 
-- ATP_VERIFICATION, JEN_INSPECTION, PENDING_ESTIMATE, APPROVED, REJECTED, 
-- TOKENS_ISSUED, IN_PROGRESS, COMPLETED, CANCELLED

CREATE INDEX idx_applications_applicant ON applications(applicant_id);
CREATE INDEX idx_applications_status ON applications(status);
CREATE INDEX idx_applications_current_authority ON applications(current_authority_id);
CREATE INDEX idx_applications_zone ON applications(zone);
CREATE INDEX idx_applications_type ON applications(application_type);
CREATE INDEX idx_applications_submitted_at ON applications(submitted_at);
CREATE INDEX idx_applications_number ON applications(application_number);
```

### 3.2 application_timeline

Workflow timeline for each application.

```sql
CREATE TABLE application_timeline (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    application_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    
    -- Event details
    status VARCHAR(30) NOT NULL,
    action VARCHAR(50) NOT NULL, -- SUBMITTED, FORWARDED, APPROVED, REJECTED, etc.
    
    -- Actor
    actor_id UUID REFERENCES users(id),
    actor_name VARCHAR(255),
    actor_role VARCHAR(50),
    
    -- Details
    comments TEXT,
    metadata JSONB, -- Additional action-specific data
    
    -- Timing
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    time_in_status INTERVAL -- Time spent in previous status
);

CREATE INDEX idx_timeline_application ON application_timeline(application_id);
CREATE INDEX idx_timeline_timestamp ON application_timeline(timestamp);
```

### 3.3 documents

Uploaded documents for applications.

```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    application_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    
    -- Document info
    document_type VARCHAR(50) NOT NULL,
    -- OWNERSHIP_DEED, SITE_MAP, NOC, ID_PROOF, ESTIMATE, PERMISSION_LETTER, etc.
    
    original_name VARCHAR(255) NOT NULL,
    stored_name VARCHAR(255) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    size_bytes BIGINT NOT NULL,
    
    -- Storage
    storage_path TEXT NOT NULL,
    public_url TEXT,
    
    -- Verification
    verified BOOLEAN DEFAULT FALSE,
    verified_by UUID REFERENCES users(id),
    verified_at TIMESTAMP,
    verification_comments TEXT,
    
    -- Upload info
    uploaded_by UUID NOT NULL REFERENCES users(id),
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Soft delete
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMP
);

CREATE INDEX idx_documents_application ON documents(application_id);
CREATE INDEX idx_documents_type ON documents(document_type);
```

### 3.4 estimates

Material estimates for applications.

```sql
CREATE TABLE estimates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    application_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    
    -- Estimate type
    estimate_type VARCHAR(30) NOT NULL CHECK (estimate_type IN ('PHASE_WISE', 'ONE_TIME')),
    version INTEGER DEFAULT 1,
    
    -- Source file
    source_file_url TEXT,
    source_file_name VARCHAR(255),
    
    -- Total materials (denormalized for quick access)
    total_materials JSONB,
    /*
    {
        "CEMENT": {"quantity": 500, "unit": "bags"},
        "SAND": {"quantity": 50, "unit": "truckloads"}
    }
    */
    
    -- Status
    status VARCHAR(20) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED')),
    approved_by UUID REFERENCES users(id),
    approved_at TIMESTAMP,
    
    -- Upload info
    uploaded_by UUID NOT NULL REFERENCES users(id),
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_estimates_application ON estimates(application_id);
```

### 3.5 estimate_phases

Phase-wise breakdown of estimates.

```sql
CREATE TABLE estimate_phases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    estimate_id UUID NOT NULL REFERENCES estimates(id) ON DELETE CASCADE,
    
    -- Phase info
    phase_number INTEGER NOT NULL,
    phase_name VARCHAR(100),
    
    -- Materials for this phase
    materials JSONB NOT NULL,
    /*
    [
        {"material": "CEMENT", "quantity": 200, "unit": "bags"},
        {"material": "SAND", "quantity": 20, "unit": "truckloads"}
    ]
    */
    
    -- Status
    status VARCHAR(20) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED')),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(estimate_id, phase_number)
);

CREATE INDEX idx_estimate_phases_estimate ON estimate_phases(estimate_id);
```

### 3.6 inspections

Site inspection records.

```sql
CREATE TABLE inspections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    application_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    
    -- Inspection type
    inspection_type VARCHAR(50) NOT NULL,
    -- SITE_VERIFICATION, PROGRESS_CHECK, COMPLETION_CHECK
    
    -- Inspector
    inspector_id UUID NOT NULL REFERENCES users(id),
    
    -- Inspection details
    inspection_date DATE NOT NULL,
    
    -- Findings (flexible JSONB)
    findings JSONB,
    /*
    {
        "siteExists": true,
        "matchesApplication": true,
        "boundaryMarked": true,
        "noEncroachment": true
    }
    */
    
    -- Recommendation
    recommendation VARCHAR(20), -- APPROVE, REJECT, PENDING
    comments TEXT,
    
    -- Layout approval (for JEN)
    layout_approved BOOLEAN,
    layout_comments TEXT,
    
    -- Status
    status VARCHAR(20) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'COMPLETED', 'PHOTOS_PENDING')),
    
    -- Location verification
    inspection_location JSONB,
    /*
    {
        "latitude": 24.5926,
        "longitude": 72.7156,
        "accuracy": 10
    }
    */
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_inspections_application ON inspections(application_id);
CREATE INDEX idx_inspections_inspector ON inspections(inspector_id);
```

### 3.7 inspection_photos

Geo-tagged photos from inspections.

```sql
CREATE TABLE inspection_photos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    inspection_id UUID NOT NULL REFERENCES inspections(id) ON DELETE CASCADE,
    
    -- Photo info
    description TEXT,
    storage_path TEXT NOT NULL,
    public_url TEXT NOT NULL,
    mime_type VARCHAR(50) NOT NULL,
    size_bytes BIGINT NOT NULL,
    
    -- Geo-tag
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    altitude DECIMAL(10, 2),
    accuracy DECIMAL(10, 2),
    
    -- Verification
    geo_verified BOOLEAN DEFAULT FALSE,
    within_property_bounds BOOLEAN,
    
    -- Capture info
    captured_at TIMESTAMP NOT NULL,
    device_info JSONB,
    
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_inspection_photos_inspection ON inspection_photos(inspection_id);
CREATE INDEX idx_inspection_photos_location ON inspection_photos USING GIST (
    ll_to_earth(latitude, longitude)
);
```

---

## 4. Token Tables

### 4.1 tokens

E-Token records.

```sql
CREATE TABLE tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Token reference
    token_number VARCHAR(50) NOT NULL UNIQUE, -- Format: TKN-YYYY-NNNNN-PN
    
    -- Linked entities
    application_id UUID NOT NULL REFERENCES applications(id),
    estimate_phase_id UUID REFERENCES estimate_phases(id),
    
    -- Phase info
    phase_number INTEGER NOT NULL,
    phase_name VARCHAR(100),
    
    -- Materials allocated
    materials JSONB NOT NULL,
    /*
    [
        {
            "materialType": "CEMENT",
            "materialName": "Cement (50kg bags)",
            "approvedQuantity": 200,
            "consumedQuantity": 50,
            "remainingQuantity": 150,
            "unit": "bags"
        }
    ]
    */
    
    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    -- PENDING, ACTIVE, EXHAUSTED, EXPIRED, CANCELLED
    
    -- Validity
    valid_from TIMESTAMP NOT NULL,
    valid_until TIMESTAMP NOT NULL,
    
    -- QR code
    qr_code_data TEXT NOT NULL, -- Encoded QR data
    qr_code_url TEXT,
    
    -- Usage tracking
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP,
    
    -- Generation info
    generated_by UUID NOT NULL REFERENCES users(id),
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Cancellation
    cancelled_at TIMESTAMP,
    cancelled_by UUID REFERENCES users(id),
    cancellation_reason TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tokens_application ON tokens(application_id);
CREATE INDEX idx_tokens_status ON tokens(status);
CREATE INDEX idx_tokens_valid ON tokens(valid_from, valid_until);
CREATE INDEX idx_tokens_number ON tokens(token_number);
```

### 4.2 token_shares

Token sharing with drivers.

```sql
CREATE TABLE token_shares (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    token_id UUID NOT NULL REFERENCES tokens(id) ON DELETE CASCADE,
    
    -- Shared by (applicant)
    shared_by UUID NOT NULL REFERENCES users(id),
    
    -- Driver details
    driver_name VARCHAR(255) NOT NULL,
    driver_mobile VARCHAR(15) NOT NULL,
    vehicle_number VARCHAR(20) NOT NULL,
    
    -- Share link
    share_code VARCHAR(50) NOT NULL UNIQUE,
    share_link TEXT NOT NULL,
    
    -- Material limits for this share
    material_limits JSONB,
    /*
    {
        "CEMENT": 50,
        "SAND": 5
    }
    */
    
    -- Validity
    valid_until TIMESTAMP NOT NULL,
    
    -- Status
    status VARCHAR(20) DEFAULT 'ACTIVE',
    used BOOLEAN DEFAULT FALSE,
    used_at TIMESTAMP,
    
    -- Notification
    sms_sent BOOLEAN DEFAULT FALSE,
    whatsapp_sent BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_token_shares_token ON token_shares(token_id);
CREATE INDEX idx_token_shares_driver ON token_shares(driver_mobile);
CREATE INDEX idx_token_shares_code ON token_shares(share_code);
```

### 4.3 vehicle_entries

Vehicle entry logs at naka points.

```sql
CREATE TABLE vehicle_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Token used
    token_id UUID NOT NULL REFERENCES tokens(id),
    token_share_id UUID REFERENCES token_shares(id),
    
    -- Vehicle details
    vehicle_number VARCHAR(20) NOT NULL,
    driver_name VARCHAR(255),
    driver_mobile VARCHAR(15),
    
    -- Material details
    material_type VARCHAR(50) NOT NULL,
    material_name VARCHAR(100),
    quantity DECIMAL(10, 2) NOT NULL,
    unit VARCHAR(20) NOT NULL,
    
    -- Naka details
    naka_location VARCHAR(100) NOT NULL,
    naka_coordinates JSONB,
    /*
    {
        "latitude": 24.5900,
        "longitude": 72.7100
    }
    */
    
    -- Verification
    verified_by UUID NOT NULL REFERENCES users(id),
    verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Photos
    photos JSONB, -- Array of photo URLs with geo-tags
    
    -- Auto-fetched data
    auto_fetched JSONB,
    /*
    {
        "vehicleFromOCR": "RJ-14-AB-1234",
        "timestampFromDevice": "...",
        "locationFromDevice": {...}
    }
    */
    
    -- Status
    entry_status VARCHAR(20) DEFAULT 'COMPLETED',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_vehicle_entries_token ON vehicle_entries(token_id);
CREATE INDEX idx_vehicle_entries_vehicle ON vehicle_entries(vehicle_number);
CREATE INDEX idx_vehicle_entries_date ON vehicle_entries(created_at);
CREATE INDEX idx_vehicle_entries_naka ON vehicle_entries(naka_location);
CREATE INDEX idx_vehicle_entries_material ON vehicle_entries(material_type);
```

### 4.4 token_usage_summary

Aggregated token usage (materialized view for performance).

```sql
CREATE MATERIALIZED VIEW token_usage_summary AS
SELECT 
    t.id as token_id,
    t.token_number,
    t.application_id,
    t.status,
    t.phase_number,
    
    -- Per material summary
    m.material_type,
    m.approved_quantity,
    COALESCE(SUM(ve.quantity), 0) as consumed_quantity,
    m.approved_quantity - COALESCE(SUM(ve.quantity), 0) as remaining_quantity,
    m.unit,
    
    -- Entry count
    COUNT(ve.id) as entry_count,
    MAX(ve.verified_at) as last_entry_at
    
FROM tokens t
CROSS JOIN LATERAL jsonb_to_recordset(t.materials) 
    AS m(material_type TEXT, approved_quantity DECIMAL, unit TEXT)
LEFT JOIN vehicle_entries ve ON ve.token_id = t.id AND ve.material_type = m.material_type
GROUP BY t.id, t.token_number, t.application_id, t.status, t.phase_number,
         m.material_type, m.approved_quantity, m.unit;

CREATE UNIQUE INDEX idx_token_usage_summary ON token_usage_summary(token_id, material_type);

-- Refresh periodically
-- REFRESH MATERIALIZED VIEW CONCURRENTLY token_usage_summary;
```

---

## 5. Blacklist & Audit Tables

### 5.1 user_blacklist_status

Blacklist status tracking.

```sql
CREATE TABLE user_blacklist_status (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    
    -- Status
    is_blacklisted BOOLEAN DEFAULT FALSE,
    
    -- Rejection counters
    consecutive_rejections INTEGER DEFAULT 0,
    total_rejections INTEGER DEFAULT 0,
    total_approvals INTEGER DEFAULT 0,
    
    -- Blacklist info
    blacklisted_at TIMESTAMP,
    blacklist_reason TEXT,
    blacklist_category VARCHAR(50), -- AUTO_CONSECUTIVE, MANUAL_FRAUD, etc.
    blacklisted_by UUID REFERENCES users(id),
    
    -- Last rejection
    last_rejection_at TIMESTAMP,
    last_rejection_application_id UUID REFERENCES applications(id),
    
    -- Whitelist info
    whitelisted_at TIMESTAMP,
    whitelisted_by UUID REFERENCES users(id),
    whitelist_reason TEXT,
    whitelist_conditions JSONB,
    
    -- Warning tracking
    warning_issued BOOLEAN DEFAULT FALSE,
    warning_issued_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_blacklist_user ON user_blacklist_status(user_id);
CREATE INDEX idx_blacklist_status ON user_blacklist_status(is_blacklisted);
```

### 5.2 application_rejections

Detailed rejection history.

```sql
CREATE TABLE application_rejections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    user_id UUID NOT NULL REFERENCES users(id),
    application_id UUID NOT NULL REFERENCES applications(id),
    
    -- Rejection details
    rejected_by UUID NOT NULL REFERENCES users(id),
    rejected_by_role VARCHAR(50) NOT NULL,
    
    rejection_reason VARCHAR(100) NOT NULL,
    rejection_category VARCHAR(50) NOT NULL,
    -- DOCUMENT_ISSUE, FRAUD, INCOMPLETE, INVALID_DATA, OTHER
    
    authority_comments TEXT,
    
    -- Was this part of consecutive rejections?
    was_consecutive BOOLEAN DEFAULT TRUE,
    consecutive_count INTEGER, -- Count at time of rejection
    
    -- Did this trigger blacklist?
    triggered_blacklist BOOLEAN DEFAULT FALSE,
    
    rejected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_rejections_user ON application_rejections(user_id);
CREATE INDEX idx_rejections_application ON application_rejections(application_id);
CREATE INDEX idx_rejections_date ON application_rejections(rejected_at);
CREATE INDEX idx_rejections_consecutive ON application_rejections(user_id, was_consecutive);
```

### 5.3 blacklist_audit_log

Audit trail for blacklist actions.

```sql
CREATE TABLE blacklist_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    user_id UUID NOT NULL REFERENCES users(id),
    
    -- Action
    action VARCHAR(30) NOT NULL,
    -- AUTO_BLACKLIST, MANUAL_BLACKLIST, WHITELIST, WARNING_ISSUED
    
    -- Actor (NULL for auto actions)
    performed_by UUID REFERENCES users(id),
    performed_by_role VARCHAR(50),
    
    -- Details
    reason TEXT NOT NULL,
    
    -- Metadata
    metadata JSONB,
    /*
    For AUTO_BLACKLIST:
    {
        "triggerApplicationId": "...",
        "consecutiveRejections": 3,
        "rejectionHistory": [...]
    }
    
    For WHITELIST:
    {
        "verificationMethod": "IN_PERSON",
        "conditions": [...],
        "supportingDocuments": [...]
    }
    */
    
    -- Before/After state
    previous_state JSONB,
    new_state JSONB,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_blacklist_audit_user ON blacklist_audit_log(user_id);
CREATE INDEX idx_blacklist_audit_action ON blacklist_audit_log(action);
CREATE INDEX idx_blacklist_audit_date ON blacklist_audit_log(created_at);
```

### 5.4 audit_logs

General audit log for all actions.

```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Actor
    user_id UUID REFERENCES users(id),
    user_name VARCHAR(255),
    user_role VARCHAR(50),
    
    -- Action
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL, -- APPLICATION, TOKEN, USER, etc.
    resource_id UUID,
    
    -- Details
    description TEXT,
    
    -- Request info
    ip_address INET,
    user_agent TEXT,
    request_id UUID,
    
    -- Changes
    old_values JSONB,
    new_values JSONB,
    
    -- Result
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_date ON audit_logs(created_at);

-- Partition by month for performance
-- ALTER TABLE audit_logs PARTITION BY RANGE (created_at);
```

---

## 6. Content Management Tables

### 6.1 pages

Website pages content.

```sql
CREATE TABLE pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    slug VARCHAR(100) NOT NULL UNIQUE,
    
    -- Content (bilingual)
    title_en VARCHAR(255) NOT NULL,
    title_hi VARCHAR(255),
    
    content_en TEXT,
    content_hi TEXT,
    
    meta_description_en TEXT,
    meta_description_hi TEXT,
    
    -- SEO
    meta_keywords VARCHAR(500),
    
    -- Status
    status VARCHAR(20) DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'PUBLISHED', 'ARCHIVED')),
    
    -- Ordering
    sort_order INTEGER DEFAULT 0,
    
    -- Media
    featured_image_url TEXT,
    
    -- Metadata
    published_at TIMESTAMP,
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_pages_slug ON pages(slug);
CREATE INDEX idx_pages_status ON pages(status);
```

### 6.2 notices

Public notices.

```sql
CREATE TABLE notices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    notice_number VARCHAR(50) NOT NULL UNIQUE,
    
    -- Content
    title_en VARCHAR(255) NOT NULL,
    title_hi VARCHAR(255),
    
    content_en TEXT NOT NULL,
    content_hi TEXT,
    
    -- Category
    category VARCHAR(50), -- GENERAL, TENDER, CIRCULAR, etc.
    
    -- Attachment
    attachment_url TEXT,
    attachment_name VARCHAR(255),
    
    -- Validity
    published_at TIMESTAMP,
    valid_until TIMESTAMP,
    
    -- Status
    status VARCHAR(20) DEFAULT 'DRAFT',
    is_important BOOLEAN DEFAULT FALSE,
    
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_notices_status ON notices(status, published_at);
CREATE INDEX idx_notices_category ON notices(category);
CREATE INDEX idx_notices_validity ON notices(valid_until);
```

### 6.3 notifications

User notifications.

```sql
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Notification details
    type VARCHAR(50) NOT NULL, -- APPLICATION, TOKEN, SYSTEM, BLACKLIST
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    
    -- Action
    action_url TEXT,
    action_data JSONB,
    
    -- Status
    read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP,
    
    -- Delivery
    push_sent BOOLEAN DEFAULT FALSE,
    sms_sent BOOLEAN DEFAULT FALSE,
    email_sent BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_notifications_user ON notifications(user_id, read);
CREATE INDEX idx_notifications_created ON notifications(created_at);
```

---

## 7. Indexes & Performance

### 7.1 Performance Indexes

```sql
-- Composite indexes for common queries

-- Applications list for authority
CREATE INDEX idx_app_authority_status 
ON applications(current_authority_id, status, submitted_at DESC);

-- Applicant's applications
CREATE INDEX idx_app_applicant_status 
ON applications(applicant_id, status, submitted_at DESC);

-- Token validation
CREATE INDEX idx_token_validation 
ON tokens(token_number, status, valid_from, valid_until);

-- Vehicle entry reporting
CREATE INDEX idx_vehicle_entries_report 
ON vehicle_entries(created_at, naka_location, material_type);

-- Blacklist check
CREATE INDEX idx_blacklist_active 
ON user_blacklist_status(user_id) WHERE is_blacklisted = TRUE;
```

### 7.2 Partial Indexes

```sql
-- Active applications only
CREATE INDEX idx_active_applications 
ON applications(status, current_authority_id) 
WHERE status NOT IN ('COMPLETED', 'REJECTED', 'CANCELLED');

-- Active tokens only
CREATE INDEX idx_active_tokens 
ON tokens(application_id, status) 
WHERE status IN ('ACTIVE', 'PENDING');

-- Unread notifications
CREATE INDEX idx_unread_notifications 
ON notifications(user_id, created_at) 
WHERE read = FALSE;
```

### 7.3 Full Text Search

```sql
-- Search applications
ALTER TABLE applications ADD COLUMN search_vector tsvector;

CREATE INDEX idx_applications_search ON applications USING GIN(search_vector);

CREATE FUNCTION applications_search_trigger() RETURNS trigger AS $$
BEGIN
    NEW.search_vector := 
        setweight(to_tsvector('english', COALESCE(NEW.application_number, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.property_details->>'plotNumber', '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.property_details->'address'->>'line1', '')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER applications_search_update
    BEFORE INSERT OR UPDATE ON applications
    FOR EACH ROW EXECUTE FUNCTION applications_search_trigger();
```

---

## 8. Sample Queries

### 8.1 Check User Blacklist Status

```sql
-- Before allowing new application
SELECT 
    u.id,
    u.name,
    bs.is_blacklisted,
    bs.consecutive_rejections,
    bs.blacklisted_at,
    bs.blacklist_reason
FROM users u
LEFT JOIN user_blacklist_status bs ON u.id = bs.user_id
WHERE u.id = $1;
```

### 8.2 Auto-Blacklist Trigger Function

```sql
CREATE OR REPLACE FUNCTION process_application_rejection()
RETURNS TRIGGER AS $$
DECLARE
    v_consecutive_rejections INTEGER;
    v_blacklist_threshold INTEGER := 3;
BEGIN
    -- Update or insert blacklist status
    INSERT INTO user_blacklist_status (user_id, consecutive_rejections, total_rejections, last_rejection_at, last_rejection_application_id)
    VALUES (NEW.user_id, 1, 1, NEW.rejected_at, NEW.application_id)
    ON CONFLICT (user_id) DO UPDATE SET
        consecutive_rejections = user_blacklist_status.consecutive_rejections + 1,
        total_rejections = user_blacklist_status.total_rejections + 1,
        last_rejection_at = NEW.rejected_at,
        last_rejection_application_id = NEW.application_id,
        updated_at = CURRENT_TIMESTAMP
    RETURNING consecutive_rejections INTO v_consecutive_rejections;
    
    -- Check if threshold reached
    IF v_consecutive_rejections >= v_blacklist_threshold THEN
        -- Blacklist the user
        UPDATE user_blacklist_status
        SET 
            is_blacklisted = TRUE,
            blacklisted_at = CURRENT_TIMESTAMP,
            blacklist_reason = 'Automatic blacklist: 3 consecutive rejected applications',
            blacklist_category = 'AUTO_CONSECUTIVE'
        WHERE user_id = NEW.user_id;
        
        -- Update rejection record
        UPDATE application_rejections
        SET triggered_blacklist = TRUE
        WHERE id = NEW.id;
        
        -- Create audit log
        INSERT INTO blacklist_audit_log (user_id, action, reason, metadata)
        VALUES (
            NEW.user_id,
            'AUTO_BLACKLIST',
            'Automatic blacklist triggered by 3 consecutive rejected applications',
            jsonb_build_object(
                'triggerApplicationId', NEW.application_id,
                'consecutiveRejections', v_consecutive_rejections,
                'lastRejectionReason', NEW.rejection_reason
            )
        );
        
        -- Create notification for user
        INSERT INTO notifications (user_id, type, title, message, action_url)
        VALUES (
            NEW.user_id,
            'BLACKLIST',
            'Account Blacklisted',
            'Your account has been blacklisted due to 3 consecutive rejected applications. Please visit the SDM office for whitelist request.',
            '/profile/blacklist-status'
        );
    ELSIF v_consecutive_rejections = 2 THEN
        -- Issue warning
        UPDATE user_blacklist_status
        SET warning_issued = TRUE, warning_issued_at = CURRENT_TIMESTAMP
        WHERE user_id = NEW.user_id;
        
        -- Create warning notification
        INSERT INTO notifications (user_id, type, title, message)
        VALUES (
            NEW.user_id,
            'BLACKLIST',
            'Application Rejection Warning',
            'Warning: You have 2 consecutive rejected applications. One more rejection will result in automatic blacklisting.'
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_application_rejection
    AFTER INSERT ON application_rejections
    FOR EACH ROW
    EXECUTE FUNCTION process_application_rejection();
```

### 8.3 Reset Consecutive Rejections on Approval

```sql
CREATE OR REPLACE FUNCTION process_application_approval()
RETURNS TRIGGER AS $$
BEGIN
    -- Reset consecutive rejections on approval
    UPDATE user_blacklist_status
    SET 
        consecutive_rejections = 0,
        total_approvals = total_approvals + 1,
        warning_issued = FALSE,
        updated_at = CURRENT_TIMESTAMP
    WHERE user_id = NEW.applicant_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_application_approval
    AFTER UPDATE OF status ON applications
    FOR EACH ROW
    WHEN (NEW.status = 'APPROVED' AND OLD.status != 'APPROVED')
    EXECUTE FUNCTION process_application_approval();
```

### 8.4 Daily Report Query

```sql
-- Daily entry report
SELECT 
    ve.naka_location,
    ve.material_type,
    COUNT(ve.id) as entry_count,
    SUM(ve.quantity) as total_quantity,
    ve.unit,
    COUNT(DISTINCT ve.vehicle_number) as unique_vehicles,
    COUNT(DISTINCT t.application_id) as unique_applications
FROM vehicle_entries ve
JOIN tokens t ON ve.token_id = t.id
WHERE ve.created_at >= CURRENT_DATE
  AND ve.created_at < CURRENT_DATE + INTERVAL '1 day'
GROUP BY ve.naka_location, ve.material_type, ve.unit
ORDER BY ve.naka_location, total_quantity DESC;
```

### 8.5 Authority Performance Query

```sql
-- Authority processing time
SELECT 
    u.name as authority_name,
    r.display_name as role,
    COUNT(DISTINCT at.application_id) as files_processed,
    AVG(at.time_in_status) as avg_processing_time,
    COUNT(DISTINCT at.application_id) FILTER (WHERE at.action = 'APPROVED') as approvals,
    COUNT(DISTINCT at.application_id) FILTER (WHERE at.action = 'REJECTED') as rejections
FROM application_timeline at
JOIN users u ON at.actor_id = u.id
JOIN roles r ON u.role_id = r.id
WHERE at.timestamp >= CURRENT_DATE - INTERVAL '30 days'
  AND at.actor_role IS NOT NULL
GROUP BY u.id, u.name, r.display_name
ORDER BY files_processed DESC;
```

---

*Database Schema Documentation for Mount Abu E-Token Management System v1.0*
