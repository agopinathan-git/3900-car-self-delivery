# 3900projectRepository
# CarHub: Online Car Ordering and Delivery System

## 🚗 Project Description

CarHub is a modern web application built with Django that streamlines the process of Browse, ordering, and delivering cars. It provides functionalities for customers to place orders, administrators to manage car inventory, and delivery agents to handle order assignments and tracking.

## ✨ Features

**For Customers:**
* **Browse Inventory:** View available cars with details (make, model, year, price, etc.).
* **Place Orders:** A multi-step form to specify delivery details and payment information.
* **Order History:** (Potentially) View past orders and their statuses.

**For Administrators/Staff:**
* **Car Management:** Add, edit, and delete cars from the inventory.
* **Order Management:** View and update the status of incoming orders.
* **Delivery Assignment:** Assign orders to specific delivery agents.
* **User Management:** Manage users and assign roles (e.g., 'CarhubDeliveryAgent').

## 🛠️ Technologies Used

* **Backend:** Python 3.x, Django 5.x (or compatible version)
* **Database:** SQLite (default for development), PostgreSQL (recommended for production)
* **Frontend:** HTML5, CSS3 (Bootstrap 5 for responsive design), JavaScript
* **Form Handling:** Django Forms with custom validation
* **Deployment:** (Not covered in this README, but typically Gunicorn/Nginx)

## 🚀 Getting Started

Follow these instructions to get a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

Before you begin, ensure you have the following installed:

* **Python 3.8+**: [python.org](https://www.python.org/downloads/)
* **pip**: Python package installer (usually comes with Python)
* **virtualenv** (recommended): `pip install virtualenv`

### Installation

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/agopinathan-git/3900-car-self-delivery
    cd carhub_project_root # Navigate to your project's root directory (where manage.py is)
    ```

2.  **Create and Activate a Virtual Environment:**
    ```bash
    python -m venv venv
    # On Windows:
    .\venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    ```

3.  **Install Dependencies:**
    pip install -r requirements.txt
    ```

4.  **Database Migrations:**
    Apply the initial database migrations.
    ```bash
    python manage.py migrate
    ```

5.  **Create a Superuser (Admin Account):**
    This will allow you to access the Django admin panel.
    ```bash
    python manage.py createsuperuser
    # Follow the prompts to create your username, email, and password.
    ```

6.  **Run the Development Server:**
    ```bash
    python manage.py runserver
    ```
    The application will now be running on `http://127.0.0.1:8000/`.

## 🖥️ Usage

1.  **Access the Application:** Open your web browser and go to `http://127.0.0.1:8000/`.
2.  **Browse Cars:** Navigate through the car inventory.
3.  **Place an Order:** Select a car and proceed to the order form, filling in delivery and payment details.
4.  **Admin Panel:** Access the Django administration interface at `http://127.0.0.1:8000/admin/` using the superuser credentials you created.
    * From here, you can manage `Car` inventory, `Order` statuses, and create/assign `DeliveryAssignment`s.
    * Ensure you create a Django `Group` named `CarhubDeliveryAgent` in the admin, and assign relevant user accounts to this group for delivery assignment functionality.


## ⚙️ Configuration

* **`carhub_project/settings.py`**:
    * **`DATABASES`**: Configure your database connection (e.g., switch from SQLite to PostgreSQL for production).
    * **`ALLOWED_HOSTS`**: Important for deployment.
    * **`INSTALLED_APPS`**: Ensure all your apps are listed.
* **`carhub/forms.py`**: Contains the form definitions and custom validation logic (e.g., for expiration dates).


## 📧 Contact

For any questions or inquiries, please contact:
[Arunjith Gopinathan]
