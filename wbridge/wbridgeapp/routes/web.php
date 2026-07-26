<?php

use Illuminate\Support\Facades\Route;

// Default route (protected by auth middleware)
Route::get('/', function () {
    return redirect()->route('dashboard');
})->middleware('auth');

// Dashboard
Route::get('/dashboard', function () {
    return view('dashboard');
})->name('dashboard')->middleware('auth');

// Authentication Routes
Route::group(['prefix' => 'auth'], function () {
    Route::get('login', \App\Livewire\Auth\Login::class)->name('login')->middleware('guest');
    Route::get('forgot-password', \App\Livewire\Auth\ForgotPassword::class)->name('forgot-password')->middleware('guest');
    Route::get('reset-password', \App\Livewire\Auth\ResetPassword::class)->name('reset-password')->middleware('guest');
    Route::get('2fa', \App\Livewire\Auth\TwoFactorsAuthentication::class)->name('2fa')->middleware('guest');
    Route::get('logout', \App\Livewire\Auth\Logout::class)->name('logout')->middleware('auth');
});
