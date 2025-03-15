-- Add verification code fields to users table
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS verification_code VARCHAR(6),
ADD COLUMN IF NOT EXISTS verification_code_expires TIMESTAMPTZ;

-- Add index for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_verification_code 
ON users(verification_code) 
WHERE verification_code IS NOT NULL;

-- Add index for faster expiration checks
CREATE INDEX IF NOT EXISTS idx_users_verification_code_expires 
ON users(verification_code_expires) 
WHERE verification_code_expires IS NOT NULL; 