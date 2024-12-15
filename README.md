# Amherst Coursework

Amherst Coursework is a web application that provides Amherst College students and faculty with an intuitive, advanced interface for course search.

## Getting Started

To clone and set up the application locally, follow the instructions below.

### Clone the Repository

```bash
git clone https://github.com/ac-i2i-engineering/amherst-coursework.git
cd amherst-coursework
```

### Set Up a Virtual Environment

Create and activate a virtual environment to manage dependencies locally.

```bash
python3 -m venv env
source env/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run Database Migrations

Navigate to the backend directory and apply migrations to set up the database schema.

```bash
cd access_amherst_backend
python manage.py makemigrations
python manage.py migrate
```

### Start the Development Server

To run the application locally, use the following command:

```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000/` in your browser to view the application.

## Contributing

We welcome contributions to improve Amherst Coursework. Please follow these guidelines:

1. **Code Formatting**: Ensure your code adheres to the `black` style guidelines. You can format your code by running:
   ```bash
   python -m black ./
   ```
   A pre-commit hook is set up to enforce this format.

2. **Documentation**: For adding or updating documentation, please refer to the [Amherst Coursework Backend Documentation Guide](./docs/) in `docs/`. It includes instructions on using Sphinx to document models and views, creating `.rst` files, and previewing the documentation.

3. **Pull Requests**: Before submitting a pull request, ensure that all code is well-documented, tested, and follows our coding standards.

---

For any questions or further support, please reach out to our team.