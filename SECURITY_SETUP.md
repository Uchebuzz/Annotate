# Security Setup Guide

## Password Security Improvements

This application has been updated with enhanced security measures. Follow these steps to secure your installation.

### 1. Environment Variables Setup

**Option 1: Use the template file (Recommended)**
```bash
# Copy the template file
cp env_template.txt .env

# Edit .env and set your ADMIN_PASSWORD
# On Windows: notepad .env
# On Linux/Mac: nano .env
```

**Option 2: Create manually**
Create a `.env` file in the project root with the following content:

```env
# Admin Password (for initial setup)
# IMPORTANT: Change this to a strong password before deployment
ADMIN_PASSWORD=YourSecurePasswordHere
```

**Important:** 
- Never commit the `.env` file to version control
- Use a strong, unique password
- The `.env` file is already in `.gitignore`
- A template file `env_template.txt` is provided for your convenience

### 2. Password Hashing Upgrade

The application now uses **bcrypt** for password hashing instead of SHA-256:
- ✅ Bcrypt is designed for password hashing (slow, resistant to brute force)
- ✅ Includes salt automatically
- ✅ Backward compatible with old SHA-256 hashes (migration support)

### 3. First Login Security

When you first log in with the default password:
1. You will be **required** to change your password
2. The system tracks if the default password has been changed
3. You cannot proceed until the password is changed

### 4. Password Change

**For Admins:**
- Go to Admin Dashboard → Password Management
- Use "Change My Password" to update your password
- Password must be at least 6 characters

**Security Best Practices:**
- Use a strong password (12+ characters, mix of letters, numbers, symbols)
- Change default password immediately after first login
- Don't reuse passwords from other systems
- Consider using a password manager

### 5. Installation Steps

1. **Install new dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Create `.env` file:**
   ```bash
   # Option 1: Copy the template (recommended)
   cp env_template.txt .env
   # Then edit .env and set your ADMIN_PASSWORD
   
   # Option 2: Create manually
   echo "ADMIN_PASSWORD=YourSecurePasswordHere" > .env
   ```

3. **Run the application:**
   ```bash
   streamlit run app.py
   ```

4. **On first login:**
   - Log in with default credentials (from `.env` or fallback)
   - You will be prompted to change your password
   - Change it immediately

### 6. Migration from Old System

If you have existing users with SHA-256 hashed passwords:
- The system will automatically verify old passwords
- When users log in, their passwords will be re-hashed with bcrypt on next password change
- No manual migration needed

### 7. Security Checklist

- [ ] `.env` file created with strong `ADMIN_PASSWORD`
- [ ] `.env` file added to `.gitignore` (already done)
- [ ] Default password changed on first login
- [ ] Strong password policy enforced (6+ characters minimum)
- [ ] Regular password updates recommended for admins

### 8. What Changed

**Before:**
- ❌ Hardcoded password in source code
- ❌ SHA-256 hashing (fast, vulnerable)
- ❌ No password change functionality
- ❌ No forced password change

**After:**
- ✅ Password in environment variable
- ✅ Bcrypt hashing (secure, slow)
- ✅ Password change functionality
- ✅ Forced password change on first login
- ✅ Password change tracking

### 9. Troubleshooting

**Issue:** "ModuleNotFoundError: No module named 'bcrypt'"
- **Solution:** Run `pip install -r requirements.txt`

**Issue:** "ModuleNotFoundError: No module named 'dotenv'"
- **Solution:** Run `pip install -r requirements.txt`

**Issue:** Default password not working
- **Solution:** Check `.env` file exists and `ADMIN_PASSWORD` is set correctly

**Issue:** Can't change password
- **Solution:** Ensure new password is at least 6 characters and matches confirmation

---

**Security Note:** This application is now more secure, but remember:
- Keep your `.env` file secure and never share it
- Use strong passwords
- Regularly update passwords
- Consider additional security measures for production (HTTPS, firewall, etc.)

