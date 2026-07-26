<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('ecg_records', function (Blueprint $table) {
            $table->uuid('id')->primary();

            // ── File info ─────────────────────────────────────────────────
            $table->string('filename');
            $table->string('file_path')->nullable();
            $table->string('hl7_path')->nullable();
            $table->unsignedBigInteger('file_size_bytes')->nullable();
            $table->string('file_format')->default('SCP-ECG');
            $table->string('source_device')->default('Edan SE-1200 Express');
            $table->string('device_no')->nullable();

            // ── Patient info ──────────────────────────────────────────────
            $table->string('patient_id')->nullable()->index();
            $table->string('patient_name')->nullable();
            $table->string('patient_first_name')->nullable();
            $table->string('patient_last_name')->nullable();
            $table->date('patient_dob')->nullable();
            $table->string('patient_age')->nullable();
            $table->string('patient_sex')->nullable();
            $table->string('patient_weight')->nullable();
            $table->string('patient_height')->nullable();
            $table->string('patient_room')->nullable();
            $table->string('hospital')->nullable();
            $table->string('department')->nullable();
            $table->string('referring_physician')->nullable();
            $table->string('diagnosis_doctor')->nullable();
            $table->string('technician')->nullable();

            // ── Recording info ────────────────────────────────────────────
            $table->date('recording_date')->nullable()->index();
            $table->time('recording_time')->nullable();
            $table->timestamp('recorded_at')->nullable()->index();
            $table->unsignedSmallInteger('sample_rate_hz')->nullable();
            $table->unsignedTinyInteger('num_leads')->default(12);
            $table->decimal('duration_sec', 6, 2)->nullable();

            // ── Measurements ──────────────────────────────────────────────
            $table->unsignedSmallInteger('heart_rate_bpm')->nullable();
            $table->string('heart_rate_interp')->nullable();
            $table->unsignedSmallInteger('p_duration_ms')->nullable();
            $table->unsignedSmallInteger('pr_interval_ms')->nullable();
            $table->unsignedSmallInteger('qrs_duration_ms')->nullable();
            $table->unsignedSmallInteger('qt_interval_ms')->nullable();
            $table->unsignedSmallInteger('qtc_interval_ms')->nullable();
            $table->string('qtc_interpretation')->nullable();
            $table->smallInteger('p_axis_degrees')->nullable();
            $table->smallInteger('qrs_axis_degrees')->nullable();
            $table->string('qrs_axis_interpretation')->nullable();
            $table->smallInteger('t_axis_degrees')->nullable();
            $table->unsignedSmallInteger('atrial_rate_bpm')->nullable();

            // ── Diagnosis & Interpretation ────────────────────────────────
            $table->json('auto_diagnosis')->nullable();
            $table->json('interpretation_findings')->nullable();
            $table->json('interpretation_flags')->nullable();
            $table->boolean('is_normal')->nullable();
            $table->text('interpretation_summary')->nullable();
            $table->text('clinical_summary')->nullable();
            $table->text('free_text')->nullable();

            // ── Lead data (summary) ───────────────────────────────────────
            $table->json('leads_summary')->nullable();

            // ── Raw data ──────────────────────────────────────────────────
            $table->text('hl7_message')->nullable();
            $table->json('raw_parsed')->nullable();

            // ── Status ────────────────────────────────────────────────────
            $table->enum('status', ['received', 'parsed', 'reviewed', 'error'])
                  ->default('received')->index();
            $table->text('parse_error')->nullable();
            $table->text('doctor_notes')->nullable();
            $table->timestamp('reviewed_at')->nullable();
            $table->string('reviewed_by')->nullable();

            $table->softDeletes();
            $table->timestamps();

            // ── Indexes ───────────────────────────────────────────────────
            $table->index(['patient_id', 'recorded_at']);
            $table->index(['recording_date', 'status']);
            $table->index('heart_rate_bpm');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('ecg_records');
    }
};
