# Member 1 — User & Authentication Module  
## ChronoCampus: Smart Time-Aware University Infrastructure System

This branch contains the development work for **Member 1**, responsible for building the **User and Authentication Module** of the ChronoCampus system.

The goal of this module is to provide secure user management, login sessions, and role-based access control for students, staff, and administrators.


##  Responsibilities (Member 1 Role)

This module handles:

- User registration
- Secure login and logout functionality
- University email validation and format verification
- Role detection (Student / Staff / Admin)
- Password security using hashing (bcrypt)
- Session handling using Flask backend framework
- Change-password functionality
- Backend REST API development for frontend integration
- PostgreSQL database intergration

This is the **core security layer** of the ChronoCampus platform.


##  Project Structure

Sara_UserAuthenticationModule/
├── code/
|    ├── backend/ # Flask backend (authentication logic,routes, models)
|    └── frontend/ # HTML/CSS/JS pages for login, register, profile
├── docs/
|   ├── architecture.md # High-level MVC architecture overview
|   ├── api_design.md # REST API structure for authentication
|   └──auth_flow_diagram.md # Authentication workflow explanation 
├── database/
│   └── schema.sql
├── .gitignore
└── README.md


##  Tech Stack

### Backend
- Python
- Flask Framework
- Session-based authentication
- Bcrypt for password hashing
- REST API design

### Frontend
- HTML / CSS / JavaScript (vanilla, no framework)
- UI theme: Dark navy/cyan
- Fonts: Playfair Display, DM Sans
  

### Database
- PostgreSQL


##  Authentication Features (Implemented)

- User registration
- Login / Logout system
- Secure session management
- Role-based authorization via university email pattern detection
- Change-password functionality
- JSON API responses for frontend integration
- Protected routes


##  Architecture Approach

This module follows a **Layered / MVC-based architecture**:

- Models → user data structure
- Routes → authentication endpoints
- Views → frontend login,signup & dashboard pages
- Sessions → manage logged-in users



## General workflow 

1. Clone repository  
2. Navigate to backend folder  
3. Create virtual environment  
4. Install dependencies  
5. Run Flask server


##  Author — N.A.Sara

User & Authentication Module Developer  
ChronoCampus Project — CO2060
