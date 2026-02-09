# ChronoCampus — Facility & Reservation Module
### Smart Time-Aware University Infrastructure System

This branch contains the development work for **Member 3**, responsible for implementing the **Facility and Reservation Module** of the ChronoCampus system.

This module manages university infrastructure such as rooms and laboratories and handles the complete reservation workflow, including availability searching, booking management, and conflict detection.

---

## Module Goal
The main objective of this module is to provide a structured and centralized system for managing facilities and reservations within the ChronoCampus platform.

It enables users to search available spaces, create bookings, and ensures scheduling conflicts are prevented through backend validation logic.

---

## Responsibilities (Member 3 Role)

This module handles:

- Room and laboratory management
- Resource availability searching
- Reservation creation and tracking
- Conflict detection and prevention
- Booking validation logic
- Reservation backend APIs
- Integration with user authentication module

---

## Backend File Structure

'''
backend/
│
├── models/
│ └── room.py
│
└── routes/
  └── reservation.py
'''

### File Descriptions

**room.py**
- Defines room and facility data structures
- Stores infrastructure details
- Supports availability tracking

**reservation.py**
- Handles reservation endpoints
- Processes booking requests
- Validates time conflicts
- Manages booking workflows

---

## Branch Information

Branch Name: 
feature-reservation


Purpose:
Development of the Facility and Reservation Module.

---

## Technology Stack

### Backend
- Python
- Flask Framework
- REST API Design
- MVC / Layered Architecture

### Frontend (Integration)
- HTML
- CSS
- JavaScript

### Database
- PostgreSQL (planned integration)

---

## Planned Features

- Facility listing and management
- Availability search functionality
- Reservation creation
- Booking conflict detection
- Reservation tracking
- Backend validation rules

---

## Architecture Approach

This module follows a **Layered / MVC-based architecture**:

- **Models** → Infrastructure and facility data
- **Routes** → Reservation API endpoints
- **Controllers** → Booking logic and validation
- **Database Layer** → Storage of reservations and facilities

---

## System Workflow (High-Level)

1. User requests facility availability
2. System checks database records
3. Available slots are returned
4. User submits reservation request
5. Backend validates conflicts
6. Reservation stored in database

---

## Development Setup

Detailed setup instructions are available in:
docs/setup_guide.md


General Development Steps:

1. Clone the repository
2. Navigate to the backend directory
3. Create a virtual environment
4. Install required dependencies
5. Run the Flask development server

---

## Integration Dependencies

This module depends on:

- User & Authentication Module
- Database Configuration Module
- Frontend Booking Interface

---

## Future Enhancements (Beyond MVP Scope)

- Advanced reservation analytics
- Automated scheduling optimization
- Enhanced reporting features
- Database scaling improvements

---

## ✍️ Author
**S. Simasa**

