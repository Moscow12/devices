<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        // Add two_factor_tokens table
        Schema::create('two_factor_tokens', function (Blueprint $table) {
            $table->id();
            $table->string('email')->index();
            $table->string('token', 6);
            $table->timestamp('expires_at');
            $table->boolean('used')->default(false);
            $table->timestamps();

            $table->index(['email', 'token']);
        });

        // Add trusted_devices table
        Schema::create('trusted_devices', function (Blueprint $table) {
            $table->uuid('id')->primary();
            $table->foreignId('user_id')->constrained('users')->cascadeOnDelete();
            $table->string('device_fingerprint')->unique();
            $table->string('device_name')->nullable();
            $table->string('ip_address', 45)->nullable();
            $table->text('user_agent')->nullable();
            $table->timestamp('trusted_at');
            $table->timestamp('expires_at')->nullable();
            $table->timestamp('last_used_at')->nullable();
            $table->boolean('is_active')->default(true);
            $table->timestamps();

            $table->index(['user_id', 'device_fingerprint']);
            $table->index(['user_id', 'is_active']);
            $table->index('expires_at');
        });

        // Modify password_reset_tokens table if it exists
        if (Schema::hasTable('password_reset_tokens')) {
            Schema::table('password_reset_tokens', function (Blueprint $table) {
                if (!Schema::hasColumn('password_reset_tokens', 'expires_at')) {
                    $table->timestamp('expires_at')->nullable()->after('token');
                }
                if (!Schema::hasColumn('password_reset_tokens', 'used')) {
                    $table->boolean('used')->default(false)->after('expires_at');
                }
            });
        } else {
            Schema::create('password_reset_tokens', function (Blueprint $table) {
                $table->string('email')->primary();
                $table->string('token', 6);
                $table->timestamp('expires_at');
                $table->boolean('used')->default(false);
                $table->timestamps();
            });
        }
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('trusted_devices');
        Schema::dropIfExists('two_factor_tokens');

        // Only drop password_reset_tokens if we created it
        // Otherwise just remove the columns we added
        if (Schema::hasTable('password_reset_tokens')) {
            if (Schema::hasColumn('password_reset_tokens', 'used')) {
                Schema::table('password_reset_tokens', function (Blueprint $table) {
                    $table->dropColumn(['expires_at', 'used']);
                });
            }
        }
    }
};
