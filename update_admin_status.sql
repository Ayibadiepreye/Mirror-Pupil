-- Update admin status for users
-- Set bonnieprincewill6@gmail.com to super admin
-- Set dotacademy.ai@gmail.com to non-admin

-- Update bonnieprincewill6@gmail.com to be super admin
UPDATE users 
SET is_super_admin = TRUE, is_approved = TRUE
WHERE email = 'bonnieprincewill6@gmail.com';

-- Update dotacademy.ai@gmail.com to be non-admin (regular user)
UPDATE users 
SET is_super_admin = FALSE
WHERE email = 'dotacademy.ai@gmail.com';

-- Show the updated users
SELECT user_id, email, display_name, is_super_admin, is_approved, created_at
FROM users
WHERE email IN ('bonnieprincewill6@gmail.com', 'dotacademy.ai@gmail.com')
ORDER BY email;
