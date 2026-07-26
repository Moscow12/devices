<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Random\RandomException;

class TwoFactorToken extends Model
{
    protected $fillable = [
        'email',
        'token',
        'expires_at',
        'used',
    ];

    protected function casts(): array
    {
        return [
            'expires_at' => 'datetime',
            'used' => 'boolean',
        ];
    }

    /**
     * @throws RandomException
     */
    public static function createForEmail(string $email): self
    {
        self::where('email', $email)->delete();

        return self::create([
            'email' => $email,
            'token' => str_pad(random_int(0, 999999), 6, '0', STR_PAD_LEFT),
            'expires_at' => now()->addMinutes(10),
            'used' => false,
        ]);
    }

    public function isExpired(): bool
    {
        return now()->isAfter($this->expires_at);
    }

    public function isUsed(): bool
    {
        return $this->used;
    }

    public function markAsUsed(): bool
    {
        $result = self::where('email', $this->email)
            ->where('token', $this->token)
            ->update([
                'used' => true,
                'updated_at' => now(),
            ]);

        if ($result > 0) {
            $this->used = true;

            return true;
        }

        return false;
    }

    public static function findValidToken(string $email, string $token): ?self
    {
        return self::where('email', $email)
            ->where('token', $token)
            ->where('used', false)
            ->where('expires_at', '>', now())
            ->first();
    }
}
