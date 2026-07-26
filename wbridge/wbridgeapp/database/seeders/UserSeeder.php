<?php

namespace Database\Seeders;

use App\Models\User;
use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\Hash;

class UserSeeder extends Seeder
{
    /**
     * Run the database seeds.
     */
    public function run(): void
    {
        $this->command->info('👥 Creating Users...');

        // Create Super Admin User
        $superAdmin = User::firstOrCreate(
            ['email' => 'superadmin@wbridge.test'],
            [
                'name' => 'Super Administrator',
                'username' => 'superadmin',
                'phone_number' => '0700000001',
                'password' => Hash::make('superadmin'),
                'is_super_admin' => true,
            ]
        );

        // Ensure super admin flag is set
        if (!$superAdmin->is_super_admin) {
            $superAdmin->update(['is_super_admin' => true]);
        }

        // Assign super-admin role
        $superAdmin->assignRole('super-admin');
        $this->command->info("  ✓ Super Admin: {$superAdmin->email} (password: superadmin)");

        // Create Admin User
        $admin = User::firstOrCreate(
            ['email' => 'admin@wbridge.test'],
            [
                'name' => 'Administrator',
                'username' => 'admin',
                'phone_number' => '0700000002',
                'password' => Hash::make('admin'),
                'is_super_admin' => false,
            ]
        );

        $admin->assignRole('admin');
        $this->command->info("  ✓ Admin: {$admin->email} (password: admin)");

        // Create Operator User
        $operator = User::firstOrCreate(
            ['email' => 'operator@wbridge.test'],
            [
                'name' => 'Weighbridge Operator',
                'username' => 'operator',
                'phone_number' => '0700000003',
                'password' => Hash::make('operator'),
                'is_super_admin' => false,
            ]
        );

        $operator->assignRole('operator');
        $this->command->info("  ✓ Operator: {$operator->email} (password: operator)");

        // Create Viewer User
        $viewer = User::firstOrCreate(
            ['email' => 'viewer@wbridge.test'],
            [
                'name' => 'Report Viewer',
                'username' => 'viewer',
                'phone_number' => '0700000004',
                'password' => Hash::make('viewer'),
                'is_super_admin' => false,
            ]
        );

        $viewer->assignRole('viewer');
        $this->command->info("  ✓ Viewer: {$viewer->email} (password: viewer)");

        $this->command->info("\n✅ Users seeded successfully!");
        $this->command->info("\n📋 Login Credentials:");
        $this->command->table(
            ['Role', 'Email', 'Password'],
            [
                ['Super Admin', 'superadmin@wbridge.test', 'superadmin'],
                ['Admin', 'admin@wbridge.test', 'admin'],
                ['Operator', 'operator@wbridge.test', 'operator'],
                ['Viewer', 'viewer@wbridge.test', 'viewer'],
            ]
        );
    }
}
