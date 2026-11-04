# Sales and Inventory Management System

A web-based Sales and Inventory Management System developed as an Advanced Database course project.

The system aims to simplify product management, inventory monitoring, sales transactions, purchasing, supplier records, and business reporting.

## Project Information

| Item | Details |
|---|---|
| Project Name | Sales and Inventory Management System |
| Course | Advanced Database |
| Backend | Python / Django |
| Database | MySQL |
| Database Management Tool | MySQL Workbench |
| Frontend | HTML, CSS, JavaScript, Bootstrap |
| Version Control | Git and GitHub |
| Project Status | In Development |

## Objectives

- Manage product information and categories.
- Monitor inventory and stock availability.
- Record sales transactions and automatically update stock levels.
- Manage purchases and stock replenishment.
- Maintain supplier information and purchasing history.
- Generate sales and inventory reports.
- Implement user authentication and role-based access control.

## Planned Features

### 1. Product Management
- Create, view, update, and delete products.
- Manage product categories.
- Search and filter products.
- Monitor product prices and stock levels.

### 2. Inventory Management
- Track available stock.
- Record stock additions and deductions.
- Automatically update inventory after sales and restocking.
- Generate low-stock and reorder alerts.

### 3. Sales Management
- Record customer purchases.
- Calculate subtotals, taxes, totals, and change.
- Generate sales receipts.
- Automatically deduct sold quantities from inventory.

### 4. Purchasing and Supplier Management
- Maintain supplier records.
- Record purchase transactions.
- Track purchased products and quantities.
- Update inventory after stock replenishment.

### 5. Reports and Analytics
- Daily, weekly, and monthly sales reports.
- Inventory status reports.
- Fast-moving and slow-moving product reports.
- Profit and loss reports.
- Export reports to PDF and Excel.

### 6. User and Access Management
- Administrator
- Cashier
- Inventory Clerk

Implement authentication and permissions based on user roles.

## Technology Stack

- **Python:** Backend programming language.
- **Django:** Web application framework.
- **MySQL:** Relational database management system.
- **MySQL Workbench:** Database design and administration.
- **HTML, CSS, JavaScript, Bootstrap:** Frontend technologies.
- **Git and GitHub:** Version control and project collaboration.

## Project Structure

```text
advanced-db-sales-inventory/
│
├── core/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── manage.py
├── .gitignore
├── README.md
└── .venv/
```

The project structure will expand as application modules are developed.

## Installation and Setup

### Prerequisites

- Python 3.12+
- MySQL Server
- MySQL Workbench
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR-USERNAME/advanced-db-sales-inventory.git

cd advanced-db-sales-inventory
```

### 2. Create a Virtual Environment

```bash
python3.12 -m venv .venv
```

### 3. Activate the Virtual Environment

macOS / Linux:

```bash
source .venv/bin/activate
```

### 4. Install Dependencies

```bash
python -m pip install django
```

### 5. Run Database Migrations

```bash
python manage.py migrate
```

### 6. Start the Development Server

```bash
python manage.py runserver
```

Open the application at:

```text
http://127.0.0.1:8000/
```

## Development Guidelines

- Use Django applications to organize system modules.
- Use Django ORM for database operations.
- Keep database credentials in environment variables.
- Use migrations to manage database schema changes.
- Follow consistent naming conventions.
- Commit changes using descriptive Git commit messages.

## Project Status

This project is currently under development. Features, database structures, diagrams, and documentation will be updated as development progresses.

## License

This project is developed for academic purposes.