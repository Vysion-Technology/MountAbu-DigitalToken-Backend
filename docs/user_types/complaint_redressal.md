# Complaint Redressal System

## Overview
A dedicated module for citizens to raise grievances allocated to specific Junior Engineers (J.E.) based on categories.

## Workflow
1.  **Submission**: User submits complaint selecting one of 3-4 specific categories.
2.  **Assignment**: System automatically assigns the complaint to the specifically designated J.E. for that category.
3.  **Resolution**: J.E. inspects/resolves the issue.
4.  **Closing**: J.E. **must** upload a "resolution photo" and comments to close the complaint.

## User Personas & Roles

### 1. Complainant (Citizen)
*   **Action**: Lodge complaint with Category + Description.
*   **Tracking**: View status and resolution photo.

### 2. Junior Engineer (Resolver)
*   **Assignment**: Receives complaints for their assigned categories.
*   **Action**: Resolve issue on ground.
*   **Mandatory Step**: Upload proof (Resolution Photo) to close the ticket.

## Related APIs

### Complaint Management
*   `POST /complaints` - Create a new complaint (Category mandatory)
*   `GET /complaints` - List complaints
*   `GET /complaints/categories` - List 3-4 fixed categories mapped to J.E.s
*   `POST /complaints/:id/resolve` - Resolve complaint (Multipart upload: Photo mandatory)
