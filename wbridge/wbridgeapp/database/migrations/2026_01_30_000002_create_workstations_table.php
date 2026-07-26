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
        Schema::create('workstations', function (Blueprint $table) {
            $table->uuid('id')->primary();
            $table->string('workstation_name');
            $table->string('location')->nullable();
            $table->string('postal_code')->nullable();
            $table->string('physical_address')->nullable();
            $table->string('phone_number')->nullable();
            $table->string('tin_number')->nullable();
            $table->string('email_address')->nullable();
            $table->string('logo')->nullable();
            $table->string('official_stamp')->nullable();
            $table->string('letter_head')->nullable();
            $table->unsignedBigInteger('country_id')->nullable();
            $table->unsignedBigInteger('region_id')->nullable();
            $table->unsignedBigInteger('district_id')->nullable();
            $table->unsignedBigInteger('ward_id')->nullable();
            $table->foreignId('added_by')->nullable()->constrained('users')->nullOnDelete();
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('workstations');
    }
};
