# HPL Inventory Management System

A comprehensive Django-based inventory management system designed for managing stationery and housekeeping items with role-based workflow approval.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Configuration](#configuration)
- [User Roles & Permissions](#user-roles--permissions)
- [Workflow](#workflow)
- [Default Login Credentials](#default-login-credentials)
- [Management Commands](#management-commands)
- [API Endpoints](#api-endpoints)
- [Screenshots](#screenshots)

## Overview

The HPL Inventory Management System is a web-based application built with Django 4.2 that provides complete inventory control for organizations. It handles the complete lifecycle of inventory items from procurement to issuance, with a robust requisition workflow that involves multiple levels of approval.

The system is designed to manage two primary categories of inventory items: stationery items (such as paper, pens, notebooks, and other office supplies) and housekeeping items (such as cleaning supplies, maintenance materials, and other facility-related inventory). Each item is tracked with its quantity, location, and reorder level to ensure optimal stock levels are maintained.

The requisition module implements a multi-step approval workflow where employees (initiators) can request items, department heads (HODs) can approve or reject requests, and administrators can issue the approved items. This ensures proper accountability and control over inventory usage throughout the organization.

## Features

### Core Features

The system offers a comprehensive set of features that cover all aspects of inventory management. Item management allows users to add, update, and delete inventory items with detailed information including material codes, descriptions, unit of measurements, and storage locations. The system supports multiple unit types such as pieces, boxes, packs, reams, kilograms, liters, dozens, sets, rolls, and bottles to accommodate various inventory categories.

Stock tracking provides real-time visibility into inventory levels with automatic low-stock alerts when items fall below their reorder levels. The transaction history feature maintains a complete audit trail of all inventory movements, recording inward stock receipts, outward issuances, adjustments, returns, and write-offs with timestamps and user information.

The location management module enables organizations to define their warehouse storage structure with racks and shelves, allowing items to be assigned to specific locations for easier tracking and retrieval. Each location can be activated or deactivated as needed.

### Requisition Workflow

The requisition system implements a sophisticated multi-step approval workflow that ensures proper authorization for all inventory withdrawals. The workflow begins when an initiator creates a requisition request, which initially stays in draft status until submitted. Upon submission, the request moves to "Pending HOD Approval" status, where the department head can review, approve, authorize, send back for revision, or reject the request.

Approved requisitions move to "Authorized" status, where they wait for administrative issuance. Administrators can then issue the items, which automatically updates the inventory quantities and generates appropriate transaction records. The system supports partial fulfillment, allowing administrators to issue only some items or partial quantities from a requisition.

### User Management

The system implements role-based access control with four distinct user roles. Super Admins have complete system access including user management, department management, system-wide reporting, and all administrative functions. Admins are responsible for day-to-day inventory operations including item management, stock adjustments, and issuing approved requisitions.

Heads of Department (HODs) have approval authority over requisitions submitted by users within their department. They can also create requisitions as initiators for their own department needs. Initiators are regular employees who can create requisitions, track their submission status, and view their requisition history.

### Reporting & Analytics

The system includes dashboard views tailored to each user role, displaying relevant statistics and pending items requiring attention. Administrators can generate reports on inventory levels, transaction history, and requisition status. The system supports Excel export functionality for items, allowing bulk data import and offline analysis using pandas and openpyxl.

### Notifications

An integrated notification system keeps users informed of important events such as requisition status changes, approval requests, and system announcements. Notifications appear in the user interface and can be marked as read individually or in bulk.

## Technology Stack

The HPL Inventory Management System is built using modern and reliable technologies that ensure stability, security, and ease of maintenance.

**Backend Framework:** Django 4.2 is used as the primary web framework, providing robust security features, an admin interface, and an ORM for database operations. Django's built-in authentication system was extended to create a custom user model with role-based permissions.

**Database:** SQLite is used as the default database for development and deployment, offering zero-configuration setup and reliable data storage. The database schema is optimized with appropriate indexes for query performance.

**Frontend:** The user interface is built with Bootstrap 5 for responsive design across devices. Django crispy-forms with crispy-bootstrap5 template pack provides clean and consistent form styling without extensive custom CSS.

**Data Processing:** Pandas and openpyxl enable Excel file processing for bulk item imports and data exports. This allows administrators to quickly populate the inventory with large datasets from spreadsheets.

**Image Handling:** Pillow library provides image processing capabilities for any media uploads, ensuring efficient storage and display of item images.

## Project Structure

The project follows Django's recommended application structure with clear separation of concerns across multiple apps.

```
inventory management system/
├── hpl_ims/                    # Main Django project configuration
│   ├── __init__.py
│   ├── settings.py            # Project settings and configuration
│   ├── urls.py                # Root URL configuration
│   └── wsgi.py                # WSGI application entry point
├── core/                       # Core application (authentication, users)
│   ├── __init__.py
│   ├── admin.py               # Admin configuration for User and Department
│   ├── apps.py
│   ├── forms.py               # Forms for user and authentication
│   ├── models.py              # User, Department, Notification models
│   ├── urls.py                # Core app URL patterns
│   ├── views.py               # Authentication and dashboard views
│   └── management/commands/
│       └── seed_data.py       # Management command for sample data
├── inventory/                  # Inventory management app
│   ├── __init__.py
│   ├── admin.py               # Admin configuration for items
│   ├── forms.py               # Item and stock adjustment forms
│   ├── models.py              # Item, Location, Transaction models
│   ├── urls.py                # Inventory app URL patterns
│   └── views.py               # Item CRUD and stock operations
├── requisition/                # Requisition workflow app
│   ├── __init__.py
│   ├── admin.py               # Admin configuration for requisitions
│   ├── forms.py               # Requisition creation forms
│   ├── models.py              # Requisition, LineItem models
│   ├── urls.py                # Requisition app URL patterns
│   └── views.py               # Workflow views and API endpoints
├── templates/                  # Django templates
│   ├── base.html              # Base template with navigation
│   ├── core/                  # Authentication and dashboard templates
│   ├── inventory/             # Item and inventory templates
│   ├── requisition/           # Requisition workflow templates
│   └── partials/              # Reusable template fragments
├── static/                     # Static files (CSS, JavaScript)
│   ├── css/
│   └── js/
├── scripts/                    # Utility scripts
├── screenshots/                # Application screenshots
├── db.sqlite3                 # SQLite database file
├── manage.py                   # Django management script
└── requirements.txt            # Python dependencies
```

## Installation

### Prerequisites

Before installing the HPL Inventory Management System, ensure that Python 3.8 or higher is installed on your system. The application requires pip for package management and a virtual environment is recommended for isolation.

### Setup Steps

Begin by creating a virtual environment to isolate the project dependencies. Open a terminal and navigate to your desired installation directory. Create and activate the virtual environment using your preferred method. For Python's built-in venv module, run the following commands:

Create the virtual environment by executing the virtual environment creation command with Python's venv module. This creates an isolated Python environment in a folder named venv within your project directory. Activate the environment to ensure all subsequent commands run within this isolated context.

Clone or extract the HPL Inventory Management System files to your working directory. Navigate to the project root folder where the manage.py file is located. Install all required Python packages using pip by running the installation command with the requirements file. This automatically downloads and installs Django, crispy-forms, Pillow, pandas, openpyxl, and all other dependencies.

After installing dependencies, run database migrations to create the required database tables. The migration command analyzes the models and creates corresponding database schema. Once migrations complete successfully, the database is ready for use.

### Seeding Sample Data

To populate the database with sample data for testing and demonstration purposes, use the provided management command. This command creates sample departments, locations, users with different roles, inventory items, transactions, and requisitions with various statuses.

Run the seed command with optional parameters to control the amount of sample data generated. You can specify the number of users per department, total items to create, and number of sample requisitions. The command provides output showing the progress of data generation and displays default login credentials upon completion.

The seed data command is particularly useful during initial setup, development, and testing phases. It helps visualize how the system looks and functions with realistic data without manually entering each record.

## Configuration

### Settings Customization

The primary configuration file is located at `hpl_ims/settings.py`. For production deployments, several settings should be modified to enhance security and performance.

The secret key should be changed from the default value to a unique, random string. This key is used for cryptographic signing and should be kept confidential. Generate a strong secret key using Django's built-in key generation utilities or a cryptographically secure random number generator.

Debug mode should be set to False in production environments to prevent sensitive information from being displayed in error pages. When debug is disabled, Django serves static files differently and uses more generic error messages for security.

The allowed hosts setting should be configured to specify which domain names or IP addresses can access the application. For development, keeping this as a wildcard is acceptable, but production deployments should list specific hostnames.

### Database Configuration

The default configuration uses SQLite, which requires no additional setup and is suitable for single-server deployments. For larger installations requiring better performance or concurrent access, the database can be changed to PostgreSQL or MySQL by modifying the DATABASES setting in settings.py.

When switching to PostgreSQL, install the psycopg2 package, update the database configuration with connection details including host, port, database name, username, and password. Django handles the rest of the database adaptation automatically.

### Time Zone and Localization

The system is configured for the Asia/Kolkata time zone, but this can be changed by modifying the TIME_ZONE setting. The LANGUAGE_CODE is set to en-us for English, which can be changed if localization to other languages is required.

### Static and Media Files

Static files (CSS, JavaScript, images used in the UI) are served from the static directory and accessed via the /static/ URL prefix. Media files (uploaded content like item images) are stored in the media directory and accessed via /media/ URL prefix.

For production deployments, these files should be served by a web server like nginx or Apache rather than Django's development server. Configure your web server to handle these static and media URLs appropriately.

## User Roles & Permissions

The system implements a comprehensive role-based access control system with four distinct roles, each having specific permissions and responsibilities.

### Super Admin

Super Admins possess complete system access and are responsible for overall system administration. Their capabilities include creating and managing all user accounts regardless of department, defining and modifying department structures, accessing system-wide reports and analytics, managing system-wide settings, and viewing all requisitions across all departments.

Super Admins cannot directly approve requisitions or issue items, as these functions are reserved for HODs and Admins respectively. This separation of duties ensures proper checks and balances within the system.

### Admin (Inventory Administrator)

Admins handle the day-to-day operations of inventory management. They can create and manage inventory items including adding new items, updating item details, and maintaining accurate stock quantities. Admins have authority to adjust stock levels when necessary, whether due to audits, corrections, or physical counts.

When authorized requisitions are ready for fulfillment, Admins issue the requested items, which automatically deducts quantities from inventory and creates transaction records. Admins can also create requisitions for stock replenishment purposes.

### Head of Department (HOD)

HODs serve as the approval authority for requisitions originating from their department. Their approval scope is limited to users within their assigned department, ensuring that approval authority aligns with organizational structure.

When a requisition is submitted, the appropriate HOD receives a notification and can review the request details. HODs can approve requests that appear valid, send back requests that need clarification or modification, or reject requests that are inappropriate or unauthorized. HODs can also create their own requisitions as initiators.

### Initiator

Initiators are regular employees who use the system to request inventory items for their work needs. They can create new requisition requests, specifying the items needed and the purpose. Initiators can track the status of their submitted requisitions and receive notifications when there are updates.

Initiators can edit their requisitions only while in draft or sent-back status. Once submitted for approval, the requisition moves through the workflow and cannot be modified by the initiator until and unless it is sent back for revision.

## Workflow

### Item Management Workflow

Managing inventory items follows a straightforward lifecycle. Admins create new items by providing material codes (which must be unique), descriptions, item types (stationery or housekeeping), units of measurement, and storage locations. Each item has a reorder level that determines when low-stock alerts are triggered.

When stock is received, Admins can update item quantities either directly or through stock adjustment transactions. The system records all changes as transactions with user attribution and timestamps. Items can be deactivated rather than deleted to preserve historical data and transaction records.

### Requisition Approval Workflow

The requisition workflow implements organizational approval requirements through distinct stages. The process begins when an initiator creates a requisition, adding line items for each desired inventory item along with quantities and purposes. The initiator can save as draft to continue editing later or submit directly for approval.

Upon submission, the requisition status changes to "Pending HOD Approval" and notifications are sent to appropriate HODs based on the initiator's department. The HOD reviews the request and can take one of four actions: approve the request which changes status to "Authorized" and notifies admins; send back the request which returns it to the initiator for revision with feedback; reject the request which ends the workflow with a rejection reason recorded; or leave it pending for further review.

Once authorized, the requisition waits in "Authorized" status until an Admin is ready to fulfill it. The Admin reviews the authorized requisition, checks item availability, and issues the items. The system tracks actual quantities issued versus requested, supporting partial fulfillment scenarios. Upon issuance, the status changes to "Issued," inventory quantities are reduced, transactions are recorded, and the initiator receives a notification.

At any stage before issuance, the initiator can cancel a requisition that is no longer needed, changing the status to "Cancelled" with the reason recorded.

### Stock Movement Tracking

Every change to inventory quantities is recorded as a transaction entry. Inward transactions record stock receipts, outward transactions record issuances through requisitions, adjustment transactions record corrections, return transactions record items returned to stock, and write-off transactions record discarded items. Each transaction includes the user who performed it, the timestamp, reference information, and any notes.

## Default Login Credentials

After running the seed data management command, the following user accounts are created with their respective roles and access levels:

| Username | Password | Role | Department |
|----------|----------|------|------------|
| superadmin | admin123 | Super Admin | N/A |
| admin | admin123 | Admin | N/A |
| hod_hr | admin123 | Head of Department | Human Resources |
| hod_it | admin123 | Head of Department | Information Technology |
| hod_finance | admin123 | Head of Department | Finance |
| hod_operations | admin123 | Head of Department | Operations |
| hod_admin | admin123 | Head of Department | Administration |
| user_hr_1 | admin123 | Initiator | Human Resources |
| user_it_1 | admin123 | Initiator | Information Technology |
| user_finance_1 | admin123 | Initiator | Finance |

For production deployments, ensure all default passwords are changed immediately after initial setup. The seed command is intended for development and testing purposes only.

## Management Commands

Django management commands provide convenient ways to perform administrative tasks. The following commands are available for this project.

### Seed Data Command

The seed_data command populates the database with sample data for testing and demonstration:

```bash
python manage.py seed_data --users=5 --items=30 --requisitions=15
```

The command accepts optional parameters to control data generation. The users parameter specifies the number of regular users to create per department (default is 5). The items parameter sets the total number of inventory items to generate (default is 30). The requisitions parameter determines the number of sample requisitions to create with various statuses (default is 15).

### Standard Django Commands

All standard Django management commands are available for database operations:

Run database migrations after making changes to models to update the database schema. This is necessary when deploying changes or setting up the application initially.

Create a superuser account manually if needed, bypassing the seed data command. This provides an alternative method for initial administrative access.

The system also supports Django's built-in commands for checking system requirements, optimizing the database, and other administrative functions.

## API Endpoints

The application provides REST API endpoints for programmatic access to certain functionality. These endpoints return JSON responses and can be integrated with external systems or used for custom frontend applications.

### Inventory API

The item details endpoint accepts an item ID and returns detailed information about the item including current stock levels, location, and transaction history. This endpoint is useful for real-time stock checks and integration with other systems.

### Requisition API

The item suggestions endpoint provides autocomplete functionality for requisition creation, searching items by material code or description. The create requisition API endpoint accepts JSON data to create new requisitions programmatically. The update requisition API endpoint allows modifying existing requisitions for line item changes and quantity updates.

### Notification API

The notifications list endpoint returns a list of notifications for the authenticated user. Individual notification endpoints support marking notifications as read. A bulk read endpoint marks all notifications as read at once.

## Screenshots

The project includes sample screenshots demonstrating the user interface and key functionality.

| Screenshot | Description |
|------------|-------------|
| screenshots/img1.png | Dashboard view showing system overview |
| screenshots/img2.png | Requisition workflow interface |

To view these screenshots, navigate to the screenshots directory in the project root. These images provide visual reference for the application's layout and user experience.

---

## License

This project is provided for educational and organizational use. Modify and extend the application as needed to fit your specific requirements.

## Support

For questions about implementation, customization, or troubleshooting, refer to the Django documentation at https://docs.djangoproject.com/ for framework-specific guidance. The application's modular design allows for easy extension and modification to meet additional requirements.
