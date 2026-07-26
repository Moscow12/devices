<?php
// ── Add to routes/api.php ─────────────────────────────────────────────────────

use App\Http\Controllers\Api\EcgController;

Route::prefix('ecg')->group(function () {
    Route::post   ('/receive',     [EcgController::class, 'receive']);  // machine → liscom → here
    Route::get    ('/',            [EcgController::class, 'index']);    // list all
    Route::get    ('/{id}',        [EcgController::class, 'show']);     // full detail
    Route::get    ('/{id}/log',    [EcgController::class, 'log']);      // text log
    Route::get    ('/{id}/hl7',    [EcgController::class, 'hl7']);      // raw HL7
    Route::patch  ('/{id}/review', [EcgController::class, 'review']);   // doctor review
});
