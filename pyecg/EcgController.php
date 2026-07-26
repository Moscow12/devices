<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\EcgRecord;
use Illuminate\Http\Request;
use Illuminate\Http\JsonResponse;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Str;
use Carbon\Carbon;

class EcgController extends Controller
{
    // ══════════════════════════════════════════════════════════════════════════
    // POST /api/ecg/receive
    // Called by liscom_ecg.py when machine sends a file
    // ══════════════════════════════════════════════════════════════════════════

    public function receive(Request $request): JsonResponse
    {
        $data = $request->validate([
            'source'    => 'required|string',
            'device_no' => 'nullable|string',
            'filename'  => 'required|string',
            'timestamp' => 'required|string',
            'patient'   => 'nullable|array',
            'hl7'       => 'nullable|string',
            'leads'     => 'nullable|array',
            // Full parsed result from scp_parser.py (optional)
            'parsed'    => 'nullable|array',
        ]);

        try {
            $parsed   = $data['parsed']   ?? [];
            $patient  = $data['patient']  ?? $parsed['patient'] ?? [];
            $rec      = $parsed['recording']    ?? [];
            $meas     = $parsed['measurements'] ?? [];
            $diag     = $parsed['diagnosis']    ?? [];
            $interp   = $parsed['interpretation'] ?? [];
            $leads    = $parsed['leads']        ?? [];
            $fileInfo = $parsed['file']         ?? [];

            // ── Parse recorded_at datetime ────────────────────────────────
            $recordedAt = null;
            if ($rec['datetime'] ?? null) {
                try { $recordedAt = Carbon::parse($rec['datetime']); } catch (\Exception $e) {}
            }
            if (!$recordedAt) {
                try { $recordedAt = Carbon::parse($data['timestamp']); } catch (\Exception $e) {}
            }

            // ── Save HL7 to storage ───────────────────────────────────────
            $hl7Path = null;
            if (!empty($data['hl7'])) {
                $hl7Path = 'ecg/hl7/' . now()->format('Y/m/d') . '/' .
                           pathinfo($data['filename'], PATHINFO_FILENAME) . '.hl7';
                Storage::put($hl7Path, $data['hl7']);
            }

            // ── Create ECG record ─────────────────────────────────────────
            $record = EcgRecord::create([
                // File
                'filename'         => $data['filename'],
                'hl7_path'         => $hl7Path,
                'file_size_bytes'  => $fileInfo['size_bytes'] ?? null,
                'file_format'      => $fileInfo['format']     ?? 'SCP-ECG',
                'source_device'    => 'Edan SE-1200 Express',
                'device_no'        => $data['device_no']      ?? null,

                // Patient
                'patient_id'          => $patient['id']                 ?? null,
                'patient_name'        => $patient['name']               ?? null,
                'patient_first_name'  => $patient['first_name']         ?? null,
                'patient_last_name'   => $patient['last_name']          ?? null,
                'patient_dob'         => $patient['dob']                ?? null,
                'patient_age'         => $patient['age']                ?? null,
                'patient_sex'         => $patient['sex']                ?? null,
                'patient_weight'      => $patient['weight']             ?? null,
                'patient_height'      => $patient['height']             ?? null,
                'patient_room'        => $patient['room']               ?? null,
                'hospital'            => $patient['hospital']           ?? 'St. Joseph Hospital',
                'department'          => $patient['department']         ?? null,
                'referring_physician' => $patient['referring_physician'] ?? null,
                'diagnosis_doctor'    => $patient['diagnosis_doctor']   ?? null,
                'technician'          => $patient['technician']         ?? null,

                // Recording
                'recording_date'   => $rec['date']           ?? $recordedAt?->toDateString(),
                'recording_time'   => $rec['time']           ?? $recordedAt?->toTimeString(),
                'recorded_at'      => $recordedAt,
                'sample_rate_hz'   => $rec['sample_rate_hz'] ?? null,
                'num_leads'        => $rec['num_leads']      ?? 12,
                'duration_sec'     => $rec['duration_sec']   ?? null,

                // Measurements
                'heart_rate_bpm'          => $meas['heart_rate_bpm']          ?? null,
                'heart_rate_interp'       => $meas['heart_rate_interp']       ?? null,
                'p_duration_ms'           => $meas['p_duration_ms']           ?? null,
                'pr_interval_ms'          => $meas['pr_interval_ms']          ?? null,
                'qrs_duration_ms'         => $meas['qrs_duration_ms']         ?? null,
                'qt_interval_ms'          => $meas['qt_interval_ms']          ?? null,
                'qtc_interval_ms'         => $meas['qtc_interval_ms']         ?? null,
                'qtc_interpretation'      => $meas['qtc_interpretation']      ?? null,
                'p_axis_degrees'          => $meas['p_axis_degrees']          ?? null,
                'qrs_axis_degrees'        => $meas['qrs_axis_degrees']        ?? null,
                'qrs_axis_interpretation' => $meas['qrs_axis_interpretation'] ?? null,
                't_axis_degrees'          => $meas['t_axis_degrees']          ?? null,
                'atrial_rate_bpm'         => $meas['atrial_rate_bpm']         ?? null,

                // Diagnosis
                'auto_diagnosis'          => $diag['auto_diagnosis']      ?? null,
                'interpretation_findings' => $interp['findings']          ?? null,
                'interpretation_flags'    => $interp['flags']             ?? null,
                'is_normal'               => $interp['normal']            ?? null,
                'interpretation_summary'  => $interp['summary']          ?? null,
                'clinical_summary'        => $diag['clinical_summary']   ?? null,
                'free_text'               => $diag['free_text']          ?? null,

                // Leads & raw
                'leads_summary' => !empty($leads) ? $leads : (
                    !empty($data['leads']) ? collect($data['leads'])->map(fn($s, $l) => [
                        'name'    => $l,
                        'samples' => count($s),
                    ])->values()->all() : null
                ),
                'hl7_message'  => $data['hl7']   ?? null,
                'raw_parsed'   => !empty($parsed) ? $parsed : null,
                'status'       => 'parsed',
            ]);

            Log::info('ECG record saved', [
                'id'       => $record->id,
                'file'     => $record->filename,
                'patient'  => $record->patient_id,
                'hr'       => $record->heart_rate_bpm,
                'flags'    => $record->interpretation_flags,
            ]);

            return response()->json([
                'success' => true,
                'message' => 'ECG record received and stored successfully',
                'data'    => $this->formatRecord($record),
            ], 201);

        } catch (\Exception $e) {
            Log::error('ECG receive error', ['error' => $e->getMessage(), 'file' => $data['filename'] ?? '']);

            // Save with error status
            EcgRecord::create([
                'filename'    => $data['filename'] ?? 'unknown',
                'device_no'   => $data['device_no'] ?? null,
                'hl7_message' => $data['hl7']       ?? null,
                'status'      => 'error',
                'parse_error' => $e->getMessage(),
            ]);

            return response()->json([
                'success' => false,
                'message' => 'ECG received but failed to parse: ' . $e->getMessage(),
            ], 422);
        }
    }

