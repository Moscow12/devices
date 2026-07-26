<?php

declare(strict_types=1);

namespace App\Livewire\Auth;

use App\Models\PasswordResetToken;
use App\Models\User;
use App\Notifications\ResetPasswordCode;
use Illuminate\View\View;
use Livewire\Component;
use Random\RandomException;

class ForgotPassword extends Component
{
    public string $email = '';

    protected array $rules = [
        'email' => 'required|email|exists:users,email',
    ];

    protected array $messages = [
        'email.exists' => 'We could not find a user with that email address.',
    ];

    public function render(): View
    {
        return view('livewire.auth.forgot-password')
            ->layout('components.layouts.guest');
    }

    /**
     * @throws RandomException
     */
    public function performPasswordReset(): mixed
    {
        $this->validate();

        $user = User::where('email', $this->email)->first();

        if (! $user) {
            $this->dispatch('toastMagic',
                status: 'error',
                title: 'User Not Found',
                message: 'We could not find a user with that email address.'
            );

            return null;
        }

        $resetToken = PasswordResetToken::createForEmail($this->email);

        $user->notify(new ResetPasswordCode($resetToken->token));

        $this->dispatch('toastMagic',
            status: 'success',
            title: 'Reset Code Sent',
            message: 'We have sent a reset code to your email address.'
        );

        return redirect()->route('reset-password', ['email' => $this->email]);
    }
}
