<?php

namespace Database\Seeders;

use App\Models\Permission;
use App\Models\PermissionCategory;
use App\Models\Role;
use Illuminate\Database\Seeder;

class RolePermissionSeeder extends Seeder
{
    /**
     * Run the database seeds.
     */
    public function run(): void
    {
        $this->command->info('🔐 Creating Permission Categories and Permissions...');

        $permissions = [
            'Weighbridge Management' => [
                ['name' => 'view-weighbridge', 'description' => 'View weighbridge readings and data'],
                ['name' => 'manage-weighbridge', 'description' => 'Manage weighbridge settings and configurations'],
                ['name' => 'export-weighbridge-data', 'description' => 'Export weighbridge data and reports'],
            ],
            'Vehicle Management' => [
                ['name' => 'view-vehicles', 'description' => 'View vehicle records'],
                ['name' => 'create-vehicles', 'description' => 'Create new vehicle records'],
                ['name' => 'update-vehicles', 'description' => 'Update existing vehicle records'],
                ['name' => 'delete-vehicles', 'description' => 'Delete vehicle records'],
            ],
            'Transaction Management' => [
                ['name' => 'view-transactions', 'description' => 'View weighbridge transactions'],
                ['name' => 'create-transactions', 'description' => 'Create new transactions'],
                ['name' => 'update-transactions', 'description' => 'Update existing transactions'],
                ['name' => 'delete-transactions', 'description' => 'Delete transactions'],
                ['name' => 'approve-transactions', 'description' => 'Approve weighbridge transactions'],
            ],
            'Reports & Analytics' => [
                ['name' => 'view-reports', 'description' => 'View reports and analytics'],
                ['name' => 'export-reports', 'description' => 'Export reports to various formats'],
                ['name' => 'manage-reports', 'description' => 'Create and manage custom reports'],
            ],
            'User Management' => [
                ['name' => 'view-users', 'description' => 'View list of users'],
                ['name' => 'create-users', 'description' => 'Create new users'],
                ['name' => 'update-users', 'description' => 'Update existing users'],
                ['name' => 'delete-users', 'description' => 'Delete users'],
                ['name' => 'assign-roles', 'description' => 'Assign roles to users'],
            ],
            'Access Control' => [
                ['name' => 'view-roles', 'description' => 'View list of roles'],
                ['name' => 'create-roles', 'description' => 'Create new roles'],
                ['name' => 'update-roles', 'description' => 'Update existing roles'],
                ['name' => 'delete-roles', 'description' => 'Delete roles'],
                ['name' => 'view-permissions', 'description' => 'View list of permissions'],
                ['name' => 'assign-permissions', 'description' => 'Assign permissions to roles'],
            ],
            'System Settings' => [
                ['name' => 'view-settings', 'description' => 'View system settings'],
                ['name' => 'manage-settings', 'description' => 'Manage system settings and configurations'],
                ['name' => 'view-audit-logs', 'description' => 'View audit logs and system activity'],
                ['name' => 'manage-backups', 'description' => 'Manage system backups'],
            ],
        ];

        foreach ($permissions as $categoryName => $categoryPermissions) {
            // Create or find the category
            $category = PermissionCategory::firstOrCreate(
                ['name' => $categoryName]
            );

            $this->command->info("  📁 Category: {$categoryName}");

            // Create permissions for this category
            foreach ($categoryPermissions as $permissionData) {
                Permission::firstOrCreate(
                    [
                        'name' => $permissionData['name'],
                        'guard_name' => 'web',
                    ],
                    [
                        'description' => $permissionData['description'],
                        'category_id' => $category->id,
                    ]
                );

                $this->command->info("    ✓ {$permissionData['name']}");
            }
        }

        $this->command->info("\n🎭 Creating Roles...");

        // Create Super Admin Role
        $superAdminRole = Role::firstOrCreate(
            ['name' => 'super-admin', 'guard_name' => 'web']
        );
        $this->command->info("  ✓ Super Admin");

        // Create Admin Role
        $adminRole = Role::firstOrCreate(
            ['name' => 'admin', 'guard_name' => 'web']
        );
        $this->command->info("  ✓ Admin");

        // Create Operator Role
        $operatorRole = Role::firstOrCreate(
            ['name' => 'operator', 'guard_name' => 'web']
        );
        $this->command->info("  ✓ Operator");

        // Create Viewer Role
        $viewerRole = Role::firstOrCreate(
            ['name' => 'viewer', 'guard_name' => 'web']
        );
        $this->command->info("  ✓ Viewer");

        $this->command->info("\n🔗 Assigning Permissions to Roles...");

        // Super Admin gets ALL permissions
        $allPermissions = Permission::all();
        $superAdminRole->syncPermissions($allPermissions);
        $this->command->info("  ✓ Super Admin: {$allPermissions->count()} permissions");

        // Admin gets most permissions (except super admin specific ones)
        $adminPermissions = Permission::whereNotIn('name', [
            'delete-users',
            'manage-backups',
        ])->get();
        $adminRole->syncPermissions($adminPermissions);
        $this->command->info("  ✓ Admin: {$adminPermissions->count()} permissions");

        // Operator gets transaction and weighbridge permissions
        $operatorPermissions = Permission::whereIn('name', [
            'view-weighbridge',
            'view-vehicles',
            'view-transactions',
            'create-transactions',
            'update-transactions',
            'view-reports',
        ])->get();
        $operatorRole->syncPermissions($operatorPermissions);
        $this->command->info("  ✓ Operator: {$operatorPermissions->count()} permissions");

        // Viewer gets only view permissions
        $viewerPermissions = Permission::where('name', 'like', 'view-%')->get();
        $viewerRole->syncPermissions($viewerPermissions);
        $this->command->info("  ✓ Viewer: {$viewerPermissions->count()} permissions");

        $this->command->info("\n✅ Roles and Permissions seeded successfully!");
    }
}