    // ══════════════════════════════════════════════════════════════════════════
    // GET /api/ecg
    // List all ECG records with filters
    // ══════════════════════════════════════════════════════════════════════════

    public function index(Request $request): JsonResponse
    {
        $query = EcgRecord::query()->latest('recorded_at');

        // Filters
        if ($request->filled('patient_id')) {
            $query->forPatient($request->patient_id);
        }
        if ($request->filled('date')) {
            $query->whereDate('recording_date', $request->date);
        }
        if ($request->filled('date_from')) {
            $query->whereDate('recording_date', '>=', $request->date_from);
        }
        if ($request->filled('date_to')) {
            $query->whereDate('recording_date', '<=', $request->date_to);
        }
        if ($request->boolean('abnormal')) {
            $query->abnormal();
        }
        if ($request->boolean('flagged')) {
            $query->withFlags();
        }
        if ($request->boolean('unreviewed')) {
            $query->unreviewed();
        }
        if ($request->filled('status')) {
            $query->where('status', $request->status);
        }
        if ($request->boolean('today')) {
            $query->today();
        }

        $records = $query->paginate($request->integer('per_page', 20));

        return response()->json([
            'success' => true,
            'data'    => $records->through(fn($r) => $this->formatRecordList($r)),
            'summary' => $this->buildSummary(),
        ]);
    }

