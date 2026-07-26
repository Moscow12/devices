<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\SoftDeletes;
use Illuminate\Database\Eloquent\Concerns\HasUuids;

class EcgRecord extends Model
{
    use HasUuids, SoftDeletes;

    protected $table = 'ecg_records';

    protected $fillable = [
        'filename', 'file_path', 'hl7_path', 'file_size_bytes',
        'file_format', 'source_device', 'device_no',
        'patient_id', 'patient_name', 'patient_first_name',
        'patient_last_name', 'patient_dob', 'patient_age',
        'patient_sex', 'patient_weight', 'patient_height',
        'patient_room', 'hospital', 'department',
        'referring_physician', 'diagnosis_doctor', 'technician',
        'recording_date', 'recording_time', 'recorded_at',
        'sample_rate_hz', 'num_leads', 'duration_sec',
        'heart_rate_bpm', 'heart_rate_interp',
        'p_duration_ms', 'pr_interval_ms', 'qrs_duration_ms',
        'qt_interval_ms', 'qtc_interval_ms', 'qtc_interpretation',
        'p_axis_degrees', 'qrs_axis_degrees', 'qrs_axis_interpretation',
        't_axis_degrees', 'atrial_rate_bpm',
        'auto_diagnosis', 'interpretation_findings',
        'interpretation_flags', 'is_normal', 'interpretation_summary',
        'clinical_summary', 'free_text', 'leads_summary',
        'hl7_message', 'raw_parsed',
        'status', 'parse_error', 'doctor_notes',
        'reviewed_at', 'reviewed_by',
    ];

    protected $casts = [
        'auto_diagnosis'          => 'array',
        'interpretation_findings' => 'array',
        'interpretation_flags'    => 'array',
        'leads_summary'           => 'array',
        'raw_parsed'              => 'array',
        'is_normal'               => 'boolean',
        'recording_date'          => 'date',
        'recorded_at'             => 'datetime',
        'reviewed_at'             => 'datetime',
        'patient_dob'             => 'date',
    ];

    // ── Scopes ────────────────────────────────────────────────────────────────

    public function scopeForPatient($query, string $patientId)
    {
        return $query->where('patient_id', $patientId);
    }

    public function scopeAbnormal($query)
    {
        return $query->where('is_normal', false);
    }

    public function scopeUnreviewed($query)
    {
        return $query->where('status', 'parsed')->whereNull('reviewed_at');
    }

    public function scopeToday($query)
    {
        return $query->whereDate('recording_date', today());
    }

    public function scopeWithFlags($query)
    {
        return $query->whereJsonLength('interpretation_flags', '>', 0);
    }

    // ── Accessors ─────────────────────────────────────────────────────────────

    public function getHasAbnormalFlagsAttribute(): bool
    {
        return !empty($this->interpretation_flags);
    }

    public function getSeverityAttribute(): string
    {
        $flags = $this->interpretation_flags ?? [];
        foreach ($flags as $flag) {
            if (str_contains(strtoupper($flag), 'CRITICAL')) return 'critical';
        }
        if (!empty($flags)) return 'warning';
        return $this->is_normal ? 'normal' : 'review';
    }

    public function getFormattedDurationAttribute(): string
    {
        if (!$this->duration_sec) return 'N/A';
        $m = floor($this->duration_sec / 60);
        $s = $this->duration_sec % 60;
        return $m > 0 ? "{$m}m {$s}s" : "{$s}s";
    }
}
