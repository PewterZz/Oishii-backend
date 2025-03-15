# Oishii - Student Food Swapping App Backend

Oishii is a food swapping application designed specifically for university students. This repository contains the backend API built with FastAPI.

## Features

- **User Management**: Registration with university email verification
- **User Profiles**: Detailed profiles with cooking preferences and dietary requirements
- **Food Listings**: Create, update, and browse food listings with allergen information
- **Food Swapping**: Request and manage food swaps between students
- **Notifications**: Real-time notifications for swap requests and updates
- **Ratings**: Rate other users after completed swaps
- **Location-based Search**: Find food listings near your location

## Tech Stack

- FastAPI
- Pydantic
- Supabase (PostgreSQL + Auth)
- JWT Authentication
- Python 3.11

## Local Development

### Prerequisites

- Python 3.8+
- pip (Python package manager)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/oishii-backend.git
   cd oishii-backend
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file based on `.env.example`:
   ```bash
   cp .env.example .env
   ```

5. Update the `.env` file with your Supabase credentials and other configuration.

6. Run the application:
   ```bash
   uvicorn src.main:app --reload
   ```

7. Access the API documentation at http://localhost:8000/docs

## Deployment to Fly.io

### Prerequisites

1. Install the Fly.io CLI:
   ```bash
   # On macOS
   brew install flyctl

   # On Linux
   curl -L https://fly.io/install.sh | sh

   # On Windows (using PowerShell)
   iwr https://fly.io/install.ps1 -useb | iex
   ```

2. Sign up and log in to Fly.io:
   ```bash
   fly auth signup
   # or
   fly auth login
   ```

### Deployment Steps

1. Initialize your app (if not already done):
   ```bash
   fly launch
   ```
   This will create a `fly.toml` file if it doesn't exist.

2. Set up secrets for environment variables:
   ```bash
   fly secrets set SUPABASE_URL=https://your-project-id.supabase.co
   fly secrets set SUPABASE_KEY=your-supabase-anon-key
   fly secrets set JWT_SECRET=your-jwt-secret
   fly secrets set EMAIL_HOST=smtp.example.com
   fly secrets set EMAIL_PORT=587
   fly secrets set EMAIL_USERNAME=your-email@example.com
   fly secrets set EMAIL_PASSWORD=your-email-password
   fly secrets set EMAIL_FROM=noreply@oishii.com
   ```

3. Deploy the application:
   ```bash
   fly deploy
   ```

4. Open the deployed application:
   ```bash
   fly open
   ```

### Monitoring and Logs

- View logs:
  ```bash
  fly logs
  ```

- Monitor the application:
  ```bash
  fly status
  ```

- SSH into the VM:
  ```bash
  fly ssh console
  ```

## API Documentation

Once deployed, the API documentation is available at:
- Swagger UI: https://your-app-name.fly.dev/docs
- ReDoc: https://your-app-name.fly.dev/redoc

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- FastAPI for the amazing web framework
- Pydantic for the data validation
- All the university students who inspired this project