    // ══════════════════════════════════════════════════════════════════════════
    // GET /api/ecg/{id}
    // Full detail of one ECG record
    // ══════════════════════════════════════════════════════════════════════════

    public function show(string $id): JsonResponse
    {
        $record = EcgRecord::findOrFail($id);

        return response()->json([
            'success' => true,
            'data'    => $this->formatRecord($record),
        ]);
    }

    // ══════════════════════════════════════════════════════════════════════════
    // GET /api/ecg/{id}/log
    // Human-readable text log of ECG record
    // ══════════════════════════════════════════════════════════════════════════

    public function log(string $id): JsonResponse
    {
        $r = EcgRecord::findOrFail($id);

        $lines = [
            str_repeat('=', 65),
            "  ECG REPORT  —  {$r->filename}",
            "  Record ID  : {$r->id}",
            "  Parsed at  : {$r->created_at}",
            str_repeat('=', 65),
            "",
            "── RECORDING ──────────────────────────────────────────────",
            "  Date/Time  : " . ($r->recorded_at?->format('Y-m-d H:i:s') ?? 'N/A'),
            "  Device     : {$r->source_device}",
            "  Device No  : " . ($r->device_no ?? 'N/A'),
            "  Sample Rate: " . ($r->sample_rate_hz ? "{$r->sample_rate_hz} Hz" : 'N/A'),
            "  Leads      : {$r->num_leads}",
            "  Duration   : " . ($r->formatted_duration),
            "  File Size  : " . ($r->file_size_bytes ? number_format($r->file_size_bytes) . ' bytes' : 'N/A'),
            "",
            "── PATIENT ────────────────────────────────────────────────",
            "  ID         : " . ($r->patient_id    ?? 'N/A'),
            "  Name       : " . ($r->patient_name  ?? 'N/A'),
            "  DOB        : " . ($r->patient_dob?->format('Y-m-d') ?? 'N/A'),
            "  Age        : " . ($r->patient_age   ?? 'N/A'),
            "  Sex        : " . ($r->patient_sex   ?? 'N/A'),
            "  Weight     : " . ($r->patient_weight ?? 'N/A'),
            "  Height     : " . ($r->patient_height ?? 'N/A'),
            "  Room       : " . ($r->patient_room  ?? 'N/A'),
            "  Hospital   : " . ($r->hospital      ?? 'N/A'),
            "  Department : " . ($r->department    ?? 'N/A'),
            "  Ref. Doctor: " . ($r->referring_physician ?? 'N/A'),
            "  Diag Doctor: " . ($r->diagnosis_doctor    ?? 'N/A'),
            "  Technician : " . ($r->technician    ?? 'N/A'),
            "",
            "── MEASUREMENTS ───────────────────────────────────────────",
            "  Heart Rate  : " . ($r->heart_rate_bpm  ? "{$r->heart_rate_bpm} bpm [{$r->heart_rate_interp}]" : 'N/A'),
            "  Atrial Rate : " . ($r->atrial_rate_bpm ? "{$r->atrial_rate_bpm} bpm" : 'N/A'),
            "  PR Interval : " . ($r->pr_interval_ms  ? "{$r->pr_interval_ms} ms"  : 'N/A'),
            "  QRS Duration: " . ($r->qrs_duration_ms ? "{$r->qrs_duration_ms} ms" : 'N/A'),
            "  QT Interval : " . ($r->qt_interval_ms  ? "{$r->qt_interval_ms} ms"  : 'N/A'),
            "  QTc Interval: " . ($r->qtc_interval_ms ? "{$r->qtc_interval_ms} ms [{$r->qtc_interpretation}]" : 'N/A'),
            "  P  Axis     : " . ($r->p_axis_degrees   !== null ? "{$r->p_axis_degrees}°"   : 'N/A'),
            "  QRS Axis    : " . ($r->qrs_axis_degrees !== null ? "{$r->qrs_axis_degrees}° [{$r->qrs_axis_interpretation}]" : 'N/A'),
            "  T  Axis     : " . ($r->t_axis_degrees   !== null ? "{$r->t_axis_degrees}°"   : 'N/A'),
            "",
            "── INTERPRETATION ─────────────────────────────────────────",
        ];

        foreach ($r->interpretation_findings ?? [] as $finding) {
            $lines[] = "  • {$finding}";
        }

        $flags = $r->interpretation_flags ?? [];
        if ($flags) {
            $lines[] = "";
            $lines[] = "  ⚠  FLAGS:";
            foreach ($flags as $flag) {
                $lines[] = "    ⚠  {$flag}";
            }
        }

        $lines[] = "";
        $lines[] = "── AUTO DIAGNOSIS ─────────────────────────────────────────";
        foreach ($r->auto_diagnosis ?? ['N/A'] as $d) {
            $lines[] = "  → {$d}";
        }

        if ($r->clinical_summary) {
            $lines[] = "";
            $lines[] = "── CLINICAL SUMMARY ───────────────────────────────────────";
            $lines[] = "  {$r->clinical_summary}";
        }

        if ($r->doctor_notes) {
            $lines[] = "";
            $lines[] = "── DOCTOR NOTES ───────────────────────────────────────────";
            $lines[] = "  {$r->doctor_notes}";
        }

        $lines[] = "";
        $lines[] = "── LEADS ──────────────────────────────────────────────────";
        foreach ($r->leads_summary ?? [] as $lead) {
            $name    = $lead['name']    ?? 'N/A';
            $samples = $lead['num_samples'] ?? $lead['samples'] ?? 0;
            $dur     = isset($lead['duration_ms']) ? "  ({$lead['duration_ms']} ms)" : '';
            $lines[] = sprintf("  %-6s: %6d samples%s", $name, $samples, $dur);
        }

        $lines[] = "";
        $lines[] = "── STATUS ─────────────────────────────────────────────────";
        $lines[] = "  Status      : " . strtoupper($r->status);
        $lines[] = "  Severity    : " . strtoupper($r->severity);
        $lines[] = "  Reviewed    : " . ($r->reviewed_at ? $r->reviewed_at->format('Y-m-d H:i:s') . " by {$r->reviewed_by}" : 'Not reviewed');
        $lines[] = "";
        $lines[] = str_repeat('=', 65);

        return response()->json([
            'success'   => true,
            'record_id' => $r->id,
            'filename'  => $r->filename,
            'log'       => implode("\n", $lines),
            'lines'     => $lines,
        ]);
    }

