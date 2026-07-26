<?php

declare(strict_types=1);

namespace App\Livewire\Auth;

use App\Models\TrustedDevice;
use App\Models\TwoFactorToken;
use App\Models\User;
use App\Models\workstations;
use App\Notifications\TwoFactorCode;
use App\Services\DeviceFingerprinter;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Session;
use Illuminate\View\View;
use Livewire\Attributes\Validate;
use Livewire\Component;
use Random\RandomException;

class TwoFactorsAuthentication extends Component
{
    #[Validate('required|string|size:6|regex:/^[0-9]+$/')]
    public string $token = '';

    public bool $remember_device = false;

    public string $email = '';

    public string $maskedEmail = '';

    /**
     * @throws RandomException
     */
    public function mount(): void
    {
        $this->email = Session::get('2fa_user_email', '');

        if (! $this->email) {
            redirect()->route('login');

            return;
        }

        $this->maskedEmail = $this->maskEmail($this->email);

        // Send 2FA token automatically on mount
        $this->sendTwoFactorCode();
    }

    public function render(): View
    {
        $workstation = workstations::first();

        return view('livewire.auth.two-factors-authentication', [
            'workstation' => $workstation,
            'appName' => config('app.name', 'Dasher'),
        ])->layout('components.layouts.guest');
    }

    public function verifyTwoFactor(): mixed
    {
        sleep(1); // Prevent rapid resends
        $this->validate();

        $user = User::where('email', $this->email)->first();

        if (! $user) {
            $this->addError('token', 'Invalid authentication attempt.');

            return null;
        }

        $tokenRecord = TwoFactorToken::findValidToken($this->email, $this->token);

        if (! $tokenRecord) {
            $this->addError('token', 'Invalid or expired code. Please request a new one.');

            return null;
        }

        // Mark token as used
        $tokenRecord->markAsUsed();

        // Save device as trusted if user opted in
        if ($this->remember_device) {
            $this->saveDeviceAsTrusted($user);
        }

        // Log the user in
        Auth::login($user, $this->remember_device);

        // Clear 2FA session data
        Session::forget([
            '2fa_user_email',
            '2fa_device_fingerprint',
            '2fa_device_name',
            '2fa_device_ip',
            '2fa_device_user_agent',
        ]);

        // Redirect to intended page or dashboard
        return redirect()->route('dashboard');
    }

    /**
     * @throws RandomException
     */
    public function resendCode(): void
    {
        sleep(1); // Prevent rapid resends
        $this->sendTwoFactorCode();

        $this->dispatch('toastMagic',
            status: 'success',
            title: 'Verification Code Sent',
            message: 'A new verification code has been sent to your email.'
        );

    }

    /**
     * @throws RandomException
     */
    private function sendTwoFactorCode(): void
    {
        $user = User::where('email', $this->email)->first();

        if ($user) {
            $tokenRecord = TwoFactorToken::createForEmail($this->email);
            $user->notify(new TwoFactorCode($tokenRecord->token));
        }
    }

    private function saveDeviceAsTrusted(User $user): void
    {
        // Get device details from session (stored during login)
        $deviceFingerprint = Session::get('2fa_device_fingerprint');
        $deviceName = Session::get('2fa_device_name');
        $ipAddress = Session::get('2fa_device_ip');
        $userAgent = Session::get('2fa_device_user_agent');

        // Fallback to current request if session data is missing
        if (! $deviceFingerprint) {
            $fingerprinter = new DeviceFingerprinter(request());
            $deviceFingerprint = $fingerprinter->generateFingerprint();
            $deviceName = $fingerprinter->generateDeviceName();
            $ipAddress = $fingerprinter->getCurrentIpAddress();
            $userAgent = request()->userAgent() ?? '';
        }

        // Check if device already exists and just needs reactivation
        $existingDevice = TrustedDevice::where('user_id', $user->id)
            ->where('device_fingerprint', $deviceFingerprint)
            ->first();

        if ($existingDevice) {
            $existingDevice->update([
                'is_active' => true,
                'expires_at' => now()->addDays(30),
                'last_used_at' => now(),
                'ip_address' => $ipAddress,
                'user_agent' => $userAgent,
            ]);
        } else {
            TrustedDevice::createForUser(
                userId: $user->id,
                deviceFingerprint: $deviceFingerprint,
                deviceName: $deviceName,
                ipAddress: $ipAddress,
                userAgent: $userAgent,
                trustDays: 30
            );
        }
    }

    private function maskEmail(string $email): string
    {
        $parts = explode('@', $email);
        $username = $parts[0];
        $domain = $parts[1];

        if (strlen($username) <= 3) {
            $maskedUsername = str_repeat('*', strlen($username));
        } else {
            $maskedUsername = substr($username, 0, 3).str_repeat('*', strlen($username) - 3);
        }

        return $maskedUsername.'@'.$domain;
    }
}
