-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create enum types
CREATE TYPE cook_type AS ENUM (
  'the meal prepper',
  'the daily fresh cook',
  'the one-big-batch cook',
  'the non-cook'
);

CREATE TYPE cook_frequency AS ENUM (
  '1-2 times',
  '3-4 times',
  '5-7 times',
  'more than 7 times'
);

CREATE TYPE dietary_requirement AS ENUM (
  'vegetarian',
  'vegan',
  'halal',
  'none'
);

CREATE TYPE purpose AS ENUM (
  'save on food expenses',
  'eat healthier meals',
  'try out new dishes',
  'make new friends'
);

CREATE TYPE food_category AS ENUM (
  'meal',
  'snack',
  'dessert',
  'drink',
  'leftover'
);

CREATE TYPE swap_status AS ENUM (
  'pending',
  'accepted',
  'rejected',
  'completed'
);

CREATE TYPE notification_type AS ENUM (
  'swap_request',
  'swap_accepted',
  'swap_rejected',
  'swap_completed',
  'food_expiring',
  'system'
);

-- Create users table
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL,
  first_name TEXT NOT NULL,
  last_name TEXT NOT NULL,
  bio TEXT NOT NULL,
  cook_type cook_type NOT NULL,
  cook_frequency cook_frequency NOT NULL,
  dietary_requirements dietary_requirement[] DEFAULT '{}',
  allergies TEXT NOT NULL,
  purpose purpose NOT NULL,
  home_address TEXT NOT NULL,
  profile_picture TEXT,
  swap_rating FLOAT DEFAULT 0.0,
  is_verified BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create verification_codes table
