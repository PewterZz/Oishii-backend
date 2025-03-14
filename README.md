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

## Getting Started

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

4. Run the application:
   ```bash
   uvicorn src.main:app --reload
   ```

5. Open your browser and navigate to:
   ```
   http://localhost:8000/docs
   ```

## API Documentation

The API documentation is available at `/docs` or `/redoc` when the server is running.

### Main Endpoints

#### Authentication & User Management

- `POST /api/v1/users/register` - Register a new user
- `POST /api/v1/users/verify` - Verify email with verification code
- `POST /api/v1/users/resend-verification` - Resend verification code
- `POST /api/v1/users/token` - Get an access token

#### Users

- `GET /api/v1/users/me` - Get current user profile
- `PATCH /api/v1/users/me` - Update current user profile
- `GET /api/v1/users/{user_id}` - Get a specific user's profile

#### Food Listings

- `POST /api/v1/foods` - Create a new food listing
- `GET /api/v1/foods` - Get all food listings with filtering
- `GET /api/v1/foods/nearby` - Get food listings near a specific location
- `GET /api/v1/foods/{food_id}` - Get a specific food listing
- `PATCH /api/v1/foods/{food_id}` - Update a food listing
- `DELETE /api/v1/foods/{food_id}` - Delete a food listing
- `GET /api/v1/foods/user/{user_id}` - Get all food listings for a specific user

#### Swaps

- `POST /api/v1/swaps` - Create a new swap request
- `GET /api/v1/swaps` - Get all swaps with filtering
- `GET /api/v1/swaps/{swap_id}` - Get a specific swap
- `PATCH /api/v1/swaps/{swap_id}` - Update a swap status (accept, reject, complete)

#### Ratings

- `POST /api/v1/ratings` - Rate a user after a completed swap
- `GET /api/v1/ratings/user/{user_id}` - Get all ratings for a specific user
- `GET /api/v1/ratings/swap/{swap_id}` - Get all ratings for a specific swap

#### Notifications

- `GET /api/v1/notifications` - Get all notifications for the current user
- `PATCH /api/v1/notifications/{notification_id}` - Mark a notification as read/unread
- `PATCH /api/v1/notifications` - Mark all notifications as read/unread
- `DELETE /api/v1/notifications/{notification_id}` - Delete a notification

#### Uploads

- `POST /api/v1/uploads/profile-picture` - Upload a profile picture
- `POST /api/v1/uploads/food-image` - Upload a food image
- `GET /api/v1/uploads/{file_path}` - Get an uploaded file
- `DELETE /api/v1/uploads/{file_path}` - Delete an uploaded file

## Development

### Project Structure

```
oishii-backend/
├── src/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── foods.py
│   │       │   ├── notifications.py
│   │       │   ├── ratings.py
│   │       │   ├── swaps.py
│   │       │   ├── uploads.py
│   │       │   └── users.py
│   │       └── api.py
│   ├── core/
│   │   ├── config.py
│   │   └── middleware.py
│   ├── schemas/
│   │   ├── food.py
│   │   ├── notification.py
│   │   ├── rating.py
│   │   ├── swap.py
│   │   └── user.py
│   ├── services/
│   │   └── file_service.py
│   └── main.py
├── uploads/
│   ├── food_images/
│   └── profile_pictures/
├── .gitignore
├── README.md
└── requirements.txt
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- FastAPI for the amazing web framework
- Pydantic for the data validation
- All the university students who inspired this project