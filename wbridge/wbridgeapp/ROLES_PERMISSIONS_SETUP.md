# Roles & Permissions Setup Guide

## Overview
Successfully integrated Spatie Laravel Permission package with custom roles and permissions system based on the dasher project.

---

## 📦 **Installed Components**

### 1. **Composer Packages**
- `spatie/laravel-permission: ^6.21` - Role and permission management
- `livewire/livewire: ^3.0` - For Livewire components

### 2. **Models**
- **Permission.php** - Extends Spatie Permission with UUID support
- **PermissionCategory.php** - Groups permissions into categories
- **Role.php** - Extends Spatie Role with UUID support
- **User.php** - Updated with `HasRoles` trait and additional fields

### 3. **Database Migrations**
1. `2026_01_30_000001_add_authentication_tables.php` - 2FA tables
2. `2026_01_30_000002_create_workstations_table.php` - Workstation support
3. `2026_01_30_000003_create_permission_tables.php` - Spatie permission tables
4. `2026_01_30_000004_add_user_fields_for_auth.php` - Additional user fields

### 4. **Seeders**
- **RolePermissionSeeder.php** - Creates roles, permissions, and categories
- **UserSeeder.php** - Creates test users with roles
- **DatabaseSeeder.php** - Main seeder orchestrator

---

## 🎭 **Roles Created**

| Role | Slug | Description |
|------|------|-------------|
| **Super Admin** | `super-admin` | Full system access (all permissions) |
| **Admin** | `admin` | Most permissions (except critical ones) |
| **Operator** | `operator` | Transaction and weighbridge management |
| **Viewer** | `viewer` | Read-only access to view data |

---

## 🔐 **Permission Categories**

### 1. **Weighbridge Management**
- `view-weighbridge` - View weighbridge readings and data
- `manage-weighbridge` - Manage weighbridge settings
- `export-weighbridge-data` - Export reports

### 2. **Vehicle Management**
- `view-vehicles` - View vehicle records
- `create-vehicles` - Create new vehicles
- `update-vehicles` - Update vehicles
- `delete-vehicles` - Delete vehicles

### 3. **Transaction Management**
- `view-transactions` - View transactions
- `create-transactions` - Create new transactions
- `update-transactions` - Update transactions
- `delete-transactions` - Delete transactions
- `approve-transactions` - Approve transactions

### 4. **Reports & Analytics**
- `view-reports` - View reports
- `export-reports` - Export reports
- `manage-reports` - Create custom reports

### 5. **User Management**
- `view-users` - View users list
- `create-users` - Create new users
- `update-users` - Update users
- `delete-users` - Delete users
- `assign-roles` - Assign roles to users

### 6. **Access Control**
- `view-roles` - View roles
- `create-roles` - Create roles
- `update-roles` - Update roles
- `delete-roles` - Delete roles
- `view-permissions` - View permissions
- `assign-permissions` - Assign permissions to roles

### 7. **System Settings**
- `view-settings` - View settings
- `manage-settings` - Manage settings
- `view-audit-logs` - View audit logs
- `manage-backups` - Manage system backups

---

## 👥 **Test Users Created**

| Role | Email | Username | Password |
|------|-------|----------|----------|
| Super Admin | superadmin@wbridge.test | superadmin | superadmin |
| Admin | admin@wbridge.test | admin | admin |
| Operator | operator@wbridge.test | operator | operator |
| Viewer | viewer@wbridge.test | viewer | viewer |

---

## 🚀 **Installation Steps**

### 1. Install Composer Dependencies
```bash
cd /home/moscow/Desktop/PY/wbridge/wbridgeapp
composer install
```

### 2. Run Migrations
```bash
php artisan migrate
```

### 3. Publish Spatie Config (Optional)
```bash
php artisan vendor:publish --provider="Spatie\Permission\PermissionServiceProvider"
```

### 4. Run Seeders
```bash
php artisan db:seed
# or specifically:
php artisan db:seed --class=RolePermissionSeeder
php artisan db:seed --class=UserSeeder
```

---

## 📊 **Database Tables Created**

### Permission System Tables:
1. **permission_categories** - Groups permissions
2. **permissions** - All system permissions
3. **roles** - All system roles
4. **model_has_permissions** - Direct user permissions
5. **model_has_roles** - User role assignments
6. **role_has_permissions** - Role permission assignments

### Authentication Tables:
1. **users** (updated with new fields)
2. **two_factor_tokens**
3. **trusted_devices**
4. **password_reset_tokens**
5. **workstations**

---

## 💻 **Usage Examples**

### Check User Permissions
```php
// Check if user has permission
if ($user->can('create-transactions')) {
    // Allow creating transactions
}

// Check if user has role
if ($user->hasRole('admin')) {
    // User is admin
}

// Check if user has any of these roles
if ($user->hasAnyRole(['admin', 'super-admin'])) {
    // User is admin or super admin
}

// Check if user is super admin
if ($user->isSuperAdmin()) {
    // Full access
}
```

### In Blade Templates
```blade
@can('create-transactions')
    <button>Create Transaction</button>
@endcan

@role('admin')
    <a href="/admin">Admin Panel</a>
@endrole

@hasanyrole('admin|super-admin')
    <a href="/settings">Settings</a>
@endhasanyrole
```

