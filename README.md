# Simple-Store-CMS

## Overview

**Simple-Store-CMS** is a lightweight, modular, and extensible Content Management System for online stores.  
It currently  **does not include any payment processing**, focusing instead on product presentation, order handling, and full control over templates and data.

The system is designed for:
- **Developers** who want to build custom shop solutions or extend the CMS via plugins
- **Shop operators** with basic HTML/CSS knowledge who want a simple, self-hosted store

The architecture prioritizes clarity and minimal external dependencies.

---

## Core Principles

- No built-in payment providers
- Full control over templates and frontend behavior
- JSON-based persistence for transparency and portability
- Plugin-based extensibility instead of core modification
- Clear separation of concerns (logic, data, presentation)

---

## Feature Set

### Frontend / Store Features

- Product listings
- Product categories
- Product detail pages
- Shopping cart
- Checkout workflow (without payment)
- CAPTCHA-protected checkout
- Contact forms
- Template-driven page rendering
- Plugin-driven frontend components (e.g. carousel)

---

### Admin Panel

The Admin Panel is the central control interface of the CMS.

Main features:

- Universal admin login (single global account)
- Product management (create, edit, delete)
- Category management
- Order management and order status handling
- Template configuration
- File manager for uploads and assets
- Plugin management
- Central configuration of all CMS settings

Admin login URL:
`https://your-domain.com/login`

---

## Authentication Model

- Single universal admin account
- No user or role management
- Password-based access
- Designed for small to medium deployments
- All sensitive routes are admin-protected

This intentionally simple model reduces complexit.

---

## Technology Stack

### Backend

- Python 3
- Flask (Blueprint-based modular structure)
- Waitress (production WSGI server)

Development server:
```bash
flask run
```
Production server:
```bash
python main.py
```
---

## Frontend
- Jinja2 HTML templates
- Vanilla JavaScript
- Plain CSS
- No frontend frameworks required

---
## Data Storage

- JSON-based storage
- Human-readable and version-controllable
- Easy backup and migration

The system can be extended to support e.g.:
- MongoDB
- MySQL

This can be done via custom plugins or backend extensions.
---

## Project Structure

```
Simple-Store-CMS/
│
├── main.py                 # Application entry point
├── settings.json           # Global configuration file
│
├── templates/              # Jinja2 templates
│   ├── base.html
│   ├── index.html
│   └── admin/
│
├── static/                 # Static assets (CSS, JS, images)
│
├── plugins/                # Plugin modules
│   └── carousel/
│
├── data/                   # JSON data storage
│   ├── products.json
│   ├── categories.json
│   └── orders.json
│
├── logs/                   # Application logs
└── utils/                  # Helper modules
```

---
## Configuration
### settings.json
All configuration is handled via `settings.json` or through the Admin Panel.
No enviroment variables are needed.

Example: 
```json
{
    "server_config": {
        "MAX_CONTENT_LENGTH": 12582912,
        "PERMANENT_SESSION_LIFETIME": 2592000,
        "SESSION_COOKIE_NAME": "session-name",
        "maintenance": false
    },
    "format": "#.##0,00",
    "admin-password": "change-me",
    "url": "localhost",
    "categories": []
}
```

---

## Plugin System

This project supports modular plugins that extend functionality without modifying the core code.

### Plugin Characteristics
- Isolated from the core application
- Can register templates, static files, or logic
- Can interact with JSON data or external databases
- Can modify frontend behavior

---
## Installing a plugin
1. Copy the plugin folder into the `plugins/` directory:
```
plugins/
└── my_plugin/
    ├── plugin.py
    ├── templates/
    └── static/
```
2. Restart the application
3. Enable or configure the plugin via the Admin Panel (if applicable and/or supported)

---
## Order Workflow
1. User adds products to the cart
2. User proceeds to checkout
3. CAPTCHA verification
4. Order is stored in JSON
5. Admin can review and manage the order via dashboard

No payment processing is performed.
---
## Use Cases

- Product catalogs
- Pre-order systems
- Inquiry-based stores
- Prototypes
- Educational Flask CMS projects

---
## License

This project is released under the MIT License.

You are free to:

- Use
- Modify
- Distribute
- Build upon the project

## Contribution Policy
There are currently no external contributors.
