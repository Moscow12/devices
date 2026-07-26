# WBridge App - Quick Start Guide

## 🚀 Installation

```bash
cd /home/moscow/Desktop/PY/wbridge/wbridgeapp

# 1. Install PHP dependencies
composer install

# 2. Run database migrations
php artisan migrate

# 3. Seed database with roles, permissions, and users
php artisan db:seed

# 4. Start development server
php artisan serve
```

## 🔐 Login Credentials

Visit: http://localhost:8000/auth/login

| Role | Email | Password |
|------|-------|----------|
| Super Admin | superadmin@wbridge.test | superadmin |
| Admin | admin@wbridge.test | admin |
| Operator | operator@wbridge.test | operator |
| Viewer | viewer@wbridge.test | viewer |

You can login with **email**, **username**, or **phone number**.

## 📧 Two-Factor Authentication

- **Enabled by default** (can be disabled in .env)
- Check your email for 6-digit verification code
- Or check Laravel logs: `tail -f storage/logs/laravel.log`

To disable 2FA:
```env
TWO_FACTOR_ENABLED=false
```

## 🗄️ Database Configuration

Currently using MySQL. Check `.env`:
```env
DB_CONNECTION=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_DATABASE=wbridge
DB_USERNAME=root
DB_PASSWORD=root1234
```

## 📚 Documentation

- `AUTHENTICATION_REFACTOR_SUMMARY.md` - Full auth setup guide
- `ROLES_PERMISSIONS_SETUP.md` - Roles & permissions guide

## ⚡ Quick Commands

```bash
# Clear all caches
php artisan optimize:clear

# Reset permissions cache
php artisan permission:cache-reset

# Fresh install (⚠️ deletes all data)
php artisan migrate:fresh --seed

# Run specific seeder
php artisan db:seed --class=RolePermissionSeeder
```

## 🎯 What's Included

✅ Multi-field login (email/username/phone)
✅ Two-factor authentication
✅ Trusted device management
✅ Role-based permissions (4 roles, 30+ permissions)
✅ User seeding with test accounts
✅ Beautiful login UI
✅ Dashboard with permissions

## 🐛 Troubleshooting

**Issue: Class not found errors**
```bash
composer dump-autoload
```

**Issue: Permission denied**
```bash
chmod -R 755 storage bootstrap/cache
```

**Issue: 2FA email not sent**
- Check `storage/logs/laravel.log` for the code
- Or disable 2FA: `TWO_FACTOR_ENABLED=false`

**Issue: Database connection error**
- Check MySQL is running
- Verify `.env` database credentials
- Create database: `CREATE DATABASE wbridge;`

---

🎉 **Ready to go!** Start the server and login!