### In Routes
```php
Route::middleware(['auth', 'role:admin'])->group(function () {
    Route::get('/admin', [AdminController::class, 'index']);
});

Route::middleware(['auth', 'permission:create-transactions'])->group(function () {
    Route::post('/transactions', [TransactionController::class, 'store']);
});
```

### Assign Roles/Permissions
```php
// Assign role to user
$user->assignRole('operator');

// Assign multiple roles
$user->assignRole(['operator', 'viewer']);

// Give permission directly to user
$user->givePermissionTo('view-reports');

// Give permissions to role
$role = Role::findByName('operator');
$role->givePermissionTo(['view-transactions', 'create-transactions']);

// Sync permissions (replaces all existing)
$role->syncPermissions(['view-transactions', 'create-transactions']);
```

### Check Permissions in Controller
```php
public function store(Request $request)
{
    // Method 1: Authorize
    $this->authorize('create-transactions');

    // Method 2: Manual check
    if (!auth()->user()->can('create-transactions')) {
        abort(403);
    }

    // Method 3: Using Gate
    if (Gate::denies('create-transactions')) {
        abort(403);
    }

    // Create transaction...
}
```

---

## 🔧 **Configuration**

### Spatie Permission Config
Location: `config/permission.php` (after publishing)

Key settings:
```php
return [
    'models' => [
        'permission' => App\Models\Permission::class,
        'role' => App\Models\Role::class,
    ],

    'table_names' => [
        'roles' => 'roles',
        'permissions' => 'permissions',
        'model_has_permissions' => 'model_has_permissions',
        'model_has_roles' => 'model_has_roles',
        'role_has_permissions' => 'role_has_permissions',
    ],

    // Enable teams (multi-tenancy)
    'teams' => false,

    // Cache settings
    'cache' => [
        'expiration_time' => \DateInterval::createFromDateString('24 hours'),
        'key' => 'spatie.permission.cache',
        'store' => 'default',
    ],
];
```

---

## 🛡️ **Middleware**

Available middleware:
- `role:admin` - Require specific role
- `permission:create-users` - Require specific permission
- `role_or_permission:admin|create-users` - Require role OR permission

Example:
```php
Route::group(['middleware' => ['auth', 'role:admin']], function () {
    Route::get('/admin/users', [UserController::class, 'index']);
});
```

---

## 📝 **Adding New Permissions**

### Via Seeder
Edit `database/seeders/RolePermissionSeeder.php`:
```php
'New Category' => [
    ['name' => 'new-permission', 'description' => 'Description here'],
],
```

Then run:
```bash
php artisan db:seed --class=RolePermissionSeeder
```

### Via Code
```php
use App\Models\Permission;
use App\Models\PermissionCategory;

$category = PermissionCategory::firstOrCreate(['name' => 'New Category']);

Permission::create([
    'name' => 'new-permission',
    'guard_name' => 'web',
    'description' => 'Description',
    'category_id' => $category->id,
]);
```

---

## 🎯 **Best Practices**

1. **Always cache permissions** - Use `php artisan cache:clear` after changes
2. **Use policy classes** for complex authorization logic
3. **Name permissions with action-resource** format (e.g., `create-users`, `view-reports`)
4. **Group related permissions** into categories
5. **Test permissions** thoroughly in different roles

---

## 🧪 **Testing**

### Create Test User with Role
```php
$user = User::factory()->create();
$user->assignRole('operator');
```

### Test Permissions
```php
// Test if user can perform action
$this->assertTrue($user->can('create-transactions'));

// Test middleware
$response = $this->actingAs($user)
    ->get('/transactions/create');
$response->assertStatus(200);
```

---

## 🔄 **Syncing Permissions**

If you need to re-seed permissions:
```bash
# Fresh migration and seed
php artisan migrate:fresh --seed

# Or just re-run seeders
php artisan db:seed --class=RolePermissionSeeder
```

---

## ⚠️ **Important Notes**

1. **Super Admin Bypass**: The `isSuperAdmin()` check bypasses all permission checks
2. **UUID Support**: All IDs are UUIDs (string type, not auto-increment)
3. **Soft Deletes**: Roles and permissions use soft deletes
4. **Cache**: Clear cache after permission changes: `php artisan permission:cache-reset`
5. **Guard Name**: Always use `web` guard (default for web applications)

---

## 📚 **Additional Resources**

- [Spatie Permission Docs](https://spatie.be/docs/laravel-permission)
- [Laravel Authorization](https://laravel.com/docs/authorization)
- [Livewire Docs](https://livewire.laravel.com)

---

## ✅ **Checklist**

- [x] Spatie Permission package installed
- [x] Permission and Role models configured
- [x] User model updated with HasRoles trait
- [x] Migrations created and ready
- [x] Seeders created with roles and permissions
- [x] Test users created
- [x] Documentation completed

**Next Steps:**
1. Run `composer install`
2. Run `php artisan migrate`
3. Run `php artisan db:seed`
4. Login with test users and verify permissions

---

**🎉 Roles & Permissions system ready to use!**
