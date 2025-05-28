# PrimeTrust Banking Application

A modern online banking application built with Django and HTMX.

## Features

- Secure user authentication
- Account management
- Transaction history
- Fund transfers
- Bill payments
- Responsive design with Tailwind CSS
- Real-time updates with HTMX

## Deployment on Render

This application is configured for deployment on Render. The following files are used for deployment:

- `render.yaml`: Configuration for Render services
- `Procfile`: Defines the web service command
- `start.sh`: Main entry point that handles setup and starts the application server

## SEO Configuration

The application includes the following SEO enhancements:

- Sitemap generation
- Meta tags for search engines
- Open Graph and Twitter card tags
- Robots.txt configuration
- Favicon and logo placeholders

## Local Development

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables in `.env` file
4. Run migrations: `python manage.py migrate`
5. Create a superuser: `python manage.py createsuperuser`
6. Run the development server: `python manage.py runserver`

## Production Deployment

1. Push your code to GitHub
2. Connect your GitHub repository to Render
3. Configure the environment variables in Render dashboard
4. Deploy the application

## Directory Structure

- `core/`: Project settings and configuration
- `accounts/`: User authentication and profile management
- `banking/`: Banking features and transactions
- `dashboard/`: User dashboard and account overview
- `pages/`: Static pages (about, contact, etc.)
- `templates/`: HTML templates
- `static/`: Static files (CSS, JavaScript, images)
- `media/`: User-uploaded files

## License

This project is licensed under the MIT License - see the LICENSE file for details.