    // ══════════════════════════════════════════════════════════════════════════
    // GET /api/ecg/{id}/hl7
    // Return raw HL7 message
    // ══════════════════════════════════════════════════════════════════════════

    public function hl7(string $id): JsonResponse
    {
        $record = EcgRecord::findOrFail($id);

        return response()->json([
            'success'  => true,
            'hl7'      => $record->hl7_message,
            'filename' => $record->filename,
        ]);
    }

    // ══════════════════════════════════════════════════════════════════════════
    // PATCH /api/ecg/{id}/review
    // Doctor adds notes / marks as reviewed
    // ══════════════════════════════════════════════════════════════════════════

    public function review(Request $request, string $id): JsonResponse
    {
        $data   = $request->validate([
            'notes'       => 'nullable|string',
            'reviewed_by' => 'required|string',
        ]);

        $record = EcgRecord::findOrFail($id);
        $record->update([
            'doctor_notes' => $data['notes']       ?? $record->doctor_notes,
            'reviewed_by'  => $data['reviewed_by'],
            'reviewed_at'  => now(),
            'status'       => 'reviewed',
        ]);

        return response()->json([
            'success' => true,
            'message' => 'ECG record reviewed',
            'data'    => $this->formatRecord($record->fresh()),
        ]);
    }

    // ══════════════════════════════════════════════════════════════════════════
    // Formatters
    // ══════════════════════════════════════════════════════════════════════════

