<?php

namespace App\Livewire\Auth;

use App\Models\LoginActivity;
use App\Models\TrustedDevice;
use App\Models\User;
use App\Models\workstations;
use App\Services\DeviceFingerprinter;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Hash;
use Illuminate\Validation\ValidationException;
use Illuminate\View\View;
use Jenssegers\Agent\Agent;
use Livewire\Attributes\Validate;
use Livewire\Component;

class Login extends Component
{
    #[Validate('required')]
    public string $login = ''; // email | phone_number | username

    #[Validate('required')]
    public string $password = '';

    /**
     * @throws ValidationException
     */
    public function loginUser(): mixed
    {

        $this->validate();

        // Find the user by email, username, or phone
        $user = User::query()
            ->where('email', $this->login)
            ->orWhere('username', $this->login)
            ->orWhere('phone_number', $this->login)
            ->first();

        if (! $user || ! Hash::check($this->password, $user->password)) {
            throw ValidationException::withMessages([
                'login' => __('The provided credentials are incorrect.'),
            ]);
        }

        session()->regenerate();

        // Check if this device is trusted
        $fingerprinter = new DeviceFingerprinter(request());

        $deviceFingerprint = $fingerprinter->generateFingerprint();

        $trustedDevice = TrustedDevice::findValidDevice($user->id, $deviceFingerprint);

        // $agent = new Agent;
        // LoginActivity::create([
        //     'user_id' => $user->id,
        //     'ip_address' => request()->ip(),
        //     'user_agent' => request()->userAgent(),
        //     'platform' => $agent->platform(),
        //     'browser' => $agent->browser(),
        //     'device' => $agent->device(),
        //     'login_at' => now(),
        // ]);

        // Check if 2FA is enabled in config
        $twoFactorEnabled = config('auth.two_factor_enabled', true);

        if ($trustedDevice) {
            // Device is trusted - skip 2FA and log in directly
            $trustedDevice->updateLastUsed();
            Auth::login($user);

            $this->dispatch('toastMagic',
                status: 'success',
                title: 'Welcome Back',
                message: 'Logged in from trusted device'
            );

            return redirect()->route('dashboard');
        }

        // If 2FA is disabled, log in directly without verification
        if (! $twoFactorEnabled) {
            Auth::login($user);

            $this->dispatch('toastMagic',
                status: 'success',
                title: 'Welcome Back',
                message: 'Login successful'
            );

            return redirect()->route('dashboard');
        }

        // Device is not trusted and 2FA is enabled - enforce 2FA
        // Store device details in session for potential saving after 2FA
        session([
            '2fa_user_email' => $user->email,
            '2fa_device_fingerprint' => $deviceFingerprint,
            '2fa_device_name' => $fingerprinter->generateDeviceName(),
            '2fa_device_ip' => $fingerprinter->getCurrentIpAddress(),
            '2fa_device_user_agent' => request()->userAgent() ?? '',
        ]);

        $this->dispatch('toastMagic',
            status: 'success',
            title: 'Credentials Verified',
            message: 'Please check your email for the verification code'
        );

        return redirect()->route('2fa');
    }

    public function render(): View
    {
        $workstation = workstations::first();
        $twoFactorEnabled = config('auth.two_factor_enabled', true);

        return view('livewire.auth.login', [
            'workstation' => $workstation,
            'twoFactorEnabled' => $twoFactorEnabled,
            'appName' => config('app.name', 'Dasher'),
        ])->layout('components.layouts.guest');
    }
}