CREATE TABLE verification_codes (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  email TEXT NOT NULL,
  code TEXT NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create foods table
CREATE TABLE foods (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  category food_category NOT NULL,
  dietary_requirements dietary_requirement[] DEFAULT '{}',
  allergens TEXT NOT NULL,
  expiry_date TIMESTAMPTZ,
  location TEXT NOT NULL,
  is_homemade BOOLEAN DEFAULT FALSE,
  is_available BOOLEAN DEFAULT TRUE,
  image_url TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create swaps table
CREATE TABLE swaps (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  requester_id UUID REFERENCES users(id) ON DELETE CASCADE,
  provider_id UUID REFERENCES users(id) ON DELETE CASCADE,
  requester_food_id UUID REFERENCES foods(id) ON DELETE CASCADE,
  provider_food_id UUID REFERENCES foods(id) ON DELETE CASCADE,
  message TEXT,
  response_message TEXT,
  status swap_status DEFAULT 'pending',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create notifications table
CREATE TABLE notifications (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  type notification_type NOT NULL,
  title TEXT NOT NULL,
  message TEXT NOT NULL,
  related_id UUID,
  is_read BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create ratings table
CREATE TABLE ratings (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  swap_id UUID REFERENCES swaps(id) ON DELETE CASCADE,
  rater_id UUID REFERENCES users(id) ON DELETE CASCADE,
  rated_user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
  comment TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create RLS policies
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE foods ENABLE ROW LEVEL SECURITY;
ALTER TABLE swaps ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE ratings ENABLE ROW LEVEL SECURITY;

-- Users policies
CREATE POLICY "Users can view their own profile" 
  ON users FOR SELECT 
  USING (auth.uid() = id);

CREATE POLICY "Users can view other users' profiles" 
  ON users FOR SELECT 
  USING (true);

CREATE POLICY "Users can update their own profile" 
  ON users FOR UPDATE 
  USING (auth.uid() = id);

-- Foods policies
CREATE POLICY "Anyone can view available foods" 
  ON foods FOR SELECT 
  USING (is_available = true);

CREATE POLICY "Users can view their own foods even if unavailable" 
  ON foods FOR SELECT 
  USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own foods" 
  ON foods FOR INSERT 
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own foods" 
  ON foods FOR UPDATE 
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own foods" 
  ON foods FOR DELETE 
  USING (auth.uid() = user_id);

-- Swaps policies
CREATE POLICY "Users can view swaps they are part of" 
  ON swaps FOR SELECT 
  USING (auth.uid() = requester_id OR auth.uid() = provider_id);

CREATE POLICY "Users can create swap requests" 
  ON swaps FOR INSERT 
  WITH CHECK (auth.uid() = requester_id);

CREATE POLICY "Users can update swaps they are part of" 
  ON swaps FOR UPDATE 
  USING (auth.uid() = requester_id OR auth.uid() = provider_id);

-- Notifications policies
CREATE POLICY "Users can view their own notifications" 
  ON notifications FOR SELECT 
  USING (auth.uid() = user_id);

CREATE POLICY "Users can update their own notifications" 
  ON notifications FOR UPDATE 
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own notifications" 
  ON notifications FOR DELETE 
  USING (auth.uid() = user_id);

-- Ratings policies
CREATE POLICY "Anyone can view ratings" 
  ON ratings FOR SELECT 
  USING (true);

CREATE POLICY "Users can create ratings for swaps they are part of" 
  ON ratings FOR INSERT 
  WITH CHECK (
    auth.uid() = rater_id AND 
    EXISTS (
      SELECT 1 FROM swaps 
      WHERE swaps.id = swap_id AND 
      (swaps.requester_id = auth.uid() OR swaps.provider_id = auth.uid()) AND
      swaps.status = 'completed'
    )
  );

-- Create functions for updating timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = NOW();
   RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updating timestamps
CREATE TRIGGER update_users_updated_at
  BEFORE UPDATE ON users
  FOR EACH ROW
  EXECUTE PROCEDURE update_updated_at_column();

CREATE TRIGGER update_foods_updated_at
  BEFORE UPDATE ON foods
  FOR EACH ROW
  EXECUTE PROCEDURE update_updated_at_column();

CREATE TRIGGER update_swaps_updated_at
  BEFORE UPDATE ON swaps
  FOR EACH ROW
  EXECUTE PROCEDURE update_updated_at_column();

-- Create function to update user's swap rating
CREATE OR REPLACE FUNCTION update_user_swap_rating()
RETURNS TRIGGER AS $$
BEGIN
  UPDATE users
  SET swap_rating = (
    SELECT AVG(rating)
    FROM ratings
    WHERE rated_user_id = NEW.rated_user_id
  )
  WHERE id = NEW.rated_user_id;
  RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to update user's swap rating when a new rating is added
CREATE TRIGGER update_user_swap_rating_trigger
  AFTER INSERT OR UPDATE ON ratings
  FOR EACH ROW
  EXECUTE PROCEDURE update_user_swap_rating();

-- Create function to create notification when a swap is created
CREATE OR REPLACE FUNCTION create_swap_request_notification()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO notifications (user_id, type, title, message, related_id)
  VALUES (
    NEW.provider_id,
    'swap_request',
    'New Swap Request',
    'You have received a new swap request',
    NEW.id
  );
  RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to create notification when a swap is created
CREATE TRIGGER create_swap_request_notification_trigger
  AFTER INSERT ON swaps
  FOR EACH ROW
  EXECUTE PROCEDURE create_swap_request_notification();

-- Create function to create notification when a swap status changes
CREATE OR REPLACE FUNCTION create_swap_status_notification()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.status = 'accepted' AND OLD.status = 'pending' THEN
    INSERT INTO notifications (user_id, type, title, message, related_id)
    VALUES (
      NEW.requester_id,
      'swap_accepted',
      'Swap Request Accepted',
      'Your swap request has been accepted',
      NEW.id
    );
  ELSIF NEW.status = 'rejected' AND OLD.status = 'pending' THEN
    INSERT INTO notifications (user_id, type, title, message, related_id)
    VALUES (
      NEW.requester_id,
      'swap_rejected',
      'Swap Request Rejected',
      'Your swap request has been rejected',
      NEW.id
    );
  ELSIF NEW.status = 'completed' AND OLD.status = 'accepted' THEN
    INSERT INTO notifications (user_id, type, title, message, related_id)
    VALUES (
      NEW.requester_id,
      'swap_completed',
      'Swap Completed',
      'Your swap has been marked as completed',
      NEW.id
    );
    INSERT INTO notifications (user_id, type, title, message, related_id)
    VALUES (
      NEW.provider_id,
      'swap_completed',
      'Swap Completed',
      'Your swap has been marked as completed',
      NEW.id
    );
  END IF;
  RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to create notification when a swap status changes
CREATE TRIGGER create_swap_status_notification_trigger
  AFTER UPDATE ON swaps
  FOR EACH ROW
  WHEN (OLD.status IS DISTINCT FROM NEW.status)
  EXECUTE PROCEDURE create_swap_status_notification();

-- Create function to create notification when a food is about to expire
CREATE OR REPLACE FUNCTION create_food_expiring_notification()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.expiry_date IS NOT NULL AND NEW.expiry_date - INTERVAL '1 day' <= NOW() AND NEW.is_available = TRUE THEN
    INSERT INTO notifications (user_id, type, title, message, related_id)
    VALUES (
      NEW.user_id,
      'food_expiring',
      'Food Expiring Soon',
      'Your food item "' || NEW.title || '" is expiring soon',
      NEW.id
    );
  END IF;
  RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to create notification when a food is about to expire
CREATE TRIGGER create_food_expiring_notification_trigger
  AFTER INSERT OR UPDATE ON foods
  FOR EACH ROW
  EXECUTE PROCEDURE create_food_expiring_notification(); 