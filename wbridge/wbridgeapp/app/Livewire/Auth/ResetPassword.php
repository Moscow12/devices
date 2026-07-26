<?php

declare(strict_types=1);

namespace App\Livewire\Auth;

use App\Models\PasswordResetToken;
use App\Models\TrustedDevice;
use App\Models\User;
use App\Services\DeviceFingerprinter;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Hash;
use Illuminate\View\View;
use Livewire\Attributes\Validate;
use Livewire\Component;
use Psr\Container\ContainerExceptionInterface;
use Psr\Container\NotFoundExceptionInterface;

class ResetPassword extends Component
{
    public string $email = '';

    #[Validate('required|string|size:6')]
    public string $token = '';

    #[Validate('required|string|min:8|confirmed')]
    public string $password = '';

    public string $password_confirmation = '';

    public bool $showTokenForm = true;

    /**
     * @throws ContainerExceptionInterface
     * @throws NotFoundExceptionInterface
     */
    public function mount(): void
    {
        $this->email = request()->get('email', '');
    }

    public function render(): View
    {
        return view('livewire.auth.reset-password')
            ->layout('components.layouts.guest');
    }

    public function verifyToken(): void
    {
        $this->validate(['token' => 'required|string|size:6']);

        $resetToken = PasswordResetToken::findValidToken($this->email, $this->token);

        if (! $resetToken) {
            $this->addError('token', 'The reset code is invalid or has expired.');

            return;
        }

        $this->showTokenForm = false;
        $this->dispatch('toastMagic',
            status: 'success',
            title: 'Code Verified',
            message: 'Please enter your new password.'
        );
    }

    public function resetPassword(): mixed
    {
        if ($this->showTokenForm) {
            $this->verifyToken();

            return null;
        }

        $this->validate([
            'password' => 'required|string|min:8|confirmed',
        ]);

        $resetToken = PasswordResetToken::findValidToken($this->email, $this->token);

        if (! $resetToken) {
            $this->addError('token', 'The reset session has expired. Please request a new reset code.');

            return null;
        }

        $user = User::where('email', $this->email)->first();

        if (! $user) {
            $this->addError('email', 'User not found.');

            return null;
        }

        // Update password
        $user->update([
            'password' => Hash::make($this->password),
        ]);

        PasswordResetToken::query()->where('email', $this->email)->update(['used' => true]);

        // Invalidate other sessions for security
        Auth::logoutOtherDevices($this->password);

        // Regenerate session
        session()->regenerate();

        // Check device fingerprint
        $fingerprinter = new DeviceFingerprinter(request());
        $deviceFingerprint = $fingerprinter->generateFingerprint();

        // Check if this device is already trusted
        $trustedDevice = TrustedDevice::findValidDevice($user->id, $deviceFingerprint);

        if ($trustedDevice) {
            // Update last used for existing trusted device
            $trustedDevice->updateLastUsed();
        } else {
            // Create new trusted device (auto-trust after password reset)
            TrustedDevice::createForUser(
                userId: $user->id,
                deviceFingerprint: $deviceFingerprint,
                deviceName: $fingerprinter->generateDeviceName(),
                ipAddress: $fingerprinter->getCurrentIpAddress(),
                userAgent: request()->userAgent() ?? '',
                trustDays: 30
            );
        }

        // Log the user in
        Auth::login($user);

        $this->dispatch('toastMagic',
            status: 'success',
            title: 'Welcome Back!',
            message: 'Your password has been updated successfully. You are now logged in.'
        );

        return redirect()->route('dashboard');
    }
}