    private function formatRecord(EcgRecord $r): array
    {
        return [
            'id'       => $r->id,
            'status'   => $r->status,
            'severity' => $r->severity,

            'file' => [
                'name'        => $r->filename,
                'format'      => $r->file_format,
                'size_bytes'  => $r->file_size_bytes,
                'device'      => $r->source_device,
                'device_no'   => $r->device_no,
            ],

            'patient' => [
                'id'                  => $r->patient_id,
                'name'                => $r->patient_name,
                'first_name'          => $r->patient_first_name,
                'last_name'           => $r->patient_last_name,
                'dob'                 => $r->patient_dob?->toDateString(),
                'age'                 => $r->patient_age,
                'sex'                 => $r->patient_sex,
                'weight'              => $r->patient_weight,
                'height'              => $r->patient_height,
                'room'                => $r->patient_room,
                'hospital'            => $r->hospital,
                'department'          => $r->department,
                'referring_physician' => $r->referring_physician,
                'diagnosis_doctor'    => $r->diagnosis_doctor,
                'technician'          => $r->technician,
            ],

            'recording' => [
                'date'            => $r->recording_date?->toDateString(),
                'time'            => $r->recording_time,
                'datetime'        => $r->recorded_at?->toIso8601String(),
                'sample_rate_hz'  => $r->sample_rate_hz,
                'num_leads'       => $r->num_leads,
                'duration_sec'    => $r->duration_sec,
                'duration_format' => $r->formatted_duration,
            ],

            'measurements' => [
                'heart_rate' => [
                    'value'  => $r->heart_rate_bpm,
                    'unit'   => 'bpm',
                    'interp' => $r->heart_rate_interp,
                ],
                'atrial_rate' => [
                    'value' => $r->atrial_rate_bpm,
                    'unit'  => 'bpm',
                ],
                'intervals' => [
                    'pr_ms'  => $r->pr_interval_ms,
                    'qrs_ms' => $r->qrs_duration_ms,
                    'qt_ms'  => $r->qt_interval_ms,
                    'qtc_ms' => $r->qtc_interval_ms,
                    'qtc_interpretation' => $r->qtc_interpretation,
                    'p_duration_ms' => $r->p_duration_ms,
                ],
                'axes' => [
                    'p_degrees'   => $r->p_axis_degrees,
                    'qrs_degrees' => $r->qrs_axis_degrees,
                    'qrs_interp'  => $r->qrs_axis_interpretation,
                    't_degrees'   => $r->t_axis_degrees,
                ],
            ],

            'interpretation' => [
                'is_normal' => $r->is_normal,
                'summary'   => $r->interpretation_summary,
                'findings'  => $r->interpretation_findings ?? [],
                'flags'     => $r->interpretation_flags   ?? [],
                'has_flags' => $r->has_abnormal_flags,
            ],

            'diagnosis' => [
                'auto'             => $r->auto_diagnosis ?? [],
                'clinical_summary' => $r->clinical_summary,
                'free_text'        => $r->free_text,
                'doctor_notes'     => $r->doctor_notes,
            ],

            'leads'    => $r->leads_summary ?? [],
            'hl7_path' => $r->hl7_path,

            'review' => [
                'reviewed_at' => $r->reviewed_at?->toIso8601String(),
                'reviewed_by' => $r->reviewed_by,
            ],

            'created_at' => $r->created_at->toIso8601String(),
            'updated_at' => $r->updated_at->toIso8601String(),
        ];
    }

    private function formatRecordList(EcgRecord $r): array
    {
        return [
            'id'          => $r->id,
            'filename'    => $r->filename,
            'status'      => $r->status,
            'severity'    => $r->severity,
            'patient'     => [
                'id'   => $r->patient_id,
                'name' => $r->patient_name,
                'age'  => $r->patient_age,
                'sex'  => $r->patient_sex,
            ],
            'recorded_at'    => $r->recorded_at?->toIso8601String(),
            'heart_rate_bpm' => $r->heart_rate_bpm,
            'heart_rate_interp' => $r->heart_rate_interp,
            'is_normal'      => $r->is_normal,
            'has_flags'      => $r->has_abnormal_flags,
            'diagnosis'      => $r->auto_diagnosis ?? [],
            'num_leads'      => $r->num_leads,
            'duration_sec'   => $r->duration_sec,
        ];
    }

    private function buildSummary(): array
    {
        return [
            'total'       => EcgRecord::count(),
            'today'       => EcgRecord::today()->count(),
            'unreviewed'  => EcgRecord::unreviewed()->count(),
            'flagged'     => EcgRecord::withFlags()->count(),
            'abnormal'    => EcgRecord::abnormal()->count(),
        ];
    }
}
